"""Job status and management router."""
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks
from typing import Optional
from datetime import datetime

from services.firestore import firestore_service
from services.job_queue import enqueue_dubbing_job
from schemas.jobs import CreateJobRequest, ProcessingJobResponse, JobListResponse
from middleware.auth import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=ProcessingJobResponse)
async def create_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
) -> ProcessingJobResponse:
    """
    Create a new dubbing job.
    
    This will:
    1. Download the video from YouTube
    2. Process with Sync Labs for each target language
    3. Upload to the corresponding language channels
    
    Args:
        request: Job creation request with video ID and target languages
        background_tasks: FastAPI background tasks for async processing
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        ProcessingJobResponse: Created job details
        
    Raises:
        HTTPException: If job creation fails
    """
    user_id = current_user["user_id"]
    
    try:
        # Validate that user has language channels for requested languages
        language_channels = firestore_service.get_language_channels(user_id)
        available_languages = [ch.get('language_code') for ch in language_channels if not ch.get('is_paused', False)]
        
        # Filter out paused channels
        valid_languages = [lang for lang in request.target_languages if lang in available_languages]
        
        if not valid_languages:
            raise HTTPException(
                status_code=400,
                detail=f"No active language channels found for languages: {request.target_languages}. Available: {available_languages}"
            )
        
        # Create and enqueue the job
        job_id = await enqueue_dubbing_job(
            source_video_id=request.source_video_id,
            source_channel_id=request.source_channel_id,
            user_id=user_id,
            target_languages=valid_languages,
            background_tasks=background_tasks
        )
        
        # Get the created job to return
        job = firestore_service.get_processing_job(job_id)
        
        if not job:
            raise HTTPException(
                status_code=500,
                detail="Job created but could not be retrieved"
            )
        
        # Convert Firestore timestamps
        created_at = job.get('created_at')
        updated_at = job.get('updated_at')
        
        if hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp())
        elif isinstance(created_at, (int, float)):
            created_at = datetime.fromtimestamp(created_at)
        
        if hasattr(updated_at, 'timestamp'):
            updated_at = datetime.fromtimestamp(updated_at.timestamp())
        elif isinstance(updated_at, (int, float)):
            updated_at = datetime.fromtimestamp(updated_at)
        
        return ProcessingJobResponse(
            job_id=job['id'],
            status=job.get('status', 'pending'),
            progress=job.get('progress', 0),
            source_video_id=job.get('source_video_id'),
            source_channel_id=job.get('source_channel_id'),
            target_languages=job.get('target_languages', []),
            created_at=created_at or datetime.utcnow(),
            updated_at=updated_at or datetime.utcnow(),
            completed_at=None,
            error_message=None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job: {str(e)}"
        )


@router.get("/{job_id}", response_model=ProcessingJobResponse)
async def get_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
) -> ProcessingJobResponse:
    """
    Get processing job status and progress.
    
    Args:
        job_id: Job ID
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        ProcessingJobResponse: Job details
        
    Raises:
        HTTPException: If job not found
    """
    user_id = current_user["user_id"]
    job = firestore_service.get_processing_job(job_id)
    
    if not job or job.get('user_id') != user_id:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )
    
    # Convert Firestore timestamps to datetime if needed
    created_at = job.get('created_at')
    updated_at = job.get('updated_at')
    completed_at = job.get('completed_at')
    
    if isinstance(created_at, datetime):
        pass
    elif hasattr(created_at, 'timestamp'):
        created_at = created_at.timestamp()
        created_at = datetime.fromtimestamp(created_at) if created_at else None
    
    return ProcessingJobResponse(
        job_id=job['id'],
        status=job.get('status', 'pending'),
        progress=job.get('progress'),
        source_video_id=job.get('source_video_id'),
        source_channel_id=job.get('source_channel_id'),
        target_languages=job.get('target_languages', []),
        created_at=created_at or datetime.utcnow(),
        updated_at=updated_at or datetime.utcnow(),
        completed_at=completed_at,
        error_message=job.get('error_message')
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user)
) -> JobListResponse:
    """
    List jobs for user with optional filtering.
    
    Args:
        status: Optional status filter
        limit: Maximum number of jobs to return
        offset: Pagination offset
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        JobListResponse: List of jobs
    """
    user_id = current_user["user_id"]
    jobs, total = firestore_service.list_processing_jobs(
        user_id=user_id,
        status=status,
        limit=limit,
        offset=offset
    )
    
    # Convert Firestore data to response models
    job_responses = []
    for job in jobs:
        created_at = job.get('created_at')
        updated_at = job.get('updated_at')
        completed_at = job.get('completed_at')
        
        # Handle Firestore timestamp conversion
        if hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp())
        elif isinstance(created_at, (int, float)):
            created_at = datetime.fromtimestamp(created_at)
        
        if hasattr(updated_at, 'timestamp'):
            updated_at = datetime.fromtimestamp(updated_at.timestamp())
        elif isinstance(updated_at, (int, float)):
            updated_at = datetime.fromtimestamp(updated_at)
        
        if completed_at:
            if hasattr(completed_at, 'timestamp'):
                completed_at = datetime.fromtimestamp(completed_at.timestamp())
            elif isinstance(completed_at, (int, float)):
                completed_at = datetime.fromtimestamp(completed_at)
        
        job_responses.append(ProcessingJobResponse(
            job_id=job['id'],
            status=job.get('status', 'pending'),
            progress=job.get('progress'),
            source_video_id=job.get('source_video_id'),
            source_channel_id=job.get('source_channel_id'),
            target_languages=job.get('target_languages', []),
            created_at=created_at or datetime.utcnow(),
            updated_at=updated_at or datetime.utcnow(),
            completed_at=completed_at,
            error_message=job.get('error_message')
        ))
    
    return JobListResponse(
        jobs=job_responses,
        total=total
    )
