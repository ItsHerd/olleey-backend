
"""
Script to seed the REAL Test Firestore Database (olleey-test) with rich data.
Target User: L5gVvYWKdAMz7Fxdx6NmX39fzrX2
"""
import sys
import os
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure we use test environment
os.environ["ENVIRONMENT"] = "test"
# Ensure we definitely do NOT use mock DB
os.environ["USE_MOCK_DB"] = "false"

from services.firestore import firestore_service
from firebase_admin import firestore

def seed_test_db():
    TARGET_USER_ID = "L5gVvYWKdAMz7Fxdx6NmX39fzrX2"
    TARGET_EMAIL = "testuser@example.com"
    
    print(f"🌱 Seeding REAL Test DB (olleey-test) for user: {TARGET_USER_ID}")
    
    db = firestore_service
    
    # 1. Create/Update User
    print(f"Creating user record...")
    db.create_or_update_user(
        user_id=TARGET_USER_ID,
        email=TARGET_EMAIL,
        access_token="mock_access_token_real_db",
        refresh_token="mock_refresh_token_real_db",
        token_expiry=datetime.utcnow() + timedelta(hours=1)
    )
    
    # 2. YouTube Connections
    print("Creating YouTube connections...")
    # Primary Channel
    db.create_youtube_connection(
        user_id=TARGET_USER_ID,
        youtube_channel_id="UC_real_test_primary",
        youtube_channel_name="Real Test Channel Main",
        channel_avatar_url="https://ui-avatars.com/api/?name=Real+Test&background=0D8ABC&color=fff",
        access_token="mock_yt_token_1",
        refresh_token="mock_yt_refresh_1",
        is_primary=True,
        token_expiry=datetime.utcnow() + timedelta(days=7)
    )
    
    # 3. Language Channels
    print("Creating Language Channels...")
    languages = [
        ("es", "Spanish", "Real Test Español"),
        ("fr", "French", "Real Test Français"),
        ("de", "German", "Real Test Deutsch"),
        ("hi", "Hindi", "Real Test Hindi"),
        ("pt", "Portuguese", "Real Test Português")
    ]
    
    language_channel_ids = {} # lang_code -> channel_doc_id
    
    for code, name, channel_name in languages:
        channel_id = f"UC_real_test_{code}_{random.randint(1000, 9999)}"
        doc_id = db.create_language_channel(
            user_id=TARGET_USER_ID,
            channel_id=channel_id,
            language_code=code,
            channel_name=channel_name,
            channel_avatar_url=f"https://ui-avatars.com/api/?name={code.upper()}&background=random"
        )
        language_channel_ids[code] = channel_id

    # 4. Processing Jobs & Localized Videos
    print("Creating Processing Jobs and Videos...")
    
    # Job 1: Completed - Spanish & French
    job1_id = db.create_processing_job(
        source_video_id="vid_real_test_101",
        source_channel_id="UC_real_test_primary",
        user_id=TARGET_USER_ID,
        target_languages=["es", "fr"]
    )
    # Manually update created_at to be in the past
    db.db.collection('processing_jobs').document(job1_id).update({
        'status': 'completed',
        'progress': 100,
        'created_at': datetime.utcnow() - timedelta(days=5),
        'updated_at': datetime.utcnow() - timedelta(days=5)
    })
    
    # Create Localized Videos for Job 1
    db.create_localized_video(
        job_id=job1_id,
        source_video_id="vid_real_test_101",
        language_code="es",
        channel_id=language_channel_ids.get("es"),
        localized_video_id=f"vid_loc_101_es",
        status="uploaded",
        storage_url="https://storage.googleapis.com/test-bucket/vid_101_es.mp4"
    )
    db.create_localized_video(
        job_id=job1_id,
        source_video_id="vid_real_test_101",
        language_code="fr",
        channel_id=language_channel_ids.get("fr"),
        localized_video_id=f"vid_loc_101_fr",
        status="uploaded",
        storage_url="https://storage.googleapis.com/test-bucket/vid_101_fr.mp4"
    )

    # Job 2: Processing (Dubbing) - German
    job2_id = db.create_processing_job(
        source_video_id="vid_real_test_102",
        source_channel_id="UC_real_test_primary",
        user_id=TARGET_USER_ID,
        target_languages=["de"]
    )
    db.db.collection('processing_jobs').document(job2_id).update({
        'status': 'processing',
        'progress': 45,
        'created_at': datetime.utcnow() - timedelta(minutes=30),
        'updated_at': datetime.utcnow() - timedelta(minutes=1)
    })

    # Job 3: Failed - Hindi
    job3_id = db.create_processing_job(
        source_video_id="vid_real_test_103",
        source_channel_id="UC_real_test_primary",
        user_id=TARGET_USER_ID,
        target_languages=["hi"]
    )
    db.db.collection('processing_jobs').document(job3_id).update({
        'status': 'failed',
        'progress': 10,
        'error_message': 'YouTube API Quota Exceeded (Simulated)',
        'created_at': datetime.utcnow() - timedelta(hours=2),
        'updated_at': datetime.utcnow() - timedelta(hours=2)
    })

    # 5. User Settings
    print("Creating User Settings...")
    db.update_user_settings(
        user_id=TARGET_USER_ID,
        theme="system",
        notifications={
            "email": True,
            "push": False
        }
    )

    print("✅ Real Test DB seeded successfully!")

if __name__ == "__main__":
    seed_test_db()
