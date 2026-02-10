"""
Enhanced script to seed rich mock data with comprehensive relationships.
Includes: projects, channels, videos, jobs, localizations, activity logs, and user settings.
"""
import sys
import os
import uuid
import random
from datetime import datetime, timedelta
from typing import List, Dict

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firestore import firestore_service
from firebase_admin import firestore

USER_ID = "M8yD1YEve9OaW2Q2HhVh3tSCmGo2"
USER_EMAIL = "demo@olleey.com"

# Extended language support
LANGUAGES = ['es', 'de', 'fr', 'it', 'pt', 'ru', 'ja', 'ko', 'hi', 'ar', 'zh', 'en']
LANGUAGE_NAMES = {
    'es': 'Spanish', 'de': 'German', 'fr': 'French', 'it': 'Italian',
    'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese', 'ko': 'Korean',
    'hi': 'Hindi', 'ar': 'Arabic', 'zh': 'Chinese', 'en': 'English'
}

# Real YouTube videos with metadata
SOURCE_VIDEOS = [
    {
        "id": "dQw4w9WgXcQ",
        "title": "Rick Astley - Never Gonna Give You Up (Official Video)",
        "description": "The official video for 'Never Gonna Give You Up' by Rick Astley. Listen to Rick Astley: https://RickAstley.lnk.to/_listenYD",
        "img": "https://i.ytimg.com/vi/dQw4w9WgXcQ/maxresdefault.jpg",
        "duration": 213,
        "views": 1400000000,
        "likes": 16000000,
        "published": "2009-10-25"
    },
    {
        "id": "jNQXAC9IVRw",
        "title": "Me at the zoo",
        "description": "The first video on YouTube. Maybe it's time to go back to the zoo?",
        "img": "https://i.ytimg.com/vi/jNQXAC9IVRw/maxresdefault.jpg",
        "duration": 19,
        "views": 280000000,
        "likes": 12000000,
        "published": "2005-04-23"
    },
    {
        "id": "9bZkp7q19f0",
        "title": "PSY - GANGNAM STYLE(강남스타일) M/V",
        "description": "PSY - GANGNAM STYLE (강남스타일) M/V @ https://youtu.be/9bZkp7q19f0",
        "img": "https://i.ytimg.com/vi/9bZkp7q19f0/maxresdefault.jpg",
        "duration": 253,
        "views": 4900000000,
        "likes": 25000000,
        "published": "2012-07-15"
    },
    {
        "id": "OPf0YbXqDm0",
        "title": "Mark Ronson - Uptown Funk (Official Video) ft. Bruno Mars",
        "description": "Official Video for 'Uptown Funk' by Mark Ronson ft. Bruno Mars",
        "img": "https://i.ytimg.com/vi/OPf0YbXqDm0/maxresdefault.jpg",
        "duration": 270,
        "views": 5100000000,
        "likes": 32000000,
        "published": "2014-11-19"
    },
    {
        "id": "kJQP7kiw5Fk",
        "title": "Luis Fonsi - Despacito ft. Daddy Yankee",
        "description": "'Despacito' available on these digital platforms: iTunes: http://smarturl.it/...",
        "img": "https://i.ytimg.com/vi/kJQP7kiw5Fk/maxresdefault.jpg",
        "duration": 282,
        "views": 8300000000,
        "likes": 52000000,
        "published": "2017-01-12"
    },
    {
        "id": "kffacxfA7G4",
        "title": "The Beatles - Here Comes The Sun",
        "description": "From The Beatles' Abbey Road album. Subscribe to The Beatles' YouTube channel",
        "img": "https://i.ytimg.com/vi/kffacxfA7G4/maxresdefault.jpg",
        "duration": 186,
        "views": 890000000,
        "likes": 7800000,
        "published": "2019-06-28"
    },
    {
        "id": "2Vv-BfVoq4g",
        "title": "Ed Sheeran - Perfect (Official Music Video)",
        "description": "Official music video for 'Perfect' by Ed Sheeran",
        "img": "https://i.ytimg.com/vi/2Vv-BfVoq4g/maxresdefault.jpg",
        "duration": 263,
        "views": 3700000000,
        "likes": 28000000,
        "published": "2017-11-09"
    },
    {
        "id": "fJ9rUzIMcZQ",
        "title": "Queen – Bohemian Rhapsody (Official Video Remastered)",
        "description": "Bohemian Rhapsody - Taken from 'A Night At The Opera'",
        "img": "https://i.ytimg.com/vi/fJ9rUzIMcZQ/maxresdefault.jpg",
        "duration": 355,
        "views": 1900000000,
        "likes": 19000000,
        "published": "2008-08-01"
    }
]

