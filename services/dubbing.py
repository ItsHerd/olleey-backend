"""Main dubbing pipeline orchestration."""
import os
import asyncio
import tempfile
import json
import uuid
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from services.firestore import firestore_service
from services.notification import notification_service
from services.video_download import download_video
from services.synclabs import process_lip_sync, download_video_from_url
from services.storage import get_storage_service
from services.elevenlabs_service import elevenlabs_service
from routers.youtube_auth import get_youtube_service
from config import settings


async def update_job_status_and_notify(job_id: str, **kwargs):
    """
    Helper to update Firestore and broadcast notification.
    """
    # 1. Update Firestore
    firestore_service.update_processing_job(job_id, **kwargs)
    
    # 2. Get updated job data for notification
    # We could fetch it, or construct it from kwargs. Fetching ensures consistency.
    job = firestore_service.get_processing_job(job_id)
    if job:
        # Broadcast update
        await notification_service.broadcast_job_update(
            user_id=job.get('user_id'),
            job_id=job_id,
            status=job.get('status'),
            data=job
        )


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
        await update_job_status_and_notify(job_id, status='downloading', progress=10)
        
        # Step 1: Download video from YouTube
        source_video_id = job.get('source_video_id')
        user_id = job.get('user_id')
        video_url = f"https://www.youtube.com/watch?v={source_video_id}"
        video_path, audio_path, video_info = await download_video(video_url)
        
        print(f"[DUBBING] Downloaded video: {video_path}")
        print(f"[DUBBING] Downloaded audio: {audio_path}")
        
        # Log activity
        firestore_service.log_activity(
            user_id=user_id,
            project_id=job.get('project_id'),
            action="Downloaded source video",
            details=f"Video ID: {source_video_id}"
        )
        
        await update_job_status_and_notify(job_id, status='processing', progress=30)
        
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

                # Step 2a.1: Save localized audio to permanent storage for preview
                # We do this so the UI can play the "Dubbed Audio" preview before Lip Sync
                audio_filename = f"{source_video_id}_{language_code}_audio.mp3"
                audio_storage_path = storage_service.upload_file(
                    file_path=localized_audio_path,
                    user_id=user_id,
                    job_id=job_id,
                    language_code=language_code,
                    filename=audio_filename
                )
                
                # Generate persistent URL for audio
                base_url = getattr(settings, 'webhook_base_url', 'http://localhost:8000')
                # Assuming upload_video puts it in a place accessible via get_storage_url or similar
                # Since upload_video is specific to videos, we might want to check storage_service
                # But for now we use what we have. If upload_video works for mp3, great.
                dubbed_audio_url = storage_service.get_storage_url(audio_storage_path, base_url)
                
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
                
                # Generate URL for storage path
                base_url = getattr(settings, 'webhook_base_url', 'http://localhost:8000')
                storage_url = storage_service.get_storage_url(storage_path, base_url)
                
                # Get channel ID if available
                channel_id = ''
                language_channel = firestore_service.get_language_channel_by_language(
                    user_id=user_id,
                    language_code=language_code
                )
                if language_channel:
                    channel_id = language_channel.get('channel_id', '')
                
                # Prepare metadata
                original_title = video_info.get('title', 'Untitled Video')
                original_description = video_info.get('description', '')
                thumbnail_url = video_info.get('thumbnail')
                
                # Simple "translation" for metadata (append language code)
                # In a real app we would call an LLM or Translation API here
                localized_title = f"{original_title} ({language_code})"
                localized_description = f"Translated to {language_code}:\n\n{original_description}"

                # Create localized video record with waiting_approval status
                firestore_service.create_localized_video(
                    job_id=job_id,
                    user_id=user_id,  # Added user_id
                    source_video_id=source_video_id,
                    language_code=language_code,
                    channel_id=channel_id,
                    status='waiting_approval',
                    storage_url=storage_url,
                    dubbed_audio_url=dubbed_audio_url,
                    thumbnail_url=thumbnail_url,
                    title=localized_title,
                    description=localized_description
                )
                
                # Log activity
                firestore_service.log_activity(
                    user_id=user_id,
                    project_id=job.get('project_id'),
                    action="Processed video",
                    details=f"Video localized for language {language_code}. Awaiting approval."
                )
                
                processed_videos[language_code] = {
                    'local_path': synced_video_path,
                    'storage_path': storage_path
                }
                
                # Update progress
                progress = 30 + int((idx + 1) / total_languages * 40)
                await update_job_status_and_notify(job_id, progress=progress)
                
            except Exception as e:
                # Log error but continue with other languages
                print(f"[DUBBING] Error processing {language_code}: {str(e)}")
                firestore_service.create_localized_video(
                    job_id=job_id,
                    user_id=user_id,  # Added user_id
                    source_video_id=source_video_id,
                    language_code=language_code,
                    channel_id='',  # Will be set when we get channel
                    status='failed'
                )
                
                # Log activity
                firestore_service.log_activity(
                    user_id=user_id,
                    project_id=job.get('project_id'),
                    action="Processing failed",
                    status="error",
                    details=f"Failed to process language {language_code}: {str(e)}"
                )
                continue
        
        # Update job status to waiting_approval
        await update_job_status_and_notify(
            job_id, 
            status='waiting_approval', 
            progress=90
        )
        
        # Clean up temp storage files
        print(f"[DUBBING] Cleaning up temp files for job {job_id}")
        storage_service.cleanup_temp_files(user_id, job_id)
        
        # Clean up downloaded files
        if os.path.exists(video_path):
            os.unlink(video_path)
        if os.path.exists(audio_path) and audio_path != video_path:
            os.unlink(audio_path)
            
        # Send system notification for approval
        await notification_service.broadcast_system_message(
            user_id,
            f"Job {job_id} processed and waiting for approval"
        )
            
    except Exception as e:
        # Update job status to failed
        await update_job_status_and_notify(
            job_id,
            status='failed',
            error_message=str(e),
            completed_at=datetime.utcnow()
        )


