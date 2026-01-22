"""Localization router for caption and subtitle management."""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import asyncio

from schemas.localization import CaptionUploadRequest, CaptionUploadResponse
from routers.youtube_auth import get_youtube_service
from middleware.auth import get_current_user

router = APIRouter(prefix="/localization", tags=["localization"])


@router.post("/captions/upload", response_model=CaptionUploadResponse)
async def upload_captions(
    video_id: str = Form(...),
    language_code: str = Form(...),
    caption_file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
) -> CaptionUploadResponse:
    """
    Upload caption track to an existing YouTube video.
    
    Args:
        video_id: YouTube video ID
        language_code: ISO 639-1 language code (e.g., 'es', 'de', 'fr')
        caption_file: SRT caption file
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        CaptionUploadResponse: Upload result with caption ID
        
    Raises:
        HTTPException: If upload fails or video not found
    """
    user_id = current_user["user_id"]
    
    # Validate language code (basic ISO 639-1 format check)
    if len(language_code) != 2 or not language_code.isalpha():
        raise HTTPException(
            status_code=400,
            detail="Invalid language_code. Must be a valid ISO 639-1 code (2 letters, e.g., 'es', 'de', 'fr')"
        )
    
    try:
        # Get YouTube service
        youtube = await asyncio.to_thread(get_youtube_service, user_id)
        
        # Read caption file content
        caption_content = await caption_file.read()
        caption_text = caption_content.decode('utf-8')
        
        # Create caption metadata
        caption_body = {
            'snippet': {
                'videoId': video_id,
                'language': language_code,
                'name': f'{language_code} captions'
            }
        }
        
        # Insert caption track
        insert_request = youtube.captions().insert(
            part='snippet',
            body=caption_body,
            media_body=caption_text.encode('utf-8')
        )
        
        response = await asyncio.to_thread(insert_request.execute)
        caption_id = response['id']
        
        return CaptionUploadResponse(
            message="Caption uploaded successfully",
            caption_id=caption_id,
            video_id=video_id,
            language_code=language_code
        )
        
    except HttpError as e:
        error_reason = e.error_details[0].get('reason', '') if e.error_details else ''
        if e.resp.status == 404:
            raise HTTPException(
                status_code=404,
                detail=f"Video not found: {video_id}"
            )
        elif e.resp.status == 403 and 'quotaExceeded' in error_reason:
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
            detail=f"Failed to upload captions: {str(e)}"
        )
