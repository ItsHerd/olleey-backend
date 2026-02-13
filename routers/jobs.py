"""Job status and management router."""
from fastapi import APIRouter, HTTPException, Query, Depends, BackgroundTasks, UploadFile, File, Form, Body
from typing import Optional, List
from datetime import datetime, timezone
import re
import tempfile
import os
import asyncio
import uuid
import logging

logger = logging.getLogger(__name__)

from services.supabase_db import supabase_service
from services.job_queue import enqueue_dubbing_job
from services.demo_simulator import demo_simulator
from services.job_statistics import job_statistics
from schemas.jobs import CreateJobRequest, CreateManualJobRequest, ProcessingJobResponse, JobListResponse, LocalizedVideoResponse
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
        all_channels = supabase_service.get_language_channels(user_id)
        
        # Create a map of channel document IDs to channel data
        channel_map = {ch.get('id'): ch for ch in all_channels}
        
        # Validate requested channels exist and are not paused
        target_languages = []
        valid_channel_ids = []
        
        # 1. Use direct languages if provided
        if request.target_languages:
            target_languages.extend(request.target_languages)
            
        # 2. Use channel-derived languages if provided
        if request.target_channel_ids:
            for channel_id in request.target_channel_ids:
                channel = channel_map.get(channel_id)
                
                if not channel:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Channel not found: {channel_id}"
                    )
                
                if channel.get('is_paused', False):
                    continue  # Skip paused channels
                
                # Extract language from this channel
                lang_code = channel.get('language_code')
                
                if lang_code:
                    target_languages.append(lang_code)
                    valid_channel_ids.append(channel_id)
        
        # Remove duplicates while preserving order
        target_languages = list(dict.fromkeys(target_languages))
        
        if not target_languages:
            raise HTTPException(
                status_code=400,
                detail=f"No target languages found. Please provide target_channel_ids or target_languages."
            )
        
        source_channel_id = request.source_channel_id or "unknown"
        
        # Create and enqueue the job
        job_id = await enqueue_dubbing_job(
            source_video_id=source_video_id,
            source_channel_id=source_channel_id,
            user_id=user_id,
            target_languages=target_languages,
            project_id=request.project_id,
            is_simulation=request.is_simulation,
            background_tasks=background_tasks
        )
        
        # Log activity
        supabase_service.log_activity(
            user_id=user_id,
            project_id=request.project_id,
            action="Created dubbing job",
            details=f"Job {job_id} created for video {source_video_id}. Status: pending."
        )
        
        # Get the created job to return
        job = supabase_service.get_processing_job(job_id)
        
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
            is_simulation=job.get('is_simulation', False),
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
    is_simulation: bool = Form(False, description="If True, simulates the job instead of actual processing"),
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
        all_channels = supabase_service.get_language_channels(user_id)
        
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
            is_simulation=is_simulation,
            background_tasks=background_tasks
        )
        
        # Log activity
        supabase_service.log_activity(
            user_id=user_id,
            project_id=project_id,
            action="Created manual dubbing job",
            details=f"Job {job_id} created for video {source_video_id}. Status: pending."
        )
        
        # Get the created job to return
        job = supabase_service.get_processing_job(job_id)
        
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
            is_simulation=job.get('is_simulation', False),
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
    job = supabase_service.get_processing_job(job_id)
    
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
    jobs, total = supabase_service.list_processing_jobs(
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
    job = supabase_service.get_processing_job(job_id)
    
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

    # Check if this is a demo user - simulate approval
    if demo_simulator.is_demo_user(user_id) or job.get('is_simulation'):
        print(f"[DEMO] Simulating job approval for {job_id}")
        # Get all videos for this job to approve them all
        videos = supabase_service.get_localized_videos_by_job_id(job_id)
        print(f"[DEMO] Found {len(videos)} videos for job {job_id}")
        video_ids = [v['id'] for v in videos if v.get('status') == 'waiting_approval']
        print(f"[DEMO] Videos waiting approval: {video_ids}")
        if not video_ids:
            print(f"[DEMO] Warning: No videos with 'waiting_approval' status found")
            # Try to find any videos and approve them anyway
            video_ids = [v['id'] for v in videos]
            print(f"[DEMO] Using all video ids: {video_ids}")
        asyncio.create_task(demo_simulator.simulate_approval(user_id, job_id, video_ids, "approve"))
        
        # Log activity
        supabase_service.log_activity(
            user_id=user_id,
            project_id=job.get('project_id'),
            action="Approved dubbing job (simulated)",
            details=f"Job {job_id} approved for publishing."
        )
        
        return {"status": "approved", "message": "Job approved (simulation)", "is_demo": True}
    
    # Import here to avoid potential circular imports if moved to top
    from services.dubbing import publish_dubbed_videos
    
    # Add to background tasks
    background_tasks.add_task(publish_dubbed_videos, job_id)

    # Log activity
    supabase_service.log_activity(
        user_id=user_id,
        project_id=job.get('project_id'),
        action="Approved dubbing job",
        details=f"Job {job_id} approved for publishing."
    )

    return {"status": "approved", "message": "Job approved for publishing"}


@router.post("/{job_id}/videos/approve")
async def approve_videos(
    job_id: str,
    video_ids: List[str],
    current_user: dict = Depends(get_current_user)
):
    """
    Approve specific videos within a job.
    
    This allows selective approval of individual language videos.
    """
    user_id = current_user["user_id"]
    
    # Verify job ownership
    job = supabase_service.get_processing_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if demo/simulation
    if demo_simulator.is_demo_user(user_id) or job.get('is_simulation'):
        print(f"[DEMO] Simulating video approval: {video_ids}")
        asyncio.create_task(demo_simulator.simulate_approval(user_id, job_id, video_ids, "approve"))
        return {"status": "success", "message": f"Approved {len(video_ids)} video(s)", "is_demo": True}
    
    # Real approval logic here
    return {"status": "success", "message": f"Approved {len(video_ids)} video(s)"}


@router.post("/{job_id}/videos/reject")
async def reject_videos(
    job_id: str,
    video_ids: List[str],
    reason: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Reject specific videos within a job.
    
    Rejected videos can be reprocessed or marked for manual review.
    """
    user_id = current_user["user_id"]
    
    # Verify job ownership
    job = supabase_service.get_processing_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    if job.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Check if demo/simulation
    if demo_simulator.is_demo_user(user_id) or job.get('is_simulation'):
        print(f"[DEMO] Simulating video rejection: {video_ids}, reason: {reason}")
        asyncio.create_task(demo_simulator.simulate_approval(user_id, job_id, video_ids, "reject"))
        return {"status": "success", "message": f"Rejected {len(video_ids)} video(s)", "is_demo": True}
    
    # Real rejection logic here
    return {"status": "success", "message": f"Rejected {len(video_ids)} video(s)"}


@router.post("/{job_id}/videos/{language_code}/status")
async def update_demo_video_status(
    job_id: str,
    language_code: str,
    new_status: str = Query(..., regex="^(processing|waiting_approval|published)$"),
    current_user: dict = Depends(get_current_user)
):
    """
    Update video status for demo users (interactive demo control).
    
    This endpoint allows demo users to interactively change the status of localized videos
    to test different workflow states: processing → waiting_approval (draft) → published (live)
    
    Only available for demo@olleey.com user.
    """
    from services.demo_simulator import DEMO_EMAIL
    
    user_id = current_user["user_id"]
    email = current_user.get("email")
    
    # Only allow for demo users
    if email != DEMO_EMAIL:
        raise HTTPException(status_code=403, detail="Only available in demo mode")
    
    try:
        result = await demo_simulator.update_localization_status(
            user_id=user_id,
            job_id=job_id,
            language_code=language_code,
            new_status=new_status
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update status: {str(e)}")


@router.post("/{job_id}/start-processing")
async def start_demo_processing(
    job_id: str,
    language_code: str = Query(default='es'),
    current_user: dict = Depends(get_current_user)
):
    """
    Start processing for queued demo job.
    Simulates 3-4 second processing before moving to draft/review state.
    
    Demo only - requires demo@olleey.com user.
    """
    from services.demo_simulator import DEMO_EMAIL
    
    user_id = current_user["user_id"]
    email = current_user.get("email")
    
    # Only allow for demo users
    if email != DEMO_EMAIL:
        raise HTTPException(status_code=403, detail="Only available in demo mode")
    
    try:
        result = await demo_simulator.start_processing(
            user_id=user_id,
            job_id=job_id,
            language_code=language_code
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start processing: {str(e)}")


@router.post("/{job_id}/pause")
async def pause_demo_job(
    job_id: str,
    language_code: str = Query(default='es'),
    current_user: dict = Depends(get_current_user)
):
    """
    Pause job - return to queued state.
    Allows user to stop review and return video to queue.
    
    Demo only - requires demo@olleey.com user.
    """
    from services.demo_simulator import DEMO_EMAIL
    
    user_id = current_user["user_id"]
    email = current_user.get("email")
    
    # Only allow for demo users
    if email != DEMO_EMAIL:
        raise HTTPException(status_code=403, detail="Only available in demo mode")
    
    try:
        # Move back to queued
        result = await demo_simulator.update_localization_status(
            user_id=user_id,
            job_id=job_id,
            language_code=language_code,
            new_status='queued'
        )
        
        # Also update job status
        job_ref = demo_simulator.db.collection('processing_jobs').document(job_id)
        job_ref.update({
            'status': 'queued',
            'progress': 0,
            'updated_at': datetime.now(timezone.utc).isoformat()
        })
        
        return {"success": True, "status": "paused"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pause job: {str(e)}")


@router.delete("/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Cancel/delete a dubbing job.

    This will:
    1. Update the job status to 'cancelled'
    2. Update all associated localized videos to 'cancelled' status
    3. Log the cancellation activity

    Args:
        job_id: Job ID to cancel
        current_user: Current authenticated user

    Returns:
        Success message

    Raises:
        HTTPException: If job not found or user not authorized
    """
    user_id = current_user["user_id"]

    # Try to get job by job_id first
    job = supabase_service.get_processing_job(job_id)

    # If not found, search by source_video_id (handles cases like Garry Tan demo)
    if not job:
        jobs, _ = supabase_service.list_processing_jobs(user_id, limit=1000)
        for j in jobs:
            if j.get('source_video_id') == job_id:
                job = j
                job_id = j.get('id')
                break

    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found"
        )

    if job.get('user_id') != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not authorized to cancel this job"
        )

    try:
        # Update job status to cancelled
        supabase_service.update_processing_job(job_id, {
            'status': 'cancelled'
        })

        # Update all associated localized videos to cancelled
        videos = supabase_service.get_localized_videos_by_job_id(job_id)
        for video in videos:
            supabase_service.update_localized_video(video['id'], {
                'status': 'cancelled'
            })

        # Log activity
        supabase_service.log_activity(
            user_id=user_id,
            project_id=job.get('project_id'),
            action="Cancelled dubbing job",
            details=f"Job {job_id} was cancelled by user."
        )

        return {
            "success": True,
            "message": f"Job {job_id} cancelled successfully",
            "cancelled_videos": len(videos)
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.get("/{job_id}/videos", response_model=List[LocalizedVideoResponse])
async def get_job_videos(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all localized videos for a specific job.

    This is used by the frontend to fetch video previews for approval.
    """
    user_id = current_user["user_id"]

    # Verify job ownership
    job = supabase_service.get_processing_job(job_id)
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

    # Get localized videos
    videos = supabase_service.get_localized_videos_by_job_id(job_id)

    # Convert timestamps and format response
    response = []
    for vid in videos:
        created_at = vid.get('created_at')
        updated_at = vid.get('updated_at')

        if hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp())
        elif isinstance(created_at, (int, float)):
            created_at = datetime.fromtimestamp(created_at)

        if hasattr(updated_at, 'timestamp'):
            updated_at = datetime.fromtimestamp(updated_at.timestamp())
        elif isinstance(updated_at, (int, float)):
            updated_at = datetime.fromtimestamp(updated_at)

        response.append(LocalizedVideoResponse(
            id=vid['id'],
            job_id=vid.get('job_id'),
            source_video_id=vid.get('source_video_id'),
            language_code=vid.get('language_code'),
            status=vid.get('status'),
            storage_url=vid.get('storage_url'),
            thumbnail_url=vid.get('thumbnail_url'),
            dubbed_audio_url=vid.get('dubbed_audio_url'),
            title=vid.get('title'),
            description=vid.get('description'),
            created_at=created_at or datetime.utcnow(),
            updated_at=updated_at or datetime.utcnow()
        ))

    return response


@router.get("/{job_id}/transcript")
async def get_job_transcript(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get the source transcript for a job.

    Returns the original transcript extracted from ElevenLabs dubbing.
    """
    user_id = current_user["user_id"]

    # Verify job ownership
    job = supabase_service.get_processing_job(job_id)
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

    # Get transcript
    transcript = supabase_service.get_transcript(job_id)

    if not transcript:
        raise HTTPException(
            status_code=404,
            detail="Transcript not found for this job"
        )

    return transcript


@router.get("/{job_id}/translations")
async def get_job_translations(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get all translations for a job.

    Returns translations for all target languages.
    """
    user_id = current_user["user_id"]

    # Verify job ownership
    job = supabase_service.get_processing_job(job_id)
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

    # Get all translations
    translations = supabase_service.get_translations(job_id)

    return translations


@router.get("/{job_id}/translations/{language_code}")
async def get_job_translation(
    job_id: str,
    language_code: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get translation for a specific language.

    Returns the translation for the specified target language.
    """
    user_id = current_user["user_id"]

    # Verify job ownership
    job = supabase_service.get_processing_job(job_id)
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

    # Get specific translation
    translation = supabase_service.get_translation(job_id, language_code)

    if not translation:
        raise HTTPException(
            status_code=404,
            detail=f"Translation not found for language {language_code}"
        )

    return translation


@router.patch("/{job_id}/videos/{language_code}")
async def update_localized_video(
    job_id: str,
    language_code: str,
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    thumbnail_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
):
    """
    Update metadata for a localized video (title, description, thumbnail).
    Used by the Review page to save changes before approval.
    """
    user_id = current_user["user_id"]

    # Verify job ownership
    job = supabase_service.get_processing_job(job_id)
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

    # Find the localized video
    videos = supabase_service.get_localized_videos_by_job_id(job_id)
    target_video = next((v for v in videos if v.get('language_code') == language_code), None)

    if not target_video:
        raise HTTPException(
            status_code=404,
            detail=f"No localized video found for language {language_code}"
        )

    # Prepare update data
    update_data = {
        'updated_at': datetime.now(timezone.utc).isoformat()
    }

    if title is not None:
        update_data['title'] = title

    if description is not None:
        update_data['description'] = description

    # Handle thumbnail upload
    if thumbnail_file:
        try:
            # Create storage path for thumbnail
            thumbnail_suffix = os.path.splitext(thumbnail_file.filename)[1] if thumbnail_file.filename else '.jpg'
            thumbnail_filename = f"{uuid.uuid4()}_thumb{thumbnail_suffix}"
            thumbnail_path = f"videos/{user_id}/localizations/{job_id}/{language_code}/thumbnails/{thumbnail_filename}"

            # Save thumbnail to storage
            os.makedirs(os.path.dirname(f"./storage/{thumbnail_path}"), exist_ok=True)

            with open(f"./storage/{thumbnail_path}", "wb") as f:
                content = await thumbnail_file.read()
                f.write(content)

            # Store relative path (frontend will prepend API_BASE_URL)
            update_data['thumbnail_url'] = f"/storage/{thumbnail_path}"

        except Exception as e:
            logger.error(f"Failed to save thumbnail: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save thumbnail: {str(e)}"
            )

    # Update the localized video in Supabase
    supabase_service.update_localized_video(target_video['id'], update_data)

    return {
        "success": True,
        "message": "Localized video updated successfully",
        "updated_fields": list(update_data.keys())
    }


@router.post("/{job_id}/save-draft")
async def save_draft(
    job_id: str,
    request: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Save localized video as draft.

    This marks the video as ready but not yet published, allowing the user
    to review and make changes before final publishing.

    Accepts either a job_id or a video_id (source_video_id).
    """
    user_id = current_user["user_id"]
    language_code = request.get('language_code')

    if not language_code:
        raise HTTPException(status_code=400, detail="language_code is required")

    # Try to get job by job_id first
    job = supabase_service.get_processing_job(job_id)

    # If not found, assume it's a video_id and search for the job
    if not job:
        logger.info(f"Job not found by job_id '{job_id}', searching by source_video_id...")
        jobs, _ = supabase_service.list_processing_jobs(user_id, limit=1000)

        for j in jobs:
            if j.get('source_video_id') == job_id:
                job = j
                job_id = j.get('id')  # Use the actual job_id
                logger.info(f"Found job by source_video_id: {job_id}")
                break

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found for job_id or video_id: {job_id}"
        )

    if job.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Find the localized video for this language
    localized_videos = supabase_service.get_localized_videos_by_job_id(job_id)
    target_video = None

    for vid in localized_videos:
        if vid.get('language_code') == language_code:
            target_video = vid
            break

    if not target_video:
        raise HTTPException(
            status_code=404,
            detail=f"Localized video not found for language {language_code}"
        )

    # Update status to draft (or keep as waiting_approval)
    # The status indicates it's ready for review but not published
    supabase_service.update_localized_video(target_video['id'], {
        'status': 'draft'
    })

    # Log activity
    supabase_service.log_activity(
        user_id=user_id,
        project_id=job.get('project_id'),
        action="Saved video as draft",
        details=f"Video {target_video.get('title', 'Untitled')} saved as draft for language {language_code}."
    )

    logger.info(f"Video saved as draft: job_id={job_id}, language={language_code}")

    return {
        "message": "Video saved as draft successfully",
        "job_id": job_id,
        "language_code": language_code,
        "status": "draft"
    }


@router.patch("/{job_id}/status")
async def update_job_status(
    job_id: str,
    request: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Update job status (for demo purposes).

    This endpoint allows updating the job status for demo simulations,
    such as showing a job as processing and then ready for review.
    """
    user_id = current_user["user_id"]
    new_status = request.get('status')

    if not new_status:
        raise HTTPException(status_code=400, detail="status is required")

    # Try to get job by job_id first
    job = supabase_service.get_processing_job(job_id)

    # If not found, assume it's a video_id and search for the job
    if not job:
        logger.info(f"Job not found by job_id '{job_id}', searching by source_video_id...")
        jobs, _ = supabase_service.list_processing_jobs(user_id, limit=1000)

        for j in jobs:
            if j.get('source_video_id') == job_id:
                job = j
                job_id = j.get('id')  # Use the actual job_id
                logger.info(f"Found job by source_video_id: {job_id}")
                break

    if not job:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found for job_id or video_id: {job_id}"
        )

    if job.get('user_id') != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Update job status
    supabase_service.update_processing_job(job_id, {
        'status': new_status
    })

    # If status is waiting_approval, also update localized videos
    if new_status == 'waiting_approval':
        localized_videos = supabase_service.get_localized_videos_by_job_id(job_id)
        for vid in localized_videos:
            supabase_service.update_localized_video(vid['id'], {
                'status': 'waiting_approval'
            })

    # Log activity
    supabase_service.log_activity(
        user_id=user_id,
        project_id=job.get('project_id'),
        action=f"Updated job status to {new_status}",
        details=f"Job {job_id} status changed to {new_status} (demo flow)"
    )

    logger.info(f"Job status updated: job_id={job_id}, status={new_status}")

    return {
        "message": f"Job status updated to {new_status}",
        "job_id": job_id,
        "status": new_status
    }


@router.get("/statistics/metrics")
async def get_job_metrics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get comprehensive job metrics and statistics.
    
    Returns metrics including:
    - Total jobs by status
    - Success rate
    - Average processing time
    - Language statistics
    """
    try:
        user_id = current_user["user_id"]
        
        # Get all user jobs
        jobs = supabase_service.get_user_processing_jobs(user_id)
        
        # Calculate metrics
        metrics = job_statistics.calculate_job_metrics(jobs)
        
        return {
            "success": True,
            "metrics": metrics
        }
    except Exception as e:
        logger.error(f"Failed to get job metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/recent")
async def get_recent_activity(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user)
):
    """
    Get recent activity metrics for the specified period.
    
    Args:
        days: Number of days to analyze (default: 7, max: 90)
    """
    try:
        user_id = current_user["user_id"]
        
        # Get all user jobs
        jobs = supabase_service.get_user_processing_jobs(user_id)
        
        # Get recent activity
        activity = job_statistics.get_recent_activity(jobs, days=days)
        
        return {
            "success": True,
            "activity": activity
        }
    except Exception as e:
        logger.error(f"Failed to get recent activity: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/errors")
async def get_error_summary(
    current_user: dict = Depends(get_current_user)
):
    """
    Get summary of failed jobs and common errors.
    
    Useful for identifying and debugging recurring issues.
    """
    try:
        user_id = current_user["user_id"]
        
        # Get all user jobs
        jobs = supabase_service.get_user_processing_jobs(user_id)
        
        # Analyze errors
        error_summary = job_statistics.get_error_summary(jobs)
        
        return {
            "success": True,
            "errors": error_summary
        }
    except Exception as e:
        logger.error(f"Failed to get error summary: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/languages")
async def get_language_statistics(
    current_user: dict = Depends(get_current_user)
):
    """
    Get statistics on language usage and popularity.
    
    Shows which languages are most commonly requested.
    """
    try:
        user_id = current_user["user_id"]
        
        # Get all user jobs
        jobs = supabase_service.get_user_processing_jobs(user_id)
        
        # Get language stats
        lang_stats = job_statistics.get_language_popularity(jobs)
        
        return {
            "success": True,
            "languages": lang_stats
        }
    except Exception as e:
        logger.error(f"Failed to get language statistics: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics/insights")
async def get_performance_insights(
    current_user: dict = Depends(get_current_user)
):
    """
    Get AI-generated insights and recommendations.
    
    Provides actionable insights based on job performance data.
    """
    try:
        user_id = current_user["user_id"]
        
        # Get all user jobs
        jobs = supabase_service.get_user_processing_jobs(user_id)
        
        # Generate insights
        insights = job_statistics.get_performance_insights(jobs)
        
        return {
            "success": True,
            "insights": insights
        }
    except Exception as e:
        logger.error(f"Failed to get performance insights: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{job_id}/transcript")
async def update_job_transcript(
    job_id: str,
    transcript_text: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the source transcript text for a job.

    Allows users to edit and correct transcription errors in the review interface.
    """
    user_id = current_user["user_id"]

    # Verify job ownership
    job = supabase_service.get_processing_job(job_id)
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

    # Get the transcript
    transcript = supabase_service.get_transcript(job_id)
    if not transcript:
        raise HTTPException(
            status_code=404,
            detail="Transcript not found for this job"
        )

    try:
        # Update the transcript text
        supabase_service.client.table("transcripts").update({
            "transcript_text": transcript_text,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("job_id", job_id).execute()

        logger.info(f"Updated transcript for job {job_id}")

        return {
            "success": True,
            "message": "Transcript updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update transcript for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update transcript: {str(e)}"
        )


@router.patch("/{job_id}/translations/{language_code}")
async def update_job_translation(
    job_id: str,
    language_code: str,
    translated_text: str = Body(..., embed=True),
    current_user: dict = Depends(get_current_user)
):
    """
    Update the translation text for a specific language.

    Allows users to edit and improve translations in the review interface.
    """
    user_id = current_user["user_id"]

    # Verify job ownership
    job = supabase_service.get_processing_job(job_id)
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

    # Get the translation
    translation = supabase_service.get_translation(job_id, language_code)
    if not translation:
        raise HTTPException(
            status_code=404,
            detail=f"Translation not found for language {language_code}"
        )

    try:
        # Update the translation text
        supabase_service.client.table("translations").update({
            "translated_text": translated_text,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }).eq("job_id", job_id).eq("target_language", language_code).execute()

        logger.info(f"Updated translation for job {job_id}, language {language_code}")

        return {
            "success": True,
            "message": "Translation updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update translation for job {job_id}, language {language_code}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to update translation: {str(e)}"
        )
