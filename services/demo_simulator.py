"""
Demo Simulation Service

This service provides a fully interactive demo experience that:
- Maintains persistent demo user (demo@olleey.com)
- Resets demo data on logout
- Simulates all actions (approvals, processing, etc.)
- Provides realistic responses for all operations
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from firebase_admin import firestore as firestore_admin
from services.firestore import firestore_service

DEMO_EMAIL = "demo@olleey.com"
DEMO_PASSWORD = "password"

# Demo configuration
DEMO_CONFIG = {
    "master_channel": {
        "id": "UCdemo_master_english",
        "name": "Demo Master Channel (English)",
        "avatar": "https://via.placeholder.com/150/FF6B6B/FFFFFF?text=EN"
    },
    "language_channels": [
        {"code": "es", "name": "Spanish", "channel_id": "UCdemo_spanish", "channel_name": "Demo Spanish Channel"},
        {"code": "de", "name": "German", "channel_id": "UCdemo_german", "channel_name": "Demo German Channel"},
        {"code": "fr", "name": "French", "channel_id": "UCdemo_french", "channel_name": "Demo French Channel"},
        {"code": "it", "name": "Italian", "channel_id": "UCdemo_italian", "channel_name": "Demo Italian Channel"},
        {"code": "pt", "name": "Portuguese", "channel_id": "UCdemo_portuguese", "channel_name": "Demo Portuguese Channel"},
        {"code": "ja", "name": "Japanese", "channel_id": "UCdemo_japanese", "channel_name": "Demo Japanese Channel"},
    ],
    "source_videos": [
        {
            "id": "dQw4w9WgXcQ",
            "title": "Never Gonna Give You Up - Rick Astley",
            "description": "Official music video for Rick Astley's classic hit",
            "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "duration": 213,
        },
        {
            "id": "jNQXAC9IVRw",
            "title": "Me at the zoo",
            "description": "The first video ever uploaded to YouTube",
            "thumbnail": "https://i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg",
            "duration": 19,
        },
        {
            "id": "9bZkp7q19f0",
            "title": "PSY - GANGNAM STYLE",
            "description": "Official music video for Gangnam Style",
            "thumbnail": "https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg",
            "duration": 252,
        },
        {
            "id": "kJQP7kiw5Fk",
            "title": "Luis Fonsi - Despacito",
            "description": "Official music video for Despacito",
            "thumbnail": "https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg",
            "duration": 282,
        },
    ]
}


class DemoSimulator:
    """Handles demo user simulation and data reset."""
    
    def __init__(self):
        self.db = firestore_service.db
    
    def is_demo_user(self, user_id: str = None, email: str = None) -> bool:
        """Check if user is the demo user."""
        if email:
            return email == DEMO_EMAIL
        if user_id:
            try:
                from firebase_admin import auth
                user = auth.get_user(user_id)
                return user.email == DEMO_EMAIL
            except:
                return False
        return False
    
    async def reset_demo_data(self, user_id: str):
        """Reset demo data to initial state (called on logout)."""
        if not self.is_demo_user(user_id):
            return
        
        print(f"[DEMO] Resetting demo data for user: {user_id}")
        
        # Delete existing data
        await self._cleanup_demo_data(user_id)
        
        # Recreate fresh demo data
        await self._create_demo_data(user_id)
        
        print(f"[DEMO] Demo data reset complete")
    
    async def _cleanup_demo_data(self, user_id: str):
        """Clean up all demo data."""
        # Delete processing jobs
        jobs_ref = self.db.collection('processing_jobs')
        jobs_query = firestore_service._where(jobs_ref, 'user_id', '==', user_id)
        for doc in jobs_query.stream():
            doc.reference.delete()
        
        # Delete localized videos
        videos_ref = self.db.collection('localized_videos')
        videos_query = firestore_service._where(videos_ref, 'user_id', '==', user_id)
        for doc in videos_query.stream():
            doc.reference.delete()
        
        # Delete projects (keep default, remove others)
        projects_ref = self.db.collection('projects')
        projects_query = firestore_service._where(projects_ref, 'user_id', '==', user_id)
        for doc in projects_query.stream():
            data = doc.to_dict()
            if data.get('name') != 'Default Project':
                doc.reference.delete()
        
        # Delete language channels
        channels_ref = self.db.collection('language_channels')
        channels_query = firestore_service._where(channels_ref, 'user_id', '==', user_id)
        for doc in channels_query.stream():
            doc.reference.delete()
        
        # Delete youtube connections
        connections_ref = self.db.collection('youtube_connections')
        connections_query = firestore_service._where(connections_ref, 'user_id', '==', user_id)
        for doc in connections_query.stream():
            doc.reference.delete()
        
        # Delete activity logs
        logs_ref = self.db.collection('activity_logs')
        logs_query = firestore_service._where(logs_ref, 'user_id', '==', user_id)
        for doc in logs_query.stream():
            doc.reference.delete()
    
    async def _create_demo_data(self, user_id: str):
        """Create fresh demo data."""
        # Create master YouTube connection
        master_connection_id = firestore_service.create_youtube_connection(
            user_id=user_id,
            youtube_channel_id=DEMO_CONFIG["master_channel"]["id"],
            youtube_channel_name=DEMO_CONFIG["master_channel"]["name"],
            access_token="mock_demo_token",
            refresh_token="mock_demo_refresh",
            is_primary=True,
            channel_avatar_url=DEMO_CONFIG["master_channel"]["avatar"]
        )
        
        # Create projects
        project_workflow = firestore_service.create_project(
            user_id=user_id,
            name="Demo Workflow",
            master_connection_id=master_connection_id
        )
        
        project_music = firestore_service.create_project(
            user_id=user_id,
            name="Music Videos",
            master_connection_id=master_connection_id
        )
        
        # Create language channels
        for lang_info in DEMO_CONFIG["language_channels"]:
            firestore_service.create_language_channel(
                user_id=user_id,
                channel_id=lang_info["channel_id"],
                language_code=lang_info["code"],
                channel_name=lang_info["channel_name"],
                master_connection_id=master_connection_id,
                project_id=project_workflow
            )
        
        # Create demo jobs
        await self._create_demo_jobs(user_id, project_workflow, project_music, master_connection_id)
    
    async def _create_demo_jobs(self, user_id: str, project_workflow: str, project_music: str, master_channel_id: str):
        """Create demo jobs in various states."""
        # Job 1: Waiting Approval (3 languages)
        job_1 = str(uuid.uuid4())
        self.db.collection('processing_jobs').document(job_1).set({
            'source_video_id': DEMO_CONFIG["source_videos"][1]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_workflow,
            'status': 'waiting_approval',
            'target_languages': ['es', 'de', 'it'],
            'progress': 100,
            'is_simulation': True,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        
        # Create localized videos for job 1
        for lang in ['es', 'de', 'it']:
            self._create_localized_video(job_1, DEMO_CONFIG["source_videos"][1], lang, 'waiting_approval', user_id)
        
        # Job 2: Waiting Approval (5 languages)
        job_2 = str(uuid.uuid4())
        self.db.collection('processing_jobs').document(job_2).set({
            'source_video_id': DEMO_CONFIG["source_videos"][3]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_workflow,
            'status': 'waiting_approval',
            'target_languages': ['es', 'fr', 'de', 'it', 'pt'],
            'progress': 100,
            'is_simulation': True,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        
        for lang in ['es', 'fr', 'de', 'it', 'pt']:
            self._create_localized_video(job_2, DEMO_CONFIG["source_videos"][3], lang, 'waiting_approval', user_id)
        
        # Job 3: Processing (simulated progress)
        job_3 = str(uuid.uuid4())
        self.db.collection('processing_jobs').document(job_3).set({
            'source_video_id': DEMO_CONFIG["source_videos"][2]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_music,
            'status': 'processing',
            'target_languages': ['ja', 'pt'],
            'progress': 45,
            'is_simulation': True,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        
        for lang in ['ja', 'pt']:
            self._create_localized_video(job_3, DEMO_CONFIG["source_videos"][2], lang, 'processing', user_id)
        
        # Job 4: Completed
        job_4 = str(uuid.uuid4())
        self.db.collection('processing_jobs').document(job_4).set({
            'source_video_id': DEMO_CONFIG["source_videos"][0]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_music,
            'status': 'completed',
            'target_languages': ['es', 'de', 'fr'],
            'progress': 100,
            'is_simulation': True,
            'completed_at': firestore_admin.SERVER_TIMESTAMP,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        
        for lang in ['es', 'de', 'fr']:
            self._create_localized_video(job_4, DEMO_CONFIG["source_videos"][0], lang, 'published', user_id)
    
    def _create_localized_video(self, job_id: str, source_video: Dict, lang_code: str, status: str, user_id: str):
        """Create a localized video."""
        lang_names = {'es': 'Spanish', 'de': 'German', 'fr': 'French', 'it': 'Italian', 'pt': 'Portuguese', 'ja': 'Japanese'}
        lang_name = lang_names.get(lang_code, lang_code.upper())
        channel_id = f"UCdemo_{lang_code}"
        
        video_id = str(uuid.uuid4())
        storage_url = None
        localized_video_id = None
        
        if status in ['waiting_approval', 'published']:
            storage_url = f"gs://demo-bucket/videos/{job_id}/{lang_code}/output.mp4"
        
        if status == 'published':
            localized_video_id = f"VID{uuid.uuid4().hex[:10]}"
        
        self.db.collection('localized_videos').document(video_id).set({
            'job_id': job_id,
            'source_video_id': source_video['id'],
            'localized_video_id': localized_video_id,
            'language_code': lang_code,
            'channel_id': channel_id,
            'user_id': user_id,
            'status': status,
            'storage_url': storage_url,
            'thumbnail_url': source_video['thumbnail'],
            'title': f"{source_video['title']} ({lang_name} Dub)",
            'description': f"AI-dubbed version in {lang_name}. Demo simulation.",
            'is_simulation': True,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
    
    async def simulate_approval(self, user_id: str, job_id: str, video_ids: List[str], action: str):
        """Simulate video approval/rejection with realistic delays."""
        if not self.is_demo_user(user_id):
            return
        
        print(f"[DEMO] Simulating {action} for job {job_id}, videos: {video_ids}")
        
        # Simulate processing delay
        await asyncio.sleep(1)
        
        if action == "approve":
            # Update videos to published status
            for video_id in video_ids:
                video_ref = self.db.collection('localized_videos').document(video_id)
                video_ref.update({
                    'status': 'published',
                    'localized_video_id': f"VID{uuid.uuid4().hex[:10]}",
                    'published_at': firestore_admin.SERVER_TIMESTAMP,
                    'updated_at': firestore_admin.SERVER_TIMESTAMP
                })
            
            # Check if all videos are now published/rejected
            job_ref = self.db.collection('processing_jobs').document(job_id)
            job = job_ref.get().to_dict()
            
            videos_ref = self.db.collection('localized_videos')
            videos_query = firestore_service._where(videos_ref, 'job_id', '==', job_id)
            all_videos = list(videos_query.stream())
            
            all_decided = all(
                v.to_dict().get('status') in ['published', 'rejected']
                for v in all_videos
            )
            
            if all_decided:
                job_ref.update({
                    'status': 'completed',
                    'completed_at': firestore_admin.SERVER_TIMESTAMP,
                    'updated_at': firestore_admin.SERVER_TIMESTAMP
                })
        
        elif action == "reject":
            # Update videos to rejected status
            for video_id in video_ids:
                video_ref = self.db.collection('localized_videos').document(video_id)
                video_ref.update({
                    'status': 'rejected',
                    'updated_at': firestore_admin.SERVER_TIMESTAMP
                })
        
        # Log activity
        firestore_service.log_activity(
            user_id=user_id,
            project_id=job.get('project_id'),
            action=f"Videos {action}d",
            status='success',
            details=f"{len(video_ids)} video(s) {action}d"
        )
    
    async def simulate_processing_progress(self, user_id: str, job_id: str):
        """Simulate processing progress for a job."""
        if not self.is_demo_user(user_id):
            return
        
        job_ref = self.db.collection('processing_jobs').document(job_id)
        job = job_ref.get()
        
        if not job.exists:
            return
        
        job_data = job.to_dict()
        current_progress = job_data.get('progress', 0)
        
        # Increment progress
        new_progress = min(current_progress + 15, 95)  # Cap at 95% until completion
        
        job_ref.update({
            'progress': new_progress,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        
        # Update video statuses if needed
        if new_progress >= 95:
            videos_ref = self.db.collection('localized_videos')
            videos_query = firestore_service._where(videos_ref, 'job_id', '==', job_id)
            for video_doc in videos_query.stream():
                video_doc.reference.update({
                    'status': 'waiting_approval',
                    'storage_url': f"gs://demo-bucket/videos/{job_id}/{video_doc.to_dict()['language_code']}/output.mp4",
                    'updated_at': firestore_admin.SERVER_TIMESTAMP
                })
            
            job_ref.update({
                'status': 'waiting_approval',
                'progress': 100,
                'updated_at': firestore_admin.SERVER_TIMESTAMP
            })
    
    async def simulate_job_creation(self, user_id: str, source_video_id: str, target_languages: List[str], project_id: str):
        """Simulate creating a new dubbing job."""
        if not self.is_demo_user(user_id):
            return None
        
        print(f"[DEMO] Simulating job creation for video {source_video_id}")
        
        # Find video info
        video_info = next(
            (v for v in DEMO_CONFIG["source_videos"] if v['id'] == source_video_id),
            DEMO_CONFIG["source_videos"][0]
        )
        
        # Create job
        job_id = str(uuid.uuid4())
        master_channel_id = DEMO_CONFIG["master_channel"]["id"]
        
        self.db.collection('processing_jobs').document(job_id).set({
            'source_video_id': source_video_id,
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_id,
            'status': 'processing',
            'target_languages': target_languages,
            'progress': 0,
            'is_simulation': True,
            'created_at': firestore_admin.SERVER_TIMESTAMP,
            'updated_at': firestore_admin.SERVER_TIMESTAMP
        })
        
        # Create placeholder videos
        for lang in target_languages:
            self._create_localized_video(job_id, video_info, lang, 'processing', user_id)
        
        # Start background progress simulation
        asyncio.create_task(self._simulate_job_progress(user_id, job_id))
        
        return job_id
    
    async def _simulate_job_progress(self, user_id: str, job_id: str):
        """Background task to simulate job progress."""
        while True:
            await asyncio.sleep(10)  # Update every 10 seconds
            
            job_ref = self.db.collection('processing_jobs').document(job_id)
            job = job_ref.get()
            
            if not job.exists:
                break
            
            job_data = job.to_dict()
            status = job_data.get('status')
            
            if status != 'processing':
                break
            
            await self.simulate_processing_progress(user_id, job_id)


# Global simulator instance
demo_simulator = DemoSimulator()
