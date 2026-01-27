"""Service for downloading videos from YouTube."""
import os
import tempfile
import asyncio
from typing import Optional
from pathlib import Path

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False


async def download_video(video_url: str, output_dir: Optional[str] = None) -> tuple[str, str]:
    """
    Download video from YouTube.
    
    Args:
        video_url: YouTube video URL or video ID
        output_dir: Optional output directory (uses temp if not provided)
        
    Returns:
        tuple: (video_path, audio_path) - Paths to downloaded files
        
    Raises:
        Exception: If download fails or yt-dlp is not available
    """
    if not YT_DLP_AVAILABLE:
        raise Exception("yt-dlp is not installed. Please install it: pip install yt-dlp")
    
    # Build full URL if just video ID provided
    if not video_url.startswith('http'):
        video_url = f"https://www.youtube.com/watch?v={video_url}"
    
    # Create output directory
    if not output_dir:
        output_dir = tempfile.mkdtemp()
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }
    
    video_path = None
    audio_path = None
    info_dict = None

    def download():
        nonlocal video_path, audio_path, info_dict
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            info_dict = info
            video_id = info.get('id', 'video')
            
            # Find downloaded files
            for file in os.listdir(output_dir):
                if file.startswith(video_id):
                    file_path = os.path.join(output_dir, file)
                    ext = Path(file).suffix.lower()
                    if ext in ['.mp4', '.webm', '.mkv']:
                        video_path = file_path
                    elif ext in ['.m4a', '.mp3', '.webm']:
                        audio_path = file_path
    
    # Run download in thread pool
    await asyncio.to_thread(download)
    
    if not video_path:
        raise Exception("Failed to download video")
    
    # If audio not separate, extract it
    if not audio_path:
        # For now, return video path for both
        # In production, you might want to extract audio using ffmpeg
        audio_path = video_path
    
    return video_path, audio_path, info_dict
