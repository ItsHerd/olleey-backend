"""Script to seed an approval-needed job for testuser."""
import sys
import os
import uuid
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firestore import firestore_service
from firebase_admin import firestore

def seed_approval_job():
    user_id = "5TEUt0AICGcrKAum7LJauZJcODq1"
    print(f"Seeding approval job for user: {user_id}")
    
    # 1. Create Job in waiting_approval
    job_id = str(uuid.uuid4())
    source_video_id = "dQw4w9WgXcQ"
    
    job_data = {
        'source_video_id': source_video_id,
        'source_channel_id': "UCmock_main_channel_123",
        'user_id': user_id,
        'project_id': None,
        'status': 'waiting_approval',
        'target_languages': ['es', 'de'],
        'progress': 90,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }
    
    print(f"Creating job {job_id}...")
    firestore_service.db.collection('processing_jobs').document(job_id).set(job_data)
    
    # 2. Create Localized Videos in waiting_approval
    languages = ['es', 'de']
    
    for lang in languages:
        video_id = str(uuid.uuid4())
        video_data = {
            'job_id': job_id,
            'source_video_id': source_video_id,
            'localized_video_id': None,
            'language_code': lang,
            'channel_id': f"UCmock_{lang}_channel",
            'status': 'waiting_approval',
            'storage_url': f"/storage/videos/mock_dub_{lang}.mp4",
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        print(f"Creating localized video for {lang}...")
        firestore_service.db.collection('localized_videos').document(video_id).set(video_data)

    print("✅ Seed complete! Job ready for approval.")
    print(f"Job ID: {job_id}")

if __name__ == "__main__":
    seed_approval_job()
