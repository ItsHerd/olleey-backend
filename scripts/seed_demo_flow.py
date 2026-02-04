#!/usr/bin/env python3
"""
Seed script for demo@olleey.com user with comprehensive mock data.

This script creates:
- Demo user with credentials: demo@olleey.com / password
- Mock YouTube connection with channels
- Projects with various workflows
- Videos in different states (processing, waiting_approval, published, failed)
- Localized videos for testing the approval workflow
- Activity logs and notifications
"""

import sys
import os
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_admin import auth, firestore
from services.firestore import firestore_service
from config import settings

# Demo user credentials
DEMO_EMAIL = "demo@olleey.com"
DEMO_PASSWORD = "password"
DEMO_NAME = "Demo User"

# Mock YouTube channels
MASTER_CHANNEL = {
    "id": "UCdemo_master_english",
    "name": "Demo Master Channel (English)",
    "avatar": "https://via.placeholder.com/150/FF6B6B/FFFFFF?text=EN"
}

LANGUAGE_CHANNELS = [
    {"code": "es", "name": "Spanish", "channel_id": "UCdemo_spanish", "channel_name": "Demo Spanish Channel"},
    {"code": "de", "name": "German", "channel_id": "UCdemo_german", "channel_name": "Demo German Channel"},
    {"code": "fr", "name": "French", "channel_id": "UCdemo_french", "channel_name": "Demo French Channel"},
    {"code": "it", "name": "Italian", "channel_id": "UCdemo_italian", "channel_name": "Demo Italian Channel"},
    {"code": "pt", "name": "Portuguese", "channel_id": "UCdemo_portuguese", "channel_name": "Demo Portuguese Channel"},
    {"code": "ja", "name": "Japanese", "channel_id": "UCdemo_japanese", "channel_name": "Demo Japanese Channel"},
]

# Source videos for mock data
SOURCE_VIDEOS = [
    {
        "id": "dQw4w9WgXcQ",
        "title": "Never Gonna Give You Up - Rick Astley",
        "description": "Official music video for Rick Astley's classic hit",
        "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration": 213,
        "views": 1500000000
    },
    {
        "id": "jNQXAC9IVRw",
        "title": "Me at the zoo",
        "description": "The first video ever uploaded to YouTube",
        "thumbnail": "https://i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg",
        "duration": 19,
        "views": 280000000
    },
    {
        "id": "9bZkp7q19f0",
        "title": "PSY - GANGNAM STYLE",
        "description": "Official music video for Gangnam Style",
        "thumbnail": "https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg",
        "duration": 252,
        "views": 5000000000
    },
    {
        "id": "kJQP7kiw5Fk",
        "title": "Luis Fonsi - Despacito",
        "description": "Official music video for Despacito",
        "thumbnail": "https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg",
        "duration": 282,
        "views": 8400000000
    },
    {
        "id": "OPf0YbXqDm0",
        "title": "Mark Ronson - Uptown Funk",
        "description": "Official video for Uptown Funk",
        "thumbnail": "https://i.ytimg.com/vi/OPf0YbXqDm0/hqdefault.jpg",
        "duration": 269,
        "views": 5100000000
    }
]


def create_or_get_demo_user():
    """Create demo user in Firebase Auth or return existing user."""
    print("=" * 60)
    print("STEP 1: Creating Demo User")
    print("=" * 60)
    
    try:
        # Check if user already exists
        try:
            existing_user = auth.get_user_by_email(DEMO_EMAIL)
            print(f"✅ Demo user already exists: {DEMO_EMAIL}")
            print(f"   UID: {existing_user.uid}")
            return existing_user.uid
        except auth.UserNotFoundError:
            pass
        
        # Create new user
        user_record = auth.create_user(
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            display_name=DEMO_NAME,
            email_verified=True
        )
        
        print(f"✅ Created demo user: {DEMO_EMAIL}")
        print(f"   UID: {user_record.uid}")
        print(f"   Password: {DEMO_PASSWORD}")
        
        return user_record.uid
        
    except Exception as e:
        print(f"❌ Failed to create demo user: {str(e)}")
        raise


