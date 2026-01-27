"""Job queue interface for dubbing pipeline."""
from fastapi import BackgroundTasks
from typing import Optional
import asyncio

from services.firestore import firestore_service
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
    # Create ProcessingJob record in Firestore
    job_id = firestore_service.create_processing_job(
        source_video_id=source_video_id,
        source_channel_id=source_channel_id,
        user_id=user_id,
        target_languages=target_languages,
        project_id=project_id,
        is_simulation=is_simulation
    )
    
    # Enqueue to background task
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
