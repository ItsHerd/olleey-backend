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
        self._warned_missing_tables: set[str] = set()
        print(f"✅ Supabase connected: {SUPABASE_URL}")

    def _is_missing_table_error(self, error: Exception, table_name: str) -> bool:
        message = str(error)
        return (
            "PGRST205" in message
            or f"Could not find the table 'public.{table_name}'" in message
            or f"relation \"{table_name}\" does not exist" in message
        )

    def _warn_missing_table_once(self, table_name: str):
        if table_name in self._warned_missing_tables:
            return
        self._warned_missing_tables.add(table_name)
        print(f"[WARN] Supabase table '{table_name}' is missing. Skipping related operation.")

    def _is_missing_column_error(self, error: Exception, column_name: str) -> bool:
        message = str(error)
        return (
            "PGRST204" in message
            or "schema cache" in message
            or f"column '{column_name}'" in message
            or f'"{column_name}"' in message and "does not exist" in message
        )

    def _resolve_processing_job_internal_id(self, job_id: Optional[str]) -> Optional[str]:
        """
        Resolve a job identifier to processing_jobs.id.

        Some callers pass external `processing_jobs.job_id`, while localized_videos.job_id
        is FK-linked to `processing_jobs.id` in newer schemas.
        """
        if not job_id:
            return None

        # First try as internal PK.
        try:
            by_id = (
                self.client.table('processing_jobs')
                .select('id')
                .eq('id', job_id)
                .limit(1)
                .execute()
            )
            if by_id.data:
                return by_id.data[0].get('id')
        except Exception:
            pass

        # Then try as external/job-facing ID.
        try:
            by_external = (
                self.client.table('processing_jobs')
                .select('id')
                .eq('job_id', job_id)
                .limit(1)
                .execute()
            )
            if by_external.data:
                return by_external.data[0].get('id')
        except Exception:
            pass

        return None

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

    def upsert_video(self, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert a video by unique constraints (video_id)."""
        if 'created_at' not in video_data:
            video_data['created_at'] = datetime.now(timezone.utc).isoformat()
        video_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        result = self.client.table('videos').upsert(video_data, on_conflict='video_id,user_id').execute()
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

    def get_job_by_video(self, source_video_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a processing job for a source video + user."""
        try:
            result = (
                self.client.table('processing_jobs')
                .select('*')
                .eq('source_video_id', source_video_id)
                .eq('user_id', user_id)
                .order('created_at', desc=True)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting job by video {source_video_id}: {e}")
            return None

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

    def update_processing_job(
        self,
        job_id: str,
        updates: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a processing job.

        Supports both call styles:
        - update_processing_job(job_id, {"status": "processing"})
        - update_processing_job(job_id, status="processing")
        """
        payload: Dict[str, Any] = {}
        if isinstance(updates, dict):
            payload.update(updates)
        payload.update(kwargs)
        payload['updated_at'] = datetime.now(timezone.utc).isoformat()

        result = self.client.table('processing_jobs').update(payload).eq('job_id', job_id).execute()
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
        """Get all localized videos for a job (supports external and internal job IDs)."""
        candidate_ids: List[str] = []
        if job_id:
            candidate_ids.append(job_id)

        internal_job_id = self._resolve_processing_job_internal_id(job_id)
        if internal_job_id and internal_job_id not in candidate_ids:
            candidate_ids.append(internal_job_id)

        videos: List[Dict[str, Any]] = []
        seen_ids: set[str] = set()

        for candidate in candidate_ids:
            result = self.client.table('localized_videos').select('*').eq('job_id', candidate).execute()
            for row in result.data or []:
                row_id = row.get('id')
                if row_id and row_id in seen_ids:
                    continue
                if row_id:
                    seen_ids.add(row_id)
                videos.append(row)

        return videos

    def get_localized_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get a single localized video."""
        try:
            result = self.client.table('localized_videos').select('*').eq('id', video_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting localized video {video_id}: {e}")
            return None

    def create_localized_video(
        self,
        video_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a new localized video.

        Supports both call styles:
        - create_localized_video({...})
        - create_localized_video(job_id="...", language_code="es", ...)
        """
        payload: Dict[str, Any] = {}
        if isinstance(video_data, dict):
            payload.update(video_data)
        payload.update(kwargs)

        if 'id' not in payload:
            payload['id'] = str(uuid.uuid4())
        if 'created_at' not in payload:
            payload['created_at'] = datetime.now(timezone.utc).isoformat()
        if 'updated_at' not in payload:
            payload['updated_at'] = datetime.now(timezone.utc).isoformat()

        # Normalize to processing_jobs.id for schemas where localized_videos.job_id
        # references processing_jobs.id instead of processing_jobs.job_id.
        if payload.get("job_id"):
            internal_job_id = self._resolve_processing_job_internal_id(payload.get("job_id"))
            if internal_job_id:
                payload["job_id"] = internal_job_id

        try:
            result = self.client.table('localized_videos').insert(payload).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            # Backward-compatible fallback for schemas that store `video_url`
            # but do not expose `storage_url` / `dubbed_audio_url`.
            fallback_payload = dict(payload)
            if "storage_url" in fallback_payload and "video_url" not in fallback_payload:
                fallback_payload["video_url"] = fallback_payload.get("storage_url")
            fallback_payload.pop("storage_url", None)
            fallback_payload.pop("dubbed_audio_url", None)

            if fallback_payload == payload:
                raise

            print(f"[WARN] create_localized_video fallback due to schema mismatch: {e}")
            result = self.client.table('localized_videos').insert(fallback_payload).execute()
            return result.data[0] if result.data else {}

    def update_localized_video(
        self,
        video_id: str,
        updates: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Update a localized video.

        Supports both call styles:
        - update_localized_video(video_id, {"status": "draft"})
        - update_localized_video(video_id, status="draft")
        """
        payload: Dict[str, Any] = {}
        if isinstance(updates, dict):
            payload.update(updates)
        payload.update(kwargs)
        payload['updated_at'] = datetime.now(timezone.utc).isoformat()

        try:
            result = self.client.table('localized_videos').update(payload).eq('id', video_id).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            fallback_payload = dict(payload)
            if "storage_url" in fallback_payload and "video_url" not in fallback_payload:
                fallback_payload["video_url"] = fallback_payload.get("storage_url")
            fallback_payload.pop("storage_url", None)
            fallback_payload.pop("dubbed_audio_url", None)

            if fallback_payload == payload:
                raise

            print(f"[WARN] update_localized_video fallback due to schema mismatch: {e}")
            result = self.client.table('localized_videos').update(fallback_payload).eq('id', video_id).execute()
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

    def get_language_channel_by_language(self, user_id: str, language_code: str) -> Optional[Dict[str, Any]]:
        """
        Get one channel for a user by language code.

        Firestore compatibility helper used by dubbing/simulation flows.
        """
        try:
            result = (
                self.client.table('channels')
                .select('*')
                .eq('user_id', user_id)
                .eq('language_code', language_code)
                .order('created_at', desc=False)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting language channel for user={user_id}, language={language_code}: {e}")
            return None

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
    # YOUTUBE CONNECTIONS
    # ============================================================

    def delete_project(self, project_id: str) -> bool:
        """Delete a project."""
        try:
            self.client.table('projects').delete().eq('id', project_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting project {project_id}: {e}")
            return False

    # ============================================================
    # ACTIVITY LOGS
    # ============================================================

    def log_activity(
        self,
        user_id: str,
        project_id: Optional[str],
        action: str,
        status: str = 'info',
        details: Optional[str] = None
    ) -> str:
        """Log user activity."""
        log_id = str(uuid.uuid4())
        data = {
            'id': log_id,
            'user_id': user_id,
            'project_id': project_id,
            'action': action,
            'status': status,
            'details': details,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        try:
            self.client.table('activity_logs').insert(data).execute()
            return log_id
        except Exception as e:
            if self._is_missing_table_error(e, "activity_logs"):
                self._warn_missing_table_once("activity_logs")
                return ""
            print(f"Error logging activity: {e}")
            return ""

    def list_activity_logs(
        self,
        user_id: str,
        project_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get activity logs for a user."""
        try:
            query = self.client.table('activity_logs').select('*').eq('user_id', user_id)
            if project_id:
                query = query.eq('project_id', project_id)
            
            result = query.order('timestamp', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            if self._is_missing_table_error(e, "activity_logs"):
                self._warn_missing_table_once("activity_logs")
                return []
            print(f"Error listing activity logs: {e}")
            return []

    # ============================================================
    # YOUTUBE CONNECTIONS
    # ============================================================

    def create_youtube_connection(self, user_id: str, youtube_channel_id: str,
                                  access_token: str, refresh_token: str,
                                  youtube_channel_name: Optional[str] = None,
                                  token_expiry: Optional[datetime] = None,
                                  is_primary: bool = False,
                                  channel_avatar_url: Optional[str] = None,
                                  master_connection_id: Optional[str] = None,
                                  language_code: Optional[str] = None) -> str:
        """Create YouTube channel connection."""
        connection_id = str(uuid.uuid4())
        data = {
            'connection_id': connection_id,
            'user_id': user_id,
            'youtube_channel_id': youtube_channel_id,
            'youtube_channel_name': youtube_channel_name,
            'channel_avatar_url': channel_avatar_url,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_expiry': token_expiry.isoformat() if token_expiry else None,
            'is_primary': is_primary,
            'language_code': language_code,
            'master_connection_id': master_connection_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        try:
            self.client.table('youtube_connections').insert(data).execute()
            return connection_id
        except Exception as e:
            print(f"Error creating youtube connection: {e}")
            return ""

    def get_youtube_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get YouTube connections."""
        try:
            result = self.client.table('youtube_connections').select('*').eq('user_id', user_id).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting youtube connections: {e}")
            return []

    def get_youtube_connection(self, connection_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a single YouTube connection."""
        try:
            result = self.client.table('youtube_connections').select('*').eq('connection_id', connection_id).eq('user_id', user_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting youtube connection {connection_id}: {e}")
            return None

    def get_youtube_connection_by_channel(self, user_id: str, youtube_channel_id: str) -> Optional[Dict[str, Any]]:
        """Get YouTube connection by channel ID."""
        try:
            result = self.client.table('youtube_connections').select('*').eq('user_id', user_id).eq('youtube_channel_id', youtube_channel_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting youtube connection for channel {youtube_channel_id}: {e}")
            return None

    def get_primary_youtube_connection(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's primary YouTube connection."""
        try:
            result = (
                self.client.table('youtube_connections')
                .select('*')
                .eq('user_id', user_id)
                .eq('is_primary', True)
                .limit(1)
                .execute()
            )
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting primary youtube connection for {user_id}: {e}")
            return None

    def update_youtube_connection(self, connection_id: str, **updates) -> bool:
        """Update YouTube connection fields."""
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        if 'token_expiry' in updates and isinstance(updates['token_expiry'], datetime):
            updates['token_expiry'] = updates['token_expiry'].isoformat()
        try:
            self.client.table('youtube_connections').update(updates).eq('connection_id', connection_id).execute()
            return True
        except Exception as e:
            print(f"Error updating youtube connection {connection_id}: {e}")
            return False

    def set_primary_connection(self, connection_id: str, user_id: str) -> bool:
        """Set one connection as primary and unset others."""
        target = self.get_youtube_connection(connection_id, user_id)
        if not target:
            return False
        try:
            # Unset all existing primaries for this user.
            self.client.table('youtube_connections').update({
                'is_primary': False,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('user_id', user_id).eq('is_primary', True).execute()
            # Set requested connection as primary.
            self.client.table('youtube_connections').update({
                'is_primary': True,
                'updated_at': datetime.now(timezone.utc).isoformat()
            }).eq('connection_id', connection_id).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            print(f"Error setting primary youtube connection {connection_id}: {e}")
            return False

    def delete_youtube_connection(self, connection_id: str, user_id: str) -> bool:
        """Delete a YouTube connection owned by user."""
        try:
            self.client.table('youtube_connections').delete().eq('connection_id', connection_id).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting youtube connection {connection_id}: {e}")
            return False

    def get_youtube_credentials(self, user_id: str, connection_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get OAuth credentials from specific or primary YouTube connection."""
        connection = self.get_youtube_connection(connection_id, user_id) if connection_id else self.get_primary_youtube_connection(user_id)
        if not connection:
            return None
        return {
            'access_token': connection.get('access_token'),
            'refresh_token': connection.get('refresh_token'),
            'token_expiry': connection.get('token_expiry'),
            'youtube_channel_id': connection.get('youtube_channel_id'),
            'connection_id': connection.get('connection_id'),
        }

    # ============================================================
    # SUBSCRIPTIONS
    # ============================================================

    def create_subscription(self, user_id: str, channel_id: str, callback_url: str,
                           topic: str, lease_seconds: int, 
                           expires_at: Optional[datetime] = None,
                           secret: Optional[str] = None) -> str:
        """Create PubSubHubbub subscription."""
        subscription_id = str(uuid.uuid4())
        data = {
            'id': subscription_id,
            'user_id': user_id,
            'channel_id': channel_id,
            'callback_url': callback_url,
            'topic': topic,
            'lease_seconds': lease_seconds,
            'expires_at': expires_at.isoformat() if expires_at else None,
            'secret': secret,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        try:
            self.client.table('subscriptions').insert(data).execute()
            return subscription_id
        except Exception as e:
            print(f"Error creating subscription: {e}")
            return ""

    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by ID."""
        try:
            result = self.client.table('subscriptions').select('*').eq('id', subscription_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting subscription {subscription_id}: {e}")
            return None

    def get_subscription_by_channel(self, user_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by channel."""
        try:
            query = self.client.table('subscriptions').select('*').eq('channel_id', channel_id)
            if user_id:
                query = query.eq('user_id', user_id)
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting subscription for channel {channel_id}: {e}")
            return None

    def get_subscription_by_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get subscription by topic URL."""
        try:
            result = self.client.table('subscriptions').select('*').eq('topic', topic).limit(1).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting subscription by topic: {e}")
            return None

    def list_subscriptions(self, user_id: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """List subscriptions, optionally scoped to a user."""
        try:
            query = self.client.table('subscriptions').select('*')
            if user_id:
                query = query.eq('user_id', user_id)
            result = query.limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"Error listing subscriptions: {e}")
            return []

    def update_subscription_lease(self, subscription_id: str, expires_at: datetime, lease_seconds: int) -> bool:
        """Update subscription lease metadata."""
        try:
            self.client.table('subscriptions').update({
                'expires_at': expires_at.isoformat(),
                'lease_seconds': lease_seconds,
                'last_verified_at': datetime.now(timezone.utc).isoformat(),
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'status': 'active',
            }).eq('id', subscription_id).execute()
            return True
        except Exception as e:
            print(f"Error updating subscription lease {subscription_id}: {e}")
            return False

    def update_subscription_status(
        self,
        subscription_id: str,
        status: str,
        renewal_attempts: Optional[int] = None,
        error: Optional[str] = None,
    ) -> bool:
        """Update subscription status and renewal metadata."""
        payload: Dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if renewal_attempts is not None:
            payload["renewal_attempts"] = renewal_attempts
        if error is not None:
            payload["last_error"] = error
        try:
            self.client.table('subscriptions').update(payload).eq('id', subscription_id).execute()
            return True
        except Exception:
            # Some deployments may not have optional status columns yet.
            try:
                self.client.table('subscriptions').update({
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }).eq('id', subscription_id).execute()
                return True
            except Exception as e:
                print(f"Error updating subscription status {subscription_id}: {e}")
                return False

    def delete_subscription(self, subscription_id: str) -> bool:
        """Delete subscription."""
        try:
            self.client.table('subscriptions').delete().eq('id', subscription_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting subscription {subscription_id}: {e}")
            return False

    # ============================================================
    # UPLOADED VIDEOS
    # ============================================================

    def get_uploaded_videos(self, user_id: str, project_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Get uploaded videos for a user."""
        try:
            query = self.client.table('uploaded_videos').select('*').eq('user_id', user_id)
            if project_id:
                query = query.eq('project_id', project_id)
            result = query.order('uploaded_at', desc=True).limit(limit).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting uploaded videos: {e}")
            return []

    def get_uploaded_video(self, video_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific uploaded video by ID."""
        try:
            result = self.client.table('uploaded_videos').select('*').eq('id', video_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting uploaded video {video_id}: {e}")
            return None

    # ============================================================
    # LOCALIZED VIDEOS (EXTRA)
    # ============================================================

    def get_all_localized_videos_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all localized videos for user."""
        try:
            result = self.client.table('localized_videos').select('*').eq('user_id', user_id).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting all localized videos: {e}")
            return []

    def get_localized_video_by_localized_id(self, video_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get localized video by YouTube video ID."""
        try:
            result = self.client.table('localized_videos').select('*').eq('user_id', user_id).eq('localized_video_id', video_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"Error getting localized video by youtube id {video_id}: {e}")
            return None

    def get_localized_videos_by_source_id(self, video_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get localized videos by source ID."""
        try:
            result = self.client.table('localized_videos').select('*').eq('user_id', user_id).eq('source_video_id', video_id).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting localized videos for source {video_id}: {e}")
            return []

    # ============================================================
    # LANGUAGE CHANNELS
    # ============================================================

    def update_language_channel(self, channel_id: str, user_id: str, **updates) -> bool:
        """Update language channel."""
        try:
            updates['updated_at'] = datetime.now(timezone.utc).isoformat()
            self.client.table('channels').update(updates).eq('channel_id', channel_id).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            print(f"Error updating language channel {channel_id}: {e}")
            return False

    def delete_language_channel(self, channel_id: str, user_id: str) -> bool:
        """Delete language channel."""
        try:
            self.client.table('channels').delete().eq('channel_id', channel_id).eq('user_id', user_id).execute()
            return True
        except Exception as e:
            print(f"Error deleting language channel {channel_id}: {e}")
            return False

    def create_language_channel(self, user_id: str, channel_id: str,
                               language_code: str,
                               channel_name: Optional[str] = None,
                               channel_avatar_url: Optional[str] = None,
                               master_connection_id: Optional[str] = None,
                               project_id: Optional[str] = None) -> str:
        """Create language channel with a single associated language."""
        channel_doc_id = str(uuid.uuid4())
        data = {
            'id': channel_doc_id,
            'user_id': user_id,
            'project_id': project_id,
            'channel_id': channel_id,
            'language_code': language_code,
            'channel_name': channel_name,
            'channel_avatar_url': channel_avatar_url,
            'master_connection_id': master_connection_id,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        try:
            self.client.table('channels').insert(data).execute()
            return channel_doc_id
        except Exception as e:
            print(f"Error creating language channel: {e}")
            return ""

    # ============================================================
    # USER SETTINGS & USERS
    # ============================================================

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        try:
            result = self.client.table('users').select('*').eq('id', user_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting user {user_id}: {e}")
            return None

    def create_or_update_user(self, user_id: str, email: Optional[str], 
                              access_token: str, refresh_token: str,
                              token_expiry: Optional[datetime] = None) -> Dict[str, Any]:
        """Create or update user tokens."""
        data = {
            'id': user_id,
            'email': email,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_expiry': token_expiry.isoformat() if token_expiry else None,
            'updated_at': datetime.now(timezone.utc).isoformat()
        }
        try:
            result = self.client.table('users').upsert(data).execute()
            return result.data[0] if result.data else {}
        except Exception as e:
            print(f"Error upserting user {user_id}: {e}")
            return {}

    def get_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user settings."""
        try:
            result = self.client.table('user_settings').select('*').eq('user_id', user_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            if self._is_missing_table_error(e, 'user_settings'):
                self._warn_missing_table_once('user_settings')
                try:
                    user_result = self.client.table('users').select('preferences').eq('id', user_id).single().execute()
                    preferences = (user_result.data or {}).get('preferences', {})
                    return preferences if isinstance(preferences, dict) else None
                except Exception as fallback_error:
                    print(f"Error getting fallback user preferences for {user_id}: {fallback_error}")
                    return None
            print(f"Error getting user settings {user_id}: {e}")
            return None

    def update_user_settings(self, user_id: str, **updates):
        """Update user settings."""
        updates['user_id'] = user_id
        updates['updated_at'] = datetime.now(timezone.utc).isoformat()
        try:
            self.client.table('user_settings').upsert(updates).execute()
        except Exception as e:
            if self._is_missing_table_error(e, 'user_settings'):
                self._warn_missing_table_once('user_settings')
                try:
                    user_result = self.client.table('users').select('preferences').eq('id', user_id).single().execute()
                    current_preferences = (user_result.data or {}).get('preferences', {})
                    if not isinstance(current_preferences, dict):
                        current_preferences = {}
                    settings_updates = {
                        key: value
                        for key, value in updates.items()
                        if key not in {'user_id', 'updated_at'}
                    }
                    merged_preferences = {**current_preferences, **settings_updates}
                    self.client.table('users').update({
                        'preferences': merged_preferences,
                        'updated_at': datetime.now(timezone.utc).isoformat()
                    }).eq('id', user_id).execute()
                    return
                except Exception as fallback_error:
                    print(f"Error updating fallback user preferences {user_id}: {fallback_error}")
                    return
            print(f"Error updating user settings {user_id}: {e}")



    # ============================================================
    # TRANSCRIPTS
    # ============================================================

    def create_transcript(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new transcript."""
        if 'created_at' not in transcript_data:
            transcript_data['created_at'] = datetime.now(timezone.utc).isoformat()
        if 'updated_at' not in transcript_data:
            transcript_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        result = self.client.table('transcripts').insert(transcript_data).execute()
        return result.data[0] if result.data else {}
    
    def get_transcript(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get transcript for a job."""
        try:
            result = self.client.table('transcripts').select('*').eq('job_id', job_id).single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting transcript for job {job_id}: {e}")
            return None

    # ============================================================
    # TRANSLATIONS
    # ============================================================

    def create_translation(self, translation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new translation."""
        if 'created_at' not in translation_data:
            translation_data['created_at'] = datetime.now(timezone.utc).isoformat()
        if 'updated_at' not in translation_data:
            translation_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        result = self.client.table('translations').insert(translation_data).execute()
        return result.data[0] if result.data else {}
    
    def get_translations(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all translations for a job."""
        try:
            result = self.client.table('translations').select('*').eq('job_id', job_id).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting translations for job {job_id}: {e}")
            return []
    
    def get_translation(self, job_id: str, target_language: str) -> Optional[Dict[str, Any]]:
        """Get specific translation for a job and language."""
        try:
            result = self.client.table('translations').select('*')\
                .eq('job_id', job_id)\
                .eq('target_language', target_language)\
                .single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting translation for job {job_id}, lang {target_language}: {e}")
            return None

    # ============================================================
    # DUBBED AUDIO
    # ============================================================

    def create_dubbed_audio(self, audio_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new dubbed audio record."""
        if 'created_at' not in audio_data:
            audio_data['created_at'] = datetime.now(timezone.utc).isoformat()
        if 'updated_at' not in audio_data:
            audio_data['updated_at'] = datetime.now(timezone.utc).isoformat()
        
        result = self.client.table('dubbed_audio').insert(audio_data).execute()
        return result.data[0] if result.data else {}
    
    def get_dubbed_audio(self, job_id: str, language_code: str) -> Optional[Dict[str, Any]]:
        """Get dubbed audio for a job and language."""
        try:
            result = self.client.table('dubbed_audio').select('*')\
                .eq('job_id', job_id)\
                .eq('language_code', language_code)\
                .single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting dubbed audio for job {job_id}, lang {language_code}: {e}")
            return None
    
    def get_all_dubbed_audio(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all dubbed audio files for a job."""
        try:
            result = self.client.table('dubbed_audio').select('*').eq('job_id', job_id).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting dubbed audio for job {job_id}: {e}")
            return []

    # ============================================================
    # LIP SYNC JOBS
    # ============================================================

    def create_lip_sync_job(self, lipsync_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new lip sync job record."""
        if 'created_at' not in lipsync_data:
            lipsync_data['created_at'] = datetime.now(timezone.utc).isoformat()
        
        result = self.client.table('lip_sync_jobs').insert(lipsync_data).execute()
        return result.data[0] if result.data else {}
    
    def update_lip_sync_job(self, lipsync_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update a lip sync job."""
        result = self.client.table('lip_sync_jobs').update(updates)\
            .eq('id', lipsync_id).execute()
        return result.data[0] if result.data else {}
    
    def get_lip_sync_job(self, job_id: str, language_code: str) -> Optional[Dict[str, Any]]:
        """Get lip sync job for a job and language."""
        try:
            result = self.client.table('lip_sync_jobs').select('*')\
                .eq('job_id', job_id)\
                .eq('language_code', language_code)\
                .single().execute()
            return result.data if result.data else None
        except Exception as e:
            print(f"Error getting lip sync job for {job_id}, lang {language_code}: {e}")
            return None
    
    def get_all_lip_sync_jobs(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all lip sync jobs for a job."""
        try:
            result = self.client.table('lip_sync_jobs').select('*').eq('job_id', job_id).execute()
            return result.data or []
        except Exception as e:
            print(f"Error getting lip sync jobs for job {job_id}: {e}")
            return []


# Create singleton instance
supabase_service = SupabaseService()