def create_youtube_connections(user_id: str):
    """Create mock YouTube connections for demo user."""
    print("\n" + "=" * 60)
    print("STEP 2: Creating YouTube Connections")
    print("=" * 60)
    
    # Create master channel connection
    print(f"\n📺 Creating master channel: {MASTER_CHANNEL['name']}")
    master_connection_id = firestore_service.create_youtube_connection(
        user_id=user_id,
        youtube_channel_id=MASTER_CHANNEL["id"],
        youtube_channel_name=MASTER_CHANNEL["name"],
        access_token="mock_demo_access_token",  # Starts with mock_ for mock mode
        refresh_token="mock_demo_refresh_token",
        is_primary=True,
        channel_avatar_url=MASTER_CHANNEL["avatar"]
    )
    print(f"✅ Master connection created: {master_connection_id}")
    
    return master_connection_id


def create_projects(user_id: str, master_connection_id: str):
    """Create demo projects."""
    print("\n" + "=" * 60)
    print("STEP 3: Creating Projects")
    print("=" * 60)
    
    projects = []
    
    # Project 1: Music Videos
    print("\n📁 Creating project: Music Videos")
    project_1 = firestore_service.create_project(
        user_id=user_id,
        name="Music Videos",
        master_connection_id=master_connection_id
    )
    projects.append({"id": project_1, "name": "Music Videos"})
    print(f"✅ Project created: {project_1}")
    
    # Project 2: Educational Content
    print("\n📁 Creating project: Educational Content")
    project_2 = firestore_service.create_project(
        user_id=user_id,
        name="Educational Content",
        master_connection_id=master_connection_id
    )
    projects.append({"id": project_2, "name": "Educational Content"})
    print(f"✅ Project created: {project_2}")
    
    # Project 3: Demo Workflow
    print("\n📁 Creating project: Demo Workflow")
    project_3 = firestore_service.create_project(
        user_id=user_id,
        name="Demo Workflow",
        master_connection_id=master_connection_id
    )
    projects.append({"id": project_3, "name": "Demo Workflow"})
    print(f"✅ Project created: {project_3}")
    
    return projects


def create_language_channels(user_id: str, master_connection_id: str, project_id: str):
    """Create language-specific channels."""
    print("\n" + "=" * 60)
    print("STEP 4: Creating Language Channels")
    print("=" * 60)
    
    channels = []
    for lang_info in LANGUAGE_CHANNELS:
        print(f"\n🌍 Creating {lang_info['name']} channel...")
        channel_doc_id = firestore_service.create_language_channel(
            user_id=user_id,
            channel_id=lang_info["channel_id"],
            language_code=lang_info["code"],
            channel_name=lang_info["channel_name"],
            master_connection_id=master_connection_id,
            project_id=project_id
        )
        channels.append({
            "doc_id": channel_doc_id,
            "code": lang_info["code"],
            "name": lang_info["name"],
            "channel_id": lang_info["channel_id"]
        })
        print(f"✅ {lang_info['name']} channel created: {channel_doc_id}")
    
    return channels