async def simulate_dubbing_job(job_id: str):
    """
    Simulate a dubbing job processing for UI testing.
    """
    job = firestore_service.get_processing_job(job_id)
    if not job:
        return
    
    try:
        user_id = job.get('user_id')
        source_video_id = job.get('source_video_id')
        target_languages = job.get('target_languages', [])
        
        print(f"[SIMULATION] Starting simulation for job {job_id}")
        
        # 1. Simulate Downloading (0-10%)
        time_step = 0.5  # Seconds per step
        await update_job_status_and_notify(job_id, status='downloading', progress=10)
        await asyncio.sleep(time_step * 2)
        
        # 2. Simulate Processing (10-90%)
        # Calculate steps based on languages
        progress_per_lang = 80 / max(len(target_languages), 1)
        current_progress = 10
        
        # Mock source video thumbnail
        mock_thumbnail = f"https://i.ytimg.com/vi/{source_video_id}/hqdefault.jpg" if source_video_id else None
        
        for lang in target_languages:
            # Simulate ElevenLabs & Veo processing time
            await update_job_status_and_notify(job_id, status='processing', progress=int(current_progress))
            await asyncio.sleep(time_step)
            
            current_progress += progress_per_lang / 2
            await update_job_status_and_notify(job_id, progress=int(current_progress))
            await asyncio.sleep(time_step)
            
            current_progress += progress_per_lang / 2
            
            # Create localized video record
            language_name = lang.upper() # In real app we map code to name
            
            # Use mock storage URL
            mock_storage_url = f"/storage/videos/mock_dub_{lang}_{uuid.uuid4().hex[:6]}.mp4"
            
            channel_id = ''
            language_channel = firestore_service.get_language_channel_by_language(
                user_id=user_id,
                language_code=lang
            )
            if language_channel:
                channel_id = language_channel.get('channel_id', '')
                
            firestore_service.create_localized_video(
                job_id=job_id,
                user_id=user_id,  # Added user_id
                source_video_id=source_video_id,
                language_code=lang,
                channel_id=channel_id,
                status='waiting_approval',
                storage_url=mock_storage_url,
                thumbnail_url=mock_thumbnail,
                dubbed_audio_url=f"/storage/audios/mock_dub_{lang}_{uuid.uuid4().hex[:6]}.mp3",
                title=f"Simulated Title {source_video_id} ({lang})",
                description=f"This is a simulated translated description for language {lang}."
            )
            
            # Log activity
            firestore_service.log_activity(
                user_id=user_id,
                project_id=job.get('project_id'),
                action="Processed video (Simulated)",
                details=f"Video localized for language {lang}. Awaiting approval."
            )
            
        # 3. Complete Processing -> Waiting Approval
        await update_job_status_and_notify(job_id, status='waiting_approval', progress=90)
        
        await notification_service.broadcast_system_message(
            user_id,
            f"Job {job_id} (Simulated) ready for approval"
        )
        print(f"[SIMULATION] Job {job_id} waiting for approval")
        
    except Exception as e:
        print(f"[SIMULATION] Error: {str(e)}")
        await update_job_status_and_notify(job_id, status='failed', error_message=str(e))


