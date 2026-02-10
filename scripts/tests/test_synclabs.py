"""Quick test script for Sync Labs integration."""
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.synclabs import process_lip_sync, validate_urls


async def test_sync_labs():
    """Test Sync Labs with example URLs."""
    print("=" * 60)
    print("🧪 Testing Sync Labs Integration")
    print("=" * 60)
    
    # Example URLs from Sync Labs documentation
    video_url = "https://assets.sync.so/docs/example-video.mp4"
    audio_url = "https://assets.sync.so/docs/example-audio.wav"
    
    print("\n1️⃣ Testing URL validation...")
    validation = await validate_urls(video_url, audio_url)
    
    if validation["valid"]:
        print("✅ URLs are accessible")
    else:
        print("❌ URL validation failed:")
        for error in validation["errors"]:
            print(f"  - {error}")
        return
    
    print("\n2️⃣ Testing lip-sync generation...")
    print(f"  Video: {video_url}")
    print(f"  Audio: {audio_url}")
    
    try:
        result = await process_lip_sync(
            video_url=video_url,
            audio_url=audio_url,
            sync_mode="loop",
            model="lipsync-2"
        )
        
        print("\n✅ Lip-sync generation successful!")
        print(f"  Generation ID: {result['id']}")
        print(f"  Status: {result['status']}")
        print(f"  Video URL: {result['url']}")
        print(f"  Model: {result['model']}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return
    
    print("\n" + "=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_sync_labs())