def create_job_with_videos(
    user_id: str,
    project_id: str,
    source_video: Dict,
    target_languages: List[str],
    status: str,
    progress: int = 0,
    error_message: str = None
):
    """Create a processing job with localized videos."""
    job_id = str(uuid.uuid4())
    
    # Create job
    job_data = {
        'source_video_id': source_video['id'],
        'source_channel_id': MASTER_CHANNEL['id'],
        'user_id': user_id,
        'project_id': project_id,
        'status': status,
        'target_languages': target_languages,
        'progress': progress,
        'error_message': error_message,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }
    
    if status == 'completed':
        job_data['completed_at'] = firestore.SERVER_TIMESTAMP
        job_data['progress'] = 100
    
    firestore_service.db.collection('processing_jobs').document(job_id).set(job_data)
    
    # Create localized videos based on status
    for lang_code in target_languages:
        lang_name = next((lc['name'] for lc in LANGUAGE_CHANNELS if lc['code'] == lang_code), lang_code.upper())
        channel_id = next((lc['channel_id'] for lc in LANGUAGE_CHANNELS if lc['code'] == lang_code), f"UCdemo_{lang_code}")
        
        video_id = str(uuid.uuid4())
        video_status = status
        
        # Determine video status based on job status
        if status == 'processing':
            video_status = 'processing'
        elif status == 'waiting_approval':
            video_status = 'waiting_approval'
        elif status == 'completed':
            video_status = 'published'
        elif status == 'failed':
            video_status = 'failed'
        
        # Create storage URL for completed/waiting_approval videos
        storage_url = None
        if video_status in ['waiting_approval', 'published']:
            storage_url = f"gs://demo-bucket/videos/{job_id}/{lang_code}/output.mp4"
        
        # Create localized video ID for published videos
        localized_video_id = None
        if video_status == 'published':
            localized_video_id = f"VID{uuid.uuid4().hex[:10]}"
        
        video_data = {
            'job_id': job_id,
            'source_video_id': source_video['id'],
            'localized_video_id': localized_video_id,
            'language_code': lang_code,
            'channel_id': channel_id,
            'user_id': user_id,
            'status': video_status,
            'storage_url': storage_url,
            'thumbnail_url': source_video['thumbnail'],
            'title': f"{source_video['title']} ({lang_name} Dub)",
            'description': f"AI-dubbed version of '{source_video['title']}' in {lang_name}. Powered by Olleey's advanced dubbing technology.",
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP
        }
        
        firestore_service.db.collection('localized_videos').document(video_id).set(video_data)
    
    return job_id


def seed_demo_data(user_id: str, projects: List[Dict], channels: List[Dict]):
    """Create mock jobs and videos in various states."""
    print("\n" + "=" * 60)
    print("STEP 5: Creating Demo Jobs & Videos")
    print("=" * 60)
    
    jobs_created = []
    
    # Scenario 1: Completed Job - Published videos
    print("\n✨ Scenario 1: Completed job with published videos")
    job_1 = create_job_with_videos(
        user_id=user_id,
        project_id=projects[0]['id'],
        source_video=SOURCE_VIDEOS[0],
        target_languages=['es', 'de', 'fr'],
        status='completed',
        progress=100
    )
    jobs_created.append({"id": job_1, "status": "completed", "video": SOURCE_VIDEOS[0]['title']})
    print(f"✅ Created completed job: {job_1}")
    
    # Scenario 2: Waiting Approval - Ready for review
    print("\n⏳ Scenario 2: Job waiting for approval")
    job_2 = create_job_with_videos(
        user_id=user_id,
        project_id=projects[2]['id'],
        source_video=SOURCE_VIDEOS[1],
        target_languages=['es', 'de', 'it'],
        status='waiting_approval',
        progress=100
    )
    jobs_created.append({"id": job_2, "status": "waiting_approval", "video": SOURCE_VIDEOS[1]['title']})
    print(f"✅ Created approval-waiting job: {job_2}")
    
    # Scenario 3: Processing - Mid-flight
    print("\n🔄 Scenario 3: Job currently processing")
    job_3 = create_job_with_videos(
        user_id=user_id,
        project_id=projects[1]['id'],
        source_video=SOURCE_VIDEOS[2],
        target_languages=['ja', 'pt'],
        status='processing',
        progress=45
    )
    jobs_created.append({"id": job_3, "status": "processing", "video": SOURCE_VIDEOS[2]['title']})
    print(f"✅ Created processing job: {job_3}")
    
    # Scenario 4: Another Waiting Approval - Multiple languages
    print("\n⏳ Scenario 4: Another job waiting for approval (multi-language)")
    job_4 = create_job_with_videos(
        user_id=user_id,
        project_id=projects[2]['id'],
        source_video=SOURCE_VIDEOS[3],
        target_languages=['es', 'fr', 'de', 'it', 'pt'],
        status='waiting_approval',
        progress=100
    )
    jobs_created.append({"id": job_4, "status": "waiting_approval", "video": SOURCE_VIDEOS[3]['title']})
    print(f"✅ Created multi-language approval job: {job_4}")
    
    # Scenario 5: Failed Job
    print("\n❌ Scenario 5: Failed job")
    job_5 = create_job_with_videos(
        user_id=user_id,
        project_id=projects[0]['id'],
        source_video=SOURCE_VIDEOS[4],
        target_languages=['ja'],
        status='failed',
        progress=20,
        error_message="Source video download failed: Copyright restriction detected"
    )
    jobs_created.append({"id": job_5, "status": "failed", "video": SOURCE_VIDEOS[4]['title']})
    print(f"✅ Created failed job: {job_5}")
    
    # Scenario 6: Recent Processing Job
    print("\n🔄 Scenario 6: Recent processing job")
    job_6 = create_job_with_videos(
        user_id=user_id,
        project_id=projects[1]['id'],
        source_video=SOURCE_VIDEOS[0],
        target_languages=['de', 'fr'],
        status='processing',
        progress=75
    )
    jobs_created.append({"id": job_6, "status": "processing", "video": SOURCE_VIDEOS[0]['title']})
    print(f"✅ Created recent processing job: {job_6}")
    
    return jobs_created


