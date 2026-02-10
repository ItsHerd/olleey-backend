"""
Test script for S3 storage integration.
Tests S3 connectivity, upload, download, and URL generation.
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.s3_storage import S3StorageService, S3_AVAILABLE
from services.storage_factory import get_storage_service
from config import settings


async def test_s3_connection():
    """Test basic S3 connectivity."""
    print("=" * 60)
    print("Testing S3 Connection")
    print("=" * 60)
    
    if not S3_AVAILABLE:
        print("❌ boto3 not installed. Install with: pip install boto3")
        return False
    
    try:
        storage = S3StorageService(
            bucket_name=settings.aws_s3_bucket,
            region=settings.aws_region
        )
        
        # Test bucket access
        storage.s3_client.head_bucket(Bucket=storage.bucket_name)
        print(f"✅ Successfully connected to S3 bucket: {storage.bucket_name}")
        print(f"   Region: {storage.region}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to S3: {e}")
        return False


async def test_upload_download():
    """Test file upload and download."""
    print("\n" + "=" * 60)
    print("Testing Upload & Download")
    print("=" * 60)
    
    try:
        storage = get_storage_service()
        
        # Create a test file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Test content for S3 upload")
            test_file = f.name
        
        print(f"Created test file: {test_file}")
        
        # Upload file
        print("Uploading file to S3...")
        s3_key = await storage.upload_file(
            file_path=test_file,
            user_id="test_user",
            job_id="test_job",
            language_code="en",
            filename="test.txt"
        )
        print(f"✅ Uploaded file to: {s3_key}")
        
        # Get URL
        print("Generating presigned URL...")
        url = await storage.get_storage_url(s3_key)
        print(f"✅ Generated URL: {url[:80]}...")
        
        # Download file
        print("Downloading file from S3...")
        download_path = tempfile.mktemp(suffix='.txt')
        if hasattr(storage, 'download_file'):
            downloaded = await storage.download_file(s3_key, download_path)
            print(f"✅ Downloaded file to: {downloaded}")
            
            # Verify content
            with open(downloaded, 'r') as f:
                content = f.read()
                if content == "Test content for S3 upload":
                    print("✅ File content verified!")
                else:
                    print("⚠️  File content mismatch")
            
            os.unlink(downloaded)
        else:
            print("ℹ️  Download not available for local storage")
        
        # Cleanup
        print("Cleaning up test file...")
        await storage.delete_video(s3_key)
        os.unlink(test_file)
        print("✅ Cleanup complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_video_operations():
    """Test video-specific operations."""
    print("\n" + "=" * 60)
    print("Testing Video Operations")
    print("=" * 60)
    
    try:
        storage = get_storage_service()
        
        # Create a fake video file
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.mp4', delete=False) as f:
            f.write(b"FAKE_VIDEO_DATA_FOR_TESTING")
            test_video = f.name
        
        print(f"Created test video: {test_video}")
        
        # Upload video
        print("Uploading video...")
        s3_key = await storage.upload_video(
            file_path=test_video,
            user_id="test_user",
            job_id="test_job",
            language_code="es",
            video_id="test_video_123"
        )
        print(f"✅ Uploaded video to: {s3_key}")
        
        # Test upload from bytes
        print("Testing upload from bytes...")
        video_bytes = b"FAKE_VIDEO_BYTES"
        s3_key_bytes = await storage.upload_video_from_bytes(
            video_data=video_bytes,
            user_id="test_user",
            job_id="test_job",
            language_code="fr",
            video_id="test_video_456"
        )
        print(f"✅ Uploaded video from bytes to: {s3_key_bytes}")
        
        # Get video URL
        video_url = await storage.get_video_url(
            user_id="test_user",
            job_id="test_job",
            language_code="es",
            video_id="test_video_123"
        )
        print(f"✅ Video URL: {video_url}")
        
        # Cleanup
        print("Cleaning up...")
        await storage.delete_video(s3_key)
        await storage.delete_video(s3_key_bytes)
        os.unlink(test_video)
        print("✅ Cleanup complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_storage_factory():
    """Test storage factory switching between local and S3."""
    print("\n" + "=" * 60)
    print("Testing Storage Factory")
    print("=" * 60)
    
    storage_type = getattr(settings, 'storage_type', 'local')
    print(f"Current storage type: {storage_type}")
    
    storage = get_storage_service()
    storage_class = type(storage).__name__
    print(f"Storage service class: {storage_class}")
    
    if storage_type == 's3':
        expected = 'S3StorageService'
    else:
        expected = 'StorageService'
    
    if expected in storage_class:
        print(f"✅ Correct storage service loaded: {storage_class}")
        return True
    else:
        print(f"⚠️  Expected {expected}, got {storage_class}")
        return False


def print_configuration():
    """Print current S3 configuration."""
    print("\n" + "=" * 60)
    print("Current Configuration")
    print("=" * 60)
    print(f"Storage Type: {getattr(settings, 'storage_type', 'local')}")
    print(f"S3 Bucket: {getattr(settings, 'aws_s3_bucket', 'Not configured')}")
    print(f"AWS Region: {getattr(settings, 'aws_region', 'Not configured')}")
    print(f"Access Key: {'*' * 16 if getattr(settings, 'aws_access_key_id', None) else 'Not configured'}")
    print(f"Presigned URL Expiry: {getattr(settings, 's3_presigned_url_expiry', 3600)}s")
    print(f"CloudFront URL: {getattr(settings, 'cloudfront_url', 'Not configured')}")
    print("=" * 60)


async def main():
    """Run all tests."""
    print("\n🚀 S3 Storage Integration Test Suite\n")
    
    print_configuration()
    
    # Check if S3 is configured
    storage_type = getattr(settings, 'storage_type', 'local')
    if storage_type != 's3':
        print("\n⚠️  STORAGE_TYPE is not set to 's3'")
        print("   To test S3, set STORAGE_TYPE=s3 in your .env file")
        print("   Currently using local storage for testing...\n")
    
    results = []
    
    # Test storage factory
    results.append(("Storage Factory", await test_storage_factory()))
    
    if storage_type == 's3':
        # Run S3-specific tests
        results.append(("S3 Connection", await test_s3_connection()))
        results.append(("Upload & Download", await test_upload_download()))
        results.append(("Video Operations", await test_video_operations()))
    else:
        # Run local storage tests
        print("\nRunning basic storage tests with local storage...")
        results.append(("Upload & Download", await test_upload_download()))
        results.append(("Video Operations", await test_video_operations()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    
    print(f"\nTotal: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
