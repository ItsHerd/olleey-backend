"""Dashboard router for user overview and statistics."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List, Optional
import json

from schemas.dashboard import DashboardResponse, YouTubeConnectionSummary, ProcessingJobSummary, ProjectSummary, CreditSummary, WeeklyStats, ActivityFeedItem
from middleware.auth import get_current_user
from services.supabase_db import supabase_service
from firebase_admin import auth
from datetime import timedelta

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(
    current_user: dict = Depends(get_current_user),
    project_id: Optional[str] = None
):
    """
    Get dashboard statistics (jobs, videos, channels counts).
    """
    user_id = current_user["user_id"]

    # Get job counts
    jobs_data, total_jobs = supabase_service.list_processing_jobs(user_id, project_id=project_id, limit=100)
    active_jobs = sum(1 for job in jobs_data if job.get('status') in ['pending', 'downloading', 'processing', 'uploading', 'waiting_approval'])
    completed_jobs = sum(1 for job in jobs_data if job.get('status') == 'completed')

    # Get channel counts
    language_channels = supabase_service.get_language_channels(user_id, project_id=project_id)

    # Calculate weekly stats
    from datetime import timedelta
    now = datetime.utcnow()
    one_week_ago = now - timedelta(days=7)
    videos_completed_this_week = 0

    for job in jobs_data:
        if job.get('status') == 'completed':
            comp_at = job.get('completed_at', job.get('updated_at'))
            if comp_at:
                if hasattr(comp_at, 'timestamp'):
                    comp_at_dt = datetime.fromtimestamp(comp_at.timestamp())
                else:
                    comp_at_dt = comp_at

                if isinstance(comp_at_dt, datetime) and comp_at_dt > one_week_ago:
                    videos_completed_this_week += 1

    return {
        "total_jobs": total_jobs,
        "active_jobs": active_jobs,
        "completed_jobs": completed_jobs,
        "total_language_channels": len(language_channels),
        "weekly_stats": {
            "videos_completed": videos_completed_this_week,
            "languages_added": len(language_channels),
            "growth_percentage": 15.5 if completed_jobs > 0 else 0.0
        },
        "credits": {
            "used": completed_jobs * 10,
            "limit": 1000,
            "reset_date": (now + timedelta(days=30)).isoformat()
        }
    }


@router.get("/jobs")
async def get_dashboard_jobs(
    current_user: dict = Depends(get_current_user),
    project_id: Optional[str] = None,
    limit: int = 20
):
    """
    Get recent processing jobs for dashboard.
    """
    user_id = current_user["user_id"]
    jobs_data, total = supabase_service.list_processing_jobs(user_id, project_id=project_id, limit=limit)

    return {
        "jobs": jobs_data,
        "total": total
    }


@router.get("/channels")
async def get_dashboard_channels(
    current_user: dict = Depends(get_current_user),
    project_id: Optional[str] = None
):
    """
    Get language channels for dashboard.
    """
    user_id = current_user["user_id"]
    channels = supabase_service.get_language_channels(user_id, project_id=project_id)

    return {
        "channels": channels,
        "total": len(channels)
    }


@router.get("/projects")
async def get_dashboard_projects(
    current_user: dict = Depends(get_current_user)
):
    """
    Get projects for dashboard.
    """
    user_id = current_user["user_id"]
    projects = supabase_service.list_projects(user_id)

    return {
        "projects": projects,
        "total": len(projects)
    }


@router.get("/connections")
async def get_dashboard_connections(
    current_user: dict = Depends(get_current_user)
):
    """
    Get YouTube connections for dashboard.
    """
    user_id = current_user["user_id"]
    connections = supabase_service.get_youtube_connections(user_id)
    subscriptions = supabase_service.list_subscriptions(user_id=user_id, limit=1000)

    def parse_dt(raw):
        if not raw:
            return None
        if isinstance(raw, datetime):
            return raw
        if isinstance(raw, str):
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except Exception:
                return None
        return None

    # Keep the newest subscription per channel (by expires_at, then updated_at).
    subs_by_channel = {}
    for sub in subscriptions:
        channel_id = sub.get("channel_id")
        if not channel_id:
            continue

        current = subs_by_channel.get(channel_id)
        candidate_ts = parse_dt(sub.get("expires_at")) or parse_dt(sub.get("updated_at")) or datetime.min
        current_ts = (
            parse_dt(current.get("expires_at")) or parse_dt(current.get("updated_at")) or datetime.min
            if current else datetime.min
        )
        if not current or candidate_ts >= current_ts:
            subs_by_channel[channel_id] = sub

    now = datetime.utcnow()
    enriched_connections = []
    for conn in connections:
        connection = dict(conn)
        channel_id = connection.get("youtube_channel_id") or connection.get("channel_id")
        sub = subs_by_channel.get(channel_id) if channel_id else None

        if sub:
            expires_at_raw = sub.get("expires_at")
            expires_at = parse_dt(expires_at_raw)
            webhook_expired = bool(expires_at and expires_at.replace(tzinfo=None) < now)
            connection["webhook_subscription_id"] = sub.get("id")
            connection["webhook_expires_at"] = expires_at_raw
            connection["webhook_expired"] = webhook_expired
            connection["webhook_subscription_status"] = (
                "expired" if webhook_expired else (sub.get("status") or "active")
            )
        else:
            connection["webhook_subscription_id"] = None
            connection["webhook_expires_at"] = None
            connection["webhook_expired"] = False
            connection["webhook_subscription_status"] = "missing"

        enriched_connections.append(connection)

    return {
        "connections": enriched_connections,
        "total": len(enriched_connections),
        "has_connection": len(enriched_connections) > 0
    }


@router.get("/activity")
async def get_activity_feed(
    current_user: dict = Depends(get_current_user),
    limit: int = 20,
    project_id: Optional[str] = None
):
    """
    Get global activity feed for the current user across all projects.
    Returns data in frontend-compatible format with message, time, icon, color.
    """
    user_id = current_user["user_id"]
    logs = supabase_service.list_activity_logs(user_id=user_id, project_id=project_id, limit=limit)
    
    # Map status to icon
    def get_icon_for_action(action: str, status: str) -> str:
        action_lower = action.lower()
        if 'upload' in action_lower:
            return 'upload'
        elif 'complet' in action_lower or 'success' in action_lower:
            return 'check'
        elif 'start' in action_lower or 'creat' in action_lower:
            return 'plus'
        elif 'publish' in action_lower or 'youtube' in action_lower:
            return 'youtube'
        elif 'error' in action_lower or 'fail' in action_lower:
            return 'alert'
        else:
            return 'zap'
    
    # Format relative time
    def get_relative_time(timestamp) -> str:
        if hasattr(timestamp, 'timestamp'):
            dt = datetime.fromtimestamp(timestamp.timestamp())
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return 'Just now'
        
        now = datetime.utcnow()
        diff = now - dt
        
        if diff.total_seconds() < 60:
            return 'Just now'
        elif diff.total_seconds() < 3600:
            mins = int(diff.total_seconds() / 60)
            return f'{mins}m ago'
        elif diff.total_seconds() < 86400:
            hours = int(diff.total_seconds() / 3600)
            return f'{hours}h ago'
        else:
            days = int(diff.total_seconds() / 86400)
            return f'{days}d ago'
    
    activity_items = []
    for log in logs:
        action = log.get('action', 'Unknown Action')
        details = log.get('details', '')
        status = log.get('status', 'info')
        timestamp = log.get('timestamp')
        
        # Create message from action and details
        message = f"{action}: {details}" if details else action
        
        activity_items.append({
            'id': log.get('id', 'unknown'),
            'message': message,
            'time': get_relative_time(timestamp),
            'timestamp': timestamp.isoformat() if hasattr(timestamp, 'isoformat') else str(timestamp),
            'icon': get_icon_for_action(action, status),
            'color': 'green' if status == 'success' else 'yellow' if status == 'warning' else 'red' if status == 'error' else 'blue',
            'type': status
        })
        
    return activity_items


@router.get(
    "",
    response_model=DashboardResponse,
    responses={
        200: {
            "description": "Dashboard data retrieved successfully",
        },
        401: {
            "description": "Unauthorized - Invalid or missing token",
            "content": {
                "application/json": {
                    "example": {"detail": "Not authenticated"}
                }
            }
        }
    }
)
async def get_dashboard(
    current_user: dict = Depends(get_current_user),
    project_id: Optional[str] = None
):
    """
    Get dashboard data for the current user, optionally filtered by project.
    """
    user_id = current_user["user_id"]

    print(f"[DASHBOARD] Getting dashboard for user_id={user_id}, project_id={project_id}")
    
    # Defaults
    now = datetime.utcnow()
    one_week_ago = now - timedelta(days=7)
    
    try:
        # User info from current_user (Supabase)
        email = current_user.get("email")
        name = current_user.get("name") or email.split("@")[0]
        claims = current_user.get("claims", {})
        
        # Extract metadata from claims
        created_at_raw = claims.get("created_at")
        if created_at_raw:
            try:
                # Supabase uses ISO format for created_at in JWT
                created_at = datetime.fromisoformat(created_at_raw.replace('Z', '+00:00'))
            except:
                created_at = now
        else:
            # Fallback to iat (issued at) if created_at not present
            iat = claims.get("iat")
            created_at = datetime.fromtimestamp(iat) if iat else now
            
        auth_provider = "email"
        # Supabase stores provider info in app_metadata
        app_metadata = claims.get("app_metadata", {})
        provider = app_metadata.get("provider")
        if provider == "google":
            auth_provider = "google"
            
        # 1. YouTube Connections
        youtube_connections: List[YouTubeConnectionSummary] = []
        try:
            youtube_connections_data = supabase_service.get_youtube_connections(user_id)
            for conn in youtube_connections_data:
                # Handle potential string timestamps from Supabase
                connected_at_raw = conn.get('created_at', now)
                if isinstance(connected_at_raw, str):
                    try:
                        connected_at = datetime.fromisoformat(connected_at_raw.replace('Z', '+00:00'))
                    except:
                        connected_at = now
                else:
                    connected_at = connected_at_raw

                youtube_connections.append(
                    YouTubeConnectionSummary(
                        connection_id=conn.get('connection_id', ''),
                        youtube_channel_id=conn.get('youtube_channel_id', ''),
                        youtube_channel_name=conn.get('youtube_channel_name'),
                        is_primary=conn.get('is_primary', False),
                        connected_at=connected_at,
                    )
                )
        except Exception as e:
            print("[DASHBOARD_WARN] failed to load youtube_connections:", str(e))
        
        # 2. Processing Jobs & Weekly Stats
        jobs_data, total_jobs = supabase_service.list_processing_jobs(user_id, project_id=project_id, limit=100)
        
        active_jobs = sum(1 for job in jobs_data if job.get('status') in ['pending', 'downloading', 'processing', 'uploading', 'waiting_approval', 'queued'])
        completed_jobs = sum(1 for job in jobs_data if job.get('status') == 'completed')
        
        # Weekly Stats calculation
        videos_completed_this_week = 0
        for job in jobs_data:
            if job.get('status') == 'completed':
                comp_at_raw = job.get('completed_at', job.get('updated_at'))
                if comp_at_raw:
                    if isinstance(comp_at_raw, str):
                        try:
                            comp_at_dt = datetime.fromisoformat(comp_at_raw.replace('Z', '+00:00'))
                        except:
                            comp_at_dt = now
                    elif hasattr(comp_at_raw, 'timestamp'):
                        comp_at_dt = datetime.fromtimestamp(comp_at_raw.timestamp())
                    else:
                        comp_at_dt = comp_at_raw
                    
                    if isinstance(comp_at_dt, datetime) and comp_at_dt.replace(tzinfo=None) > one_week_ago:
                        videos_completed_this_week += 1
        
        recent_jobs = []
        # Return more jobs for demo users to show all data
        job_limit = 20 if len(jobs_data) > 10 else 5
        for job in jobs_data[:job_limit]:
            # Parse created_at
            created_at_job_raw = job.get('created_at', now)
            if isinstance(created_at_job_raw, str):
                try:
                    created_at_job = datetime.fromisoformat(created_at_job_raw.replace('Z', '+00:00'))
                except:
                    created_at_job = now
            else:
                created_at_job = created_at_job_raw

            recent_jobs.append(
                ProcessingJobSummary(
                    job_id=job.get('job_id', ''),
                    source_video_id=job.get('source_video_id', ''),
                    status=job.get('status', 'pending'),
                    progress=job.get('progress', 0),
                    target_languages=job.get('target_languages', []),
                    created_at=created_at_job,
                )
            )
            
        # 3. Language Channels
        language_channels = []
        try:
            language_channels_data = supabase_service.get_language_channels(user_id, project_id=project_id)
            for channel in language_channels_data:
                language_channels.append({
                    'id': channel.get('id', ''),
                    'channel_id': channel.get('channel_id', ''),
                    'language_code': channel.get('language_code', ''),
                    'channel_name': channel.get('channel_name'),
                    'created_at': channel.get('created_at'),
                })
        except Exception as e:
            print("[DASHBOARD_WARN] failed to load language_channels:", str(e))
            
        # 4. Projects
        projects: List[ProjectSummary] = []
        try:
            projects_data = supabase_service.list_projects(user_id)
            for proj in projects_data:
                # Parse created_at
                created_at_proj_raw = proj.get('created_at', now)
                if isinstance(created_at_proj_raw, str):
                    try:
                        created_at_proj = datetime.fromisoformat(created_at_proj_raw.replace('Z', '+00:00'))
                    except:
                        created_at_proj = now
                else:
                    created_at_proj = created_at_proj_raw

                projects.append(ProjectSummary(
                    id=proj.get('id', ''),
                    name=proj.get('name', 'Untitled Project'),
                    created_at=created_at_proj
                ))
        except Exception as e:
            print("[DASHBOARD_WARN] failed to load projects:", str(e))
            
        # 5. Recent Activity
        recent_activity = []
        try:
            activity_data = supabase_service.list_activity_logs(user_id, project_id=project_id, limit=5)
            for log in activity_data:
                ts_raw = log.get('timestamp')
                if isinstance(ts_raw, str):
                    try:
                        ts = datetime.fromisoformat(ts_raw.replace('Z', '+00:00'))
                    except:
                        ts = now
                elif hasattr(ts_raw, 'timestamp'):
                    ts = datetime.fromtimestamp(ts_raw.timestamp())
                else:
                    ts = ts_raw or now

                recent_activity.append(ActivityFeedItem(
                    id=log.get('id', 'unknown'),
                    action=log.get('action', 'Activity'),
                    details=log.get('details'),
                    status=log.get('status', 'info'),
                    timestamp=ts,
                    project_id=log.get('project_id')
                ))
        except Exception as e:
            print("[DASHBOARD_WARN] failed to load activity logs:", str(e))
            
        # 6. Credits (Mock for now)
        credits = CreditSummary(
            used=completed_jobs * 10,  # 10 credits per completed job
            limit=1000,
            reset_date=now + timedelta(days=30)
        )
        
        # Growth percentage (Mock or simplified)
        growth = 15.5 if completed_jobs > 0 else 0.0
        
        weekly_stats = WeeklyStats(
            videos_completed=videos_completed_this_week,
            languages_added=len(language_channels), # Total hubs
            growth_percentage=growth
        )

        print(f"[DASHBOARD] Returning data: projects={len(projects)}, videos={total_jobs}, jobs={total_jobs}, channels={len(language_channels)}")

        return DashboardResponse(
            user_id=user_id,
            email=email,
            name=name,
            auth_provider=auth_provider,
            created_at=created_at.replace(tzinfo=None),
            credits=credits,
            weekly_stats=weekly_stats,
            youtube_connections=youtube_connections,
            has_youtube_connection=len(youtube_connections) > 0,
            connections_count=len(youtube_connections),
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            completed_jobs=completed_jobs,
            recent_jobs=recent_jobs,
            language_channels=language_channels,
            total_language_channels=len(language_channels),
            projects=projects,
            total_projects=len(projects),
            recent_activity=recent_activity
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[DASHBOARD_ERROR] {str(e)}")
        # Partial fallback
        return DashboardResponse(
            user_id=user_id,
            email=current_user.get("email"),
            name=current_user.get("name"),
            auth_provider="email",
            created_at=now,
            credits=CreditSummary(used=0, limit=1000),
            weekly_stats=WeeklyStats(videos_completed=0, languages_added=0, growth_percentage=0.0),
            youtube_connections=[],
            has_youtube_connection=False,
            connections_count=0,
            total_jobs=0,
            active_jobs=0,
            completed_jobs=0,
            recent_jobs=[],
            language_channels=[],
            total_language_channels=0,
            projects=[],
            total_projects=0,
            recent_activity=[]
        )
