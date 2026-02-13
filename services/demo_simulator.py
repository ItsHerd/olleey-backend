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
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any
from services.supabase_db import supabase_service as firestore_service

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
            "id": "demo_real_video_001",
            "title": "The Nature of Startups with YC CEO",
            "title_es": "La Naturaleza de las Startups con el CEO de YC",
            "description": "In-depth discussion about the fundamental nature of startups and what it takes to build something people want.",
            "description_es": "Discusión profunda sobre la naturaleza fundamental de las startups y lo que se necesita para construir algo que la gente quiera.",
            "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "duration": 180,
            "views": 2500,
            "storage_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/en.mp4",
            "audio_url_es": "https://olleey-videos.s3.us-west-1.amazonaws.com/es-audio.mp3",
            "video_url_es": "https://olleey-videos.s3.us-west-1.amazonaws.com/es.mov"
        },
        {
            "id": "dQw4w9WgXcQ",
            "title": "Never Gonna Give You Up - Rick Astley",
            "description": "Official music video for Rick Astley's classic hit",
            "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "duration": 213,
            "views": 1400000000,
        },
        {
            "id": "jNQXAC9IVRw",
            "title": "Me at the zoo",
            "description": "The first video ever uploaded to YouTube",
            "thumbnail": "https://i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg",
            "duration": 19,
            "views": 280000000,
        },
        {
            "id": "9bZkp7q19f0",
            "title": "PSY - GANGNAM STYLE",
            "description": "Official music video for Gangnam Style",
            "thumbnail": "https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg",
            "duration": 252,
            "views": 4900000000,
        },
        {
            "id": "kJQP7kiw5Fk",
            "title": "Luis Fonsi - Despacito",
            "description": "Official music video for Despacito",
            "thumbnail": "https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg",
            "duration": 282,
            "views": 8300000000,
        },
        {
            "id": "OPf0YbXqDm0",
            "title": "Mark Ronson - Uptown Funk ft. Bruno Mars",
            "description": "Official music video for Uptown Funk",
            "thumbnail": "https://i.ytimg.com/vi/OPf0YbXqDm0/hqdefault.jpg",
            "duration": 269,
            "views": 4800000000,
        },
        {
            "id": "YQHsXMglC9A",
            "title": "Adele - Hello",
            "description": "Official music video for Hello by Adele",
            "thumbnail": "https://i.ytimg.com/vi/YQHsXMglC9A/hqdefault.jpg",
            "duration": 367,
            "views": 3400000000,
        },
        {
            "id": "RgKAFK5djSk",
            "title": "Wiz Khalifa - See You Again ft. Charlie Puth",
            "description": "Official music video for See You Again",
            "thumbnail": "https://i.ytimg.com/vi/RgKAFK5djSk/hqdefault.jpg",
            "duration": 229,
            "views": 6200000000,
        },
        {
            "id": "CevxZvSJLk8",
            "title": "Katy Perry - Roar",
            "description": "Official music video for Roar",
            "thumbnail": "https://i.ytimg.com/vi/CevxZvSJLk8/hqdefault.jpg",
            "duration": 263,
            "views": 3900000000,
        },
    ]
}


