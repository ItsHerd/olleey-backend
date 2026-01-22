"""Script to seed comprehensive mock data including processing jobs and videos."""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path
import random

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from firebase_admin import auth
from services.firestore import firestore_service
from config import settings


# Mock video data
MOCK_VIDEOS = [
    {"id": "dQw4w9WgXcQ", "title": "Never Gonna Give You Up", "channel": "Rick Astley"},
    {"id": "9bZkp7q19f0", "title": "PSY - GANGNAM STYLE", "channel": "officialpsy"},
    {"id": "kJQP7kiw5Fk", "title": "Luis Fonsi - Despacito", "channel": "Luis Fonsi"},
    {"id": "OPf0YbXqDm0", "title": "Mark Ronson - Uptown Funk", "channel": "Mark Ronson"},
    {"id": "hT_nvWreIhg", "title": "OneRepublic - Counting Stars", "channel": "OneRepublic"},
]

JOB_STATUSES = [
    {"status": "completed", "progress": 100},
    {"status": "processing", "progress": 65},
    {"status": "uploading", "progress": 85},
    {"status": "downloading", "progress": 25},
    {"status": "pending", "progress": 0},
]

LANGUAGES = ["es", "fr", "de", "ja", "pt", "it", "ko", "zh"]


def create_test_user():
    """Create or get test user."""
    email = "testuser@example.com"
    password = "testpass123"
    
    try:
        # Check if user already exists
        try:
            existing_user = auth.get_user_by_email(email)
            print(f"✅ Using existing user: {email} (UID: {existing_user.uid})")
            return existing_user.uid
        except auth.UserNotFoundError:
            pass
        
        # Create new user
        user_record = auth.create_user(
            email=email,
            password=password,
            display_name="Test User",
            email_verified=True
        )
        
        print(f"✅ Created new user: {email} (UID: {user_record.uid})")
        return user_record.uid
        
    except Exception as e:
        print(f"❌ Failed to create/get user: {str(e)}")
        raise


def create_youtube_connections(user_id: str):
    """Create multiple mock YouTube connections with different statuses."""
    print("\n📺 Creating YouTube connections...")
    
    from datetime import timedelta
    
    connections_config = [
        {
            "channel_id": "UCmock_us_primary_001",
            "channel_name": "US Main Channel (Primary)",
            "access_token": "mock_access_token_primary",
            "is_primary": True,
            "token_expiry": None  # Active
        },
        {
            "channel_id": "UCmock_uk_secondary_002",
            "channel_name": "UK Secondary Channel",
            "access_token": "mock_access_token_uk",
            "is_primary": False,
            "token_expiry": datetime.utcnow() - timedelta(days=5)  # Expired 5 days ago
        },
        {
            "channel_id": "UCmock_ca_channel_003",
            "channel_name": "Canada Channel",
            "access_token": "mock_access_token_ca",
            "is_primary": False,
            "token_expiry": datetime.utcnow() + timedelta(days=30)  # Active, expires in 30 days
        }
    ]
    
    try:
        # Check if connections already exist
        existing_connections = firestore_service.get_youtube_connections(user_id)
        if existing_connections and len(existing_connections) >= 3:
            print(f"✅ Using existing {len(existing_connections)} YouTube connections")
            return [conn.get('id') for conn in existing_connections]
        
        created_connections = []
        
        for config in connections_config:
            connection_id = firestore_service.create_youtube_connection(
                user_id=user_id,
                youtube_channel_id=config["channel_id"],
                youtube_channel_name=config["channel_name"],
                access_token=config["access_token"],
                refresh_token=f"mock_refresh_{config['channel_id'][-3:]}",
                token_expiry=config["token_expiry"],
                is_primary=config["is_primary"]
            )
            
            status_emoji = "🟢" if config["token_expiry"] is None or config["token_expiry"] > datetime.utcnow() else "🔴"
            print(f"  {status_emoji} {config['channel_name']}")
            created_connections.append(connection_id)
        
        print(f"\n✅ Created {len(created_connections)} YouTube connections")
        return created_connections
        
    except Exception as e:
        print(f"❌ Failed to create YouTube connections: {str(e)}")
        raise


