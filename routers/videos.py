"""Video management router for YouTube operations."""
from collections import defaultdict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from typing import Optional
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
import asyncio
import tempfile
import os
import httpx
from datetime import datetime, timedelta

from services.firestore import firestore_service
from schemas.videos import (
    VideoListResponse, VideoItem, VideoUploadRequest, VideoUploadResponse,
    SubscriptionRequest, SubscriptionResponse, UnsubscribeRequest, LocalizationStatus
)
from routers.youtube_auth import get_youtube_service as get_youtube_service_helper
from middleware.auth import get_current_user
from config import settings

router = APIRouter(prefix="/videos", tags=["videos"])


async def get_mock_videos(user_id: str, limit: int) -> VideoListResponse:
    """
    Return mock video data for testing/development with mock credentials.
    
    This creates realistic mock videos based on the processing jobs that were created,
    so the UI can show original videos and their translated versions.
    """
    # Mock videos that correspond to our processing jobs
    mock_videos_data = [
        {
            "video_id": "dQw4w9WgXcQ",
            "title": "Never Gonna Give You Up - Rick Astley (Official Video)",
            "channel_id": "UCmock1234567890abcdefgh",
            "channel_name": "Test Main Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "published_at": "2009-10-24T09:00:00Z",
            "view_count": 1200000000
        },
        {
            "video_id": "9bZkp7q19f0",
            "title": "PSY - GANGNAM STYLE(강남스타일) M/V",
            "channel_id": "UCmock1234567890abcdefgh",
            "channel_name": "Test Main Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg",
            "published_at": "2012-07-15T00:00:00Z",
            "view_count": 4500000000
        }
    ]
    
    # Limit results
    mock_videos_data = mock_videos_data[:limit]
    
    videos = []
    for mock_video in mock_videos_data:
        video_id = mock_video["video_id"]
        
        video_item = VideoItem(
            video_id=video_id,
            title=mock_video["title"],
            thumbnail_url=mock_video["thumbnail_url"],
            published_at=datetime.fromisoformat(mock_video["published_at"].replace('Z', '+00:00')),
            view_count=mock_video.get("view_count", 0),
            channel_id=mock_video["channel_id"],
            channel_name=mock_video["channel_name"],
            video_type="original",
            source_video_id=None,
            localizations=[],
            translated_languages=[]
        )
        videos.append(video_item)
    
    return VideoListResponse(videos=videos, total=len(videos))


