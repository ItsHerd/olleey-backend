"""Sync Labs API integration for lip-sync processing using official SDK.

Documentation: https://github.com/synchronicity-labs/sync-python-sdk
"""
import asyncio
import os
from typing import Optional

try:
    from sync import AsyncSync
    from sync.common import Audio, Video, GenerationOptions
    from sync.core.api_error import ApiError
except ImportError:
    raise ImportError(
        "Sync Labs SDK not installed. Install with: pip install syncsdk"
    )

from config import settings


def _get_sync_client() -> AsyncSync:
    """Get configured Sync Labs client."""
    if not settings.sync_labs_api_key:
        raise Exception("Sync Labs API key not configured. Add SYNC_LABS_API_KEY to .env")
    
    return AsyncSync(api_key=settings.sync_labs_api_key)


async def process_lip_sync(
    video_url: str,
    audio_url: str,
    sync_mode: str = "loop",
    model: str = "lipsync-2"
) -> dict:
    """
    Complete lip-sync workflow using official Sync Labs SDK.
    
    Args:
        video_url: Publicly accessible URL to the original video
        audio_url: Publicly accessible URL to the dubbed audio
        sync_mode: Sync mode - "loop" (recommended) or "direct"
        model: Model to use - "lipsync-2" (latest) or "lipsync-1"
        
    Returns:
        dict: Generation response with video URL and metadata
        
    Raises:
        ApiError: If API request fails
        Exception: If processing fails
        
    Reference: https://github.com/synchronicity-labs/sync-python-sdk
    """
    print(f"[SYNC_LABS] Starting lip-sync process")
    print(f"  Video: {video_url}")
    print(f"  Audio: {audio_url}")
    print(f"  Model: {model}")
    print(f"  Sync Mode: {sync_mode}")
    
    try:
        client = _get_sync_client()
        
        # Create generation using official SDK
        result = await client.generations.create(
            input=[
                Video(url=video_url),
                Audio(url=audio_url),
            ],
            model=model,
            options=GenerationOptions(
                sync_mode=sync_mode,  # "loop" for better quality
            ),
        )
        
        print(f"[SYNC_LABS] ✅ Generation created: {result.id}")
        print(f"[SYNC_LABS] Status: {result.status}")
        
        # Check if video URL is immediately available
        video_url = None
        if hasattr(result, 'output_url') and result.output_url:
            video_url = result.output_url
        elif hasattr(result, 'url') and result.url:
            video_url = result.url
        
        if video_url:
            print(f"[SYNC_LABS] ✅ Video URL: {video_url}")
            return {
                "id": result.id,
                "url": video_url,
                "status": result.status,
                "model": getattr(result, 'model', model)
            }
        else:
            # If URL not immediately available, need to poll
            print(f"[SYNC_LABS] Waiting for generation to complete...")
            return await wait_for_generation(result.id)
            
    except ApiError as e:
        print(f"[SYNC_LABS] ❌ API Error: {e.status_code}")
        print(f"[SYNC_LABS] Error body: {e.body}")
        raise Exception(f"Sync Labs API Error ({e.status_code}): {e.body}")
        
    except Exception as e:
        print(f"[SYNC_LABS] ❌ Error: {str(e)}")
        raise

# Mocking for test environment
if settings.environment == "test" or settings.use_mock_db:
    async def mock_process_lip_sync(video_url: str, audio_url: str, sync_mode: str = "loop", model: str = "lipsync-2") -> dict:
        print(f"[MOCK] Sync Labs process_lip_sync called")
        print(f"  Video: {video_url}")
        print(f"  Audio: {audio_url}")
        
        # Return a mock result immediately
        return {
            "id": "mock_sync_id_12345",
            "url": video_url, # Return original video as result for testing
            "status": "COMPLETED",
            "model": model
        }
        
    process_lip_sync = mock_process_lip_sync