class DemoSimulator:
    """Handles demo user simulation and data reset."""
    
    def __init__(self):
        # Note: Demo simulator now uses Supabase instead of Firestore
        # Seeding functions that used self.db directly are disabled for now
        # Only is_demo_user() is needed for the mock pipeline to work
        pass
    
    def is_demo_user(self, user_id: str = None, email: str = None) -> bool:
        """Check if user is the demo user."""
        if email:
            return email == DEMO_EMAIL
        if user_id:
            try:
                user = firestore_service.get_user(user_id)
                if user:
                    return user.get("email") == DEMO_EMAIL
                return False
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
        try:
            firestore_service.client.table('processing_jobs').delete().eq('user_id', user_id).execute()
        except: pass
        
        # Delete localized videos
        try:
            firestore_service.client.table('localized_videos').delete().eq('user_id', user_id).execute()
        except: pass
        
        # Delete projects (keep default, remove others)
        try:
            firestore_service.client.table('projects').delete().eq('user_id', user_id).neq('name', 'Default Project').execute()
        except: pass
        
        # Delete language channels
        try:
            firestore_service.client.table('channels').delete().eq('user_id', user_id).execute()
        except: pass
        
        # Delete youtube connections
        try:
            firestore_service.client.table('youtube_connections').delete().eq('user_id', user_id).execute()
        except: pass
        
        # Delete activity logs
        try:
            firestore_service.client.table('activity_logs').delete().eq('user_id', user_id).execute()
        except: pass
    
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
        await self._create_demo_jobs(
            user_id,
            project_workflow,
            project_music,
            DEMO_CONFIG["master_channel"]["id"]
        )
        
        # Create initial activity logs
        self._create_demo_activities(user_id, project_workflow, project_music)
        
        print(f"[DEMO] Demo data creation complete for user: {user_id}")
    
    async def _create_demo_jobs(self, user_id: str, project_workflow: str, project_music: str, master_channel_id: str):
        """Create demo jobs in various states."""
        print(f"[DEMO] Creating demo jobs for user {user_id}")
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Job 1: Waiting Approval (3 languages)
        job_1 = str(uuid.uuid4())
        firestore_service.client.table('processing_jobs').insert({
            'job_id': job_1,
            'source_video_id': DEMO_CONFIG["source_videos"][1]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_workflow,
            'status': 'waiting_approval',
            'target_languages': ['es', 'de', 'it'],
            'progress': 100,
            'is_simulation': True,
            'created_at': now,
            'updated_at': now
        }).execute()
        
        # Create localized videos for job 1
        for lang in ['es', 'de', 'it']:
            self._create_localized_video(job_1, DEMO_CONFIG["source_videos"][1], lang, 'waiting_approval', user_id)
        
        # Job 2: Waiting Approval (5 languages)
        job_2 = str(uuid.uuid4())
        firestore_service.client.table('processing_jobs').insert({
            'job_id': job_2,
            'source_video_id': DEMO_CONFIG["source_videos"][3]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_workflow,
            'status': 'waiting_approval',
            'target_languages': ['es', 'fr', 'de', 'it', 'pt'],
            'progress': 100,
            'is_simulation': True,
            'created_at': now,
            'updated_at': now
        }).execute()
        
        for lang in ['es', 'fr', 'de', 'it', 'pt']:
            self._create_localized_video(job_2, DEMO_CONFIG["source_videos"][3], lang, 'waiting_approval', user_id)
        
        # Job 3: Processing (simulated progress)
        job_3 = str(uuid.uuid4())
        firestore_service.client.table('processing_jobs').insert({
            'job_id': job_3,
            'source_video_id': DEMO_CONFIG["source_videos"][2]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_music,
            'status': 'processing',
            'target_languages': ['ja', 'pt'],
            'progress': 45,
            'is_simulation': True,
            'created_at': now,
            'updated_at': now
        }).execute()
        
        for lang in ['ja', 'pt']:
            self._create_localized_video(job_3, DEMO_CONFIG["source_videos"][2], lang, 'processing', user_id)
        
        # Job 4: Completed
        job_4 = str(uuid.uuid4())
        firestore_service.client.table('processing_jobs').insert({
            'job_id': job_4,
            'source_video_id': DEMO_CONFIG["source_videos"][0]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_workflow,
            'status': 'completed',
            'target_languages': ['es', 'de', 'fr'],
            'progress': 100,
            'is_simulation': True,
            'completed_at': now,
            'created_at': now,
            'updated_at': now
        }).execute()
        
        for lang in ['es', 'de', 'fr']:
            self._create_localized_video(job_4, DEMO_CONFIG["source_videos"][0], lang, 'published', user_id)
        
        # Job 5: Published
        job_5 = str(uuid.uuid4())
        firestore_service.client.table('processing_jobs').insert({
            'job_id': job_5,
            'source_video_id': DEMO_CONFIG["source_videos"][1]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_workflow,
            'status': 'completed',
            'target_languages': ['es', 'fr', 'it', 'pt'],
            'progress': 100,
            'is_simulation': True,
            'completed_at': now,
            'created_at': now,
            'updated_at': now
        }).execute()
        
        for lang in ['es', 'fr', 'it', 'pt']:
            self._create_localized_video(job_5, DEMO_CONFIG["source_videos"][1], lang, 'published', user_id)
        
        # Job 6: Published
        job_6 = str(uuid.uuid4())
        firestore_service.client.table('processing_jobs').insert({
            'job_id': job_6,
            'source_video_id': DEMO_CONFIG["source_videos"][2]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_workflow,
            'status': 'completed',
            'target_languages': ['de', 'ja'],
            'progress': 100,
            'is_simulation': True,
            'completed_at': now,
            'created_at': now,
            'updated_at': now
        }).execute()
        
        for lang in ['de', 'ja']:
            self._create_localized_video(job_6, DEMO_CONFIG["source_videos"][2], lang, 'published', user_id)
        
        # Job 7: Published
        job_7 = str(uuid.uuid4())
        firestore_service.client.table('processing_jobs').insert({
            'job_id': job_7,
            'source_video_id': DEMO_CONFIG["source_videos"][3]['id'],
            'source_channel_id': master_channel_id,
            'user_id': user_id,
            'project_id': project_workflow,
            'status': 'completed',
            'target_languages': ['es', 'de', 'fr', 'pt', 'ja'],
            'progress': 100,
            'is_simulation': True,
            'completed_at': now,
            'created_at': now,
            'updated_at': now
        }).execute()
        
        for lang in ['es', 'de', 'fr', 'pt', 'ja']:
            self._create_localized_video(job_7, DEMO_CONFIG["source_videos"][3], lang, 'published', user_id)
        
        # More jobs for variety
        if len(DEMO_CONFIG["source_videos"]) > 4:
            job_8 = str(uuid.uuid4())
            firestore_service.client.table('processing_jobs').insert({
                'job_id': job_8,
                'source_video_id': DEMO_CONFIG["source_videos"][4]['id'],
                'source_channel_id': master_channel_id,
                'user_id': user_id,
                'project_id': project_workflow,
                'status': 'completed',
                'target_languages': ['es', 'fr', 'de'],
                'progress': 100,
                'is_simulation': True,
                'completed_at': now,
                'created_at': now,
                'updated_at': now
            }).execute()
            for lang in ['es', 'fr', 'de']:
                self._create_localized_video(job_8, DEMO_CONFIG["source_videos"][4], lang, 'published', user_id)
        
        if len(DEMO_CONFIG["source_videos"]) > 5:
            job_9 = str(uuid.uuid4())
            firestore_service.client.table('processing_jobs').insert({
                'job_id': job_9,
                'source_video_id': DEMO_CONFIG["source_videos"][5]['id'],
                'source_channel_id': master_channel_id,
                'user_id': user_id,
                'project_id': project_workflow,
                'status': 'completed',
                'target_languages': ['es', 'it', 'pt'],
                'progress': 100,
                'is_simulation': True,
                'completed_at': now,
                'created_at': now,
                'updated_at': now
            }).execute()
            for lang in ['es', 'it', 'pt']:
                self._create_localized_video(job_9, DEMO_CONFIG["source_videos"][5], lang, 'published', user_id)
        
        if len(DEMO_CONFIG["source_videos"]) > 6:
            job_10 = str(uuid.uuid4())
            firestore_service.client.table('processing_jobs').insert({
                'job_id': job_10,
                'source_video_id': DEMO_CONFIG["source_videos"][6]['id'],
                'source_channel_id': master_channel_id,
                'user_id': user_id,
                'project_id': project_workflow,
                'status': 'processing',
                'target_languages': ['es', 'de', 'fr'],
                'progress': 65,
                'is_simulation': True,
                'created_at': now,
                'updated_at': now
            }).execute()
            for lang in ['es', 'de', 'fr']:
                self._create_localized_video(job_10, DEMO_CONFIG["source_videos"][6], lang, 'processing', user_id)
        
        print(f"[DEMO] Finished creating all demo jobs")
    
    def _create_localized_video(self, job_id: str, source_video: Dict, lang_code: str, status: str, user_id: str):
        """Create a localized video."""
        lang_names = {'es': 'Spanish', 'de': 'German', 'fr': 'French', 'it': 'Italian', 'pt': 'Portuguese', 'ja': 'Japanese'}
        lang_name = lang_names.get(lang_code, lang_code.upper())
        channel_id = f"UCdemo_{lang_code}"
        
        video_id = str(uuid.uuid4())
        storage_url = None
        localized_video_id = None
        
        if status in ['waiting_approval', 'published']:
            if source_video['id'] == 'demo_real_video_001' and lang_code == 'es':
                storage_url = "https://olleey-videos.s3.us-west-1.amazonaws.com/es.mov"
            else:
                storage_url = f"gs://demo-bucket/videos/{job_id}/{lang_code}/output.mp4"
        
        if status == 'published':
            localized_video_id = f"VID{uuid.uuid4().hex[:10]}"
        
        now = datetime.now(timezone.utc).isoformat()
        
        video_data = {
            'id': video_id,
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
            'duration': source_video.get('duration', 210),
            'is_simulation': True,
            'created_at': now,
            'updated_at': now
        }
        
        if status == 'published':
            video_data['published_at'] = now
        
        firestore_service.client.table('localized_videos').insert(video_data).execute()
    
    def _create_demo_activities(self, user_id: str, project_workflow: str, project_music: str):
        """Create initial demo activity logs."""
        now = datetime.now(timezone.utc)
        
        activities = [
            {
                'user_id': user_id,
                'project_id': project_workflow,
                'action': 'Videos approved and published',
                'status': 'success',
                'details': 'Published 3 language version(s): Spanish, German, French',
                'timestamp': (now - timedelta(hours=5)).isoformat()
            },
            {
                'user_id': user_id,
                'project_id': project_workflow,
                'action': 'Video uploaded',
                'status': 'info',
                'details': 'Luis Fonsi - Despacito uploaded for dubbing',
                'timestamp': (now - timedelta(hours=2)).isoformat()
            },
            {
                'user_id': user_id,
                'project_id': project_workflow,
                'action': 'Processing started',
                'status': 'info',
                'details': 'Started dubbing to 5 languages',
                'timestamp': (now - timedelta(hours=1, minutes=55)).isoformat()
            },
            {
                'user_id': user_id,
                'project_id': project_workflow,
                'action': 'Processing completed',
                'status': 'success',
                'details': 'All language versions ready for review',
                'timestamp': (now - timedelta(hours=1, minutes=30)).isoformat()
            },
            {
                'user_id': user_id,
                'project_id': project_workflow,
                'action': 'Videos approved and published',
                'status': 'success',
                'details': 'Published 4 language version(s): Spanish, French, Italian, Portuguese',
                'timestamp': (now - timedelta(hours=1)).isoformat()
            }
        ]
        
        for activity in activities:
            log_id = str(uuid.uuid4())
            firestore_service.client.table('activity_logs').insert({
                'id': log_id,
                **activity
            }).execute()
        
        print(f"[DEMO] Created {len(activities)} activity logs")
    
    async def simulate_approval(self, user_id: str, job_id: str, video_ids: List[str], action: str):
        """Simulate video approval/rejection."""
        if not self.is_demo_user(user_id):
            return
        
        await asyncio.sleep(1)
        now = datetime.now(timezone.utc).isoformat()
        
        if action == "approve":
            for video_id in video_ids:
                firestore_service.client.table('localized_videos').update({
                    'status': 'published',
                    'localized_video_id': f"VID{uuid.uuid4().hex[:10]}",
                    'published_at': now,
                    'updated_at': now
                }).eq('id', video_id).execute()
            
            # Check if all videos decided
            all_videos = firestore_service.client.table('localized_videos').select('status').eq('job_id', job_id).execute().data
            all_decided = all(v.get('status') in ['published', 'rejected'] for v in all_videos)
            
            if all_decided:
                firestore_service.client.table('processing_jobs').update({
                    'status': 'completed',
                    'completed_at': now,
                    'updated_at': now
                }).eq('job_id', job_id).execute()
        
        elif action == "reject":
            for video_id in video_ids:
                firestore_service.client.table('localized_videos').update({
                    'status': 'rejected',
                    'updated_at': now
                }).eq('id', video_id).execute()
        
        # Log activity
        job = firestore_service.get_processing_job(job_id)
        if job:
            firestore_service.log_activity(
                user_id=user_id,
                project_id=job.get('project_id'),
                action="Videos approved and published" if action == "approve" else "Videos rejected",
                status='success' if action == "approve" else 'warning',
                details=f"{len(video_ids)} video(s) {action}d"
            )
    
    async def simulate_processing_progress(self, user_id: str, job_id: str):
        """Simulate processing progress for a job."""
        if not self.is_demo_user(user_id):
            return
        
        job = firestore_service.get_processing_job(job_id)
        if not job:
            return
        
        new_progress = min(job.get('progress', 0) + 15, 95)
        now = datetime.now(timezone.utc).isoformat()
        
        firestore_service.client.table('processing_jobs').update({
            'progress': new_progress,
            'updated_at': now
        }).eq('job_id', job_id).execute()
        
        if new_progress >= 95:
            firestore_service.client.table('localized_videos').update({
                'status': 'waiting_approval',
                'updated_at': now
            }).eq('job_id', job_id).execute()
            
            firestore_service.client.table('processing_jobs').update({
                'status': 'waiting_approval',
                'progress': 100,
                'updated_at': now
            }).eq('job_id', job_id).execute()
    
    async def simulate_job_creation(self, user_id: str, source_video_id: str, target_languages: List[str], project_id: str):
        """Simulate creating a new dubbing job."""
        if not self.is_demo_user(user_id):
            return None
        
        job_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        firestore_service.client.table('processing_jobs').insert({
            'job_id': job_id,
            'source_video_id': source_video_id,
            'source_channel_id': DEMO_CONFIG["master_channel"]["id"],
            'user_id': user_id,
            'project_id': project_id,
            'status': 'processing',
            'target_languages': target_languages,
            'progress': 0,
            'is_simulation': True,
            'created_at': now,
            'updated_at': now
        }).execute()
        
        # Start background simulation
        asyncio.create_task(self._simulate_job_progress(user_id, job_id))
        return job_id

    async def _simulate_job_progress(self, user_id: str, job_id: str):
        """Background task for job progress."""
        for _ in range(10):
            await asyncio.sleep(5)
            job = firestore_service.get_processing_job(job_id)
            if not job or job.get('status') != 'processing':
                break
            await self.simulate_processing_progress(user_id, job_id)

    async def start_processing(self, user_id: str, job_id: str, language_code: str = 'es') -> Dict[str, Any]:
        """Start processing a job."""
        now = datetime.now(timezone.utc).isoformat()
        firestore_service.client.table('processing_jobs').update({
            'status': 'processing',
            'progress': 0,
            'updated_at': now
        }).eq('job_id', job_id).execute()
        return {"status": "success"}
        
    async def update_localization_status(
        self,
        user_id: str,
        job_id: str,
        language_code: str,
        new_status: str
    ) -> Dict[str, Any]:
        """Update localization status interactively for demo."""
        if not self.is_demo_user(user_id):
            return {"success": False}
            
        now = datetime.now(timezone.utc).isoformat()
        
        updates = {
            'status': new_status,
            'updated_at': now
        }
        
        if new_status == 'published':
            updates['localized_video_id'] = f"demo_{language_code}_{uuid.uuid4().hex[:8]}"
            updates['published_at'] = now
            
        firestore_service.client.table('localized_videos').update(updates).eq('job_id', job_id).eq('language_code', language_code).execute()
        
        # Log activity
        job = firestore_service.get_processing_job(job_id)
        if job:
            firestore_service.log_activity(
                user_id=user_id,
                project_id=job.get('project_id'),
                action=f"Video {new_status}",
                status='success',
                details=f"Updated {language_code} to {new_status}"
            )
            
        return {"success": True, "status": new_status}


# Global simulator instance
demo_simulator = DemoSimulator()