async def get_demo_videos_formatted(user_id: str, project_id: Optional[str], limit: int) -> VideoListResponse:
    """Format demo jobs and localized videos into the expected video list format."""
    from typing import Dict
    
    # Get all jobs for the user
    jobs, total = firestore_service.list_processing_jobs(user_id, project_id=project_id, limit=limit)
    print(f"[DEMO] Found {len(jobs)} jobs for user {user_id}")
    
    videos = []
    for job in jobs:
        source_video_id = job.get('source_video_id')
        if not source_video_id:
            continue
            
        # Get localized videos for this job
        localized_vids = firestore_service.get_localized_videos_by_job_id(job['id'])
        
        # Build localizations list
        localizations = []
        for loc_vid in localized_vids:
            lang_code = loc_vid.get('language_code')
            status = loc_vid.get('status', 'processing')
            
            # Map statuses to frontend expectations
            if status == 'waiting_approval':
                frontend_status = 'draft'
            elif status == 'published':
                frontend_status = 'live'
            elif status in ['processing', 'pending']:
                frontend_status = 'processing'
            else:
                frontend_status = 'processing'
            
            localizations.append(LocalizationStatus(
                language_code=lang_code,
                status=frontend_status,
                video_id=loc_vid.get('localized_video_id'),
                job_id=loc_vid.get('job_id'),  # Include job_id for approval flow
                channel_id=loc_vid.get('channel_id'),
                published_at=loc_vid.get('published_at') or loc_vid.get('updated_at'),
                title=loc_vid.get('title'),
                description=loc_vid.get('description')
            ))
        
        # Get first localized video for thumbnail and title
        first_loc = localized_vids[0] if localized_vids else {}
        
        # Get all language codes
        all_lang_codes = [loc.language_code for loc in localizations]
        published_lang_codes = [loc.language_code for loc in localizations if loc.status == 'live']
        
        if published_lang_codes:
            print(f"[DEMO] Video {source_video_id}: {len(localizations)} localizations, {len(published_lang_codes)} published (status: {job.get('status')}), langs: {published_lang_codes}")
        else:
            print(f"[DEMO] Video {source_video_id}: {len(localizations)} localizations, {len(published_lang_codes)} published")
        
        # Resolve channel info (handle demo jobs storing connection_id)
        channel_id = job.get('source_channel_id', '')
        channel_name = "Demo Channel"
        if channel_id and not str(channel_id).startswith("UC"):
            # Likely a connection_id; resolve to YouTube channel id
            conn = firestore_service.get_youtube_connection(channel_id, user_id)
            if conn:
                channel_id = conn.get('youtube_channel_id', channel_id)
                channel_name = conn.get('youtube_channel_name', channel_name)

        # Create video item
        video = VideoItem(
            video_id=source_video_id,
            title=first_loc.get('title', f"Video {source_video_id}").split(' (')[0],  # Remove language suffix
            thumbnail_url=first_loc.get('thumbnail_url', f"https://i.ytimg.com/vi/{source_video_id}/hqdefault.jpg"),
            published_at=job.get('created_at', datetime.utcnow()),
            channel_id=channel_id,
            channel_name=channel_name,
            localizations=localizations,
            view_count=sum(1000 * (i+1) for i in range(len(localizations))),  # Mock view counts
            video_type="original",
            source_video_id=None,
            translated_languages=published_lang_codes,
            # Add duration for credit estimation
            duration=first_loc.get('duration', 210),  # Default 3.5 minutes
            global_views=sum(1000 * (i+1) for i in range(len(published_lang_codes)))
        )
        
        # Debug: Print localization statuses
        loc_statuses = {loc.language_code: loc.status for loc in localizations}
        print(f"[DEMO] Video {source_video_id} localization statuses: {loc_statuses}")
        
        videos.append(video)
    
    return VideoListResponse(
        videos=videos,
        total=len(videos)
    )


def get_youtube_service(user_id: str, connection_id=None, raise_on_mock=True):
    """
    Build and return YouTube Data API v3 service.
    """
    return get_youtube_service_helper(user_id, connection_id, raise_on_mock)

