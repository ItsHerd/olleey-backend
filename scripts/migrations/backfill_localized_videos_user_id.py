import sys
import os
import firebase_admin
from firebase_admin import credentials, firestore

# Add parent directory to path to import config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings

def initialize_firebase():
    """Initialize Firebase Admin SDK"""
    if not firebase_admin._apps:
        project_id = getattr(settings, 'firebase_project_id', 'vox-translate-b8c94')
        credentials_path = getattr(settings, 'firebase_credentials_path', None)
        
        # Try to find credentials file
        if credentials_path:
            if not os.path.isabs(credentials_path):
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                credentials_path = os.path.join(project_root, credentials_path)
            
            if os.path.exists(credentials_path):
                cred = credentials.Certificate(credentials_path)
                firebase_admin.initialize_app(cred, {'projectId': project_id})
                print(f"Initialized with credentials: {credentials_path}")
            else:
                print(f"Credentials file not found at {credentials_path}, using default")
                cred = credentials.ApplicationDefault()
                firebase_admin.initialize_app(cred, {'projectId': project_id})
        else:
             # Fallback to default
            print("Using default credentials")
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {'projectId': project_id})

def backfill_localized_videos():
    """Backfill user_id on localized_videos documents."""
    db = firestore.client()
    
    print("Starting backfill of user_id for localized_videos...")
    
    # Get all localized videos
    # Note: In a massive DB, you'd want to paginate this. 
    # For this script, we'll assume it fits in memory or use stream.
    videos_ref = db.collection('localized_videos')
    videos = videos_ref.stream()
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    for video in videos:
        data = video.to_dict()
        video_id = video.id
        
        # Check if user_id is already present
        if 'user_id' in data and data['user_id']:
            skipped_count += 1
            continue
            
        job_id = data.get('job_id')
        if not job_id:
            print(f"⚠️ Video {video_id} has no job_id. Skipping.")
            error_count += 1
            continue
            
        # Fetch the job to get the user_id
        job_ref = db.collection('processing_jobs').document(job_id)
        job_doc = job_ref.get()
        
        if not job_doc.exists:
            print(f"⚠️ Job {job_id} not found for video {video_id}. Skipping.")
            error_count += 1
            continue
            
        job_data = job_doc.to_dict()
        user_id = job_data.get('user_id')
        
        if not user_id:
             print(f"⚠️ Job {job_id} has no user_id. Skipping.")
             error_count += 1
             continue
             
        # Update the localized_video document
        try:
            videos_ref.document(video_id).update({'user_id': user_id})
            print(f"✅ Updated video {video_id} with user_id: {user_id}")
            updated_count += 1
        except Exception as e:
            print(f"❌ Failed to update video {video_id}: {e}")
            error_count += 1

    print("-" * 30)
    print(f"Backfill complete.")
    print(f"Updated: {updated_count}")
    print(f"Skipped (already had user_id): {skipped_count}")
    print(f"Errors/Missing Data: {error_count}")

if __name__ == "__main__":
    try:
        initialize_firebase()
        backfill_localized_videos()
    except Exception as e:
        print(f"Fatal error: {e}")