def create_activity_logs(user_id: str, jobs: List[Dict]):
    """Create activity logs for demo user."""
    print("\n" + "=" * 60)
    print("STEP 6: Creating Activity Logs")
    print("=" * 60)
    
    activities = [
        {
            "type": "job_completed",
            "message": f"Job completed: {jobs[0]['video']}",
            "timestamp": datetime.utcnow() - timedelta(hours=2)
        },
        {
            "type": "approval_needed",
            "message": f"Approval needed: {jobs[1]['video']}",
            "timestamp": datetime.utcnow() - timedelta(minutes=30)
        },
        {
            "type": "processing_started",
            "message": f"Processing started: {jobs[2]['video']}",
            "timestamp": datetime.utcnow() - timedelta(minutes=15)
        },
        {
            "type": "approval_needed",
            "message": f"Approval needed: {jobs[3]['video']}",
            "timestamp": datetime.utcnow() - timedelta(minutes=45)
        }
    ]
    
    for activity in activities:
        activity_id = str(uuid.uuid4())
        firestore_service.db.collection('activity_logs').document(activity_id).set({
            'user_id': user_id,
            'type': activity['type'],
            'message': activity['message'],
            'created_at': activity['timestamp']
        })
        print(f"✅ Created activity: {activity['message']}")