@router.get("/list", response_model=VideoListResponse)
async def list_videos(
    limit: int = 20,
    project_id: Optional[str] = None,
    channel_id: Optional[str] = None,
    video_type: str = "all", # all, original, translated
    current_user: dict = Depends(get_current_user)
) -> VideoListResponse:
    """
    Fetch authenticated user's uploaded videos from YouTube with filtering.
    """
    user_id = current_user["user_id"]
    
    # Check if demo user - return demo data in expected format
    from services.demo_simulator import demo_simulator
    if demo_simulator.is_demo_user(user_id):
        return await get_demo_videos_formatted(user_id, project_id, limit)
    
    try:
        # Get YouTube service
        youtube = await asyncio.to_thread(get_youtube_service, user_id, None, False)
        
        if youtube is None:
            # Handle mock mode
            mock_resp = await get_mock_videos(user_id, limit)
            # Apply filters to mock data
            filtered_videos = mock_resp.videos
            if video_type != "all":
                filtered_videos = [v for v in filtered_videos if v.video_type == video_type]
            if channel_id:
                filtered_videos = [v for v in filtered_videos if v.channel_id == channel_id]
            # No project filtering for mock for now
            return VideoListResponse(videos=filtered_videos, total=len(filtered_videos))
        
        # Determine which playlist to fetch from
        if channel_id:
            # Fetch specifically for a channel
            target_channel_id = channel_id
        else:
            # Fetch for primary channel
            channels_response = await asyncio.to_thread(
                youtube.channels().list(part='contentDetails', mine=True).execute
            )
            if not channels_response.get('items'):
                return VideoListResponse(videos=[], total=0)
            target_channel_id = channels_response['items'][0]['id']
            uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # If we have a specific channel_id, we need to get its uploads_playlist_id
        if channel_id:
             channels_response = await asyncio.to_thread(
                youtube.channels().list(part='contentDetails', id=channel_id).execute
            )
             if not channels_response.get('items'):
                return VideoListResponse(videos=[], total=0)
             uploads_playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

        # Get videos from uploads playlist
        playlist_items = []
        next_page_token = None
        while len(playlist_items) < limit:
            request_params = {
                'part': 'snippet,contentDetails',
                'playlistId': uploads_playlist_id,
                'maxResults': min(limit - len(playlist_items), 50)
            }
            if next_page_token:
                request_params['pageToken'] = next_page_token
            
            playlist_response = await asyncio.to_thread(
                youtube.playlistItems().list(**request_params).execute
            )
            playlist_items.extend(playlist_response.get('items', []))
            next_page_token = playlist_response.get('nextPageToken')
            if not next_page_token:
                break
        
        if not playlist_items:
            return VideoListResponse(videos=[], total=0)
        
        video_ids = [item['contentDetails']['videoId'] for item in playlist_items[:limit]]
        
        # Get full video details INCLUDING statistics (views)
        videos_response = await asyncio.to_thread(
            youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute
        )
        
        # Fetch status data from Firestore
        all_localized = firestore_service.get_all_localized_videos_for_user(user_id)
        all_jobs, _ = firestore_service.list_processing_jobs(user_id, limit=100, project_id=project_id)
        
        # Maps for quick lookup
        localized_map = defaultdict(list) # source_id -> [localized_docs]
        for loc in all_localized:
            if loc.get('source_video_id'):
                localized_map[loc['source_video_id']].append(loc)
        
        jobs_map = defaultdict(list) # source_id -> [job_docs]
        for j in all_jobs:
            if j.get('source_video_id'):
                jobs_map[j['source_video_id']].append(j)
        
        final_videos = []
        for video in videos_response.get('items', []):
            video_id = video['id']
            snippet = video['snippet']
            stats = video.get('statistics', {})
            
            # Determine type and localizations
            localizations = []
            
            # 1. Check if it IS a localized video
            is_localized = any(loc.get('localized_video_id') == video_id for loc in all_localized)
            type_str = "translated" if is_localized else "original"
            
            # 2. Get localizations for this original video
            for loc in localized_map.get(video_id, []):
                localizations.append(LocalizationStatus(
                    language_code=loc.get('language_code', ''),
                    status=loc.get('status', 'live'),
                    video_id=loc.get('localized_video_id'),
                    job_id=loc.get('job_id')
                ))
            
            # 3. Add in-progress jobs to localizations
            for j in jobs_map.get(video_id, []):
                # Filter out languages already covered by 'live' localizations to avoid duplicates
                live_langs = [l.language_code for l in localizations]
                for lang in j.get('target_languages', []):
                    if lang not in live_langs:
                        localizations.append(LocalizationStatus(
                            language_code=lang,
                            status='processing', # mapping pending/processing to processing
                            job_id=j.get('id')
                        ))
            
            # Filter by type if requested
            if video_type != "all" and type_str != video_type:
                continue
            
            # Thumbnails
            thumbnails = snippet.get('thumbnails', {})
            thumb_url = thumbnails.get('high', {}).get('url') or thumbnails.get('default', {}).get('url', '')

            video_item = VideoItem(
                video_id=video_id,
                title=snippet.get('title', ''),
                thumbnail_url=thumb_url,
                published_at=snippet.get('publishedAt'),
                view_count=int(stats.get('viewCount', 0)),
                channel_id=snippet.get('channelId', ''),
                channel_name=snippet.get('channelTitle', ''),
                video_type=type_str,
                source_video_id=next((loc.get('source_video_id') for loc in all_localized if loc.get('localized_video_id') == video_id), None),
                localizations=localizations,
                translated_languages=[l.language_code for l in localizations]
            )
            final_videos.append(video_item)
            
        return VideoListResponse(videos=final_videos, total=len(final_videos))
        
    except HttpError as e:
        error_reason = e.error_details[0].get('reason', '') if e.error_details else ''
        if e.resp.status == 403 and 'quotaExceeded' in error_reason:
            raise HTTPException(
                status_code=503,
                detail="YouTube API quota exceeded. Please try again later."
            )
        elif e.resp.status in [401, 403]:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed. Please re-authenticate."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"YouTube API error: {str(e)}"
            )
    except HTTPException:
        # Re-raise HTTP exceptions (like 401 from get_youtube_service)
        raise
    except Exception as e:
        # For mock credentials or other errors, return empty list in development
        error_msg = str(e)
        if "invalid_grant" in error_msg.lower() or "mock" in error_msg.lower() or "No YouTube channel connected" in error_msg:
            print(f"[VIDEOS] Cannot fetch videos (likely mock credentials): {error_msg[:100]}")
            return VideoListResponse(videos=[], total=0)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch videos: {str(e)}"
        )


