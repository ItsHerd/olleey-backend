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
    SubscriptionRequest, SubscriptionResponse, UnsubscribeRequest
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
            "published_at": "2009-10-24T09:00:00Z"
        },
        {
            "video_id": "9bZkp7q19f0",
            "title": "PSY - GANGNAM STYLE(강남스타일) M/V",
            "channel_id": "UCmock1234567890abcdefgh",
            "channel_name": "Test Main Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg",
            "published_at": "2012-07-15T00:00:00Z"
        },
        {
            "video_id": "kJQP7kiw5Fk",
            "title": "Luis Fonsi - Despacito ft. Daddy Yankee",
            "channel_id": "UCmock1234567890abcdefgh",
            "channel_name": "Test Main Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg",
            "published_at": "2017-01-12T00:00:00Z"
        },
        {
            "video_id": "OPf0YbXqDm0",
            "title": "Mark Ronson - Uptown Funk (Official Video) ft. Bruno Mars",
            "channel_id": "UCmock1234567890abcdefgh",
            "channel_name": "Test Main Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/OPf0YbXqDm0/hqdefault.jpg",
            "published_at": "2014-11-19T00:00:00Z"
        },
        {
            "video_id": "hT_nvWreIhg",
            "title": "OneRepublic - Counting Stars (Official Music Video)",
            "channel_id": "UCmock1234567890abcdefgh",
            "channel_name": "Test Main Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/hT_nvWreIhg/hqdefault.jpg",
            "published_at": "2013-05-31T00:00:00Z"
        },
        # Translated videos (published to language channels)
        {
            "video_id": "mock_dQw4w9WgXcQ_it",
            "title": "Never Gonna Give You Up - Rick Astley (Italian Dub)",
            "channel_id": "UCmock_italian_999",
            "channel_name": "Italian Dubbing Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "published_at": "2026-01-19T00:00:00Z"
        },
        {
            "video_id": "mock_dQw4w9WgXcQ_zh",
            "title": "Never Gonna Give You Up - Rick Astley (Chinese Dub)",
            "channel_id": "UCmock_chinese_888",
            "channel_name": "Chinese Dubbing Channel",
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "published_at": "2026-01-19T00:00:00Z"
        }
    ]
    
    # Limit results
    mock_videos_data = mock_videos_data[:limit]
    
    # Query Firestore to determine which videos are original vs translated
    # Wrap in try-except to ensure videos always appear even if Firestore fails
    videos = []
    for mock_video in mock_videos_data:
        video_id = mock_video["video_id"]
        
        try:
            # Check if this is a translated video
            localized = firestore_service.get_localized_video_by_localized_id(video_id, user_id)
            
            if localized:
                # This is a translated video
                video_item = VideoItem(
                    video_id=video_id,
                    title=mock_video["title"],
                    thumbnail_url=mock_video["thumbnail_url"],
                    published_at=datetime.fromisoformat(mock_video["published_at"].replace('Z', '+00:00')),
                    channel_id=mock_video["channel_id"],
                    channel_name=mock_video["channel_name"],
                    video_type="translated",
                    source_video_id=localized.get('source_video_id'),
                    translated_languages=[]
                )
            else:
                # Check if this is an original video with translations
                localized_list = firestore_service.get_localized_videos_by_source_id(video_id, user_id)
                
                if localized_list:
                    # Original video with translations
                    translated_languages = [
                        loc.get('language_code')
                        for loc in localized_list
                        if loc.get('language_code')
                    ]
                    video_item = VideoItem(
                        video_id=video_id,
                        title=mock_video["title"],
                        thumbnail_url=mock_video["thumbnail_url"],
                        published_at=datetime.fromisoformat(mock_video["published_at"].replace('Z', '+00:00')),
                        channel_id=mock_video["channel_id"],
                        channel_name=mock_video["channel_name"],
                        video_type="original",
                        source_video_id=None,
                        translated_languages=translated_languages
                    )
                else:
                    # Original video without translations
                    video_item = VideoItem(
                        video_id=video_id,
                        title=mock_video["title"],
                        thumbnail_url=mock_video["thumbnail_url"],
                        published_at=datetime.fromisoformat(mock_video["published_at"].replace('Z', '+00:00')),
                        channel_id=mock_video["channel_id"],
                        channel_name=mock_video["channel_name"],
                        video_type="original",
                        source_video_id=None,
                        translated_languages=[]
                    )
        except Exception as e:
            # If Firestore query fails, still return the video as original
            print(f"[VIDEOS] Firestore query failed for video {video_id}, returning as original: {str(e)}")
            video_item = VideoItem(
                video_id=video_id,
                title=mock_video["title"],
                thumbnail_url=mock_video["thumbnail_url"],
                published_at=datetime.fromisoformat(mock_video["published_at"].replace('Z', '+00:00')),
                channel_id=mock_video["channel_id"],
                channel_name=mock_video["channel_name"],
                video_type="original",
                source_video_id=None,
                translated_languages=[]
            )
        
        videos.append(video_item)
    
    # Sort by published_at descending
    videos.sort(key=lambda x: x.published_at, reverse=True)
    
    print(f"[VIDEOS] Returning {len(videos)} mock videos for user {user_id}")
    return VideoListResponse(videos=videos, total=len(videos))


