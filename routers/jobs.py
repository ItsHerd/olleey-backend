"""Job status and management router."""
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, UploadFile, File, Form
from typing import Optional, List
from datetime import datetime
import re
import tempfile
import os

from services.firestore import firestore_service
from services.job_queue import enqueue_dubbing_job
from schemas.jobs import CreateJobRequest, CreateManualJobRequest, ProcessingJobResponse, JobListResponse
from middleware.auth import get_current_user

router = APIRouter(prefix="/jobs", tags=["jobs"])


def extract_video_id_from_url(url: str) -> Optional[str]:
    """
    Extract YouTube video ID from various URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/v/VIDEO_ID
    
    Args:
        url: YouTube video URL
        
    Returns:
        Video ID if found, None otherwise
    """
    # Pattern 1: youtube.com/watch?v=VIDEO_ID
    match = re.search(r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})', url)
    if match:
        return match.group(1)
    
    # Pattern 2: Just the video ID (11 characters)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    
    return None


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
        request: Job creation request with video ID/URL and target languages
        background_tasks: FastAPI background tasks for async processing
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        ProcessingJobResponse: Created job details
        
    Raises:
        HTTPException: If job creation fails
    """
    user_id = current_user["user_id"]
    
    try:
        # Extract video ID from URL if provided
        source_video_id = request.source_video_id
        
        if not source_video_id and request.source_video_url:
            # Extract video ID from YouTube URL
            source_video_id = extract_video_id_from_url(request.source_video_url)
            if not source_video_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid YouTube URL: {request.source_video_url}"
                )
        
        if not source_video_id:
            raise HTTPException(
                status_code=400,
                detail="Either source_video_id or source_video_url must be provided"
            )
        
        # Validate target channels and extract languages
        all_channels = firestore_service.get_language_channels(user_id)
        
        # Create a map of channel document IDs to channel data
        channel_map = {ch.get('id'): ch for ch in all_channels}
        
        # Validate requested channels exist and are not paused
        target_languages = []
        valid_channel_ids = []
        
        for channel_id in request.target_channel_ids:
            channel = channel_map.get(channel_id)
            
            if not channel:
                raise HTTPException(
                    status_code=400,
                    detail=f"Channel not found: {channel_id}"
                )
            
            if channel.get('is_paused', False):
                continue  # Skip paused channels
            
            # Extract languages from this channel
            # Channels can have multiple languages (language_codes) or single language (language_code)
            channel_languages = channel.get('language_codes', [])
            if not channel_languages and channel.get('language_code'):
                channel_languages = [channel.get('language_code')]
            
            if channel_languages:
                target_languages.extend(channel_languages)
                valid_channel_ids.append(channel_id)
        
        # Remove duplicates while preserving order
        target_languages = list(dict.fromkeys(target_languages))
        
        if not target_languages:
            raise HTTPException(
                status_code=400,
                detail=f"No active channels found or channels have no languages configured. Requested: {request.target_channel_ids}"
            )
        
        # Create and enqueue the job
        job_id = await enqueue_dubbing_job(
            source_video_id=source_video_id,
            source_channel_id=request.source_channel_id,
            user_id=user_id,
            target_languages=target_languages,
            project_id=request.project_id,
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
            project_id=job.get('project_id'),
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


@router.post("/manual", response_model=ProcessingJobResponse)
async def create_manual_job(
    source_channel_id: str = Form(..., description="YouTube channel ID where video is published"),
    target_channel_ids: Optional[str] = Form(None, description="Comma-separated list of target channel IDs"),
    target_languages: Optional[str] = Form(None, description="Comma-separated list of target language codes (e.g. 'es,de')"),
    project_id: Optional[str] = Form(None, description="Project ID to assign job to"),
    video_url: Optional[str] = Form(None, description="YouTube video URL (if not uploading a file)"),
    video_file: Optional[UploadFile] = File(None, description="Video file to upload (if not providing a URL)"),
    background_tasks: BackgroundTasks = None,
    current_user: dict = Depends(get_current_user)
) -> ProcessingJobResponse:
    """
    Create a manual dubbing job with video URL or file upload.
    
    For manual requests, the user can provide:
    - Project ID (optional)
    - Source channel ID
    - Target channel IDs (optional)
    - Target languages (optional, explicit)
    - Video as either YouTube URL or file
    
    Args:
        source_channel_id: YouTube channel ID
        target_channel_ids: Comma-separated channel IDs
        target_languages: Comma-separated language codes
        project_id: Optional project ID
        video_url: Optional YouTube video URL
        video_file: Optional video file upload
        background_tasks: Tasks
        current_user: User
        
    Returns:
        ProcessingJobResponse
    """
    user_id = current_user["user_id"]
    
    try:
        # Parse inputs
        target_channel_id_list = []
        if target_channel_ids:
            target_channel_id_list = [ch_id.strip() for ch_id in target_channel_ids.split(',') if ch_id.strip()]
            
        target_language_list = []
        if target_languages:
            target_language_list = [lang.strip() for lang in target_languages.split(',') if lang.strip()]
        
        if not target_channel_id_list and not target_language_list:
            raise HTTPException(
                status_code=400,
                detail="At least one target channel OR target language must be provided"
            )
        
        # Determine video source
        source_video_id = None
        temp_file_path = None
        
        if video_url and video_file:
            raise HTTPException(
                status_code=400,
                detail="Please provide either video_url OR video_file, not both"
            )
        
        if video_url:
            # Extract video ID from URL
            source_video_id = extract_video_id_from_url(video_url)
            if not source_video_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid YouTube URL: {video_url}"
                )
        elif video_file:
            # Handle video file upload
            # For test accounts with mock credentials, we'll return a mock video ID
            # For real accounts, we'll upload it to YouTube first, then process it
            from routers.videos import get_youtube_service
            import asyncio
            from googleapiclient.http import MediaFileUpload
            
            try:
                # Get YouTube service (don't raise on mock, return None instead)
                youtube = await asyncio.to_thread(get_youtube_service, user_id, None, False)
                
                if youtube is None:
                    # Mock credentials detected - return mock video ID without uploading
                    print(f"[MANUAL_JOB] Mock credentials detected, using mock video ID for uploaded file")
                    # Generate a mock video ID based on filename
                    filename_safe = video_file.filename.replace('.', '_').replace(' ', '_')[:20] if video_file.filename else 'uploaded'
                    source_video_id = f"mock_upload_{filename_safe}_{user_id[:8]}"
                    print(f"[MANUAL_JOB] Generated mock video ID: {source_video_id}")
                else:
                    # Real credentials - actually upload to YouTube
                    # Save uploaded file to temporary location
                    suffix = os.path.splitext(video_file.filename)[1] if video_file.filename else '.mp4'
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                        temp_file_path = temp_file.name
                        # Read and write file in chunks to handle large files
                        while True:
                            chunk = await video_file.read(1024 * 1024)  # 1MB chunks
                            if not chunk:
                                break
                            temp_file.write(chunk)
                    
                    # Create video metadata
                    video_title = video_file.filename or "Uploaded Video for Dubbing"
                    body = {
                        'snippet': {
                            'title': video_title,
                            'description': 'Video uploaded for dubbing processing',
                            'tags': ['dubbing', 'localization'],
                            'categoryId': '22'  # People & Blogs category
                        },
                        'status': {
                            'privacyStatus': 'private',  # Keep uploaded videos private
                            'selfDeclaredMadeForKids': False
                        }
                    }
                    
                    # Create media upload
                    media = MediaFileUpload(
                        temp_file_path,
                        chunksize=-1,
                        resumable=True
                    )
                    
                    # Insert video
                    insert_request = youtube.videos().insert(
                        part=','.join(body.keys()),
                        body=body,
                        media_body=media
                    )
                    
                    # Execute upload
                    response = await asyncio.to_thread(insert_request.execute)
                    source_video_id = response['id']
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to upload video to YouTube: {str(e)}"
                )
            finally:
                # Clean up temporary file
                if temp_file_path and os.path.exists(temp_file_path):
                    try:
                        os.unlink(temp_file_path)
                    except Exception:
                        pass
        else:
            raise HTTPException(
                status_code=400,
                detail="Either video_url or video_file must be provided"
            )
        
        # Validate target channels and extract languages
        all_channels = firestore_service.get_language_channels(user_id)
        
        # Create a map of channel document IDs to channel data
        channel_map = {ch.get('id'): ch for ch in all_channels}
        
        # Validate requested channels exist and are not paused
        final_target_languages = []
        valid_channel_ids = []
        
        # 1. Process channels
        for channel_id in target_channel_id_list:
            channel = channel_map.get(channel_id)
            
            if not channel:
                # If channel not found, user might have passed an invalid ID
                # We can either error or ignore. Error is safer.
                raise HTTPException(
                    status_code=400,
                    detail=f"Channel not found: {channel_id}"
                )
            
            if channel.get('is_paused', False):
                continue  # Skip paused channels
            
            # Extract languages from this channel
            channel_languages = channel.get('language_codes', [])
            if not channel_languages and channel.get('language_code'):
                channel_languages = [channel.get('language_code')]
            
            if channel_languages:
                final_target_languages.extend(channel_languages)
                valid_channel_ids.append(channel_id)
        
        # 2. Process explicit languages
        if target_language_list:
            final_target_languages.extend(target_language_list)
        
        # Remove duplicates while preserving order
        final_target_languages = list(dict.fromkeys(final_target_languages))
        
        if not final_target_languages:
            raise HTTPException(
                status_code=400,
                detail=f"No valid target languages found. Please check your channels or provide explicit languages."
            )
        
        # Create and enqueue the job
        job_id = await enqueue_dubbing_job(
            source_video_id=source_video_id,
            source_channel_id=source_channel_id,
            user_id=user_id,
            target_languages=final_target_languages,
            project_id=project_id,
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
            project_id=job.get('project_id'),
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
            detail=f"Failed to create manual job: {str(e)}"
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
        project_id=job.get('project_id'),
        target_languages=job.get('target_languages', []),
        created_at=created_at or datetime.utcnow(),
        updated_at=updated_at or datetime.utcnow(),
        completed_at=completed_at,
        error_message=job.get('error_message')
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(None, description="Filter by status"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
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
        offset=offset,
        project_id=project_id
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
            project_id=job.get('project_id'),
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


@router.post("/{job_id}/approve")
async def approve_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)
):
    """
    Approve a job for publishing.
    
    This acts as the manual approval step for jobs that are in 'waiting_approval' status.
    It triggers the final upload to YouTube channels.
    """
    user_id = current_user["user_id"]
    job = firestore_service.get_processing_job(job_id)
    
    if not job:
        raise HTTPException(
            status_code=404, 
            detail="Job not found"
        )
        
    if job.get('user_id') != user_id:
        raise HTTPException(
            status_code=403, 
            detail="Not authorized to access this job"
        )

    if job.get('status') != 'waiting_approval':
        # If job is already completed or processing, we shouldn't re-approve usually,
        # unless it failed during upload. But for now strict check.
        raise HTTPException(
            status_code=400, 
            detail=f"Job is in state '{job.get('status')}', expected 'waiting_approval'"
        )

    # Import here to avoid potential circular imports if moved to top
    from services.dubbing import publish_dubbed_videos
    
    # Add to background tasks
    background_tasks.add_task(publish_dubbed_videos, job_id)

    return {"status": "approved", "message": "Job approved for publishing"}