@router.get("/{video_id}", response_model=VideoItem)
async def get_video_details(
    video_id: str,
    current_user: dict = Depends(get_current_user)
) -> VideoItem:
    """
    Get details for a specific video.
    
    Args:
        video_id: YouTube video ID
        current_user: Current authenticated user
        
    Returns:
        VideoItem: Video details with localization status
    """
    user_id = current_user["user_id"]
    
    try:
        # Get YouTube service
        youtube = await asyncio.to_thread(get_youtube_service, user_id, None, False)
        
        # Handle Mock Mode
        if youtube is None:
            # Check for specific mock videos
            mock_list = await get_mock_videos(user_id, 100)
            for video in mock_list.videos:
                if video.video_id == video_id:
                    return video
            
            # If not found in mock list but we are in mock mode, return a generic mock
            return VideoItem(
                video_id=video_id,
                title="Mock Video Details",
                thumbnail_url="https://via.placeholder.com/640x360",
                published_at=datetime.utcnow(),
                channel_id="UCmonitor_mock",
                channel_name="Mock Channel",
                video_type="original",
                source_video_id=None,
                translated_languages=[]
            )

        # Real YouTube API call
        response = await asyncio.to_thread(
            youtube.videos().list(
                part='snippet',
                id=video_id
            ).execute
        )
        
        if not response.get('items'):
            # It might be a dubbing-platform-internal ID (mock) that doesn't exist on YT
            # Check internal DB just in case it's a localized video record ID?
            # But the spec says video_id is YouTube ID. 
            # If not found on YouTube, we return 404.
            raise HTTPException(status_code=404, detail="Video not found on YouTube")
            
        video_data = response['items'][0]
        snippet = video_data['snippet']
        
        # Determine video type from Firestore
        # Check if this video is a result of a localization (i.e., it is a translated video)
        localized = firestore_service.get_localized_video_by_localized_id(video_id, user_id)
        
        if localized:
             return VideoItem(
                video_id=video_id,
                title=snippet.get('title', ''),
                thumbnail_url=snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
                published_at=snippet.get('publishedAt'),
                channel_id=snippet.get('channelId'),
                channel_name=snippet.get('channelTitle'),
                video_type="translated",
                source_video_id=localized.get('source_video_id'),
                translated_languages=[]
            )
            
        # Check if this is an original video that has translations
        localized_list = firestore_service.get_localized_videos_by_source_id(video_id, user_id)
        translated_languages = [
            loc.get('language_code') 
            for loc in localized_list 
            if loc.get('language_code')
        ]
        
        return VideoItem(
            video_id=video_id,
            title=snippet.get('title', ''),
            thumbnail_url=snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            published_at=snippet.get('publishedAt'),
            channel_id=snippet.get('channelId'),
            channel_name=snippet.get('channelTitle'),
            video_type="original",
            source_video_id=None,
            translated_languages=translated_languages
        )

    except HttpError as e:
        if e.resp.status == 404:
            raise HTTPException(status_code=404, detail="Video not found")
        raise HTTPException(status_code=500, detail=f"YouTube API error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch video details: {str(e)}")