def print_summary(user_id: str, projects: List[Dict], channels: List[Dict], jobs: List[Dict]):
    """Print summary of demo setup."""
    print("\n" + "=" * 60)
    print("🎉 DEMO SETUP COMPLETE!")
    print("=" * 60)
    
    print(f"\n👤 Demo User Credentials:")
    print(f"   Email:    {DEMO_EMAIL}")
    print(f"   Password: {DEMO_PASSWORD}")
    print(f"   User ID:  {user_id}")
    
    print(f"\n📊 Projects Created: {len(projects)}")
    for project in projects:
        print(f"   - {project['name']} ({project['id']})")
    
    print(f"\n🌍 Language Channels: {len(channels)}")
    for channel in channels:
        print(f"   - {channel['name']} ({channel['code']})")
    
    print(f"\n🎬 Jobs Created: {len(jobs)}")
    status_counts = {}
    for job in jobs:
        status = job['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    for status, count in status_counts.items():
        print(f"   - {status}: {count}")
    
    print(f"\n🔑 Login Instructions:")
    print(f"   1. Go to your Olleey login page")
    print(f"   2. Use email: {DEMO_EMAIL}")
    print(f"   3. Use password: {DEMO_PASSWORD}")
    
    print(f"\n✨ What to Test:")
    print(f"   1. Dashboard - View activity and quick stats")
    print(f"   2. Jobs Page - See jobs in different states")
    print(f"   3. Videos Page - View and filter videos")
    print(f"   4. Approval Workflow:")
    print(f"      - Find jobs with 'waiting_approval' status")
    print(f"      - Review the dubbed videos")
    print(f"      - Approve or reject videos")
    print(f"      - Test the approval flow")
    print(f"   5. Projects - Switch between different projects")
    print(f"   6. Channels - View language channels")
    
    print(f"\n📝 Notes:")
    print(f"   - All YouTube connections use mock mode (no real API calls)")
    print(f"   - Videos are in various states for testing")
    print(f"   - Activity logs show recent actions")
    print(f"   - All data is safe to modify/delete")
    
    print("\n" + "=" * 60)


def cleanup_demo_user():
    """Clean up demo user and all associated data."""
    print("\n🗑️  Cleaning up demo user...")
    
    try:
        # Get user
        user = auth.get_user_by_email(DEMO_EMAIL)
        user_id = user.uid
        
        # Delete Firestore data
        print("   Deleting Firestore data...")
        
        # Delete processing jobs
        jobs_ref = firestore_service.db.collection('processing_jobs')
        jobs_query = firestore_service._where(jobs_ref, 'user_id', '==', user_id)
        for doc in jobs_query.stream():
            doc.reference.delete()
        
        # Delete localized videos
        videos_ref = firestore_service.db.collection('localized_videos')
        videos_query = firestore_service._where(videos_ref, 'user_id', '==', user_id)
        for doc in videos_query.stream():
            doc.reference.delete()
        
        # Delete projects
        projects_ref = firestore_service.db.collection('projects')
        projects_query = firestore_service._where(projects_ref, 'user_id', '==', user_id)
        for doc in projects_query.stream():
            doc.reference.delete()
        
        # Delete language channels
        channels_ref = firestore_service.db.collection('language_channels')
        channels_query = firestore_service._where(channels_ref, 'user_id', '==', user_id)
        for doc in channels_query.stream():
            doc.reference.delete()
        
        # Delete youtube connections
        connections_ref = firestore_service.db.collection('youtube_connections')
        connections_query = firestore_service._where(connections_ref, 'user_id', '==', user_id)
        for doc in connections_query.stream():
            doc.reference.delete()
        
        # Delete activity logs
        logs_ref = firestore_service.db.collection('activity_logs')
        logs_query = firestore_service._where(logs_ref, 'user_id', '==', user_id)
        for doc in logs_query.stream():
            doc.reference.delete()
        
        # Delete Firebase Auth user
        print("   Deleting Firebase Auth user...")
        auth.delete_user(user_id)
        
        print("✅ Demo user cleanup complete!")
        
    except auth.UserNotFoundError:
        print("⚠️  Demo user not found")
    except Exception as e:
        print(f"❌ Cleanup failed: {str(e)}")
        raise


def main():
    """Main function to seed demo data."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup demo user with comprehensive mock data")
    parser.add_argument("--cleanup", action="store_true", help="Remove demo user and all data")
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_demo_user()
        return
    
    try:
        print("\n🌱 Setting up Olleey Demo Flow")
        print("=" * 60)
        
        # Step 1: Create demo user
        user_id = create_or_get_demo_user()
        
        # Step 2: Create YouTube connections
        master_connection_id = create_youtube_connections(user_id)
        
        # Step 3: Create projects
        projects = create_projects(user_id, master_connection_id)
        
        # Step 4: Create language channels
        channels = create_language_channels(user_id, master_connection_id, projects[2]['id'])
        
        # Step 5: Create jobs and videos
        jobs = seed_demo_data(user_id, projects, channels)
        
        # Step 6: Create activity logs
        create_activity_logs(user_id, jobs)
        
        # Print summary
        print_summary(user_id, projects, channels, jobs)
        
    except Exception as e:
        print(f"\n❌ Error setting up demo: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
