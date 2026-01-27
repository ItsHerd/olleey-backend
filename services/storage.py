"""Local file storage service for video file storage."""
from typing import Optional
import os
import uuid
import shutil
from pathlib import Path

from config import settings


class StorageService:
    """Service for local file storage operations."""
    
    def __init__(self):
        """Initialize local storage service."""
        # Get storage directory from config or use default
        self.storage_dir = getattr(settings, 'local_storage_dir', './storage')
        
        # Create storage directory if it doesn't exist
        os.makedirs(self.storage_dir, exist_ok=True)
        
        # Create subdirectories structure
        self.videos_dir = os.path.join(self.storage_dir, 'videos')
        os.makedirs(self.videos_dir, exist_ok=True)
    
    def upload_file(self, file_path: str, user_id: str, job_id: str,
                   language_code: str, filename: Optional[str] = None) -> str:
        """
        Copy processed file to local storage.
        
        Args:
            file_path: Local path to file
            user_id: User ID
            job_id: Processing job ID
            language_code: Language code
            filename: Storage filename (if None, uses original filename or uuid)
            
        Returns:
            str: Relative path to stored file
        """
        # Create directory structure: videos/{user_id}/{job_id}/{language_code}/
        # We stick to videos_dir for now as the main storage root for job assets
        user_dir = os.path.join(self.videos_dir, user_id)
        job_dir = os.path.join(user_dir, job_id)
        lang_dir = os.path.join(job_dir, language_code)
        os.makedirs(lang_dir, exist_ok=True)
        
        # Generate filename if not provided
        if not filename:
            filename = os.path.basename(file_path)
            
        dest_path = os.path.join(lang_dir, filename)
        
        # Copy file to storage
        shutil.copy2(file_path, dest_path)
        
        # Return relative path from storage root
        return os.path.relpath(dest_path, self.storage_dir).replace('\\', '/')

    def upload_video(self, file_path: str, user_id: str, job_id: str, 
                    language_code: str, video_id: Optional[str] = None) -> str:
        """
        Copy processed video to local storage.
        Wrapper around upload_file that enforces .mp4 extension for backward compatibility.
        
        Args:
            file_path: Local path to video file
            user_id: User ID
            job_id: Processing job ID
            language_code: Language code
            video_id: Optional video ID (for naming)
            
        Returns:
            str: Relative path to stored video file
        """
        filename = f"{video_id or uuid.uuid4()}.mp4"
        return self.upload_file(file_path, user_id, job_id, language_code, filename)
    
    def upload_video_from_bytes(self, video_data: bytes, user_id: str, job_id: str,
                               language_code: str, video_id: Optional[str] = None) -> str:
        """
        Save processed video from bytes to local storage.
        
        Args:
            video_data: Video file bytes
            user_id: User ID
            job_id: Processing job ID
            language_code: Language code
            video_id: Optional video ID (for naming)
            
        Returns:
            str: Relative path to stored video file
        """
        # Create directory structure: videos/{user_id}/{job_id}/{language_code}/
        user_dir = os.path.join(self.videos_dir, user_id)
        job_dir = os.path.join(user_dir, job_id)
        lang_dir = os.path.join(job_dir, language_code)
        os.makedirs(lang_dir, exist_ok=True)
        
        # Generate filename
        filename = f"{video_id or uuid.uuid4()}.mp4"
        dest_path = os.path.join(lang_dir, filename)
        
        # Write bytes to file
        with open(dest_path, 'wb') as f:
            f.write(video_data)
        
        # Return relative path from storage root
        return os.path.relpath(dest_path, self.storage_dir).replace('\\', '/')
    
    def get_video_path(self, storage_path: str) -> Optional[str]:
        """
        Get absolute path to video file.
        
        Args:
            storage_path: Relative path from storage root
            
        Returns:
            str: Absolute path to video file, or None if not found
        """
        full_path = os.path.join(self.storage_dir, storage_path)
        if os.path.exists(full_path):
            return full_path
        return None
    
    def delete_video(self, storage_path: str):
        """
        Delete video from local storage.
        
        Args:
            storage_path: Relative path from storage root
        """
        full_path = os.path.join(self.storage_dir, storage_path)
        if os.path.exists(full_path):
            os.remove(full_path)
    
    def get_video_url(self, user_id: str, job_id: str, language_code: str, 
                     video_id: str) -> Optional[str]:
        """
        Get storage path for video.
        
        Args:
            user_id: User ID
            job_id: Processing job ID
            language_code: Language code
            video_id: Video ID
            
        Returns:
            str: Relative storage path, or None if not found
        """
        video_path = os.path.join(self.videos_dir, user_id, job_id, language_code, f"{video_id}.mp4")
        if os.path.exists(video_path):
            return os.path.relpath(video_path, self.storage_dir).replace('\\', '/')
        return None
    
    def get_storage_url(self, storage_path: str, base_url: Optional[str] = None) -> str:
        """
        Get URL for accessing stored video (for API responses).
        
        Args:
            storage_path: Relative path from storage root
            base_url: Optional base URL for the API (e.g., http://localhost:8000)
            
        Returns:
            str: URL to access the video
        """
        if base_url:
            return f"{base_url.rstrip('/')}/storage/{storage_path}"
        return f"/storage/{storage_path}"
    
    def upload_and_get_public_url(
        self, 
        file_path: str, 
        user_id: str, 
        job_id: str, 
        filename: str
    ) -> str:
        """
        Upload file to temp storage and return public URL accessible via Cloudflare Tunnel.
        
        Args:
            file_path: Local path to file
            user_id: User ID
            job_id: Job ID
            filename: Desired filename (e.g., 'video.mp4', 'audio_german.mp3')
        
        Returns:
            str: Public URL accessible from internet
        """
        # Create temp directory structure: temp/{user_id}/{job_id}/
        temp_dir = os.path.join(self.storage_dir, 'temp', user_id, job_id)
        os.makedirs(temp_dir, exist_ok=True)
        
        # Copy file to temp storage
        dest_path = os.path.join(temp_dir, filename)
        shutil.copy2(file_path, dest_path)
        
        # Get base URL from settings (Cloudflare Tunnel URL)
        base_url = getattr(settings, 'webhook_base_url', 'http://localhost:8000')
        
        # Return public URL
        relative_path = os.path.relpath(dest_path, self.storage_dir).replace('\\', '/')
        return f"{base_url.rstrip('/')}/storage/{relative_path}"
    
    def cleanup_temp_files(self, user_id: str, job_id: str):
        """
        Delete all temp files for a job.
        
        Args:
            user_id: User ID
            job_id: Job ID
        """
        temp_dir = os.path.join(self.storage_dir, 'temp', user_id, job_id)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


# Global storage service instance (lazy initialization)
_storage_service = None

def get_storage_service() -> StorageService:
    """Get or create storage service instance."""
    global _storage_service
    if _storage_service is None:
        _storage_service = StorageService()
    return _storage_service