async def simulate_publishing(job_id: str):
    """
    Simulate publishing phase for simulation jobs.
    """
    job = firestore_service.get_processing_job(job_id)
    if not job:
        return
        
    user_id = job.get('user_id')
    localized_videos = firestore_service.get_localized_videos_by_job_id(job_id)
    
    print(f"[SIMULATION] Starting publishing simulation for job {job_id}")
    
    # Update to uploading
    await update_job_status_and_notify(job_id, status='uploading', progress=90)
    
    total_videos = len(localized_videos)
    videos_processed = 0
    
    for vid in localized_videos:
        if vid.get('status') != 'waiting_approval':
            continue
            
        # Simulate upload time
        await asyncio.sleep(1)
        
        # Update localized video status
        firestore_service.update_localized_video(
            vid['id'],
            status='uploaded',
            localized_video_id=f"sim_yt_{uuid.uuid4().hex[:10]}"
        )
        
        # Log activity
        firestore_service.log_activity(
            user_id=user_id,
            project_id=job.get('project_id'),
            action="Published video (Simulated)",
            status="success",
            details=f"Video for {vid.get('language_code')} published to YouTube."
        )
        
        videos_processed += 1
        progress = 90 + int((videos_processed / total_videos) * 9)
        await update_job_status_and_notify(job_id, progress=progress)
        
    # Complete
    await update_job_status_and_notify(
        job_id, 
        status='completed', 
        progress=100,
        completed_at=datetime.utcnow()
    )
    
    await notification_service.broadcast_system_message(
        user_id,
        f"Job {job_id} (Simulated) published successfully"
    )
    print(f"[SIMULATION] Job {job_id} publishing complete")
    return {"success": True, "published_count": videos_processed}


async def publish_dubbed_videos(job_id: str):
    """
    Publish processed videos to YouTube after approval.
    """
    try:
        job = firestore_service.get_processing_job(job_id)
        if not job:
            raise ValueError(f"Job {job_id} not found")
            
        # Check for simulation flag
        if job.get('is_simulation', False):
            return await simulate_publishing(job_id)
        
        user_id = job.get('user_id')
        source_video_id = job.get('source_video_id')
        
        # Update status to uploading
        await update_job_status_and_notify(job_id, status='uploading', progress=95)
        
        # Get all localized videos (waiting for approval)
        localized_videos = firestore_service.get_localized_videos_by_job_id(job_id)
        
        # Get YouTube service
        youtube = await asyncio.to_thread(get_youtube_service, user_id, None, False)
        
        # Get storage service
        storage_service = get_storage_service()
        
        success_count = 0
        
        for video_record in localized_videos:
            status = video_record.get('status')
            if status != 'waiting_approval':
                continue
                
            language_code = video_record.get('language_code')
            print(f"[PUBLISH] Publishing video for language: {language_code}")
            
            try:
                # Extract storage path from storage URL
                storage_url = video_record.get('storage_url', '')
                if '/storage/' in storage_url:
                    relative_path = storage_url.split('/storage/', 1)[1]
                    local_path = storage_service.get_video_path(relative_path)
                    
                    if not local_path or not os.path.exists(local_path):
                        print(f"[PUBLISH] Video file not found: {relative_path}")
                        continue
                        
                    # Get language channel
                    language_channel = firestore_service.get_language_channel_by_language(
                        user_id=user_id,
                        language_code=language_code
                    )
                    
                    if not language_channel or language_channel.get('is_paused', False):
                        print(f"[PUBLISH] No active channel for {language_code}, marking as saved")
                        # Mark as saved locally without upload
                        firestore_service.update_localized_video(
                            video_record['id'],
                            status='saved',
                            localized_video_id=None
                        )
                        success_count += 1
                        continue
                        
                    # Upload to YouTube
                    if youtube:
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
                            local_path,
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
                    else:
                        # Mock ID
                        localized_video_id = f"mock_upload_{language_code}_{int(datetime.utcnow().timestamp())}"
                    
                    # Update localized video record
                    firestore_service.update_localized_video(
                        video_record['id'],
                        status='uploaded',
                        localized_video_id=localized_video_id
                    )
                    
                    # Log activity
                    firestore_service.log_activity(
                        user_id=user_id,
                        project_id=job.get('project_id'),
                        action="Published video",
                        status="success",
                        details=f"Video for {language_code} published to YouTube (ID: {localized_video_id})."
                    )
                    
                    success_count += 1
                    
            except Exception as e:
                print(f"[PUBLISH] Error publishing {language_code}: {str(e)}")
                firestore_service.update_localized_video(
                    video_record['id'],
                    status='failed_upload'
                )
                
        # Update job status to completed
        await update_job_status_and_notify(
            job_id,
            status='completed',
            progress=100,
            completed_at=datetime.utcnow()
        )
        
        await notification_service.broadcast_system_message(
            user_id,
            f"Job {job_id} published successfully"
        )
        
        return {"success": True, "published_count": success_count}
        
    except Exception as e:
        print(f"[PUBLISH] Fatal error: {str(e)}")
        await update_job_status_and_notify(
             job_id,
             error_message=f"Publish failed: {str(e)}"
        )
        raise