async def wait_for_generation(generation_id: str, timeout_seconds: int = 600) -> dict:
    """
    Poll for generation completion using official SDK.
    
    Args:
        generation_id: Generation ID from create()
        timeout_seconds: Maximum time to wait
        
    Returns:
        dict: Generation result with video URL
    """
    import time
    
    client = _get_sync_client()
    start_time = time.time()
    check_interval = 5
    
    while True:
        elapsed = time.time() - start_time
        
        if elapsed > timeout_seconds:
            raise Exception(f"Generation timed out after {timeout_seconds}s")
        
        try:
            result = await client.generations.get(generation_id)
            status = result.status.upper() if hasattr(result, 'status') else "UNKNOWN"
            
            print(f"[SYNC_LABS] Generation {generation_id}: {status} (elapsed: {int(elapsed)}s)")
            
            if status == "COMPLETED" or status == "DONE":
                # Try different possible URL fields (output_url is the primary field)
                video_url = None
                if hasattr(result, 'output_url') and result.output_url:
                    video_url = result.output_url
                elif hasattr(result, 'url') and result.url:
                    video_url = result.url
                elif hasattr(result, 'video_url') and result.video_url:
                    video_url = result.video_url
                elif hasattr(result, 'result_url') and result.result_url:
                    video_url = result.result_url
                
                if video_url:
                    print(f"[SYNC_LABS] ✅ Video URL: {video_url}")
                    return {
                        "id": result.id,
                        "url": video_url,
                        "status": status,
                        "model": getattr(result, 'model', 'sync-2')
                    }
                else:
                    # Debug output if URL not found
                    print(f"[SYNC_LABS] ❌ No URL field found. Available: {list(result.__dict__.keys()) if hasattr(result, '__dict__') else 'N/A'}")
                    raise Exception(f"Generation completed but no URL available")
                    
            elif status == "FAILED" or status == "ERROR":
                error_msg = getattr(result, 'error', 'Unknown error')
                raise Exception(f"Generation failed: {error_msg}")
            
            # Still processing
            if elapsed > 60:
                check_interval = 10
            if elapsed > 300:
                check_interval = 15
                
            await asyncio.sleep(check_interval)
            
        except ApiError as e:
            print(f"[SYNC_LABS] Error checking status: {e.status_code}")
            await asyncio.sleep(check_interval)


async def download_video_from_url(video_url: str, output_path: str) -> str:
    """
    Download video from URL (typically from Sync Labs generation result).
    
    Args:
        video_url: URL to the video
        output_path: Local path to save the video
        
    Returns:
        str: Path to the downloaded video
    """
    import httpx
    
    print(f"[SYNC_LABS] Downloading video to {output_path}")
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        async with client.stream('GET', video_url) as response:
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                downloaded = 0
                async for chunk in response.aiter_bytes(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # Log progress every 10MB
                    if downloaded % (10 * 1024 * 1024) == 0:
                        print(f"  Downloaded {downloaded / (1024 * 1024):.1f} MB")
    
    print(f"[SYNC_LABS] ✅ Download complete: {output_path}")
    return output_path


# Keep backward compatibility
download_processed_video = download_video_from_url


async def validate_urls(video_url: str, audio_url: str) -> dict:
    """
    Validate that both URLs are publicly accessible.
    
    Returns:
        dict: {"valid": bool, "errors": list}
    """
    import httpx
    
    errors = []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Check video URL
        try:
            response = await client.head(video_url)
            if response.status_code != 200:
                errors.append(f"Video URL not accessible: {response.status_code}")
        except Exception as e:
            errors.append(f"Video URL error: {str(e)}")
        
        # Check audio URL
        try:
            response = await client.head(audio_url)
            if response.status_code != 200:
                errors.append(f"Audio URL not accessible: {response.status_code}")
        except Exception as e:
            errors.append(f"Audio URL error: {str(e)}")
    
    return {
        "valid": len(errors) == 0,
        "errors": errors
    }
