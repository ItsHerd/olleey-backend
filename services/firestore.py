"""Firebase Firestore service for metadata storage."""
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore as firestore_admin
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import uuid
import os

from config import settings

try:
    # Newer google-cloud-firestore prefers the 'filter=' keyword with FieldFilter
    # firebase-admin bundles google-cloud-firestore, so this import should work when available.
    from google.cloud.firestore_v1 import FieldFilter  # type: ignore
except Exception:  # pragma: no cover
    FieldFilter = None  # type: ignore


class FirestoreService:
    """Service for Firestore operations."""

    @staticmethod
    def _where(query, field: str, op: str, value):
        """
        Apply a Firestore where filter in a way that avoids deprecation warnings
        on newer google-cloud-firestore versions (uses filter=FieldFilter),
        while remaining compatible with older versions (positional args).
        """
        if FieldFilter is not None:
            try:
                return query.where(filter=FieldFilter(field, op, value))
            except TypeError:
                # Older client doesn't support filter= keyword
                return query.where(field, op, value)
        return query.where(field, op, value)
    
    def __init__(self):
        """Initialize Firestore client using firebase-admin."""
        # Initialize Firebase Admin SDK if not already initialized
        if not firebase_admin._apps:
            project_id = getattr(settings, 'firebase_project_id', 'vox-translate-b8c94')
            credentials_path = getattr(settings, 'firebase_credentials_path', None)
            
            # Try to find credentials file
            if credentials_path:
                # Check if path is relative or absolute
                if not os.path.isabs(credentials_path):
                    # Relative path - check from project root
                    import pathlib
                    project_root = pathlib.Path(__file__).parent.parent
                    credentials_path = str(project_root / credentials_path)
                
                if os.path.exists(credentials_path):
                    # Use service account key file
                    cred = credentials.Certificate(credentials_path)
                    firebase_admin.initialize_app(cred, {
                        'projectId': project_id
                    })
                else:
                    # Fallback to environment variable or default
                    if os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
                        cred = credentials.ApplicationDefault()
                        firebase_admin.initialize_app(cred, {
                            'projectId': project_id
                        })
                    else:
                        # Use default credentials (for GCP environments)
                        cred = credentials.ApplicationDefault()
                        firebase_admin.initialize_app(cred)
            elif os.getenv('GOOGLE_APPLICATION_CREDENTIALS'):
                # Use credentials from environment variable
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {
                    'projectId': project_id
                })
            else:
                # Use default credentials (for GCP environments)
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred)
        
        # Get Firestore client
        self.db = firestore_admin.client()
    
    # User operations
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID."""
        doc_ref = self.db.collection('users').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data['user_id'] = doc.id
            return data
        return None
    
    def create_or_update_user(self, user_id: str, email: Optional[str], 
                              access_token: str, refresh_token: str,
                              token_expiry: Optional[datetime] = None) -> Dict[str, Any]:
        """Create or update user."""
        doc_ref = self.db.collection('users').document(user_id)
        data = {
            'email': email,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_expiry': token_expiry,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        }
        doc_ref.set(data, merge=True)
        # Removed redundant .get() check for efficiency
        return {'user_id': user_id, **data}
    
    # Subscription operations
    def create_subscription(self, user_id: str, channel_id: str, callback_url: str,
                           topic: str, lease_seconds: int, 
                           expires_at: Optional[datetime] = None,
                           secret: Optional[str] = None) -> str:
        """Create PubSubHubbub subscription."""
        subscription_id = str(uuid.uuid4())
        doc_ref = self.db.collection('subscriptions').document(subscription_id)
        doc_ref.set({
            'user_id': user_id,
            'channel_id': channel_id,
            'callback_url': callback_url,
            'topic': topic,
            'lease_seconds': lease_seconds,
            'expires_at': expires_at,
            'secret': secret,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        return subscription_id
    
    def get_subscription_by_topic(self, topic: str) -> Optional[Dict[str, Any]]:
        """Get subscription by topic."""
        query = self._where(self.db.collection('subscriptions'), 'topic', '==', topic).limit(1)
        docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    def get_subscription_by_channel(self, user_id: str, channel_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by channel."""
        if user_id:
            query = self._where(self.db.collection('subscriptions'), 'user_id', '==', user_id)
            query = self._where(query, 'channel_id', '==', channel_id).limit(1)
            docs = query.stream()
        else:
            # Search by channel_id only if user_id not provided
            query = self._where(self.db.collection('subscriptions'), 'channel_id', '==', channel_id).limit(1)
            docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    def get_subscription(self, subscription_id: str) -> Optional[Dict[str, Any]]:
        """Get subscription by ID."""
        doc = self.db.collection('subscriptions').document(subscription_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    def delete_subscription(self, subscription_id: str):
        """Delete subscription."""
        self.db.collection('subscriptions').document(subscription_id).delete()
    
    def update_subscription_lease(self, subscription_id: str, expires_at: datetime, lease_seconds: int):
        """Update subscription lease."""
        self.db.collection('subscriptions').document(subscription_id).update({
            'expires_at': expires_at,
            'lease_seconds': lease_seconds,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
    
    # Project operations
    def create_project(self, user_id: str, name: str, master_connection_id: Optional[str] = None) -> str:
        """Create a new project."""
        project_id = str(uuid.uuid4())
        doc_ref = self.db.collection('projects').document(project_id)
        doc_ref.set({
            'user_id': user_id,
            'name': name,
            'master_connection_id': master_connection_id,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        return project_id

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID."""
        doc = self.db.collection('projects').document(project_id).get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None

    def list_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """List all projects for a user."""
        docs = self._where(self.db.collection('projects'), 'user_id', '==', user_id).stream()
        projects = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            projects.append(data)
        # Sort by created_at in memory
        projects.sort(key=lambda x: x.get('created_at', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        return projects

    def update_project(self, project_id: str, **updates):
        """Update project details."""
        updates['updated_at'] = firestore_admin.SERVER_TIMESTAMP
        self.db.collection('projects').document(project_id).update(updates)

    def delete_project(self, project_id: str):
        """Delete a project."""
        self.db.collection('projects').document(project_id).delete()

    # Activity Log operations
    def log_activity(self, user_id: str, project_id: Optional[str], action: str, 
                     status: str = 'info', details: Optional[str] = None) -> str:
        """Create a project-specific activity log entry."""
        log_id = str(uuid.uuid4())
        doc_ref = self.db.collection('activity_logs').document(log_id)
        doc_ref.set({
            'user_id': user_id,
            'project_id': project_id,
            'action': action,
            'status': status,  # info, success, warning, error
            'details': details,
            'timestamp': firestore_admin.SERVER_TIMESTAMP
        })
        return log_id

    def list_activity_logs(self, user_id: str, project_id: Optional[str] = None, 
                           limit: int = 50) -> List[Dict[str, Any]]:
        """List activity logs for a user or specific project."""
        # Query without ordering to avoid composite index requirement
        query = self._where(self.db.collection('activity_logs'), 'user_id', '==', user_id)
        if project_id:
            query = self._where(query, 'project_id', '==', project_id)
        
        # Get all docs and sort in memory
        docs = query.limit(limit * 2).stream()  # Get more to ensure we have enough after filtering
        
        logs = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            logs.append(data)
        
        # Sort by timestamp in memory
        logs.sort(key=lambda x: x.get('timestamp', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        
        return logs[:limit]

    # Processing Job operations
    def create_processing_job(self, source_video_id: str, source_channel_id: str,
                            user_id: str, target_languages: List[str], project_id: Optional[str] = None,
                            is_simulation: bool = False) -> str:
        """Create processing job."""
        job_id = str(uuid.uuid4())
        doc_ref = self.db.collection('processing_jobs').document(job_id)
        doc_ref.set({
            'source_video_id': source_video_id,
            'source_channel_id': source_channel_id,
            'user_id': user_id,
            'project_id': project_id,
            'status': 'pending',
            'target_languages': target_languages,
            'progress': 0,
            'is_simulation': is_simulation,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        return job_id
    
    def get_processing_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get processing job by ID."""
        doc_ref = self.db.collection('processing_jobs').document(job_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    def update_processing_job(self, job_id: str, **updates):
        """Update processing job."""
        updates['updated_at'] = firestore_admin.SERVER_TIMESTAMP
        self.db.collection('processing_jobs').document(job_id).update(updates)
    
    def list_processing_jobs(self, user_id: str, status: Optional[str] = None,
                           limit: int = 20, offset: int = 0, project_id: Optional[str] = None) -> tuple[List[Dict[str, Any]], int]:
        """List processing jobs for user, optionally filtered by project."""
        query = self._where(self.db.collection('processing_jobs'), 'user_id', '==', user_id)
        
        if project_id:
            query = self._where(query, 'project_id', '==', project_id)
            
        if status:
            query = self._where(query, 'status', '==', status)
        
        # Get all matching documents (without order_by to avoid index requirement)
        # We'll sort in-memory instead
        jobs = []
        for doc in query.stream():
            data = doc.to_dict()
            data['id'] = doc.id
            jobs.append(data)
        
        # Sort by created_at in Python (descending - newest first)
        jobs.sort(key=lambda x: x.get('created_at', datetime.min.replace(tzinfo=timezone.utc)), reverse=True)
        
        # Get total count
        total = len(jobs)
        
        # Apply pagination in Python
        start = offset
        end = offset + limit
        jobs = jobs[start:end]
        
        return jobs, total
    
    def get_job_by_video(self, source_video_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get job by source video ID."""
        query = self._where(self.db.collection('processing_jobs'), 'source_video_id', '==', source_video_id)
        query = self._where(query, 'user_id', '==', user_id).limit(1)
        docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    # Language Channel operations
    def create_language_channel(self, user_id: str, channel_id: str,
                               language_code: str,
                               channel_name: Optional[str] = None,
                               channel_avatar_url: Optional[str] = None,
                               master_connection_id: Optional[str] = None,
                               project_id: Optional[str] = None) -> str:
        """Create language channel with a single associated language."""
        
        channel_doc_id = str(uuid.uuid4())
        doc_ref = self.db.collection('language_channels').document(channel_doc_id)
        doc_ref.set({
            'user_id': user_id,
            'project_id': project_id,
            'channel_id': channel_id,
            'language_code': language_code,
            'channel_name': channel_name,
            'channel_avatar_url': channel_avatar_url,
            'master_connection_id': master_connection_id,  # Associate with master
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        return channel_doc_id
    
    def get_language_channels(self, user_id: str, project_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all language channels for user, optionally filtered by project."""
        query = self._where(self.db.collection('language_channels'), 'user_id', '==', user_id)
        
        if project_id:
            query = self._where(query, 'project_id', '==', project_id)
            
        docs = query.stream()
        channels = []
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            channels.append(data)
        return channels
    
    def get_language_channel_by_language(self, user_id: str, language_code: str) -> Optional[Dict[str, Any]]:
        """Get language channel by language code."""
        query = self._where(self.db.collection('language_channels'), 'user_id', '==', user_id)
        query = self._where(query, 'language_code', '==', language_code).limit(1)
        docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            data['id'] = doc.id
            return data
        return None
    
    def update_language_channel(self, channel_id: str, user_id: str, **updates):
        """Update language channel."""
        query = self._where(self.db.collection('language_channels'), 'channel_id', '==', channel_id)
        query = self._where(query, 'user_id', '==', user_id)
        docs = query.stream()
        for doc in docs:
            updates['updated_at'] = firestore_admin.SERVER_TIMESTAMP
            doc.reference.update(updates)
            return True
        return False
    
    def delete_language_channel(self, channel_id: str, user_id: str):
        """Delete language channel."""
        query = self._where(self.db.collection('language_channels'), 'channel_id', '==', channel_id)
        query = self._where(query, 'user_id', '==', user_id)
        docs = query.stream()
        for doc in docs:
            doc.reference.delete()
    
    # Localized Video operations
    def create_localized_video(self, job_id: str, source_video_id: str,
                               language_code: str, channel_id: str,
                               user_id: Optional[str] = None,
                              localized_video_id: Optional[str] = None,
                              status: str = 'pending',
                              storage_url: Optional[str] = None,
                              dubbed_audio_url: Optional[str] = None,
                              thumbnail_url: Optional[str] = None,
                              title: Optional[str] = None,
                              description: Optional[str] = None) -> str:
        """Create localized video record."""
        video_id = str(uuid.uuid4())
        doc_ref = self.db.collection('localized_videos').document(video_id)
        doc_ref.set({
            'job_id': job_id,
            'user_id': user_id,
            'source_video_id': source_video_id,
            'localized_video_id': localized_video_id,
            'language_code': language_code,
            'channel_id': channel_id,
            'status': status,
            'storage_url': storage_url,  # URL to video in cloud storage
            'dubbed_audio_url': dubbed_audio_url,  # URL to dubbed audio preview
            'thumbnail_url': thumbnail_url,  # Thumbnail for preview
            'title': title,  # Translated title
            'description': description,  # Translated description
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        return video_id
    
    def update_localized_video(self, video_id: str, **updates):
        """Update localized video."""
        updates['updated_at'] = firestore_admin.SERVER_TIMESTAMP
        self.db.collection('localized_videos').document(video_id).update(updates)
    
    def get_localized_video_by_localized_id(self, localized_video_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get localized video record by localized_video_id (YouTube video ID)."""
        query = self._where(
            self.db.collection('localized_videos'),
            'localized_video_id', '==', localized_video_id
        )
        # Optimized: Filter by user_id if possible (for new records)
        query = self._where(query, 'user_id', '==', user_id)
        
        docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            return {'id': doc.id, **data}
            
        # Fallback for old records without user_id (expensive loop)
        # We can remove this once data is backfilled
        query_legacy = self._where(
            self.db.collection('localized_videos'),
            'localized_video_id', '==', localized_video_id
        )
        for doc in query_legacy.stream():
            data = doc.to_dict()
            if not data.get('user_id'):
                job = self.get_processing_job(data.get('job_id'))
                if job and job.get('user_id') == user_id:
                    return {'id': doc.id, **data}
        return None
    
    def get_localized_videos_by_source_id(self, source_video_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get all localized videos for a source video ID."""
        query = self._where(
            self.db.collection('localized_videos'),
            'source_video_id', '==', source_video_id
        )
        # Optimized: Filter by user_id
        query = self._where(query, 'user_id', '==', user_id)
        
        docs = query.stream()
        results = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        
        if results:
            return results
            
        # Fallback for old records without user_id
        query_legacy = self._where(
            self.db.collection('localized_videos'),
            'source_video_id', '==', source_video_id
        )
        for doc in query_legacy.stream():
            data = doc.to_dict()
            if not data.get('user_id'):
                job = self.get_processing_job(data.get('job_id'))
                if job and job.get('user_id') == user_id:
                    results.append({'id': doc.id, **data})
        return results
    
    def get_localized_videos_by_job_id(self, job_id: str) -> List[Dict[str, Any]]:
        """Get all localized videos for a job ID."""
        query = self._where(
            self.db.collection('localized_videos'),
            'job_id', '==', job_id
        )
        docs = query.stream()
        return [{'id': doc.id, **doc.to_dict()} for doc in docs]
    
    def get_all_localized_videos_for_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get ALL localized videos for a user.
        
        This is optimized to avoid N+1 queries when listing videos.
        Instead of querying for each video ID, we fetch all localized videos for the user
        (filtering by job ownership is implicit if we trust the localized_videos table structure,
         but ideally localized_videos should have user_id. Since it doesn't, we rely on job_id link).
         
        However, to be safe and performant, we might need a composite index if we filter by job field.
        A better approach given existing schema:
        1. Fetch all jobs for user (already efficient)
        2. Fetch all localized videos that match these job IDs.
           - But 'in' query on job_id limit is 30.
        
        Alternative:
        Fetch ALL localized videos. This collection might be large.
        
        Best approach for now without schema change:
        fetch all localized_videos (if collection is not massive) or ADD user_id to localized_videos schema.
        
        Let's ADD user_id to localized_videos queries if possible, but the schema doesn't have it.
        We will iterate over all localized videos and filter in memory if the dataset is small (unlikely for prod).
        
        OPTIMAL FIX for N+1:
        We will query localized_videos by user_id directly.
        """
        query = self._where(self.db.collection('localized_videos'), 'user_id', '==', user_id)
        docs = query.stream()
        results = [{'id': doc.id, **doc.to_dict()} for doc in docs]
        
        # If we have results from optimized query, return them
        if results:
            return results

        # Fallback for legacy data (as implemented before, but keeping it safe)
        # Get all user jobs first
        jobs, _ = self.list_processing_jobs(user_id, limit=1000)
        job_ids = [j['id'] for j in jobs]
        
        if not job_ids:
            return []
            
        # Batch fetch localized videos by job_id
        # Firestore 'in' limit is 30.
        results = []
        chunk_size = 30
        for i in range(0, len(job_ids), chunk_size):
            chunk = job_ids[i:i + chunk_size]
            query = self._where(self.db.collection('localized_videos'), 'job_id', 'in', chunk)
            docs = query.stream()
            for doc in docs:
                results.append({'id': doc.id, **doc.to_dict()})
                
        return results
    
    # YouTube Connection operations
    def create_youtube_connection(self, user_id: str, youtube_channel_id: str,
                                  access_token: str, refresh_token: str,
                                  youtube_channel_name: Optional[str] = None,
                                  token_expiry: Optional[datetime] = None,
                                  is_primary: bool = False,
                                  channel_avatar_url: Optional[str] = None,
                                  master_connection_id: Optional[str] = None,
                                  language_code: Optional[str] = None) -> str:
        """Create YouTube channel connection with a single associated language."""
        # If primary, default to English if no language provided
        if is_primary and language_code is None:
            language_code = 'en'
            
        connection_id = str(uuid.uuid4())
        doc_ref = self.db.collection('youtube_connections').document(connection_id)
        doc_ref.set({
            'user_id': user_id,
            'youtube_channel_id': youtube_channel_id,
            'youtube_channel_name': youtube_channel_name,
            'channel_avatar_url': channel_avatar_url,
            'access_token': access_token,
            'refresh_token': refresh_token,
            'token_expiry': token_expiry,
            'is_primary': is_primary,
            'language_code': language_code,
            'master_connection_id': master_connection_id,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        return connection_id
    
    def get_youtube_connections(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all YouTube connections for a user."""
        docs = self._where(self.db.collection('youtube_connections'), 'user_id', '==', user_id).stream()
        connections = []
        for doc in docs:
            data = doc.to_dict()
            data['connection_id'] = doc.id
            connections.append(data)
        return connections
    
    def get_youtube_connection(self, connection_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get YouTube connection by ID."""
        doc = self.db.collection('youtube_connections').document(connection_id).get()
        if doc.exists:
            data = doc.to_dict()
            if data.get('user_id') != user_id:
                return None  # Connection doesn't belong to user
            data['connection_id'] = doc.id
            return data
        return None
    
    def get_primary_youtube_connection(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's primary YouTube connection."""
        query = self._where(self.db.collection('youtube_connections'), 'user_id', '==', user_id)
        query = self._where(query, 'is_primary', '==', True).limit(1)
        docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            data['connection_id'] = doc.id
            return data
        return None
    
    def get_youtube_connection_by_channel(self, user_id: str, youtube_channel_id: str) -> Optional[Dict[str, Any]]:
        """Get YouTube connection by channel ID."""
        query = self._where(self.db.collection('youtube_connections'), 'user_id', '==', user_id)
        query = self._where(query, 'youtube_channel_id', '==', youtube_channel_id).limit(1)
        docs = query.stream()
        for doc in docs:
            data = doc.to_dict()
            data['connection_id'] = doc.id
            return data
        return None
    
    def update_youtube_connection(self, connection_id: str, **updates):
        """Update YouTube connection."""
        updates['updated_at'] = firestore_admin.SERVER_TIMESTAMP
        self.db.collection('youtube_connections').document(connection_id).update(updates)
    
    def set_primary_connection(self, connection_id: str, user_id: str):
        """Set a connection as primary and unset all others."""
        # Verify ownership
        connection = self.get_youtube_connection(connection_id, user_id)
        if not connection:
            return False
        
        # Unset all other primary connections for this user
        all_connections = self.get_youtube_connections(user_id)
        for conn in all_connections:
            conn_id = conn.get('connection_id')
            if conn_id and conn_id != connection_id:
                self.update_youtube_connection(conn_id, is_primary=False)
        
        # Set this connection as primary
        self.update_youtube_connection(connection_id, is_primary=True)
        return True
    
    def delete_youtube_connection(self, connection_id: str, user_id: str):
        """Delete YouTube connection and unassign associated language channels.
        
        If this is a satellite connection, unassigns language channels from the parent master
        by setting their master_connection_id to None, instead of deleting them.
        """
        # Verify ownership before deleting
        connection = self.get_youtube_connection(connection_id, user_id)
        if not connection:
            return False
        
        # Get the youtube_channel_id and master_connection_id before deleting
        youtube_channel_id = connection.get('youtube_channel_id')
        master_connection_id = connection.get('master_connection_id')
        
        # Unassign associated language channels (if any)
        # Language channels are linked by channel_id which matches youtube_channel_id
        unassigned_count = 0
        if youtube_channel_id:
            # Find all language channels with this channel_id and matching master_connection_id
            query = self._where(self.db.collection('language_channels'), 'channel_id', '==', youtube_channel_id)
            query = self._where(query, 'user_id', '==', user_id)
            if master_connection_id:
                # Only unassign language channels that are associated with this master
                query = self._where(query, 'master_connection_id', '==', master_connection_id)
            
            language_channel_docs = query.stream()
            
            # Unassign language channels by setting master_connection_id to None
            for doc in language_channel_docs:
                doc.reference.update({
                    'master_connection_id': None,
                    'updated_at': firestore_admin.SERVER_TIMESTAMP
                })
                unassigned_count += 1
            
            if unassigned_count > 0:
                print(f"[DEBUG] Unassigned {unassigned_count} language channel(s) from connection {connection_id}")
        
        # Delete the YouTube connection
        self.db.collection('youtube_connections').document(connection_id).delete()
        return True
    
    def get_youtube_credentials(self, user_id: str, connection_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get YouTube OAuth credentials for a user.
        If connection_id is provided, get that specific connection.
        Otherwise, get the primary connection.
        """
        if connection_id:
            connection = self.get_youtube_connection(connection_id, user_id)
        else:
            connection = self.get_primary_youtube_connection(user_id)
        
        if not connection:
            return None
        
        return {
            'access_token': connection.get('access_token'),
            'refresh_token': connection.get('refresh_token'),
            'token_expiry': connection.get('token_expiry'),
            'youtube_channel_id': connection.get('youtube_channel_id'),
            'connection_id': connection.get('connection_id')
        }
    
    def get_user_settings(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user settings."""
        doc_ref = self.db.collection('user_settings').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict()
        return None
    
    def update_user_settings(self, user_id: str, **updates):
        """Update user settings."""
        doc_ref = self.db.collection('user_settings').document(user_id)
        updates['updated_at'] = firestore_admin.SERVER_TIMESTAMP
        doc_ref.set(updates, merge=True)
        # Removed redundant .get() check


# Global Firestore service instance
# Global Firestore service instance
firestore_service = FirestoreService()