def create_language_channels(user_id: str):
    """Create mock language channels (satellites for all connections)."""
    print("\n🌍 Creating language channels...")
    
    language_configs = [
        {"code": "es", "name": "Spanish Dubbing Channel", "channel_id": "UCmock_spanish_123", "flag": "🇪🇸"},
        {"code": "fr", "name": "French Dubbing Channel", "channel_id": "UCmock_french_456", "flag": "🇫🇷"},
        {"code": "de", "name": "German Dubbing Channel", "channel_id": "UCmock_german_789", "flag": "🇩🇪"},
        {"code": "ja", "name": "Japanese Dubbing Channel", "channel_id": "UCmock_japanese_012", "flag": "🇯🇵"},
        {"code": "it", "name": "Italian Dubbing Channel", "channel_id": "UCmock_italian_345", "flag": "🇮🇹"},
        {"code": "pt", "name": "Portuguese Dubbing Channel", "channel_id": "UCmock_portuguese_678", "flag": "🇵🇹"},
        {"code": "ko", "name": "Korean Dubbing Channel", "channel_id": "UCmock_korean_901", "flag": "🇰🇷"},
        {"code": "zh", "name": "Chinese Dubbing Channel", "channel_id": "UCmock_chinese_234", "flag": "🇨🇳"},
    ]
    
    created_channels = []
    
    for lang_config in language_configs:
        try:
            # Check if already exists
            existing = firestore_service.get_language_channel_by_language(
                user_id=user_id,
                language_code=lang_config["code"]
            )
            
            if existing:
                print(f"  ✓ {lang_config['flag']} {lang_config['name']}")
                created_channels.append(existing.get('id'))
                continue
            
            channel_id = firestore_service.create_language_channel(
                user_id=user_id,
                channel_id=lang_config["channel_id"],
                language_code=lang_config["code"],
                channel_name=lang_config["name"]
            )
            
            print(f"  ✓ {lang_config['flag']} {lang_config['name']} ({lang_config['code']})")
            created_channels.append(channel_id)
            
        except Exception as e:
            print(f"  ✗ Failed to create {lang_config['name']}: {str(e)}")
    
    print(f"\n✅ Created/verified {len(created_channels)} language channels")
    return created_channels


def create_processing_jobs(user_id: str):
    """Create mock processing jobs with various statuses."""
    print("\n⚙️  Creating processing jobs...")
    
    created_jobs = []
    
    for idx, video_data in enumerate(MOCK_VIDEOS):
        try:
            # Select job status
            job_config = JOB_STATUSES[idx % len(JOB_STATUSES)]
            
            # Random target languages (2-4 languages per job)
            num_languages = random.randint(2, 4)
            target_languages = random.sample(LANGUAGES, num_languages)
            
            # Create job
            job_id = firestore_service.create_processing_job(
                source_video_id=video_data["id"],
                source_channel_id="UCmock1234567890abcdefgh",
                user_id=user_id,
                target_languages=target_languages
            )
            
            # Update job status and progress
            created_time = datetime.utcnow() - timedelta(hours=random.randint(1, 72))
            
            update_data = {
                "status": job_config["status"],
                "progress": job_config["progress"]
            }
            
            # Add completed_at for completed jobs
            if job_config["status"] == "completed":
                update_data["completed_at"] = created_time + timedelta(minutes=random.randint(15, 120))
            
            firestore_service.update_processing_job(job_id, **update_data)
            
            created_jobs.append({
                "job_id": job_id,
                "video": video_data,
                "status": job_config["status"],
                "languages": target_languages
            })
            
            status_emoji = {
                "completed": "✅",
                "processing": "🔄",
                "uploading": "⬆️",
                "downloading": "⬇️",
                "pending": "⏳"
            }
            
            print(f"  {status_emoji.get(job_config['status'], '•')} {video_data['title'][:40]:40} | "
                  f"{job_config['status']:12} | {job_config['progress']:3}% | "
                  f"Languages: {', '.join(target_languages)}")
            
        except Exception as e:
            print(f"  ✗ Failed to create job for {video_data['title']}: {str(e)}")
    
    print(f"\n✅ Created {len(created_jobs)} processing jobs")
    return created_jobs


