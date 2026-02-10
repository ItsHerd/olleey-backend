"""Test script for public URL storage functionality."""
import sys
import os
import tempfile
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.storage import get_storage_service
from config import settings


def test_public_url_generation():
    """Test that public URLs are generated correctly."""
    print("=" * 60)
    print("🧪 Testing Public URL Storage")
    print("=" * 60)
    
    # Get storage service
    storage_service = get_storage_service()
    
    # Create a test file
    test_content = b"This is a test video file"
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as f:
        f.write(test_content)
        test_file_path = f.name
    
    try:
        print("\n1️⃣ Testing upload_and_get_public_url()...")
        
        # Test parameters
        user_id = "test_user_123"
        job_id = "test_job_456"
        filename = "test_video.mp4"
        
        # Upload and get public URL
        public_url = storage_service.upload_and_get_public_url(
            file_path=test_file_path,
            user_id=user_id,
            job_id=job_id,
            filename=filename
        )
        
        print(f"✅ Public URL generated: {public_url}")
        
        # Verify the URL format
        expected_path = f"temp/{user_id}/{job_id}/{filename}"
        if expected_path in public_url:
            print(f"✅ URL contains correct path: {expected_path}")
        else:
            print(f"❌ URL path incorrect. Expected: {expected_path}")
            return False
        
        # Verify base URL
        base_url = getattr(settings, 'webhook_base_url', 'http://localhost:8000')
        if public_url.startswith(base_url):
            print(f"✅ URL uses correct base: {base_url}")
        else:
            print(f"❌ URL base incorrect. Expected to start with: {base_url}")
            return False
        
        # Verify file exists in storage
        storage_dir = getattr(settings, 'local_storage_dir', './storage')
        file_path = os.path.join(storage_dir, 'temp', user_id, job_id, filename)
        if os.path.exists(file_path):
            print(f"✅ File exists in storage: {file_path}")
            
            # Verify content
            with open(file_path, 'rb') as f:
                if f.read() == test_content:
                    print("✅ File content matches original")
                else:
                    print("❌ File content doesn't match")
                    return False
        else:
            print(f"❌ File not found in storage: {file_path}")
            return False
        
        print("\n2️⃣ Testing cleanup_temp_files()...")
        
        # Clean up
        storage_service.cleanup_temp_files(user_id, job_id)
        
        if not os.path.exists(file_path):
            print("✅ Temp files cleaned up successfully")
        else:
            print("❌ Temp files still exist after cleanup")
            return False
        
        print("\n3️⃣ Testing static file serving endpoint...")
        print(f"   To test manually, run:")
        print(f"   1. Start the server: python main.py")
        print(f"   2. Create a test file:")
        print(f"      mkdir -p ./storage/temp/test")
        print(f"      echo 'test' > ./storage/temp/test/file.txt")
        print(f"   3. Access via curl:")
        print(f"      curl {base_url}/storage/temp/test/file.txt")
        
        print("\n" + "=" * 60)
        print("✅ All tests passed!")
        print("=" * 60)
        
        return True
        
    finally:
        # Clean up test file
        if os.path.exists(test_file_path):
            os.unlink(test_file_path)


def test_workflow_example():
    """Show example of how the workflow uses public URLs."""
    print("\n" + "=" * 60)
    print("📋 Example Workflow with Public URLs")
    print("=" * 60)
    
    print("""
    1. Download video from YouTube
       → /tmp/video_abc123.mp4
    
    2. Upload to temp storage and get public URL
       → https://vox.your-tunnel.com/storage/temp/user123/job456/original_video.mp4
    
    3. Generate dubbed audio (ElevenLabs)
       → /tmp/audio_german.mp3
    
    4. Upload audio to temp storage
       → https://vox.your-tunnel.com/storage/temp/user123/job456/audio_german.mp3
    
    5. Send public URLs to Sync Labs
       → Sync Labs downloads from public URLs
       → Processes lip-sync
       → Returns: https://synclabs.so/output/synced_video.mp4
    
    6. Download synced video from Sync Labs
       → /tmp/synced_job456_german.mp4
    
    7. Save to permanent storage
       → ./storage/videos/user123/job456/german/video.mp4
    
    8. Upload to YouTube language channel
    
    9. Cleanup temp files
       → Delete ./storage/temp/user123/job456/
       → Delete /tmp/video_abc123.mp4, /tmp/audio_german.mp3, etc.
    """)


if __name__ == "__main__":
    success = test_public_url_generation()
    test_workflow_example()
    
    if not success:
        sys.exit(1)