# Channel configurations
MASTER_CHANNEL = {
    "id": "UCMasterChannel123",
    "name": "Olleey Demo Channel",
    "avatar": "https://ui-avatars.com/api/?name=Olleey+Demo&background=FBB040&color=000"
}

def create_user_and_settings():
    """Create user record and settings"""
    print("📝 Creating user record and settings...")

    # User record
    firestore_service.create_or_update_user(
        user_id=USER_ID,
        email=USER_EMAIL,
        access_token="mock_access_token_enhanced",
        refresh_token="mock_refresh_token_enhanced",
        token_expiry=datetime.utcnow() + timedelta(days=30)
    )

    # User settings
    firestore_service.update_user_settings(
        user_id=USER_ID,
        theme="dark",
        notifications={
            "email": True,
            "push": True,
            "job_complete": True,
            "job_failed": True
        }
    )

def create_youtube_connections():
    """Create master channel and language satellite channels"""
    print("🎥 Creating YouTube channel connections...")

    # Master channel connection
    firestore_service.create_youtube_connection(
        user_id=USER_ID,
        youtube_channel_id=MASTER_CHANNEL["id"],
        youtube_channel_name=MASTER_CHANNEL["name"],
        channel_avatar_url=MASTER_CHANNEL["avatar"],
        access_token="mock_master_token",
        refresh_token="mock_master_refresh",
        is_primary=True,
        token_expiry=datetime.utcnow() + timedelta(days=30)
    )

    # Language satellite channels
    language_channels = {}
    priority_langs = ['es', 'de', 'fr', 'pt', 'ja']  # Create channels for these

    for lang in priority_langs:
        lang_name = LANGUAGE_NAMES[lang]
        channel_id = f"UC{lang.upper()}Channel{random.randint(100, 999)}"
        channel_name = f"{MASTER_CHANNEL['name']} {lang_name}"

        doc_id = firestore_service.create_language_channel(
            user_id=USER_ID,
            channel_id=channel_id,
            language_code=lang,
            channel_name=channel_name,
            channel_avatar_url=f"https://ui-avatars.com/api/?name={lang.upper()}&background=random"
        )
        language_channels[lang] = channel_id
        print(f"  ✓ Created {lang_name} channel: {channel_id}")

    return language_channels

def create_source_videos():
    """Create source video records in videos collection"""
    print("🎬 Creating source video records...")

    video_ids = []
    for video in SOURCE_VIDEOS:
        days_ago = random.randint(5, 90)
        created_at = datetime.utcnow() - timedelta(days=days_ago)

        video_data = {
            'video_id': video['id'],
            'channel_id': MASTER_CHANNEL['id'],
            'user_id': USER_ID,
            'title': video['title'],
            'description': video['description'],
            'thumbnail_url': video['img'],
            'duration': video['duration'],
            'view_count': video['views'],
            'like_count': video['likes'],
            'published_at': datetime.strptime(video['published'], '%Y-%m-%d'),
            'video_type': 'original',
            'storage_url': f"https://storage.googleapis.com/olleey-demo/originals/{video['id']}.mp4",
            'created_at': created_at,
            'updated_at': created_at
        }

        firestore_service.db.collection('videos').document(video['id']).set(video_data)
        video_ids.append(video['id'])
        print(f"  ✓ Created video: {video['title'][:50]}...")

    return video_ids

def create_project(name: str, description: str = "") -> str:
    """Create a project with metadata"""
    print(f"📁 Creating project: {name}")
    project_id = str(uuid.uuid4())

    days_ago = random.randint(10, 60)
    created_at = datetime.utcnow() - timedelta(days=days_ago)

    firestore_service.db.collection('projects').document(project_id).set({
        'user_id': USER_ID,
        'name': name,
        'description': description,
        'created_at': created_at,
        'updated_at': created_at,
        'video_count': 0,
        'completed_jobs': 0,
        'active_jobs': 0
    })
    return project_id

def log_activity(action: str, details: str, status: str = "info", project_id: str = None):
    """Create an activity log entry"""
    activity_id = str(uuid.uuid4())

    # Map status to icon
    icon_map = {
        'success': 'check',
        'error': 'alert',
        'info': 'zap',
        'warning': 'alert'
    }

    activity_data = {
        'id': activity_id,
        'user_id': USER_ID,
        'action': action,
        'details': details,
        'status': status,
        'icon': icon_map.get(status, 'zap'),
        'color': 'blue',
        'timestamp': firestore.SERVER_TIMESTAMP,
    }

    if project_id:
        activity_data['project_id'] = project_id

    firestore_service.db.collection('activity_logs').document(activity_id).set(activity_data)

