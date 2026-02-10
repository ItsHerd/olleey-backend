import asyncio
import os
import sys
import logging
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger("MockFlow")

async def run_simulation():
    print("\n🎬 STARTING FULL PIPELINE MOCK SIMULATION 🎬\n")
    print("Goal: Verify orchestration logic without spending API credits.\n")

    # 1. Setup Data
    job_id = "test_job_123"
    user_id = "test_user_456"
    source_video_id = "dQw4w9WgXcQ"
    target_languages = ["es", "de"]

    # 2. Setup Filesystem State (Real files are needed for MediaFileUpload)
    import tempfile
    temp_dir = tempfile.gettempdir()
    
    # Create dummy video/audio files
    mock_video_path = os.path.join(temp_dir, "mock_video.mp4")
    mock_audio_path = os.path.join(temp_dir, "mock_audio.mp3")
    mock_dubbed_audio_path = os.path.join(temp_dir, "dubbed_audio.mp3")
    mock_synced_video_path = os.path.join(temp_dir, "synced_video.mp4")
    
    for p in [mock_video_path, mock_audio_path, mock_dubbed_audio_path, mock_synced_video_path]:
        with open(p, "wb") as f:
            f.write(b"dummy data")

    # 3. Mock Services
    with patch('services.firestore.firestore_service') as mock_fs, \
         patch('services.dubbing.download_video') as mock_download, \
         patch('services.dubbing.get_storage_service') as mock_storage_get, \
         patch('services.dubbing.elevenlabs_service') as mock_11labs, \
         patch('services.dubbing.process_lip_sync') as mock_synclabs, \
         patch('services.dubbing.download_video_from_url') as mock_download_url, \
         patch('services.dubbing.get_youtube_service') as mock_yt_get, \
         patch('googleapiclient.http.MediaFileUpload') as mock_media_upload, \
         patch('os.unlink') as mock_unlink:

        # --- Configure Mocks ---

        # Firestore
        mock_job = {
            'id': job_id,
            'user_id': user_id,
            'source_video_id': source_video_id,
            'target_languages': target_languages,
            'status': 'pending'
        }
        mock_fs.get_processing_job.return_value = mock_job
        
        # Mock language channel lookup
        def get_channel_side_effect(user_id, language_code):
            return {
                'channel_id': f'channel_{language_code}', 
                'is_paused': False
            }
        mock_fs.get_language_channel_by_language.side_effect = get_channel_side_effect

        # Download Video
        mock_download.return_value = (mock_video_path, mock_audio_path)

        # Storage Service
        mock_storage = MagicMock()
        mock_storage_get.return_value = mock_storage
        mock_storage.upload_and_get_public_url.return_value = "https://public.url/video.mp4"
        mock_storage.upload_video.return_value = "videos/test/final.mp4"
        mock_storage.get_storage_url.return_value = "/storage/videos/test/final.mp4"

        # ElevenLabs
        # Simulate having an API key
        with patch('config.settings.elevenlabs_api_key', 'mock_key_123'):
            mock_11labs.create_dubbing_task = AsyncMock(return_value="dubbing_task_789")
            mock_11labs.wait_for_completion = AsyncMock(return_value=True)
            mock_11labs.download_dubbed_audio = AsyncMock(return_value=mock_dubbed_audio_path)
            mock_11labs.delete_dubbing_project = AsyncMock()

            # SyncLabs
            mock_synclabs.return_value = {'url': 'https://synclabs.so/video.mp4'}
            mock_download_url.return_value = mock_synced_video_path

            # YouTube Upload
            mock_youtube = MagicMock()
            mock_yt_get.return_value = mock_youtube
            mock_insert = MagicMock()
            mock_youtube.videos().insert.return_value = mock_insert
            mock_insert.execute.return_value = {'id': 'new_yt_video_id'}

            # --- Run Code Under Test ---
            from services.dubbing import process_dubbing_job
            
            print(f"🚀 Processing Job: {job_id}")
            await process_dubbing_job(job_id)

        # --- Verify Execution ---
        print("\n✅ VERIFICATION RESULTS:")
        
        # 1. Verify Firestore Updates
        print(f"\n1. Firestore Updates:")
        # We expect multiple updates: downloading, processing, uploading, completed
        calls = mock_fs.update_processing_job.call_args_list
        statuses = [c.kwargs.get('status') for c in calls if c.kwargs.get('status')]
        print(f"   - Status transitions: {statuses}")
        
        if 'completed' in statuses:
            print("   - ✅ Job reached 'completed' status")
        else:
            print("   - ❌ Job did NOT complete")

        # 2. Verify ElevenLabs Interaction
        print(f"\n2. ElevenLabs Interaction:")
        if mock_11labs.create_dubbing_task.called:
            print(f"   - ✅ Created dubbing task for: {target_languages}")
        else:
            print("   - ❌ ElevenLabs was not called")

        # 3. Verify SyncLabs Interaction
        print(f"\n3. SyncLabs Interaction:")
        if mock_synclabs.call_count == len(target_languages):
            print(f"   - ✅ Called Lip-Sync for {len(target_languages)} languages")
        else:
            print(f"   - ❌ Expected {len(target_languages)} lip-sync calls, got {mock_synclabs.call_count}")

        # 4. Verify YouTube Upload
        print(f"\n4. YouTube Upload:")
        print(f"   - get_youtube_service called? {mock_yt_get.called}")
        print(f"   - YT Mock Calls: {mock_youtube.mock_calls}")
        print(f"   - MediaUpload Calls: {mock_media_upload.mock_calls}")

        if len(mock_youtube.videos().insert.call_args_list) > 0:
            print(f"   - ✅ Uploaded to YouTube")
            print(f"   - ✅ Upload count: {len(mock_youtube.videos().insert.call_args_list)}")
        else:
            print("   - ❌ No YouTube uploads attempted")

    print("\n🎉 SIMULATION COMPLETE")

if __name__ == "__main__":
    asyncio.run(run_simulation())
