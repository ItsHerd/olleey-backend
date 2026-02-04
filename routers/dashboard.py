"""Dashboard router for user overview and statistics."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List, Optional
import json

from schemas.dashboard import DashboardResponse, YouTubeConnectionSummary, ProcessingJobSummary, ProjectSummary, CreditSummary, WeeklyStats, ActivityFeedItem
from middleware.auth import get_current_user
from services.firestore import firestore_service
from firebase_admin import auth
from datetime import timedelta

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


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
    logs = firestore_service.list_activity_logs(user_id=user_id, project_id=project_id, limit=limit)
    
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
    current_user: dict = Depends(get_current_user)
):
    """
    Get dashboard data for the current user.
    """
    user_id = current_user["user_id"]
    
    # Defaults
    now = datetime.utcnow()
    one_week_ago = now - timedelta(days=7)
    
    try:
        # Get user info from Firebase Auth
        firebase_user = auth.get_user(user_id)
        
        # 1. YouTube Connections
        youtube_connections: List[YouTubeConnectionSummary] = []
        try:
            youtube_connections_data = firestore_service.get_youtube_connections(user_id)
            for conn in youtube_connections_data:
                youtube_connections.append(
                    YouTubeConnectionSummary(
                        connection_id=conn.get('connection_id', ''),
                        youtube_channel_id=conn.get('youtube_channel_id', ''),
                        youtube_channel_name=conn.get('youtube_channel_name'),
                        is_primary=conn.get('is_primary', False),
                        connected_at=conn.get('created_at', now),
                    )
                )
        except Exception as e:
            print("[DASHBOARD_WARN] failed to load youtube_connections:", str(e))
        
        # 2. Processing Jobs & Weekly Stats
        jobs_data, total_jobs = firestore_service.list_processing_jobs(user_id, limit=100)
        
        active_jobs = sum(1 for job in jobs_data if job.get('status') in ['pending', 'downloading', 'processing', 'uploading', 'waiting_approval'])
        completed_jobs = sum(1 for job in jobs_data if job.get('status') == 'completed')
        
        # Weekly Stats calculation
        videos_completed_this_week = 0
        for job in jobs_data:
            if job.get('status') == 'completed':
                comp_at = job.get('completed_at', job.get('updated_at'))
                if comp_at:
                    if hasattr(comp_at, 'timestamp'):
                        comp_at_dt = datetime.fromtimestamp(comp_at.timestamp())
                    else:
                        comp_at_dt = comp_at # assume it's already datetime or similar
                    
                    if isinstance(comp_at_dt, datetime) and comp_at_dt > one_week_ago:
                        videos_completed_this_week += 1
        
        recent_jobs = []
        # Return more jobs for demo users to show all data
        job_limit = 20 if len(jobs_data) > 10 else 5
        for job in jobs_data[:job_limit]:
            recent_jobs.append(
                ProcessingJobSummary(
                    job_id=job.get('id', ''),
                    source_video_id=job.get('source_video_id', ''),
                    status=job.get('status', 'pending'),
                    progress=job.get('progress', 0),
                    target_languages=job.get('target_languages', []),
                    created_at=job.get('created_at', now),
                )
            )
            
        # 3. Language Channels
        language_channels = []
        try:
            language_channels_data = firestore_service.get_language_channels(user_id)
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
            projects_data = firestore_service.list_projects(user_id)
            for proj in projects_data:
                projects.append(ProjectSummary(
                    id=proj.get('id', ''),
                    name=proj.get('name', 'Untitled Project'),
                    created_at=proj.get('created_at', now)
                ))
        except Exception as e:
            print("[DASHBOARD_WARN] failed to load projects:", str(e))
            
        # 5. Recent Activity
        recent_activity = []
        try:
            activity_data = firestore_service.list_activity_logs(user_id, limit=5)
            for log in activity_data:
                ts = log.get('timestamp')
                if hasattr(ts, 'timestamp'):
                    ts = datetime.fromtimestamp(ts.timestamp())
                recent_activity.append(ActivityFeedItem(
                    id=log.get('id', 'unknown'),
                    action=log.get('action', 'Activity'),
                    details=log.get('details'),
                    status=log.get('status', 'info'),
                    timestamp=ts or now,
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

        auth_provider = "email"
        if firebase_user.provider_data:
            for provider in firebase_user.provider_data:
                if provider.provider_id == "google.com":
                    auth_provider = "google"
                    break
        
        return DashboardResponse(
            user_id=user_id,
            email=current_user.get("email") or firebase_user.email,
            name=current_user.get("name") or firebase_user.display_name,
            auth_provider=auth_provider,
            created_at=datetime.fromtimestamp(firebase_user.user_metadata.creation_timestamp / 1000),
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