@router.post("/upload", response_model=VideoUploadResponse)
async def upload_video(
    title: str = Form(...),
    description: str = Form(""),
    privacy_status: str = Form("private"),
    video_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
) -> VideoUploadResponse:
    """
    Upload a video to YouTube channel.
    
    Args:
        title: Video title
        description: Video description
        privacy_status: Privacy setting (private/unlisted/public)
        video_file: Video file to upload
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        VideoUploadResponse: Upload result with video ID
        
    Raises:
        HTTPException: If upload fails or quota exceeded
    """
    user_id = current_user["user_id"]
    
    # Validate privacy status
    valid_privacy_statuses = ['private', 'unlisted', 'public']
    if privacy_status not in valid_privacy_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid privacy_status. Must be one of: {', '.join(valid_privacy_statuses)}"
        )
    
    # Create temporary file for video
    temp_file = None
    try:
        # Get YouTube service
        youtube = await asyncio.to_thread(get_youtube_service, user_id)
        
        # Save uploaded file to temporary location
        suffix = os.path.splitext(video_file.filename)[1] if video_file.filename else '.mp4'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_path = temp_file.name
            # Read and write file in chunks to handle large files
            while True:
                chunk = await video_file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                temp_file.write(chunk)
        
        # Create video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': [],
                'categoryId': '22'  # People & Blogs category
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        # Create media upload with resumable upload
        media = MediaFileUpload(
            temp_path,
            chunksize=-1,  # Use default chunk size
            resumable=True
        )
        
        # Insert video
        insert_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        # Execute upload (resumable upload handles chunking automatically)
        response = await asyncio.to_thread(insert_request.execute)
        
        video_id = response['id']
        
        return VideoUploadResponse(
            message="Video uploaded successfully",
            video_id=video_id,
            title=title,
            privacy_status=privacy_status
        )
        
        # Log activity
        firestore_service.log_activity(
            user_id=user_id,
            project_id=None,  # No project context here usually
            action="Uploaded video",
            details=f"Video '{title}' uploaded to YouTube with ID {video_id}."
        )
        
        return response
        
    except HttpError as e:
        error_reason = e.error_details[0].get('reason', '') if e.error_details else ''
        if e.resp.status == 403 and 'quotaExceeded' in error_reason:
            raise HTTPException(
                status_code=503,
                detail="YouTube API quota exceeded. Please try again later."
            )
        elif e.resp.status in [401, 403]:
            raise HTTPException(
                status_code=401,
                detail="Authentication failed. Please re-authenticate."
            )
        else:
            raise HTTPException(
                status_code=500,
                detail=f"YouTube API error: {str(e)}"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload video: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_file and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass  # Ignore cleanup errors


@router.post("/subscribe", response_model=SubscriptionResponse)
async def subscribe_to_channel(
    request: SubscriptionRequest,
    current_user: dict = Depends(get_current_user)
) -> SubscriptionResponse:
    """
    Subscribe to a YouTube channel's feed via PubSubHubbub.
    
    Args:
        request: Subscription request with channel_id and optional callback_url
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        SubscriptionResponse: Subscription details
        
    Raises:
        HTTPException: If subscription fails
    """
    user_id = current_user["user_id"]
    
    try:
        # Verify user has access to channel
        youtube = await asyncio.to_thread(get_youtube_service, user_id)
        channels_response = await asyncio.to_thread(
            youtube.channels().list(part='id', id=request.channel_id).execute
        )
        
        if not channels_response.get('items'):
            raise HTTPException(
                status_code=404,
                detail=f"Channel not found: {request.channel_id}"
            )
        
        # Build callback URL
        callback_url = request.callback_url
        if not callback_url:
            if not settings.webhook_base_url:
                raise HTTPException(
                    status_code=400,
                    detail="callback_url required or set WEBHOOK_BASE_URL in config"
                )
            callback_url = f"{settings.webhook_base_url}/webhooks/youtube"
        
        # Build topic URL
        topic = f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={request.channel_id}"
        
        # Prepare subscription request to PubSubHubbub hub
        subscribe_data = {
            'hub.mode': 'subscribe',
            'hub.topic': topic,
            'hub.callback': callback_url,
            'hub.lease_seconds': str(request.lease_seconds)
        }
        
        # Send subscription request to PubSubHubbub hub
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.pubsubhubbub_hub_url,
                data=subscribe_data,
                timeout=30.0
            )
            response.raise_for_status()
        
        # Calculate expiry
        expires_at = datetime.utcnow() + timedelta(seconds=request.lease_seconds)
        
        # Store subscription in Firestore
        subscription_id = firestore_service.create_subscription(
            user_id=user_id,
            channel_id=request.channel_id,
            callback_url=callback_url,
            topic=topic,
            lease_seconds=request.lease_seconds,
            expires_at=expires_at
        )
        
        return SubscriptionResponse(
            subscription_id=subscription_id,
            channel_id=request.channel_id,
            expires_at=expires_at,
            message="Subscription created successfully. Awaiting verification from PubSubHubbub hub."
        )
        
        # Log activity
        firestore_service.log_activity(
            user_id=user_id,
            project_id=None,
            action="Created subscription",
            details=f"Subscribed to channel {request.channel_id} via PubSubHubbub."
        )
        
        return response
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to subscribe to PubSubHubbub hub: {str(e)}"
        )
    except HttpError as e:
        raise HTTPException(
            status_code=500,
            detail=f"YouTube API error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create subscription: {str(e)}"
        )


