"""Main dubbing pipeline orchestration."""
import os
import asyncio
import tempfile
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from services.firestore import firestore_service
from services.video_download import download_video
from services.synclabs import process_lip_sync, download_video_from_url
from services.storage import get_storage_service
from services.elevenlabs_service import elevenlabs_service
from routers.youtube_auth import get_youtube_service
from config import settings


async def process_dubbing_job(job_id: str):
    """
    Process a dubbing job: download video, process with Veo, upload to channels.
    
    Args:
        job_id: Processing job ID
    """
    job = firestore_service.get_processing_job(job_id)
    if not job:
        return
    
    try:
        # Update job status
        firestore_service.update_processing_job(job_id, status='downloading', progress=10)
        
        # Step 1: Download video from YouTube
        source_video_id = job.get('source_video_id')
        user_id = job.get('user_id')
        video_url = f"https://www.youtube.com/watch?v={source_video_id}"
        video_path, audio_path = await download_video(video_url)
        
        print(f"[DUBBING] Downloaded video: {video_path}")
        print(f"[DUBBING] Downloaded audio: {audio_path}")
        
        firestore_service.update_processing_job(job_id, status='processing', progress=30)
        
        # Get storage service
        storage_service = get_storage_service()
        
        # Step 2: Process for each target language
        target_languages = job.get('target_languages', [])
        total_languages = len(target_languages)
        processed_videos = {}
        
        for idx, language_code in enumerate(target_languages):
            try:
                # Get localized audio using ElevenLabs
                if settings.elevenlabs_api_key:
                    print(f"[DUBBING] usage ElevenLabs for {language_code}")
                    
                    # Ensure public URL for source video
                    # We utilize the storage service to get a public URL for the video
                    # This might be redundant if we did it outside, but it ensures we have it
                    video_url_for_elevenlabs = storage_service.upload_and_get_public_url(
                        file_path=video_path,
                        user_id=user_id,
                        job_id=job_id,
                        filename='original_video_for_elevenlabs.mp4'
                    )

                    dubbing_id = await elevenlabs_service.create_dubbing_task(
                        source_url=video_url_for_elevenlabs,
                        target_lang=language_code
                    )
                    
                    print(f"[DUBBING] ElevenLabs task started: {dubbing_id}")
                    await elevenlabs_service.wait_for_completion(dubbing_id)
                    
                    localized_audio_path = os.path.join(
                        tempfile.gettempdir(), 
                        f'elevenlabs_audio_{job_id}_{language_code}.mp3'
                    )
                    await elevenlabs_service.download_dubbed_audio(
                        dubbing_id, 
                        language_code, 
                        localized_audio_path
                    )
                    
                    # Cleanup ElevenLabs project to save space/clutter
                    await elevenlabs_service.delete_dubbing_project(dubbing_id)
                    
                else:
                    # Fallback to original audio if no key provided
                    localized_audio_path = audio_path
                
                print(f"[DUBBING] Processing language: {language_code}")
                
                # Step 2a: Upload original video and audio to temp storage for public URLs
                video_url_public = storage_service.upload_and_get_public_url(
                    file_path=video_path,
                    user_id=user_id,
                    job_id=job_id,
                    filename='original_video.mp4'
                )
                
                audio_url_public = storage_service.upload_and_get_public_url(
                    file_path=localized_audio_path,
                    user_id=user_id,
                    job_id=job_id,
                    filename=f'audio_{language_code}.mp3'
                )
                
                print(f"[DUBBING] Video public URL: {video_url_public}")
                print(f"[DUBBING] Audio public URL: {audio_url_public}")
                
                # Step 2b: Process with Sync Labs using public URLs
                result = await process_lip_sync(
                    video_url=video_url_public,
                    audio_url=audio_url_public
                )
                
                print(f"[DUBBING] Sync Labs result: {result}")
                
                # Step 2c: Download synced video from Sync Labs
                synced_video_path = os.path.join(
                    tempfile.gettempdir(), 
                    f'synced_{job_id}_{language_code}.mp4'
                )
                await download_video_from_url(result['url'], synced_video_path)
                
                print(f"[DUBBING] Downloaded synced video: {synced_video_path}")
                
                # Step 2d: Save processed video to permanent storage
                storage_path = storage_service.upload_video(
                    file_path=synced_video_path,
                    user_id=user_id,
                    job_id=job_id,
                    language_code=language_code,
                    video_id=f"{source_video_id}_{language_code}"
                )
                
                processed_videos[language_code] = {
                    'local_path': synced_video_path,
                    'storage_path': storage_path
                }
                
                # Update progress
                progress = 30 + int((idx + 1) / total_languages * 40)
                firestore_service.update_processing_job(job_id, progress=progress)
                
            except Exception as e:
                # Log error but continue with other languages
                print(f"[DUBBING] Error processing {language_code}: {str(e)}")
                firestore_service.create_localized_video(
                    job_id=job_id,
                    source_video_id=source_video_id,
                    language_code=language_code,
                    channel_id='',  # Will be set when we get channel
                    status='failed'
                )
                continue
        
        # Step 3: Upload to language channels
        firestore_service.update_processing_job(job_id, status='uploading', progress=70)
        
        # Get YouTube service for uploading
        youtube = await asyncio.to_thread(get_youtube_service, user_id, raise_on_mock=False)
        if not youtube:
            raise Exception("Failed to get YouTube service. Please ensure you have a connected YouTube channel.")
        
        for idx, language_code in enumerate(processed_videos.keys()):
            try:
                # Get language channel
                language_channel = firestore_service.get_language_channel_by_language(
                    user_id=user_id,
                    language_code=language_code
                )
                
                if not language_channel:
                    # Skip if no channel configured for this language
                    continue
                
                # Skip if channel is paused
                if language_channel.get('is_paused', False):
                    print(f"[DUBBING] Skipping paused channel for language: {language_code}")
                    continue
                
                video_info = processed_videos[language_code]
                processed_video_path = video_info['local_path']
                storage_path = video_info['storage_path']
                
                # Upload to YouTube
                body = {
                    'snippet': {
                        'title': f'[Dubbed] Video {source_video_id}',
                        'description': f'Localized version in {language_code}',
                        'categoryId': '22'
                    },
                    'status': {
                        'privacyStatus': 'private',
                        'selfDeclaredMadeForKids': False
                    }
                }
                
                media = MediaFileUpload(
                    processed_video_path,
                    chunksize=-1,
                    resumable=True
                )
                
                insert_request = youtube.videos().insert(
                    part=','.join(body.keys()),
                    body=body,
                    media_body=media
                )
                
                response = await asyncio.to_thread(insert_request.execute)
                localized_video_id = response['id']
                
                # Generate URL for storage path
                base_url = getattr(settings, 'webhook_base_url', 'http://localhost:8000')
                storage_url = storage_service.get_storage_url(storage_path, base_url)
                
                # Store in Firestore with storage URL
                firestore_service.create_localized_video(
                    job_id=job_id,
                    source_video_id=source_video_id,
                    language_code=language_code,
                    channel_id=language_channel.get('channel_id'),
                    localized_video_id=localized_video_id,
                    status='uploaded',
                    storage_url=storage_url
                )
                
                # Clean up processed video
                if os.path.exists(processed_video_path):
                    os.unlink(processed_video_path)
                
                # Update progress
                progress = 70 + int((idx + 1) / len(processed_videos) * 25)
                firestore_service.update_processing_job(job_id, progress=progress)
                
            except Exception as e:
                # Log error but continue
                channel_id = language_channel.get('channel_id') if 'language_channel' in locals() else ''
                firestore_service.create_localized_video(
                    job_id=job_id,
                    source_video_id=source_video_id,
                    language_code=language_code,
                    channel_id=channel_id,
                    status='failed'
                )
                continue
        
        # Clean up temp storage files
        print(f"[DUBBING] Cleaning up temp files for job {job_id}")
        storage_service.cleanup_temp_files(user_id, job_id)
        
        # Clean up downloaded files
        if os.path.exists(video_path):
            os.unlink(video_path)
        if os.path.exists(audio_path) and audio_path != video_path:
            os.unlink(audio_path)
        
        # Update job status
        firestore_service.update_processing_job(
            job_id,
            status='completed',
            progress=100,
            completed_at=datetime.utcnow()
        )
        
        print(f"[DUBBING] Job {job_id} completed successfully")
        
    except Exception as e:
        # Update job status to failed
        firestore_service.update_processing_job(
            job_id,
            status='failed',
            error_message=str(e),
            completed_at=datetime.utcnow()
        )