def create_job(
    project_id: str,
    status: str,
    source_video: Dict,
    target_langs: List[str],
    progress: int = 0,
    error_msg: str = None,
    days_ago: int = 0
) -> str:
    """Create a processing job with detailed metadata"""
    job_id = str(uuid.uuid4())

    created_at = datetime.utcnow() - timedelta(days=days_ago, hours=random.randint(0, 23))
    updated_at = datetime.utcnow() - timedelta(hours=random.randint(0, 12)) if status != 'completed' else created_at + timedelta(hours=random.randint(2, 48))

    job_data = {
        'job_id': job_id,
        'source_video_id': source_video['id'],
        'source_channel_id': MASTER_CHANNEL['id'],
        'user_id': USER_ID,
        'project_id': project_id,
        'status': status,
        'target_languages': target_langs,
        'progress': progress,
        'error_message': error_msg,
        'created_at': created_at,
        'updated_at': updated_at,
        'estimated_credits': len(target_langs) * 10,
        'priority': random.choice(['normal', 'high', 'low'])
    }

    if status == 'completed':
        job_data['completed_at'] = updated_at
        job_data['progress'] = 100

    print(f"  ⚙️  Job [{status}]: {source_video['title'][:40]}... → {', '.join(target_langs)}")
    firestore_service.db.collection('processing_jobs').document(job_id).set(job_data)

    # Log activity
    log_activity(
        "Created dubbing job",
        f"Job {job_id[:8]} created for video {source_video['id']}. Status: {status}.",
        status='info' if status != 'failed' else 'error',
        project_id=project_id
    )

    return job_id

def create_localized_video(
    job_id: str,
    source_video: Dict,
    lang: str,
    status: str,
    channel_id: str = None
):
    """Create a localized video with full metadata"""
    video_id = str(uuid.uuid4())
    lang_name = LANGUAGE_NAMES.get(lang, lang.upper())

    # Realistic storage URLs
    storage_url = None
    if status in ['live', 'waiting_approval', 'draft']:
        storage_url = f"https://storage.googleapis.com/olleey-demo/localized/{source_video['id']}_{lang}.mp4"

    # Localized metadata
    title = f"{source_video['title']} ({lang_name})"
    description = f"{source_video['description'][:200]}...\n\n🌍 Localized to {lang_name} by Olleey AI"

    # Published video ID for live videos
    localized_video_id = None
    if status == 'live':
        localized_video_id = f"LOC_{lang.upper()}_{uuid.uuid4().hex[:8]}"

    video_data = {
        'job_id': job_id,
        'source_video_id': source_video['id'],
        'localized_video_id': localized_video_id,
        'language_code': lang,
        'channel_id': channel_id or f"UCmock_{lang}_channel",
        'status': status,
        'storage_url': storage_url,
        'thumbnail_url': source_video['img'],
        'title': title,
        'description': description,
        'duration': source_video['duration'],
        'view_count': random.randint(1000, 50000) if status == 'live' else 0,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }

    firestore_service.db.collection('localized_videos').document(video_id).set(video_data)

    # Log activity for successful localizations
    if status in ['live', 'waiting_approval']:
        log_activity(
            "Processed video (Simulated)" if status == 'waiting_approval' else "Published localized video",
            f"Video localized for language {lang}. {'Awaiting approval.' if status == 'waiting_approval' else 'Now live!'}",
            status='info' if status == 'waiting_approval' else 'success'
        )

