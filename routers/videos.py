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
import uuid
import shutil
import logging
import traceback
from datetime import datetime, timedelta

from services.supabase_db import supabase_service
from services.subscription_renewal import renew_due_subscriptions
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
    jobs, total = supabase_service.list_processing_jobs(user_id, project_id=project_id, limit=limit)
    print(f"[DEMO] Found {len(jobs)} jobs for user {user_id}")
    
    videos = []
    for job in jobs:
        source_video_id = job.get('source_video_id')
        if not source_video_id:
            continue

        # Get source video document for storage_url
        source_video = supabase_service.get_video(source_video_id) or {}

        # Get localized videos for this job
        localized_vids = supabase_service.get_localized_videos_by_job_id(job['id'])

        # Demo: Ensure Garry Tan video has Spanish localized video entry
        if source_video_id == "garry_tan_yc_demo":
            has_spanish_loc = any(vid.get('language_code') == 'es' for vid in localized_vids)

            if not has_spanish_loc:
                print(f"[DEMO] Creating Spanish localized video entry for Garry Tan demo")
                # Create the localized video entry
                import uuid
                localized_video_id = str(uuid.uuid4())

                localized_video_data = {
                    'id': localized_video_id,
                    'job_id': job['id'],
                    'source_video_id': source_video_id,
                    'localized_video_id': None,
                    'language_code': 'es',
                    'channel_id': 'UCESChannel301',
                    'status': 'waiting_approval',
                    'storage_url': 'https://olleey-videos.s3.us-west-1.amazonaws.com/es.mov',
                    'thumbnail_url': 'https://tii.imgix.net/production/articles/7643/03e02ef7-f12e-4faf-8551-37d5c5785586-UQ6LXV.jpg?auto=compress&fit=crop&auto=format',
                    'title': 'Garry Tan - Presidente y CEO de Y Combinator',
                    'description': (
                        'Garry Tan es el Presidente y CEO de Y Combinator (YC), la aceleradora de startups más exitosa del mundo.\n\n'
                        'En este video, Garry comparte perspectivas sobre la misión de YC de ayudar a las startups a tener éxito, '
                        'la importancia de construir grandes productos, y consejos para fundadores navegando el viaje del emprendimiento.\n\n'
                        'Este es un video de demostración que muestra las capacidades de localización de video impulsadas por IA de Olleey.'
                    ),
                    'duration': 180,
                    'view_count': 0,
                    'created_at': datetime.utcnow(),
                    'updated_at': datetime.utcnow()
                }

                created_video = supabase_service.create_localized_video(localized_video_data)
                localized_vids.append(created_video if created_video else localized_video_data)
                print(f"[DEMO] Spanish localized video entry created: {localized_video_id}")
        
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
                description=loc_vid.get('description'),
                thumbnail_url=loc_vid.get('thumbnail_url'),
                video_url=loc_vid.get('storage_url')  # Include dubbed video storage URL
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
            conn = supabase_service.get_youtube_connection(channel_id, user_id)
            if conn:
                channel_id = conn.get('youtube_channel_id', channel_id)
                channel_name = conn.get('youtube_channel_name', channel_name)

        # Create video item
        thumbnail = first_loc.get('thumbnail_url') or f"https://i.ytimg.com/vi/{source_video_id}/hqdefault.jpg"

        video = VideoItem(
            video_id=source_video_id,
            title=first_loc.get('title', f"Video {source_video_id}").split(' (')[0],  # Remove language suffix
            thumbnail_url=thumbnail,
            published_at=job.get('created_at', datetime.utcnow()),
            channel_id=channel_id,
            channel_name=channel_name,
            localizations=localizations,
            view_count=sum(1000 * (i+1) for i in range(len(localizations))),  # Mock view counts
            video_type="original",
            source_video_id=None,
            storage_url=source_video.get('storage_url'),  # Include storage URL from source video
            translated_languages=published_lang_codes,
            # Add duration for credit estimation
            duration=first_loc.get('duration', 210),  # Default 3.5 minutes
            global_views=sum(1000 * (i+1) for i in range(len(published_lang_codes)))
        )
        
        # Demo: Ensure Garry Tan video always has Spanish localization
        if source_video_id == "garry_tan_yc_demo":
            # Check if Spanish localization exists
            has_spanish = any(loc.language_code == 'es' for loc in localizations)

            if not has_spanish:
                print(f"[DEMO] Adding Spanish localization for Garry Tan demo video")
                # Add Spanish localization with translated metadata
                spanish_loc = LocalizationStatus(
                    language_code='es',
                    status='draft',  # Ready for review
                    video_id=None,
                    job_id=job.get('id'),
                    channel_id='UCESChannel301',  # Spanish channel from seed
                    published_at=None,
                    title='Garry Tan - Presidente y CEO de Y Combinator',
                    description=(
                        'Garry Tan es el Presidente y CEO de Y Combinator (YC), la aceleradora de startups más exitosa del mundo.\n\n'
                        'En este video, Garry comparte perspectivas sobre la misión de YC de ayudar a las startups a tener éxito, '
                        'la importancia de construir grandes productos, y consejos para fundadores navegando el viaje del emprendimiento.\n\n'
                        'Este es un video de demostración que muestra las capacidades de localización de video impulsadas por IA de Olleey.'
                    ),
                    thumbnail_url='https://tii.imgix.net/production/articles/7643/03e02ef7-f12e-4faf-8551-37d5c5785586-UQ6LXV.jpg?auto=compress&fit=crop&auto=format',
                    video_url='https://olleey-videos.s3.us-west-1.amazonaws.com/es.mov'
                )
                video.localizations.append(spanish_loc)
                print(f"[DEMO] Spanish localization added to Garry Tan video")

        # Debug: Print localization statuses
        loc_statuses = {loc.language_code: loc.status for loc in video.localizations}
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
    Fetch authenticated user's videos including:
    - Uploaded videos from local/S3 storage
    - YouTube videos
    - Localized/dubbed videos
    """
    user_id = current_user["user_id"]

    # Check if demo user - return demo data in expected format
    from services.demo_simulator import demo_simulator
    if demo_simulator.is_demo_user(user_id):
        return await get_demo_videos_formatted(user_id, project_id, limit)

    try:
        # Get ALL videos from Supabase (not just uploaded ones)
        db_videos, total_count = supabase_service.list_videos(
            user_id=user_id,
            project_id=project_id,
            channel_id=channel_id,
            limit=limit
        )

        print(f"[VIDEOS] Loaded {len(db_videos)} videos from database")
        print(f"[VIDEOS] Video IDs: {[v.get('video_id') for v in db_videos]}")

        # Get localizations and jobs for enrichment
        all_localized = supabase_service.get_all_localized_videos_for_user(user_id)
        all_jobs, _ = supabase_service.list_processing_jobs(user_id, limit=100, project_id=project_id)

        print(f"[VIDEOS] Found {len(all_localized)} localizations and {len(all_jobs)} jobs")

        # Maps for quick lookup
        localized_map = defaultdict(list)  # source_id -> [localized_docs]
        for loc in all_localized:
            if loc.get('source_video_id'):
                localized_map[loc['source_video_id']].append(loc)

        jobs_map = defaultdict(list)  # source_id -> [job_docs]
        for j in all_jobs:
            if j.get('source_video_id'):
                jobs_map[j['source_video_id']].append(j)

        print(f"[VIDEOS] Localized map keys: {list(localized_map.keys())}")
        print(f"[VIDEOS] Jobs map keys: {list(jobs_map.keys())}")

        final_videos = []

        # Process ALL videos from database
        for db_video in db_videos:
            video_id = db_video.get('video_id')

            print(f"[VIDEOS] Processing video: {video_id}, title: {db_video.get('title')}")

            # Get localizations for this video
            localizations = []
            localized_docs = localized_map.get(video_id, [])
            print(f"[VIDEOS]   Found {len(localized_docs)} localized versions")

            for loc in localized_docs:
                localizations.append(LocalizationStatus(
                    language_code=loc.get('language_code', ''),
                    status=loc.get('status', 'live'),
                    video_id=loc.get('localized_video_id'),
                    job_id=loc.get('job_id'),
                    title=loc.get('title'),
                    description=loc.get('description'),
                    thumbnail_url=loc.get('thumbnail_url'),
                    video_url=loc.get('storage_url')
                ))

            # Add in-progress jobs
            job_docs = jobs_map.get(video_id, [])
            print(f"[VIDEOS]   Found {len(job_docs)} processing jobs")

            for j in job_docs:
                live_langs = [l.language_code for l in localizations]
                for lang in j.get('target_languages', []):
                    if lang not in live_langs:
                        print(f"[VIDEOS]     Adding processing job for {lang}")
                        localizations.append(LocalizationStatus(
                            language_code=lang,
                            status='processing',
                            job_id=j.get('id')
                        ))

            print(f"[VIDEOS]   Total localizations: {len(localizations)}")

            # Filter by type if requested
            if video_type != "all" and video_type != "original":
                continue

            # Create video item from database video
            video_item = VideoItem(
                video_id=video_id,
                title=db_video.get('title', 'Untitled'),
                thumbnail_url=db_video.get('thumbnail_url', ''),
                published_at=db_video.get('uploaded_at', datetime.utcnow()),
                view_count=0,  # No views for uploaded videos
                channel_id=db_video.get('channel_id', ''),
                channel_name=db_video.get('channel_name', 'Uploaded'),
                video_type="original",
                source_video_id=None,
                storage_url=db_video.get('storage_url'),  # Include storage URL
                localizations=localizations,
                translated_languages=[l.language_code for l in localizations if l.status == 'live']
            )
            final_videos.append(video_item)

        # If we've reached the limit with uploaded videos, return early
        if len(final_videos) >= limit:
            return VideoListResponse(videos=final_videos[:limit], total=len(final_videos))

        # SECOND: Try to get YouTube videos (if connected)
        remaining_limit = limit - len(final_videos)

        # Get YouTube service
        youtube = await asyncio.to_thread(get_youtube_service, user_id, None, False)

        if youtube is None:
            # Handle mock mode - add mock videos to existing uploaded videos
            mock_resp = await get_mock_videos(user_id, remaining_limit)
            # Apply filters to mock data
            filtered_mock_videos = mock_resp.videos
            if video_type != "all":
                filtered_mock_videos = [v for v in filtered_mock_videos if v.video_type == video_type]
            if channel_id:
                filtered_mock_videos = [v for v in filtered_mock_videos if v.channel_id == channel_id]
            # Combine with uploaded videos
            final_videos.extend(filtered_mock_videos[:remaining_limit])
            return VideoListResponse(videos=final_videos, total=len(final_videos))
        
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
        try:
            while len(playlist_items) < remaining_limit:
                request_params = {
                    'part': 'snippet,contentDetails',
                    'playlistId': uploads_playlist_id,
                    'maxResults': min(remaining_limit - len(playlist_items), 50)
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
        except HttpError as yt_err:
            print(f"[WARNING] YouTube API error fetching playlist {uploads_playlist_id}: {yt_err}")
            # Playlist not found or inaccessible — return just uploaded videos
            return VideoListResponse(videos=final_videos, total=len(final_videos))
        
        if not playlist_items:
            # No YouTube videos, return just uploaded videos
            return VideoListResponse(videos=final_videos, total=len(final_videos))

        video_ids = [item['contentDetails']['videoId'] for item in playlist_items[:remaining_limit]]

        # Get full video details INCLUDING statistics (views)
        videos_response = await asyncio.to_thread(
            youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=','.join(video_ids)
            ).execute
        )

        # Note: We already fetched localized_map and jobs_map above for uploaded videos
        # They are already in scope and can be reused
        for video in videos_response.get('items', []):
            video_id = video['id']
            snippet = video['snippet']
            stats = video.get('statistics', {})
            
            # Determine type and localizations
            localizations = []

            # 1. Check if it IS a localized video (check all_localized list)
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

            # Skip videos already added from the database pass (deduplication)
            if any(v.video_id == video_id for v in final_videos):
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
        # Log the full error for debugging
        import logging
        import traceback
        logger = logging.getLogger(__name__)
        logger.error(
            f"list_videos error - user_id: {user_id}, project_id: {project_id}, "
            f"channel_id: {channel_id}, error: {str(e)}\n{traceback.format_exc()}"
        )

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
        localized = supabase_service.get_localized_video_by_localized_id(video_id, user_id)
        
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
        localized_list = supabase_service.get_localized_videos_by_source_id(video_id, user_id)
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
    channel_id: Optional[str] = Form(None),
    video_file: UploadFile = File(...),
    thumbnail_file: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user)
) -> VideoUploadResponse:
    """
    Upload a video to storage (S3 or local).
    This creates a source video that can later be used for dubbing/translation jobs.

    Args:
        title: Video title
        description: Video description
        channel_id: Optional channel ID to associate video with
        video_file: Video file to upload
        current_user: Current authenticated user from Firebase Auth token

    Returns:
        VideoUploadResponse: Upload result with video ID

    Raises:
        HTTPException: If upload fails
    """
    user_id = current_user["user_id"]
    temp_path = None

    try:
        # Generate unique video ID
        video_id = str(uuid.uuid4())

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

        # Upload to storage based on configuration
        if settings.storage_type == "s3":
            from services.s3_storage import get_s3_storage_service
            s3_service = get_s3_storage_service()

            # Upload to S3 with a job_id of "uploads" for manually uploaded videos
            job_id = "uploads"
            language_code = "original"
            storage_key = await s3_service.upload_video(
                temp_path,
                user_id=user_id,
                job_id=job_id,
                language_code=language_code,
                video_id=video_id
            )

            # Get storage URL
            storage_url = await s3_service.get_storage_url(storage_key, settings.cloudfront_url)

        else:
            # Local storage
            storage_dir = os.path.join(settings.local_storage_dir, 'videos', user_id, 'uploads', 'original')
            os.makedirs(storage_dir, exist_ok=True)

            storage_filename = f"{video_id}{suffix}"
            storage_path = os.path.join(storage_dir, storage_filename)

            # Copy temp file to storage
            shutil.move(temp_path, storage_path)
            temp_path = None  # Prevent deletion in finally block

            # Build storage URL (served via /storage mount)
            storage_url = f"/storage/videos/{user_id}/uploads/original/{storage_filename}"

        # Handle thumbnail upload if provided
        thumbnail_url = None
        if thumbnail_file:
            thumbnail_suffix = os.path.splitext(thumbnail_file.filename)[1] if thumbnail_file.filename else '.jpg'
            thumbnail_filename = f"{video_id}_thumb{thumbnail_suffix}"

            if settings.storage_type == "s3":
                # Save thumbnail to temp file first
                with tempfile.NamedTemporaryFile(delete=False, suffix=thumbnail_suffix) as thumb_temp:
                    thumb_temp_path = thumb_temp.name
                    while True:
                        chunk = await thumbnail_file.read(1024 * 1024)
                        if not chunk:
                            break
                        thumb_temp.write(chunk)

                # Upload to S3
                from services.s3_storage import get_s3_storage_service
                s3_service = get_s3_storage_service()
                thumb_key = await s3_service.upload_file(
                    thumb_temp_path,
                    user_id=user_id,
                    job_id="uploads",
                    language_code="thumbnails",
                    filename=thumbnail_filename
                )
                thumbnail_url = await s3_service.get_storage_url(thumb_key, settings.cloudfront_url)
                os.unlink(thumb_temp_path)
            else:
                # Local storage
                thumbnail_dir = os.path.join(settings.local_storage_dir, 'videos', user_id, 'uploads', 'thumbnails')
                os.makedirs(thumbnail_dir, exist_ok=True)
                thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

                # Save thumbnail
                with open(thumbnail_path, 'wb') as f:
                    while True:
                        chunk = await thumbnail_file.read(1024 * 1024)
                        if not chunk:
                            break
                        f.write(chunk)

                thumbnail_url = f"/storage/videos/{user_id}/uploads/thumbnails/{thumbnail_filename}"

        # Store video metadata in Firestore
        video_data = {
            'video_id': video_id,
            'user_id': user_id,
            'title': title,
            'description': description,
            'channel_id': channel_id,
            'storage_url': storage_url,
            'thumbnail_url': thumbnail_url,
            'uploaded_at': datetime.utcnow(),
            'status': 'uploaded',
            'filename': video_file.filename
        }

        # Store in videos table (uploaded_videos collection doesn't exist in Supabase)
        supabase_service.create_video(video_data)

        # Log activity
        supabase_service.log_activity(
            user_id=user_id,
            project_id=None,
            action="Uploaded video",
            details=f"Video '{title}' uploaded to storage with ID {video_id}."
        )

        return VideoUploadResponse(
            message="Video uploaded successfully to storage",
            video_id=video_id,
            title=title,
            privacy_status="uploaded"  # Changed from YouTube privacy status
        )

    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Upload failed: {str(e)}\n{traceback.format_exc()}")

        raise HTTPException(
            status_code=500,
            detail=f"Failed to upload video: {str(e)}"
        )
    finally:
        # Clean up temporary file
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except Exception:
                pass  # Ignore cleanup errors


@router.post("/detected/sync-recent")
async def sync_recent_detected_uploads(
    days: int = 7,
    per_channel_limit: int = 20,
    current_user: dict = Depends(get_current_user)
):
    """
    Backfill recent uploads from connected YouTube channels into detected uploads.

    This is useful after connecting a new channel that already has recent videos.
    """
    user_id = current_user["user_id"]
    days = max(1, min(days, 31))
    per_channel_limit = max(1, min(per_channel_limit, 50))

    print(f"\n[SYNC] ===== sync_recent_detected_uploads START =====")
    print(f"[SYNC] user_id={user_id}, days={days}, per_channel_limit={per_channel_limit}")

    connections = supabase_service.get_youtube_connections(user_id)
    print(f"[SYNC] Found {len(connections) if connections else 0} YouTube connections")
    if connections:
        for i, c in enumerate(connections):
            print(f"[SYNC]   connection[{i}]: id={c.get('connection_id')}, channel={c.get('youtube_channel_id')}, name={c.get('channel_name')}")

    if not connections:
        print(f"[SYNC] No connected channels found. Returning early.")
        return {
            "status": "ok",
            "channels_scanned": 0,
            "videos_seen": 0,
            "videos_upserted": 0,
            "jobs_created": 0,
            "message": "No connected channels found.",
        }

    language_channels = supabase_service.get_language_channels(user_id)
    target_languages = sorted({ch.get("language_code") for ch in language_channels if ch.get("language_code")})
    print(f"[SYNC] Language channels: {len(language_channels)}, target_languages: {target_languages}")

    default_project_id = next((ch.get("project_id") for ch in language_channels if ch.get("project_id")), None)
    print(f"[SYNC] default_project_id={default_project_id}")

    from services.job_queue import enqueue_dubbing_job

    published_after = (datetime.utcnow() - timedelta(days=days)).replace(microsecond=0).isoformat() + "Z"
    print(f"[SYNC] publishedAfter={published_after}")

    seen_video_ids = set()
    channels_scanned = 0
    videos_seen = 0
    videos_upserted = 0
    jobs_created = 0

    for conn in connections:
        connection_id = conn.get("connection_id")
        channel_id = conn.get("youtube_channel_id")
        if not channel_id:
            print(f"[SYNC] Skipping connection {connection_id}: no youtube_channel_id")
            continue

        print(f"[SYNC] Building YouTube service for connection={connection_id}, channel={channel_id}")
        youtube = await asyncio.to_thread(get_youtube_service_helper, user_id, connection_id, False)
        if not youtube:
            print(f"[SYNC] YouTube service is None for connection={connection_id} (likely mock/expired credentials)")
            continue

        channels_scanned += 1
        try:
            print(f"[SYNC] Calling youtube.search().list(channelId={channel_id}, publishedAfter={published_after})")
            req = youtube.search().list(
                part="id,snippet",
                channelId=channel_id,
                type="video",
                order="date",
                publishedAfter=published_after,
                maxResults=per_channel_limit,
            )
            response = await asyncio.to_thread(req.execute)
            print(f"[SYNC] YouTube search returned {len(response.get('items', []))} items")
        except Exception as e:
            print(f"[SYNC] ERROR: YouTube search failed for channel {channel_id}: {type(e).__name__}: {e}")
            continue

        for item in response.get("items", []):
            video_id = (item.get("id") or {}).get("videoId")
            if not video_id or video_id in seen_video_ids:
                continue
            seen_video_ids.add(video_id)
            videos_seen += 1

            snippet = item.get("snippet", {})
            thumbs = snippet.get("thumbnails", {}) or {}
            thumb = (
                thumbs.get("high")
                or thumbs.get("medium")
                or thumbs.get("default")
                or {}
            )

            # Always upsert the video for this user (each user gets their own row)
            try:
                upsert_data = {
                    "video_id": video_id,
                    "source_video_id": None,
                    "user_id": user_id,
                    "project_id": default_project_id,
                    "channel_id": channel_id,
                    "channel_name": snippet.get("channelTitle"),
                    "title": snippet.get("title") or f"Video {video_id}",
                    "description": snippet.get("description") or "",
                    "thumbnail_url": thumb.get("url") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    "published_at": snippet.get("publishedAt"),
                    "status": "draft",
                    "video_type": "original",
                }
                print(f"[SYNC] Upserting video: {video_id} - '{upsert_data['title'][:50]}'")
                result = supabase_service.upsert_video(upsert_data)
                print(f"[SYNC] Upsert result: {result}")
                videos_upserted += 1
            except Exception as e:
                print(f"[SYNC] ERROR: Upsert failed for video {video_id}: {type(e).__name__}: {e}")
                continue

            # Only skip job creation if this user already has a job for this video
            existing_job = supabase_service.get_job_by_video(video_id, user_id)
            if existing_job:
                print(f"[SYNC] Video {video_id} already has a job for user {user_id}, skipping job creation")
                continue

            # Only create jobs if target languages are configured
            if target_languages:
                try:
                    await enqueue_dubbing_job(
                        source_video_id=video_id,
                        source_channel_id=channel_id,
                        user_id=user_id,
                        target_languages=target_languages,
                        project_id=default_project_id,
                        auto_approve=False,
                        is_simulation=True,
                        metadata={
                            "detected_via": "manual_backfill_sync",
                            "published_at": snippet.get("publishedAt"),
                            "title": snippet.get("title"),
                        },
                        db=None,
                        background_tasks=None,
                    )
                    jobs_created += 1
                except Exception as e:
                    print(f"[SYNC] ERROR: enqueue_dubbing_job failed for {video_id}: {type(e).__name__}: {e}")

    supabase_service.log_activity(
        user_id=user_id,
        project_id=default_project_id,
        action="Backfilled detected uploads",
        details=f"Scanned {channels_scanned} channels. Seen {videos_seen} videos. Created {jobs_created} jobs.",
    )

    print(f"[SYNC] DONE: scanned={channels_scanned}, seen={videos_seen}, upserted={videos_upserted}, jobs={jobs_created}")
    print(f"[SYNC] ===== sync_recent_detected_uploads END =====\n")

    return {
        "status": "ok",
        "channels_scanned": channels_scanned,
        "videos_seen": videos_seen,
        "videos_upserted": videos_upserted,
        "jobs_created": jobs_created,
        "window_days": days,
    }


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
        secret = uuid.uuid4().hex
        
        # Prepare subscription request to PubSubHubbub hub
        subscribe_data = {
            'hub.mode': 'subscribe',
            'hub.topic': topic,
            'hub.callback': callback_url,
            'hub.lease_seconds': str(request.lease_seconds),
            'hub.secret': secret,
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
        subscription_id = supabase_service.create_subscription(
            user_id=user_id,
            channel_id=request.channel_id,
            callback_url=callback_url,
            topic=topic,
            lease_seconds=request.lease_seconds,
            expires_at=expires_at,
            secret=secret,
        )
        
        return SubscriptionResponse(
            subscription_id=subscription_id,
            channel_id=request.channel_id,
            expires_at=expires_at,
            message="Subscription created successfully. Awaiting verification from PubSubHubbub hub."
        )
        
        # Log activity
        supabase_service.log_activity(
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
            subscription = supabase_service.get_subscription(request.subscription_id)
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
            subscription = supabase_service.get_subscription_by_channel(user_id, request.channel_id)
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
        supabase_service.delete_subscription(subscription['id'])
        
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


@router.post("/subscriptions/renew")
async def renew_subscriptions(
    renew_before_hours: int = 168,
    current_user: dict = Depends(get_current_user)
):
    """
    Renew user's subscriptions that are expiring soon.

    Intended to be callable by UI or cron-backed job runners.
    """
    user_id = current_user["user_id"]
    try:
        summary = await renew_due_subscriptions(
            user_id=user_id,
            renew_before_hours=renew_before_hours,
        )
        return {"status": "ok", **summary}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to renew subscriptions: {str(e)}",
        )
