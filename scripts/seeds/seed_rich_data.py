"""
Script to seed rich mock data for user 5TEUt0AICGcrKAum7LJauZJcODq1.
Includes projects, jobs in various states, and localized videos.
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

USER_ID = "LlGV9wGDuvMcQMOXuVgA59RONxs2"

# Constants
LANGUAGES = ['es', 'de', 'fr', 'it', 'pt', 'ru', 'jp', 'kr', 'hi', 'ar']
LANGUAGE_NAMES = {
    'es': 'Spanish', 'de': 'German', 'fr': 'French', 'it': 'Italian', 
    'pt': 'Portuguese', 'ru': 'Russian', 'jp': 'Japanese', 'kr': 'Korean',
    'hi': 'Hindi', 'ar': 'Arabic'
}

# YouTube Resources
SOURCE_VIDEOS = [
    {"id": "dQw4w9WgXcQ", "title": "Never Gonna Give You Up - Rick Astley", "img": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg"},
    {"id": "jNQXAC9IVRw", "title": "Me at the zoo", "img": "https://i.ytimg.com/vi/jNQXAC9IVRw/hqdefault.jpg"},
    {"id": "9bZkp7q19f0", "title": "Gangnam Style", "img": "https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg"},
    {"id": "CevxZvSJLk8", "title": "Katy Perry - Roar", "img": "https://i.ytimg.com/vi/CevxZvSJLk8/hqdefault.jpg"},
    {"id": "0kswYuWdlE4", "title": "Farrah Fawcett Hair", "img": "https://i.ytimg.com/vi/0kswYuWdlE4/hqdefault.jpg"}
]

def create_project(name: str) -> str:
    print(f"Creating project: {name}")
    project_id = str(uuid.uuid4())
    firestore_service.db.collection('projects').document(project_id).set({
        'user_id': USER_ID,
        'name': name,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    })
    return project_id

def create_job(
    project_id: str, 
    status: str, 
    source_video: Dict, 
    target_langs: List[str],
    progress: int = 0,
    error_msg: str = None
) -> str:
    job_id = str(uuid.uuid4())
    
    job_data = {
        'source_video_id': source_video['id'],
        'source_channel_id': "UCmock_main_channel_123",
        'user_id': USER_ID,
        'project_id': project_id,
        'status': status,
        'target_languages': target_langs,
        'progress': progress,
        'error_message': error_msg,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }
    
    if status == 'completed':
        job_data['completed_at'] = firestore.SERVER_TIMESTAMP
        job_data['progress'] = 100
    
    print(f"Creating job {job_id} [{status}] for video {source_video['title']}")
    firestore_service.db.collection('processing_jobs').document(job_id).set(job_data)
    return job_id

def create_localized_video(
    job_id: str, 
    source_video: Dict, 
    lang: str, 
    status: str,
    fail_video: bool = False
):
    video_id = str(uuid.uuid4())
    lang_name = LANGUAGE_NAMES.get(lang, lang.upper())
    
    storage_url = f"/storage/videos/mock_dub_{lang}.mp4"
    if status == 'pending':
        storage_url = None
        
    title = f"{source_video['title']} ({lang_name} Dub)"
    description = f"AI Translated version of {source_video['title']} in {lang_name}."
    
    if fail_video:
        status = 'failed'
        
    video_data = {
        'job_id': job_id,
        'source_video_id': source_video['id'],
        'localized_video_id': f"vid_{lang}_{uuid.uuid4().hex[:8]}" if status == 'published' else None,
        'language_code': lang,
        'channel_id': f"UCmock_{lang}_channel",
        'status': status,
        'storage_url': storage_url,
        'thumbnail_url': source_video['img'],
        'title': title,
        'description': description,
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    }
    
    firestore_service.db.collection('localized_videos').document(video_id).set(video_data)

def seed_rich_data():
    print(f"🚀 Seeding rich mock data for user: {USER_ID}")
    
    # 1. Projects
    p_main = create_project("Main Channel Dubs")
    p_shorts = create_project("Shorts Translations")
    p_archive = create_project("Archive Restoration")
    
    # 2. Scenario: Happy Path - Completed Job (Multi-language)
    # Status: Completed, all videos published
    j1 = create_job(p_main, 'completed', SOURCE_VIDEOS[0], ['es', 'de', 'fr'])
    for lang in ['es', 'de', 'fr']:
        create_localized_video(j1, SOURCE_VIDEOS[0], lang, 'published')
        
    # 3. Scenario: Waiting Approval (Action Needed)
    # Status: Waiting Approval, videos generated but not published
    j2 = create_job(p_main, 'waiting_approval', SOURCE_VIDEOS[1], ['it', 'pt'], progress=100)
    for lang in ['it', 'pt']:
        create_localized_video(j2, SOURCE_VIDEOS[1], lang, 'waiting_approval')

    # 4. Scenario: Processing (Mid-flight)
    # Status: processing, some videos done, some pending
    j3 = create_job(p_shorts, 'processing', SOURCE_VIDEOS[2], ['ja', 'kr'], progress=45)
    create_localized_video(j3, SOURCE_VIDEOS[2], 'ja', 'pending') # Still processing
    create_localized_video(j3, SOURCE_VIDEOS[2], 'kr', 'pending') # Still processing

    # 5. Scenario: Failed Job (Global Error)
    # Status: failed, error message
    create_job(p_archive, 'failed', SOURCE_VIDEOS[3], ['es'], progress=10, error_msg="Source video download failed: Copyright restriction")
    
    # 6. Scenario: Partial Failure (Complex Edge Case)
    # Job status might be 'completed' or 'failed' depending on logic, but let's say 'completed' with some failed videos?
    # Or 'processing' stuck. Let's do a 'waiting_approval' where one generation failed.
    # Actually, if one fails, usually the whole job might be marked failed or partial.
    # Let's verify 'failed' status with some surviving videos.
    j4 = create_job(p_archive, 'failed', SOURCE_VIDEOS[4], ['ru', 'hi'], progress=80, error_msg="Translation limit exceeded for some languages")
    create_localized_video(j4, SOURCE_VIDEOS[4], 'ru', 'waiting_approval') # This one actually worked
    create_localized_video(j4, SOURCE_VIDEOS[4], 'hi', 'failed', fail_video=True) # This one failed

    # 7. Scenario: Massive Job (Stress Test)
    # Many languages
    many_langs = ['es', 'de', 'fr', 'it', 'pt', 'ru', 'jp', 'kr']
    j5 = create_job(p_main, 'processing', SOURCE_VIDEOS[0], many_langs, progress=20)
    for lang in many_langs:
        create_localized_video(j5, SOURCE_VIDEOS[0], lang, 'pending')

    print("\n✅ Rich data seeding complete!")

if __name__ == "__main__":
    seed_rich_data()
