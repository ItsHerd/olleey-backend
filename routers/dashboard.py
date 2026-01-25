"""Dashboard router for user overview and statistics."""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime
from typing import List
import json

from schemas.dashboard import DashboardResponse, YouTubeConnectionSummary, ProcessingJobSummary, ProjectSummary
from middleware.auth import get_current_user
from services.firestore import firestore_service
from firebase_admin import auth

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get(
    "",
    response_model=DashboardResponse,
    responses={
        200: {
            "description": "Dashboard data retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "new_user": {
                            "summary": "Response for a new user with no connections",
                            "value": {
                                "user_id": "gwWVssEfHXf1e1C0DtRCU21o41x1",
                                "email": "user1@gmail.com",
                                "name": "User One",
                                "auth_provider": "email",
                                "created_at": "2026-01-18T19:51:14.015000",
                                "youtube_connections": [],
                                "has_youtube_connection": False,
                                "total_jobs": 0,
                                "active_jobs": 0,
                                "completed_jobs": 0,
                                "recent_jobs": [],
                                "language_channels": [],
                                "total_language_channels": 0,
                                "projects": [{"id": "p1", "name": "Default Project", "created_at": "2026-01-18T19:51:14.015000"}],
                                "total_projects": 1
                            }
                        },
                        "connected_user": {
                            "summary": "Response for a user with YouTube connection and jobs",
                            "value": {
                                "user_id": "gwWVssEfHXf1e1C0DtRCU21o41x1",
                                "email": "user1@gmail.com",
                                "name": "User One",
                                "auth_provider": "email",
                                "created_at": "2026-01-18T19:51:14.015000",
                                "youtube_connections": [
                                    {
                                        "connection_id": "conn_123",
                                        "youtube_channel_id": "UCxxxxxxxxxxxxxxxxxxxxx",
                                        "youtube_channel_name": "My YouTube Channel",
                                        "is_primary": True,
                                        "connected_at": "2026-01-18T20:00:00"
                                    }
                                ],
                                "has_youtube_connection": True,
                                "total_jobs": 5,
                                "active_jobs": 2,
                                "completed_jobs": 3,
                                "recent_jobs": [
                                    {
                                        "job_id": "job_123",
                                        "source_video_id": "dQw4w9WgXcQ",
                                        "status": "processing",
                                        "progress": 50,
                                        "target_languages": ["es", "fr"],
                                        "created_at": "2026-01-18T20:00:00"
                                    }
                                ],
                                "language_channels": [
                                    {
                                        "id": "channel_123",
                                        "channel_id": "UCyyyyyyyyyyyyyyyyyyyyy",
                                        "language_code": "es",
                                        "channel_name": "Spanish Channel",
                                        "created_at": "2026-01-18T20:00:00"
                                    }
                                ],
                                "total_language_channels": 1,
                                "projects": [],
                                "total_projects": 0
                            }
                        }
                    }
                }
            }
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
    
    Returns comprehensive user information including:
    - User profile info
    - YouTube channel connections
    - Processing jobs summary
    - Language channels
    - Projects
    
    For new users (no YouTube connection), returns appropriate empty/default data.
    
    Args:
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        DashboardResponse: Complete dashboard data
    """
    user_id = current_user["user_id"]
    
    try:
        # Get user info from Firebase Auth
        firebase_user = auth.get_user(user_id)
        
        # Get YouTube connections (should succeed even if other sections fail)
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
                        connected_at=conn.get('created_at', datetime.utcnow()),
                    )
                )
        except Exception as e:
            # Don't fail the entire dashboard if connections query fails
            print("[DASHBOARD_WARN] failed to load youtube_connections:", str(e))
        
        # Get processing jobs (may require a composite index; treat failures as "no jobs yet")
        jobs_data: List[dict] = []
        total_jobs = 0
        active_jobs = 0
        completed_jobs = 0
        recent_jobs: List[ProcessingJobSummary] = []
        try:
            jobs_data, total_jobs = firestore_service.list_processing_jobs(user_id, limit=100)

            # Count jobs by status
            active_jobs = sum(
                1
                for job in jobs_data
                if job.get('status') in ['pending', 'downloading', 'processing', 'uploading', 'waiting_approval']
            )
            completed_jobs = sum(1 for job in jobs_data if job.get('status') == 'completed')

            # Get recent jobs (last 5)
            for job in jobs_data[:5]:
                recent_jobs.append(
                    ProcessingJobSummary(
                        job_id=job.get('id', ''),
                        source_video_id=job.get('source_video_id', ''),
                        status=job.get('status', 'pending'),
                        progress=job.get('progress', 0),
                        target_languages=job.get('target_languages', []),
                        created_at=job.get('created_at', datetime.utcnow()),
                    )
                )
        except Exception as e:
            print("[DASHBOARD_WARN] failed to load processing_jobs (likely missing index):", str(e))
        
        # Get language channels
        language_channels: List[dict] = []
        try:
            language_channels_data = firestore_service.get_language_channels(user_id)
            for channel in language_channels_data:
                language_channels.append(
                    {
                        'id': channel.get('id', ''),
                        'channel_id': channel.get('channel_id', ''),
                        'language_code': channel.get('language_code', ''),
                        'channel_name': channel.get('channel_name'),
                        'created_at': channel.get('created_at'),
                    }
                )
        except Exception as e:
            print("[DASHBOARD_WARN] failed to load language_channels:", str(e))
            
        # Get projects
        projects: List[ProjectSummary] = []
        try:
            projects_data = firestore_service.list_projects(user_id)
            for proj in projects_data:
                projects.append(
                   ProjectSummary(
                       id=proj.get('id', ''),
                       name=proj.get('name', 'Untitled Project'),
                       created_at=proj.get('created_at', datetime.utcnow())
                   ) 
                )
        except Exception as e:
            print("[DASHBOARD_WARN] failed to load projects:", str(e))
        
        # Determine auth provider
        auth_provider = "email"
        if firebase_user.provider_data:
            for provider in firebase_user.provider_data:
                if provider.provider_id == "google.com":
                    auth_provider = "google"
                    break
                elif provider.provider_id == "apple.com":
                    auth_provider = "apple"
                    break
        
        response = DashboardResponse(
            user_id=user_id,
            email=current_user.get("email") or firebase_user.email,
            name=current_user.get("name") or firebase_user.display_name,
            auth_provider=auth_provider,
            created_at=datetime.fromtimestamp(firebase_user.user_metadata.creation_timestamp / 1000),
            
            # YouTube connections
            youtube_connections=youtube_connections,
            has_youtube_connection=len(youtube_connections) > 0,
            connections_count=len(youtube_connections),
            
            # Processing jobs
            total_jobs=total_jobs,
            active_jobs=active_jobs,
            completed_jobs=completed_jobs,
            recent_jobs=recent_jobs,
            
            # Language channels
            language_channels=language_channels,
            total_language_channels=len(language_channels),
            
            # Projects
            projects=projects,
            total_projects=len(projects)
        )

        print(
            "[DASHBOARD]",
            json.dumps(
                {
                    "user_id": response.user_id,
                    "email": response.email,
                    "auth_provider": response.auth_provider,
                    "has_youtube_connection": response.has_youtube_connection,
                    "connections_count": response.connections_count,
                    "total_jobs": response.total_jobs,
                    "active_jobs": response.active_jobs,
                    "completed_jobs": response.completed_jobs,
                    "total_language_channels": response.total_language_channels,
                    "total_projects": response.total_projects
                },
                default=str,
            ),
        )

        return response
        
    except Exception as e:
        # Fallback response for new users or if Firebase lookup fails
        response = DashboardResponse(
            user_id=user_id,
            email=current_user.get("email"),
            name=current_user.get("name"),
            auth_provider="email",
            created_at=datetime.utcnow(),
            
            # Empty data for new users
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
            total_projects=0
        )

        print(
            "[DASHBOARD_FALLBACK]",
            json.dumps(
                {
                    "user_id": response.user_id,
                    "email": response.email,
                    "auth_provider": response.auth_provider,
                    "has_youtube_connection": response.has_youtube_connection,
                    "connections_count": response.connections_count,
                    "total_jobs": response.total_jobs,
                    "active_jobs": response.active_jobs,
                    "completed_jobs": response.completed_jobs,
                    "total_language_channels": response.total_language_channels,
                    "total_projects": response.total_projects,
                    "error": str(e),
                },
                default=str,
            ),
        )

        return response