def get_youtube_service(user_id: str, connection_id=None, raise_on_mock=True):
    """
    Build and return YouTube Data API v3 service with user's connected channel credentials.
    
    Args:
        user_id: Firebase Auth user ID
        connection_id: Optional connection ID
        raise_on_mock: If False, returns None for mock credentials
        
    Returns:
        YouTube service instance or None if mock credentials
        
    Raises:
        HTTPException: If authentication fails or no YouTube connection
    """
    return get_youtube_service_helper(user_id, connection_id, raise_on_mock)


@router.get("/list", response_model=VideoListResponse)
async def list_videos(
    limit: int = 10,
    current_user: dict = Depends(get_current_user)
) -> VideoListResponse:
    """
    Fetch authenticated user's uploaded videos from YouTube.
    
    Args:
        limit: Maximum number of videos to return (default: 10)
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        VideoListResponse: List of user's videos sorted by date
        
    Raises:
        HTTPException: If authentication fails or API error occurs
    """
    user_id = current_user["user_id"]
    
    try:
        # Get YouTube service in thread pool to avoid blocking
        # Pass raise_on_mock=False to gracefully handle mock credentials
        youtube = await asyncio.to_thread(get_youtube_service, user_id, None, False)
        
        if youtube is None:
            # Mock or invalid credentials - return mock video data for development/testing
            print(f"[VIDEOS] Mock credentials detected for user {user_id}, returning mock video data")
            return await get_mock_videos(user_id, limit)
        
        # Get user's channel to find uploads playlist
        channels_response = await asyncio.to_thread(
            youtube.channels().list(part='contentDetails', mine=True).execute
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
        
        # Get video IDs
        video_ids = [item['contentDetails']['videoId'] for item in playlist_items[:limit]]
        
        # Get full video details
        videos_response = await asyncio.to_thread(
            youtube.videos().list(
                part='snippet',
                id=','.join(video_ids)
            ).execute
        )
        
        # Map to VideoItem schema
        videos = []
        video_ids = [video['id'] for video in videos_response.get('items', [])]
        
        # Optimize: Fetch ALL localized videos for the user in one go (or via batch if implemented)
        # This replaces the N+1 query loop.
        all_user_localized_videos = firestore_service.get_all_localized_videos_for_user(user_id)
        
        localized_videos_map = {}  # localized_video_id -> localized_video_data
        source_videos_map = defaultdict(list)  # source_video_id -> list of localized_videos
        
        # Populate maps from the bulk fetched data
        for loc_video in all_user_localized_videos:
            # Map by localized_video_id
            if loc_video.get('localized_video_id'):
                localized_videos_map[loc_video['localized_video_id']] = loc_video
                
            # Map by source_video_id
            if loc_video.get('source_video_id'):
                source_videos_map[loc_video['source_video_id']].append(loc_video)
        
        # Build video items with type information
        for video in videos_response.get('items', []):
            snippet = video['snippet']
            thumbnails = snippet.get('thumbnails', {})
            thumbnail_url = (
                thumbnails.get('high', {}).get('url') or
                thumbnails.get('medium', {}).get('url') or
                thumbnails.get('default', {}).get('url') or
                ''
            )
            
            video_id = video['id']
            channel_id = snippet.get('channelId', '')
            channel_name = snippet.get('channelTitle', '')
            
            # Determine video type
            if video_id in localized_videos_map:
                # This is a translated video
                localized_data = localized_videos_map[video_id]
                video_item = VideoItem(
                    video_id=video_id,
                    title=snippet.get('title', ''),
                    thumbnail_url=thumbnail_url,
                    published_at=snippet.get('publishedAt'),
                    channel_id=channel_id,
                    channel_name=channel_name,
                    video_type="translated",
                    source_video_id=localized_data.get('source_video_id'),
                    translated_languages=[]
                )
            elif video_id in source_videos_map:
                # This is an original video that has been translated
                localized_list = source_videos_map[video_id]
                translated_languages = [
                    loc.get('language_code') 
                    for loc in localized_list 
                    if loc.get('language_code')
                ]
                video_item = VideoItem(
                    video_id=video_id,
                    title=snippet.get('title', ''),
                    thumbnail_url=thumbnail_url,
                    published_at=snippet.get('publishedAt'),
                    channel_id=channel_id,
                    channel_name=channel_name,
                    video_type="original",
                    source_video_id=None,
                    translated_languages=translated_languages
                )
            else:
                # This is an original video that hasn't been translated yet
                video_item = VideoItem(
                    video_id=video_id,
                    title=snippet.get('title', ''),
                    thumbnail_url=thumbnail_url,
                    published_at=snippet.get('publishedAt'),
                    channel_id=channel_id,
                    channel_name=channel_name,
                    video_type="original",
                    source_video_id=None,
                    translated_languages=[]
                )
            
            videos.append(video_item)
        
        # Sort by published_at descending (most recent first)
        videos.sort(key=lambda x: x.published_at, reverse=True)
        
        return VideoListResponse(videos=videos, total=len(videos))
        
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
