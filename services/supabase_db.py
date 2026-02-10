"""
Supabase database service - replaces Firestore
Provides the same interface as firestore service for easy migration
"""

import os
from typing import Optional, Dict, List, Any, Tuple
from datetime import datetime, timezone
import uuid
from supabase import create_client, Client
from dotenv import load_dotenv
from config import settings

# Load environment variables from .env file
load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://wfjpbrcktxbwasbamchx.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY', '')


class SupabaseService:
    """Service for Supabase operations - compatible with Firestore service interface."""

    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print(f"✅ Supabase connected: {SUPABASE_URL}")

    # ============================================================
    # VIDEOS
    # ============================================================

    def get_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get a single video by video_id."""
        try:
            result = self.client.table('videos').select('*').eq('video_id', video_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting video {video_id}: {e}")
            return None

    def list_videos(
        self,
        user_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List videos with optional filters."""
        query = self.client.table('videos').select('*', count='exact')

        if user_id:
            query = query.eq('user_id', user_id)
        if channel_id:
            query = query.eq('channel_id', channel_id)
        if project_id:
            query = query.eq('project_id', project_id)

        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)

        result = query.execute()
        return result.data or [], result.count or 0

    def create_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new video."""
        if 'created_at' not in video_data:
            video_data['created_at'] = datetime.now(timezone.utc).isoformat()
        if 'updated_at' not in video_data:
            video_data['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('videos').insert(video_data).execute()
        return result.data[0] if result.data else {}

    def update_video(self, video_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a video."""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('videos').update(updates).eq('video_id', video_id).execute()
        return result.data[0] if result.data else {}

    def delete_video(self, video_id: str) -> bool:
        """Delete a video."""
        try:
            self.client.table('videos').delete().eq('video_id', video_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting video {video_id}: {e}")
            return False

    # ============================================================
    # PROCESSING JOBS
    # ============================================================

    def get_processing_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get a single processing job."""
        try:
            result = self.client.table('processing_jobs').select('*').eq('job_id', job_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting job {job_id}: {e}")
            return None

    def list_processing_jobs(
        self,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[Dict[str, Any]], int]:
        """List processing jobs with optional filters."""
        query = self.client.table('processing_jobs').select('*', count='exact')

        if user_id:
            query = query.eq('user_id', user_id)
        if project_id:
            query = query.eq('project_id', project_id)
        if status:
            query = query.eq('status', status)

        query = query.order('created_at', desc=True).range(offset, offset + limit - 1)

        result = query.execute()
        return result.data or [], result.count or 0

    def create_processing_job(self, job_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new processing job."""
        if 'job_id' not in job_data:
            job_data['job_id'] = str(uuid.uuid4())
        if 'created_at' not in job_data:
            job_data['created_at'] = datetime.now(timezone.utc).isoformat()
        if 'updated_at' not in job_data:
            job_data['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('processing_jobs').insert(job_data).execute()
        return result.data[0] if result.data else {}

    def update_processing_job(self, job_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a processing job."""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('processing_jobs').update(updates).eq('job_id', job_id).execute()
        return result.data[0] if result.data else {}

    def delete_processing_job(self, job_id: str) -> bool:
        """Delete a processing job."""
        try:
            self.client.table('processing_jobs').delete().eq('job_id', job_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting job {job_id}: {e}")
            return False

    # ============================================================
    # LOCALIZED VIDEOS
    # ============================================================

    def get_localized_videos_by_job_id(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all localized videos for a job."""
        result = self.client.table('localized_videos').select('*').eq('job_id', job_id).execute()
        return result.data or []

    def get_localized_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get a single localized video."""
        try:
            result = self.client.table('localized_videos').select('*').eq('id', video_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting localized video {video_id}: {e}")
            return None

    def create_localized_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new localized video."""
        if 'id' not in video_data:
            video_data['id'] = str(uuid.uuid4())
        if 'created_at' not in video_data:
            video_data['created_at'] = datetime.now(timezone.utc).isoformat()
        if 'updated_at' not in video_data:
            video_data['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('localized_videos').insert(video_data).execute()
        return result.data[0] if result.data else {}

    def update_localized_video(self, video_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a localized video."""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('localized_videos').update(updates).eq('id', video_id).execute()
        return result.data[0] if result.data else {}

    # ============================================================
    # CHANNELS
    # ============================================================

    def get_language_channels(self, user_id: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all channels for a user, optionally filtered by project."""
        query = self.client.table('channels').select('*').eq('user_id', user_id)
        if project_id:
            query = query.eq('project_id', project_id)
        result = query.execute()
        return result.data or []

    def get_channel(self, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get a single channel."""
        try:
            result = self.client.table('channels').select('*').eq('channel_id', channel_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting channel {channel_id}: {e}")
            return None

    def create_channel(self, channel_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new channel."""
        if 'created_at' not in channel_data:
            channel_data['created_at'] = datetime.now(timezone.utc).isoformat()
        if 'updated_at' not in channel_data:
            channel_data['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('channels').insert(channel_data).execute()
        return result.data[0] if result.data else {}

    def update_channel(self, channel_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a channel."""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('channels').update(updates).eq('channel_id', channel_id).execute()
        return result.data[0] if result.data else {}

    # ============================================================
    # PROJECTS
    # ============================================================

    def list_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """List all projects for a user."""
        result = self.client.table('projects').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
        return result.data or []

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get a single project."""
        try:
            result = self.client.table('projects').select('*').eq('id', project_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting project {project_id}: {e}")
            return None

    def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project."""
        if 'id' not in project_data:
            project_data['id'] = str(uuid.uuid4())
        if 'created_at' not in project_data:
            project_data['created_at'] = datetime.now(timezone.utc).isoformat()
        if 'updated_at' not in project_data:
            project_data['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('projects').insert(project_data).execute()
        return result.data[0] if result.data else {}

    def update_project(self, project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a project."""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('projects').update(updates).eq('id', project_id).execute()
        return result.data[0] if result.data else {}

    # ============================================================
    # ACTIVITY LOGS (Optional)
    # ============================================================

    def log_activity(
        self,
        user_id: str,
        project_id: Optional[str],
        action: str,
        details: str
    ) -> None:
        """Log user activity (can be implemented later)."""
        # TODO: Create activity_logs table and implement
        pass

    def list_activity_logs(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get activity logs for a user."""
        # TODO: Implement when activity_logs table is created
        # For now, return empty list to prevent errors
        return []

    # ============================================================
    # YOUTUBE CONNECTIONS (Still in Firestore)
    # ============================================================

    def get_youtube_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get YouTube connections - delegates to Firestore for now."""
        # YouTube connections are managed by non-migrated routers
        # Keep in Firestore until youtube_auth.py and youtube_connect.py are migrated
        from services.firestore import firestore_service
        return firestore_service.get_youtube_connections(user_id)

    def get_youtube_connection(self, connection_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a single YouTube connection - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.get_youtube_connection(connection_id, user_id)

    def get_youtube_connection_by_channel(self, user_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get YouTube connection by channel ID - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.get_youtube_connection_by_channel(user_id, channel_id)

    # ============================================================
    # SUBSCRIPTIONS (Still in Firestore)
    # ============================================================

    def create_subscription(self, *args, **kwargs) -> str:
        """Create subscription - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.create_subscription(*args, **kwargs)

    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.get_subscription(subscription_id)

    def get_subscription_by_channel(self, user_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by channel - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.get_subscription_by_channel(user_id, channel_id)

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete subscription - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.delete_subscription(subscription_id)

    # ============================================================
    # OTHER METHODS (Still in Firestore)
    # ============================================================

    def get_uploaded_videos(self, user_id: str, project_id: Optional[str], limit: int) -> List[Dict[str, Any]]:
        """Get uploaded videos - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.get_uploaded_videos(user_id, project_id, limit)

    def get_all_localized_videos_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all localized videos for user - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.get_all_localized_videos_for_user(user_id)

    def get_localized_video_by_localized_id(self, video_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get localized video by ID - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.get_localized_video_by_localized_id(video_id, user_id)

    def get_localized_videos_by_source_id(self, video_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get localized videos by source ID - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.get_localized_videos_by_source_id(video_id, user_id)

    def update_language_channel(self, channel_id: str, user_id: str, **updates) -> bool:
        """Update language channel - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.update_language_channel(channel_id, user_id, **updates)

    def delete_language_channel(self, channel_id: str, user_id: str) -> bool:
        """Delete language channel - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.delete_language_channel(channel_id, user_id)

    def delete_project(self, project_id: str) -> bool:
        """Delete project - delegates to Firestore for now."""
        from services.firestore import firestore_service
        return firestore_service.delete_project(project_id)


# Create singleton instance
supabase_service = SupabaseService()
