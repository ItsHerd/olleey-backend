"""
Add Garry Tan demo video for manual approval workflow demonstration.
"""
import sys
import os
import uuid
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firestore import firestore_service
from firebase_admin import firestore

# User configuration
USER_ID = "M8yD1YEve9OaW2Q2HhVh3tSCmGo2"

# Video details
VIDEO_ID = "garry_tan_yc_demo"
VIDEO_TITLE = "Garry Tan - President and CEO of Y Combinator"
VIDEO_DESCRIPTION = """Garry Tan is the President and CEO of Y Combinator (YC), the world's most successful startup accelerator.

In this video, Garry shares insights about YC's mission to help startups succeed, the importance of building great products, and advice for founders navigating the startup journey.

This is a demo video showcasing Olleey's AI-powered video localization capabilities."""

ORIGINAL_URL = "https://olleey-videos.s3.us-west-1.amazonaws.com/en.mp4"
DUBBED_URL = "https://olleey-videos.s3.us-west-1.amazonaws.com/es.mov"
THUMBNAIL_URL = "https://images.unsplash.com/photo-1557804506-669a67965ba0?w=1280&h=720&fit=crop"

# Channel info
MASTER_CHANNEL_ID = "UCMasterChannel123"
MASTER_CHANNEL_NAME = "Olleey Demo Channel"
SPANISH_CHANNEL_ID = "UCESChannel301"  # From previous seed

