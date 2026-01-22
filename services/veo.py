"""Google Veo API integration for lip sync processing."""
import httpx
import asyncio
import os
import uuid
import tempfile
from typing import Optional
from pathlib import Path

from config import settings


async def process_lip_sync(
    video_path: str,
    audio_path: str,
    language_code: str
) -> str:
    """
    Process video with Google Veo for lip sync.
    
    Args:
        video_path: Path to video file
        audio_path: Path to audio file
        language_code: Target language code
        
    Returns:
        str: Path to processed video file
        
    Raises:
        Exception: If processing fails
    """
    if not settings.google_veo_api_key:
        raise Exception("Google Veo API key not configured")
    
    if not settings.google_veo_api_url:
        # Default Veo API endpoint (this may need to be updated based on actual API)
        api_url = "https://veo-api.googleapis.com/v1/lipsync"
    else:
        api_url = settings.google_veo_api_url
    
    # Read video and audio files
    with open(video_path, 'rb') as vf:
        video_data = vf.read()
    
    with open(audio_path, 'rb') as af:
        audio_data = af.read()
    
    # Prepare multipart form data
    files = {
        'video': ('video.mp4', video_data, 'video/mp4'),
        'audio': ('audio.m4a', audio_data, 'audio/m4a'),
    }
    
    data = {
        'language': language_code
    }
    
    headers = {
        'Authorization': f'Bearer {settings.google_veo_api_key}'
    }
    
    # Submit processing request
    async with httpx.AsyncClient(timeout=300.0) as client:
        response = await client.post(
            api_url,
            files=files,
            data=data,
            headers=headers
        )
        response.raise_for_status()
        
        result = response.json()
        
        # If API returns a job ID, poll for completion
        if 'job_id' in result:
            processed_path = await _poll_veo_job(result['job_id'], api_url, headers)
        elif 'video_url' in result:
            # Download processed video
            processed_path = await _download_processed_video(result['video_url'])
        else:
            raise Exception("Unexpected response from Veo API")
    
    return processed_path


async def _poll_veo_job(job_id: str, api_url: str, headers: dict) -> str:
    """Poll Veo API for job completion."""
    import time
    import tempfile
    
    status_url = f"{api_url}/jobs/{job_id}"
    max_attempts = 60  # 5 minutes max
    attempt = 0
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        while attempt < max_attempts:
            response = await client.get(status_url, headers=headers)
            response.raise_for_status()
            status = response.json()
            
            if status.get('status') == 'completed':
                video_url = status.get('video_url')
                if video_url:
                    return await _download_processed_video(video_url)
                else:
                    raise Exception("Job completed but no video URL provided")
            elif status.get('status') == 'failed':
                raise Exception(f"Veo processing failed: {status.get('error', 'Unknown error')}")
            
            # Wait before next poll
            await asyncio.sleep(5)
            attempt += 1
    
    raise Exception("Veo processing timed out")


async def _download_processed_video(video_url: str) -> str:
    """Download processed video from URL."""
    import tempfile
    
    output_path = os.path.join(tempfile.gettempdir(), f"veo_processed_{uuid.uuid4()}.mp4")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream('GET', video_url) as response:
            response.raise_for_status()
            with open(output_path, 'wb') as f:
                async for chunk in response.aiter_bytes():
                    f.write(chunk)
    
    return output_path
