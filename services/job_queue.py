"""Job queue interface for dubbing pipeline."""
from fastapi import BackgroundTasks
from typing import Optional
import asyncio

from services.supabase_db import supabase_service as firestore_service
from services.dubbing import process_dubbing_job, simulate_dubbing_job


async def enqueue_dubbing_job(
    source_video_id: str,
    source_channel_id: str,
    user_id: str,
    target_languages: list[str],
    project_id: Optional[str] = None,
    is_simulation: bool = False,
    db: Optional[None] = None,  # Kept for compatibility but not used
    background_tasks: Optional[BackgroundTasks] = None
) -> str:
    """
    Enqueue a dubbing job and return job_id.
    
    Args:
        source_video_id: YouTube video ID to process
        source_channel_id: YouTube channel ID
        user_id: User ID
        target_languages: List of language codes to create dubs for
        project_id: Project ID
        is_simulation: If True, run simulation instead of real processing
        db: Deprecated - kept for compatibility (not used, Firestore is used instead)
        background_tasks: FastAPI BackgroundTasks (optional)
        
    Returns:
        str: Job ID
    """
    from services.demo_simulator import demo_simulator
    
    # Create ProcessingJob record in Firestore
    job_id = firestore_service.create_processing_job(
        source_video_id=source_video_id,
        source_channel_id=source_channel_id,
        user_id=user_id,
        target_languages=target_languages,
        project_id=project_id,
        is_simulation=is_simulation
    )
    
    # Check if demo user - use mock pipeline for realistic demo
    if demo_simulator.is_demo_user(user_id):
        print(f"[JOB_QUEUE] Demo user detected - using mock pipeline")
        
        if background_tasks:
            async def run_mock_pipeline():
                from services.mock_pipeline import mock_pipeline
                
                async def progress_callback(job_id, progress, stage):
                    """Update job progress in real-time."""
                    firestore_service.update_processing_job(job_id, {
                        'progress': progress,
                        'current_stage': stage,
                        'status': 'processing' if progress < 100 else 'waiting_approval'
                    })
                
                try:
                    await mock_pipeline.process_job(
                        job_id=job_id,
                        video_id=source_video_id,
                        target_languages=target_languages,
                        user_id=user_id,
                        progress_callback=progress_callback
                    )
                    
                    # Update job status to waiting_approval
                    firestore_service.update_processing_job(job_id, {
                        'status': 'waiting_approval',
                        'progress': 100,
                        'current_stage': 'completed'
                    })
                    
                    # Update all localized videos with dubbed URLs
                    localized_videos = firestore_service.get_localized_videos_by_job_id(job_id)
                    for video in localized_videos:
                        lang = video.get('language_code')
                        # Look up dubbed video URL from demo library
                        from config import DEMO_VIDEO_LIBRARY
                        for video_data in DEMO_VIDEO_LIBRARY.values():
                            if video_data["id"] == source_video_id:
                                lang_data = video_data["languages"].get(lang, {})
                                firestore_service.update_localized_video(video['id'], {
                                    'status': 'waiting_approval',
                                    'storage_url': lang_data.get('dubbed_video_url', video_data['original_url']),
                                    'dubbed_audio_url': lang_data.get('dubbed_audio_url')
                                })
                                break
                    
                except Exception as e:
                    print(f"[JOB_QUEUE] Mock pipeline failed: {str(e)}")
                    firestore_service.update_processing_job(job_id, {
                        'status': 'failed',
                        'error_message': str(e)
                    })
            
            background_tasks.add_task(run_mock_pipeline)
        return job_id
    
    # Enqueue to background task for regular users
    if background_tasks:
        async def process_job():
            if is_simulation:
                await simulate_dubbing_job(job_id)
            else:
                await process_dubbing_job(job_id)
        
        background_tasks.add_task(process_job)
    else:
        # If no background tasks provided, we'll need to handle this differently
        # For now, just create the job record
        pass
    
    return job_id