def create_localized_videos(user_id: str, jobs: list):
    """Create mock localized videos for completed/processing jobs."""
    print("\n🎬 Creating localized videos...")
    
    created_videos = 0
    
    for job in jobs:
        job_id = job["job_id"]
        source_video_id = job["video"]["id"]
        status = job["status"]
        
        # Only create localized videos for jobs that are processing, uploading, or completed
        if status in ["pending", "downloading"]:
            continue
        
        for lang_code in job["languages"]:
            try:
                # Determine video status based on job status
                if status == "completed":
                    video_status = "published"
                    localized_video_id = f"mock_{source_video_id}_{lang_code}"
                elif status == "uploading":
                    video_status = "uploaded"
                    localized_video_id = f"mock_{source_video_id}_{lang_code}"
                else:  # processing
                    video_status = "processing"
                    localized_video_id = None
                
                # Get language channel
                language_channel = firestore_service.get_language_channel_by_language(
                    user_id=user_id,
                    language_code=lang_code
                )
                
                if not language_channel:
                    continue
                
                video_id = firestore_service.create_localized_video(
                    job_id=job_id,
                    source_video_id=source_video_id,
                    language_code=lang_code,
                    channel_id=language_channel.get("channel_id"),
                    localized_video_id=localized_video_id,
                    status=video_status,
                    storage_url=f"/storage/videos/{user_id}/{job_id}/{lang_code}/video.mp4" if video_status != "processing" else None
                )
                
                created_videos += 1
                
            except Exception as e:
                print(f"  ✗ Failed to create localized video for {lang_code}: {str(e)}")
    
    print(f"✅ Created {created_videos} localized videos")


def main():
    """Main function to seed comprehensive mock data."""
    print("=" * 80)
    print("🌱 SEEDING COMPREHENSIVE MOCK DATA")
    print("=" * 80)
    
    try:
        # Step 1: Create test user
        print("\n👤 Step 1: Creating test user...")
        user_id = create_test_user()
        
        # Step 2: Create YouTube connections
        print("\n📺 Step 2: Setting up YouTube connections...")
        create_youtube_connections(user_id)
        
        # Step 3: Create language channels
        print("\n🌍 Step 3: Setting up language channels...")
        create_language_channels(user_id)
        
        # Step 4: Create processing jobs
        print("\n⚙️  Step 4: Creating processing jobs...")
        jobs = create_processing_jobs(user_id)
        
        # Step 5: Create localized videos
        print("\n🎬 Step 5: Creating localized videos...")
        create_localized_videos(user_id, jobs)
        
        # Summary
        print("\n" + "=" * 80)
        print("✅ MOCK DATA SEEDING COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        
        print("\n📊 Summary:")
        print(f"   • User: testuser@example.com (password: testpass123)")
        print(f"   • User ID: {user_id}")
        print(f"   • YouTube Connections: 3")
        print(f"      - US Main Channel (Primary) - 🟢 Active")
        print(f"      - UK Secondary Channel - 🔴 Expired")
        print(f"      - Canada Channel - 🟢 Active")
        print(f"   • Language Channels: 8 (es, fr, de, ja, it, pt, ko, zh)")
        print(f"   • Processing Jobs: {len(jobs)}")
        print(f"   • Job Statuses:")
        status_counts = {}
        for job in jobs:
            status = job["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        for status, count in status_counts.items():
            print(f"      - {status}: {count}")
        
        print("\n🧪 Test the API:")
        print("   1. Login:")
        print("      POST http://localhost:8000/auth/login")
        print("      Body: {")
        print('        "email": "testuser@example.com",')
        print('        "password": "testpass123"')
        print("      }")
        print("\n   2. View Dashboard:")
        print("      GET http://localhost:8000/dashboard")
        print("      Header: Authorization: Bearer <id_token>")
        print("\n   3. View Jobs:")
        print("      GET http://localhost:8000/jobs")
        print("      Header: Authorization: Bearer <id_token>")
        print("\n   4. View Videos:")
        print("      GET http://localhost:8000/videos/list")
        print("      Header: Authorization: Bearer <id_token>")
        
    except Exception as e:
        print(f"\n❌ Error seeding mock data: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
