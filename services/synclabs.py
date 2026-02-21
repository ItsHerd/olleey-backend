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


class SyncLabsError(Exception):
    """Base exception for Sync Labs errors."""
    def __init__(self, message: str, code: Optional[str] = None):
        super().__init__(message)
        self.code = code

class SyncLabsValidationError(SyncLabsError):
    """Exception for input validation errors (HTTP 400)."""
    pass

class SyncLabsRetryableError(SyncLabsError):
    """Exception for system/infra errors that can be retried (HTTP 500/503)."""
    pass


def _parse_sync_error(error_code: Optional[str], default_message: str) -> Exception:
    """Map Sync Labs error codes to appropriate exceptions."""
    validation_errors = {
        "generation_unsupported_model",
        "generation_media_metadata_missing",
        "generation_audio_length_exceeded",
        "generation_text_length_exceeded",
        "generation_audio_missing",
        "generation_video_missing",
        "generation_input_validation_failed",
        # Batch API errors are also validation errors for the user
        "batch_file_too_large",
        "batch_too_many_requests",
        "batch_insufficient_records",
        "batch_invalid_jsonl",
        "batch_duplicate_request_id",
        "batch_invalid_endpoint"
    }
    
    retryable_errors = {
        "generation_timeout",
        "generation_database_error",
        "generation_infra_storage_error",
        "generation_infra_resource_exhausted",
        "generation_infra_service_unavailable",
        "batch_concurrency_limit_reached"
    }

    if error_code in validation_errors:
        return SyncLabsValidationError(default_message, code=error_code)
    elif error_code in retryable_errors:
        return SyncLabsRetryableError(default_message, code=error_code)
    
    # Default to base error for unhandled, auth, pipeline failures
    return SyncLabsError(default_message, code=error_code)


def _get_sync_client() -> AsyncSync:
    """Get configured Sync Labs client."""
    if not settings.sync_labs_api_key:
        raise Exception("Sync Labs API key not configured. Add SYNC_LABS_API_KEY to .env")
    
    return AsyncSync(api_key=settings.sync_labs_api_key)


async def process_lip_sync(
    video_url: str,
    audio_url: str,
    sync_mode: str = "loop",
    model: str = "lipsync-2",
    user_id: Optional[str] = None,
    language: Optional[str] = None
) -> dict:
    """
    Complete lip-sync workflow using official Sync Labs SDK.
    
    Args:
        video_url: Publicly accessible URL to the original video
        audio_url: Publicly accessible URL to the dubbed audio
        sync_mode: Sync mode - "loop" (recommended) or "direct"
        model: Model to use - "lipsync-2" (latest) or "lipsync-1"
        user_id: Optional user ID for demo mode check
        language: Optional language code for demo video lookup
        
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
        
        # Try to extract error code/message from body
        error_code = None
        error_message = f"Sync Labs API Error ({e.status_code})"
        
        if isinstance(e.body, dict) and "error" in e.body:
            error_data = e.body["error"]
            if isinstance(error_data, dict):
                error_code = error_data.get("code")
                error_message = error_data.get("message", error_message)
            else:
                error_message = str(error_data)
        elif isinstance(e.body, dict) and "code" in e.body:
            error_code = e.body.get("code")
            error_message = e.body.get("message", error_message)
            
        raise _parse_sync_error(error_code, error_message)
        
    except Exception as e:
        print(f"[SYNC_LABS] ❌ Error: {str(e)}")
        raise

# Mocking for test environment and demo users
if settings.environment == "test" or settings.use_mock_db:
    async def mock_process_lip_sync(
        video_url: str, 
        audio_url: str, 
        sync_mode: str = "loop", 
        model: str = "lipsync-2",
        user_id: Optional[str] = None,
        language: Optional[str] = None
    ) -> dict:
        """Enhanced mock using demo video library."""
        import uuid
        from services.demo_simulator import demo_simulator
        from config import DEMO_VIDEO_LIBRARY, DEMO_PIPELINE_TIMING
        
        print(f"[MOCK] Sync Labs process_lip_sync called")
        print(f"  Video: {video_url}")
        print(f"  Audio: {audio_url}")
        print(f"  Language: {language}")
        
        # Check if demo user
        if user_id and demo_simulator.is_demo_user(user_id):
            # Simulate processing delay
            await asyncio.sleep(DEMO_PIPELINE_TIMING.get("lip_sync", 10))
            
            # Look up in demo library
            for video_data in DEMO_VIDEO_LIBRARY.values():
                if video_url in video_data.get("original_url", ""):
                    if language and language in video_data.get("languages", {}):
                        dubbed_url = video_data["languages"][language].get("dubbed_video_url")
                        if dubbed_url:
                            print(f"[MOCK] ✅ Found dubbed video for {language}: {dubbed_url}")
                            return {
                                "id": f"demo_sync_{uuid.uuid4().hex[:8]}",
                                "url": dubbed_url,
                                "status": "COMPLETED",
                                "model": model,
                                "is_demo": True
                            }
            
            # Fallback to original if no mapping found
            print(f"[MOCK] ⚠ No dubbed video found, returning original")
            return {
                "id": f"demo_sync_{uuid.uuid4().hex[:8]}",
                "url": video_url,
                "status": "COMPLETED",
                "model": model,
                "is_demo": True
            }
        
        # Non-demo mock (basic test mode)
        return {
            "id": "mock_sync_id_12345",
            "url": video_url,
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
                error_code = getattr(result, 'error_code', getattr(result, 'code', None))
                error_msg = getattr(result, 'error', 'Unknown error')
                if isinstance(error_msg, dict):
                    error_code = error_msg.get('code', error_code)
                    error_msg = error_msg.get('message', 'Unknown error')
                raise _parse_sync_error(error_code, f"Generation failed: {error_msg}")
            
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