@router.post("/unsubscribe")
async def unsubscribe_from_channel(
    request: UnsubscribeRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Unsubscribe from a YouTube channel's feed via PubSubHubbub.
    
    Args:
        request: Unsubscribe request with channel_id or subscription_id
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        dict: Unsubscribe result
    """
    user_id = current_user["user_id"]
    
    try:
        # Find subscription
        if request.subscription_id:
            subscription = firestore_service.get_subscription(request.subscription_id)
            if not subscription:
                raise HTTPException(
                    status_code=404,
                    detail="Subscription not found"
                )
            # Verify ownership
            if subscription.get('user_id') != user_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: subscription belongs to another user"
                )
        elif request.channel_id:
            subscription = firestore_service.get_subscription_by_channel(user_id, request.channel_id)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either channel_id or subscription_id must be provided"
            )
        
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail="Subscription not found"
            )
        
        # Send unsubscribe request to PubSubHubbub hub
        unsubscribe_data = {
            'hub.mode': 'unsubscribe',
            'hub.topic': subscription['topic'],
            'hub.callback': subscription['callback_url']
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.pubsubhubbub_hub_url,
                data=unsubscribe_data,
                timeout=30.0
            )
            response.raise_for_status()
        
        # Remove subscription from Firestore
        firestore_service.delete_subscription(subscription['id'])
        
        return {"message": "Unsubscribed successfully"}
        
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unsubscribe from PubSubHubbub hub: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to unsubscribe: {str(e)}"
        )