def seed_garry_tan_demo():
    print("=" * 70)
    print("🎬 ADDING GARRY TAN DEMO VIDEO")
    print("=" * 70)
    print()

    # 1. Find or create "Demo Workflow" project
    print("📁 Finding Demo Workflow project...")
    projects = firestore_service.db.collection('projects').where('user_id', '==', USER_ID).stream()
    demo_project_id = None

    for project in projects:
        project_data = project.to_dict()
        if 'demo' in project_data.get('name', '').lower() or 'workflow' in project_data.get('name', '').lower():
            demo_project_id = project.id
            print(f"   ✓ Found project: {project_data.get('name')} ({demo_project_id})")
            break

    # Create if doesn't exist
    if not demo_project_id:
        print("   Creating 'Demo Workflow' project...")
        demo_project_id = str(uuid.uuid4())
        firestore_service.db.collection('projects').document(demo_project_id).set({
            'user_id': USER_ID,
            'name': 'Demo Workflow',
            'description': 'Demonstration videos for client presentations',
            'created_at': firestore.SERVER_TIMESTAMP,
            'updated_at': firestore.SERVER_TIMESTAMP,
            'video_count': 0,
            'completed_jobs': 0,
            'active_jobs': 0
        })
        print(f"   ✓ Created Demo Workflow project: {demo_project_id}")
    print()

    # 2. Create source video record
    print("🎥 Creating source video record...")
    video_data = {
        'video_id': VIDEO_ID,
        'channel_id': MASTER_CHANNEL_ID,
        'user_id': USER_ID,
        'title': VIDEO_TITLE,
        'description': VIDEO_DESCRIPTION,
        'thumbnail_url': THUMBNAIL_URL,
        'duration': 180,  # 3 minutes
        'view_count': 12500,
        'like_count': 890,
        'published_at': datetime.utcnow() - timedelta(days=2),
        'video_type': 'original',
        'storage_url': ORIGINAL_URL,
        'created_at': datetime.utcnow() - timedelta(hours=3),
        'updated_at': datetime.utcnow() - timedelta(hours=1)
    }

    firestore_service.db.collection('videos').document(VIDEO_ID).set(video_data)
    print(f"   ✓ Source video created: {VIDEO_ID}")
    print(f"   ✓ Title: {VIDEO_TITLE}")
    print(f"   ✓ Original URL: {ORIGINAL_URL}")
    print()

    # 3. Create processing job (waiting_approval status)
    print("⚙️  Creating processing job (waiting_approval)...")
    job_id = str(uuid.uuid4())

    job_data = {
        'job_id': job_id,
        'source_video_id': VIDEO_ID,
        'source_channel_id': MASTER_CHANNEL_ID,
        'user_id': USER_ID,
        'project_id': demo_project_id,
        'status': 'waiting_approval',
        'target_languages': ['es'],
        'progress': 100,
        'error_message': None,
        'created_at': datetime.utcnow() - timedelta(hours=2),
        'updated_at': datetime.utcnow() - timedelta(minutes=30),
        'estimated_credits': 10,
        'priority': 'high'
    }

    firestore_service.db.collection('processing_jobs').document(job_id).set(job_data)
    print(f"   ✓ Job created: {job_id}")
    print(f"   ✓ Status: waiting_approval (ready for manual review)")
    print()

    # 4. Create localized video (Spanish)
    print("🌍 Creating Spanish localized video...")
    localized_video_id = str(uuid.uuid4())

    localized_data = {
        'job_id': job_id,
        'source_video_id': VIDEO_ID,
        'localized_video_id': None,  # Will be set when published
        'language_code': 'es',
        'channel_id': SPANISH_CHANNEL_ID,
        'status': 'waiting_approval',
        'storage_url': DUBBED_URL,
        'thumbnail_url': THUMBNAIL_URL,
        'title': f"{VIDEO_TITLE} (Spanish)",
        'description': f"{VIDEO_DESCRIPTION}\n\n🌍 Localized to Spanish by Olleey AI",
        'duration': 180,
        'view_count': 0,
        'created_at': datetime.utcnow() - timedelta(hours=1),
        'updated_at': datetime.utcnow() - timedelta(minutes=30)
    }

    firestore_service.db.collection('localized_videos').document(localized_video_id).set(localized_data)
    print(f"   ✓ Localized video created: {localized_video_id}")
    print(f"   ✓ Language: Spanish (es)")
    print(f"   ✓ Dubbed URL: {DUBBED_URL}")
    print(f"   ✓ Status: waiting_approval")
    print()

    # 5. Create activity logs
    print("📊 Creating activity logs...")

    # Job creation log
    activity1_id = str(uuid.uuid4())
    firestore_service.db.collection('activity_logs').document(activity1_id).set({
        'id': activity1_id,
        'user_id': USER_ID,
        'action': 'Created dubbing job',
        'details': f'Job {job_id[:8]} created for video {VIDEO_ID}. Status: pending.',
        'status': 'info',
        'icon': 'plus',
        'color': 'blue',
        'timestamp': datetime.utcnow() - timedelta(hours=2),
        'project_id': demo_project_id
    })

    # Processing complete log
    activity2_id = str(uuid.uuid4())
    firestore_service.db.collection('activity_logs').document(activity2_id).set({
        'id': activity2_id,
        'user_id': USER_ID,
        'action': 'Processed video (Demo)',
        'details': 'Video localized for language es. Awaiting approval.',
        'status': 'info',
        'icon': 'zap',
        'color': 'blue',
        'timestamp': datetime.utcnow() - timedelta(minutes=30),
        'project_id': demo_project_id
    })

    print("   ✓ Created 2 activity log entries")
    print()

    print("=" * 70)
    print("✅ GARRY TAN DEMO VIDEO ADDED SUCCESSFULLY!")
    print("=" * 70)
    print()
    print("📋 Summary:")
    print(f"   • Video ID: {VIDEO_ID}")
    print(f"   • Job ID: {job_id}")
    print(f"   • Project: Demo Workflow")
    print(f"   • Status: waiting_approval (ready for demo)")
    print(f"   • Language: Spanish (es)")
    print()
    print("🎯 Next Steps:")
    print("   1. Refresh your dashboard")
    print("   2. Go to 'All Media' or 'Workflows'")
    print("   3. Find 'Garry Tan - President and CEO of Y Combinator'")
    print("   4. Click to review and approve!")
    print()
    print("🎬 Demo Flow:")
    print("   1. Show the original English video")
    print("   2. Review the Spanish dubbed version")
    print("   3. Approve and publish to channel")
    print("   4. Show the published result")
    print()

if __name__ == "__main__":
    seed_garry_tan_demo()
