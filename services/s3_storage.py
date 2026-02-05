"""AWS S3 storage service for video file storage."""
import os
import uuid
import logging
from typing import Optional
from pathlib import Path
import tempfile

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError
    from botocore.config import Config
    S3_AVAILABLE = True
except ImportError:
    S3_AVAILABLE = False

from config import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """Service for AWS S3 storage operations."""
    
    def __init__(
        self,
        bucket_name: Optional[str] = None,
        region: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        presigned_url_expiry: int = 3600
    ):
        """
        Initialize S3 storage service.
        
        Args:
            bucket_name: S3 bucket name
            region: AWS region
            access_key: AWS access key (optional, uses boto3 defaults if not provided)
            secret_key: AWS secret key (optional, uses boto3 defaults if not provided)
            presigned_url_expiry: Presigned URL expiry in seconds (default: 1 hour)
        """
        if not S3_AVAILABLE:
            raise ImportError("boto3 is not installed. Install with: pip install boto3")
        
        self.bucket_name = bucket_name or getattr(settings, 'aws_s3_bucket', None)
        self.region = region or getattr(settings, 'aws_region', 'us-east-1')
        self.presigned_url_expiry = presigned_url_expiry or getattr(
            settings, 's3_presigned_url_expiry', 3600
        )
        
        if not self.bucket_name:
            raise ValueError("S3 bucket name must be provided")
        
        # Configure boto3 client
        config = Config(
            region_name=self.region,
            signature_version='s3v4',
            retries={'max_attempts': 3, 'mode': 'standard'}
        )
        
        # Initialize S3 client
        if access_key and secret_key:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                config=config
            )
        else:
            # Use default credentials (from ~/.aws/credentials or IAM role)
            self.s3_client = boto3.client('s3', config=config)
        
        logger.info(f"S3StorageService initialized with bucket: {self.bucket_name}")
    
    def _build_s3_key(self, user_id: str, job_id: str, language_code: str, filename: str) -> str:
        """
        Build S3 object key (path).
        
        Returns:
            str: S3 key like 'videos/user123/job456/es/video.mp4'
        """
        return f"videos/{user_id}/{job_id}/{language_code}/{filename}"
    
    async def upload_file(
        self,
        file_path: str,
        user_id: str,
        job_id: str,
        language_code: str,
        filename: Optional[str] = None
    ) -> str:
        """
        Upload file to S3.
        
        Args:
            file_path: Local path to file
            user_id: User ID
            job_id: Processing job ID
            language_code: Language code
            filename: Storage filename (if None, uses original filename)
            
        Returns:
            str: S3 key (path) of uploaded file
            
        Raises:
            Exception: If upload fails
        """
        if not filename:
            filename = os.path.basename(file_path)
        
        s3_key = self._build_s3_key(user_id, job_id, language_code, filename)
        
        try:
            # Determine content type
            content_type = self._get_content_type(filename)
            
            # Upload file
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            logger.info(f"Uploaded file to S3: {s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise Exception(f"S3 upload failed: {str(e)}")
        except NoCredentialsError:
            logger.error("AWS credentials not found")
            raise Exception("AWS credentials not configured")
    
    async def upload_video(
        self,
        file_path: str,
        user_id: str,
        job_id: str,
        language_code: str,
        video_id: Optional[str] = None
    ) -> str:
        """
        Upload video to S3.
        
        Args:
            file_path: Local path to video file
            user_id: User ID
            job_id: Processing job ID
            language_code: Language code
            video_id: Optional video ID (for naming)
            
        Returns:
            str: S3 key of uploaded video
        """
        filename = f"{video_id or uuid.uuid4()}.mp4"
        return await self.upload_file(file_path, user_id, job_id, language_code, filename)
    
    async def upload_video_from_bytes(
        self,
        video_data: bytes,
        user_id: str,
        job_id: str,
        language_code: str,
        video_id: Optional[str] = None
    ) -> str:
        """
        Upload video from bytes to S3.
        
        Args:
            video_data: Video file bytes
            user_id: User ID
            job_id: Processing job ID
            language_code: Language code
            video_id: Optional video ID (for naming)
            
        Returns:
            str: S3 key of uploaded video
        """
        filename = f"{video_id or uuid.uuid4()}.mp4"
        s3_key = self._build_s3_key(user_id, job_id, language_code, filename)
        
        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=s3_key,
                Body=video_data,
                ContentType='video/mp4',
                ServerSideEncryption='AES256'
            )
            
            logger.info(f"Uploaded video from bytes to S3: {s3_key}")
            return s3_key
            
        except ClientError as e:
            logger.error(f"Failed to upload video bytes to S3: {e}")
            raise Exception(f"S3 upload failed: {str(e)}")
    
    async def get_video_path(self, s3_key: str) -> Optional[str]:
        """
        Check if video exists in S3.
        
        Args:
            s3_key: S3 object key
            
        Returns:
            str: S3 key if exists, None otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return s3_key
        except ClientError:
            return None
    
    async def delete_video(self, s3_key: str):
        """
        Delete video from S3.
        
        Args:
            s3_key: S3 object key
        """
        try:
            self.s3_client.delete_object(Bucket=self.bucket_name, Key=s3_key)
            logger.info(f"Deleted video from S3: {s3_key}")
        except ClientError as e:
            logger.error(f"Failed to delete video from S3: {e}")
            raise Exception(f"S3 delete failed: {str(e)}")
    
    async def get_video_url(
        self,
        user_id: str,
        job_id: str,
        language_code: str,
        video_id: str
    ) -> Optional[str]:
        """
        Get S3 key for video.
        
        Args:
            user_id: User ID
            job_id: Processing job ID
            language_code: Language code
            video_id: Video ID
            
        Returns:
            str: S3 key if exists, None otherwise
        """
        s3_key = self._build_s3_key(user_id, job_id, language_code, f"{video_id}.mp4")
        return await self.get_video_path(s3_key)
    
    async def get_storage_url(
        self,
        s3_key: str,
        base_url: Optional[str] = None
    ) -> str:
        """
        Get presigned URL for accessing stored video.
        
        Args:
            s3_key: S3 object key
            base_url: Optional CloudFront/CDN URL (if provided, uses that instead of S3)
            
        Returns:
            str: Presigned URL or CloudFront URL
        """
        if base_url:
            # Use CloudFront or custom CDN
            return f"{base_url.rstrip('/')}/{s3_key}"
        
        try:
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': s3_key
                },
                ExpiresIn=self.presigned_url_expiry
            )
            return url
        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            raise Exception(f"Failed to generate URL: {str(e)}")
    
    async def upload_and_get_public_url(
        self,
        file_path: str,
        user_id: str,
        job_id: str,
        filename: str
    ) -> str:
        """
        Upload file to temp location and return public URL.
        
        Args:
            file_path: Local path to file
            user_id: User ID
            job_id: Job ID
            filename: Desired filename
        
        Returns:
            str: Presigned URL accessible from internet
        """
        # Upload to temp directory in S3
        s3_key = f"temp/{user_id}/{job_id}/{filename}"
        
        try:
            content_type = self._get_content_type(filename)
            self.s3_client.upload_file(
                file_path,
                self.bucket_name,
                s3_key,
                ExtraArgs={
                    'ContentType': content_type,
                    'ServerSideEncryption': 'AES256'
                }
            )
            
            # Generate presigned URL
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket_name, 'Key': s3_key},
                ExpiresIn=self.presigned_url_expiry
            )
            
            logger.info(f"Uploaded temp file to S3 and generated URL: {s3_key}")
            return url
            
        except ClientError as e:
            logger.error(f"Failed to upload temp file: {e}")
            raise Exception(f"S3 upload failed: {str(e)}")
    
    async def cleanup_temp_files(self, user_id: str, job_id: str):
        """
        Delete all temp files for a job.
        
        Args:
            user_id: User ID
            job_id: Job ID
        """
        prefix = f"temp/{user_id}/{job_id}/"
        
        try:
            # List objects with prefix
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' not in response:
                return
            
            # Delete all objects
            objects = [{'Key': obj['Key']} for obj in response['Contents']]
            self.s3_client.delete_objects(
                Bucket=self.bucket_name,
                Delete={'Objects': objects}
            )
            
            logger.info(f"Cleaned up {len(objects)} temp files for job {job_id}")
            
        except ClientError as e:
            logger.error(f"Failed to cleanup temp files: {e}")
    
    async def download_file(self, s3_key: str, local_path: str) -> str:
        """
        Download file from S3 to local path.
        
        Args:
            s3_key: S3 object key
            local_path: Local destination path
            
        Returns:
            str: Local file path
        """
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            # Download file
            self.s3_client.download_file(self.bucket_name, s3_key, local_path)
            logger.info(f"Downloaded file from S3: {s3_key} -> {local_path}")
            return local_path
            
        except ClientError as e:
            logger.error(f"Failed to download file from S3: {e}")
            raise Exception(f"S3 download failed: {str(e)}")
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type based on file extension."""
        ext = Path(filename).suffix.lower()
        content_types = {
            '.mp4': 'video/mp4',
            '.webm': 'video/webm',
            '.mp3': 'audio/mpeg',
            '.m4a': 'audio/mp4',
            '.wav': 'audio/wav',
            '.json': 'application/json',
            '.txt': 'text/plain',
        }
        return content_types.get(ext, 'application/octet-stream')


# Global S3 storage service instance (lazy initialization)
_s3_storage_service = None

def get_s3_storage_service() -> S3StorageService:
    """Get or create S3 storage service instance."""
    global _s3_storage_service
    if _s3_storage_service is None:
        _s3_storage_service = S3StorageService(
            bucket_name=getattr(settings, 'aws_s3_bucket', None),
            region=getattr(settings, 'aws_region', 'us-east-1'),
            access_key=getattr(settings, 'aws_access_key_id', None),
            secret_key=getattr(settings, 'aws_secret_access_key', None),
            presigned_url_expiry=getattr(settings, 's3_presigned_url_expiry', 3600)
        )
    return _s3_storage_service