def seed_comprehensive_data():
    """Seed comprehensive test data with relationships"""
    print("=" * 60)
    print("🌱 SEEDING COMPREHENSIVE TEST DATABASE")
    print("=" * 60)
    print(f"User: {USER_ID}")
    print(f"Email: {USER_EMAIL}")
    print()

    # 1. User and settings
    create_user_and_settings()
    print()

    # 2. YouTube connections
    language_channels = create_youtube_connections()
    print()

    # 3. Source videos
    video_ids = create_source_videos()
    print()

    # 4. Projects
    print("📁 Creating projects...")
    p_main = create_project("Main Channel Localizations", "Primary localization project for main content")
    p_shorts = create_project("Shorts & Clips", "Quick translations for short-form content")
    p_music = create_project("Music Videos", "Music video localization project")
    p_archive = create_project("Archive Restoration", "Legacy content restoration and localization")
    projects = [p_main, p_shorts, p_music, p_archive]
    print()

    # 5. Create diverse job scenarios
    print("⚙️  Creating processing jobs with various states...")
    print()

    # Scenario 1: Multiple completed jobs with published videos
    print("✅ Scenario 1: Completed jobs with published videos")
    j1 = create_job(p_main, 'completed', SOURCE_VIDEOS[0], ['es', 'de', 'fr'], progress=100, days_ago=7)
    for lang in ['es', 'de', 'fr']:
        create_localized_video(j1, SOURCE_VIDEOS[0], lang, 'live', language_channels.get(lang))

    j2 = create_job(p_music, 'completed', SOURCE_VIDEOS[4], ['es', 'pt', 'ja'], progress=100, days_ago=5)
    for lang in ['es', 'pt', 'ja']:
        create_localized_video(j2, SOURCE_VIDEOS[4], lang, 'live', language_channels.get(lang))
    print()

    # Scenario 2: Jobs waiting for approval (ready state)
    print("⏳ Scenario 2: Jobs awaiting approval")
    j3 = create_job(p_main, 'waiting_approval', SOURCE_VIDEOS[1], ['de', 'fr'], progress=100, days_ago=2)
    for lang in ['de', 'fr']:
        create_localized_video(j3, SOURCE_VIDEOS[1], lang, 'waiting_approval', language_channels.get(lang))

    j4 = create_job(p_shorts, 'waiting_approval', SOURCE_VIDEOS[3], ['es', 'pt'], progress=100, days_ago=1)
    for lang in ['es', 'pt']:
        create_localized_video(j4, SOURCE_VIDEOS[3], lang, 'waiting_approval', language_channels.get(lang))
    print()

    # Scenario 3: Active processing jobs
    print("🔄 Scenario 3: Active processing jobs")
    j5 = create_job(p_music, 'processing', SOURCE_VIDEOS[2], ['de', 'ja'], progress=65, days_ago=0)
    create_localized_video(j5, SOURCE_VIDEOS[2], 'de', 'processing', language_channels.get('de'))
    create_localized_video(j5, SOURCE_VIDEOS[2], 'ja', 'processing', language_channels.get('ja'))

    j6 = create_job(p_main, 'processing', SOURCE_VIDEOS[5], ['es'], progress=40, days_ago=0)
    create_localized_video(j6, SOURCE_VIDEOS[5], 'es', 'processing', language_channels.get('es'))
    print()

    # Scenario 4: Jobs in various early stages
    print("🚀 Scenario 4: Jobs in early stages")
    j7 = create_job(p_shorts, 'processing', SOURCE_VIDEOS[6], ['fr', 'pt'], progress=15, days_ago=0)
    j8 = create_job(p_archive, 'processing', SOURCE_VIDEOS[7], ['de'], progress=25, days_ago=0)
    print()

    # Scenario 5: Failed jobs with error messages
    print("❌ Scenario 5: Failed jobs")
    create_job(
        p_archive, 'failed', SOURCE_VIDEOS[3], ['zh', 'ar'],
        progress=10,
        error_msg="Translation API quota exceeded. Please upgrade your plan.",
        days_ago=3
    )

    create_job(
        p_main, 'failed', SOURCE_VIDEOS[6], ['ko'],
        progress=45,
        error_msg="Voice cloning failed: Audio quality insufficient for voice model training.",
        days_ago=1
    )
    print()

    # Scenario 6: Draft videos (saved but not published)
    print("📝 Scenario 6: Draft videos")
    j9 = create_job(p_shorts, 'completed', SOURCE_VIDEOS[1], ['es'], progress=100, days_ago=4)
    create_localized_video(j9, SOURCE_VIDEOS[1], 'es', 'draft', language_channels.get('es'))
    print()

    # Scenario 7: Large multi-language job
    print("🌍 Scenario 7: Large multi-language job")
    many_langs = ['es', 'de', 'fr', 'pt', 'ja']
    j10 = create_job(p_main, 'processing', SOURCE_VIDEOS[7], many_langs, progress=30, days_ago=0)
    for i, lang in enumerate(many_langs):
        # Simulate some completed, some in progress
        if i < 2:
            create_localized_video(j10, SOURCE_VIDEOS[7], lang, 'processing', language_channels.get(lang))
        else:
            create_localized_video(j10, SOURCE_VIDEOS[7], lang, 'pending', language_channels.get(lang))
    print()

    # 6. Additional activity logs for variety
    print("📊 Creating additional activity logs...")
    log_activity("System", "User logged in", "info")
    log_activity("Settings updated", "Changed theme to dark mode", "info")
    log_activity("Channel connected", f"Connected YouTube channel: {MASTER_CHANNEL['name']}", "success")
    print()

    print("=" * 60)
    print("✅ COMPREHENSIVE DATA SEEDING COMPLETE!")
    print("=" * 60)
    print()
    print("📈 Summary:")
    print(f"  • Users: 1")
    print(f"  • Projects: 4")
    print(f"  • Source Videos: {len(SOURCE_VIDEOS)}")
    print(f"  • Processing Jobs: 10+")
    print(f"  • Localized Videos: 20+")
    print(f"  • Language Channels: {len(language_channels)}")
    print(f"  • Activity Logs: Multiple")
    print()
    print("🎉 Your test database is ready!")
    print()

if __name__ == "__main__":
    seed_comprehensive_data()
