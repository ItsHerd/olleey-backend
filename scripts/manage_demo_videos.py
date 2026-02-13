"""Manage demo video mappings for mock pipeline."""
import asyncio
import sys
import os
import httpx

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DEMO_VIDEO_LIBRARY


async def test_demo_videos():
    """Test all configured demo videos are accessible."""
    print("=" * 60)
    print("TESTING DEMO VIDEO ACCESSIBILITY")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        for video_key, video_data in DEMO_VIDEO_LIBRARY.items():
            print(f"\n📹 {video_data['title']}")
            print(f"   ID: {video_data['id']}")
            
            # Test original video URL
            original_url = video_data.get('original_url')
            if original_url:
                try:
                    response = await client.head(original_url)
                    if response.status_code == 200:
                        print(f"   ✓ Original video accessible: {original_url}")
                    else:
                        print(f"   ⚠ Original video returned {response.status_code}: {original_url}")
                except Exception as e:
                    print(f"   ❌ Original video error: {str(e)}")
            
            # Test language-specific videos
            languages = video_data.get('languages', {})
            for lang_code, lang_data in languages.items():
                print(f"   Language: {lang_code}")
                
                # Test dubbed video
                dubbed_video = lang_data.get('dubbed_video_url')
                if dubbed_video:
                    try:
                        response = await client.head(dubbed_video)
                        if response.status_code == 200:
                            print(f"     ✓ Dubbed video accessible")
                        else:
                            print(f"     ⚠ Dubbed video returned {response.status_code}")
                    except Exception as e:
                        print(f"     ❌ Dubbed video error: {str(e)}")
                
                # Test dubbed audio
                dubbed_audio = lang_data.get('dubbed_audio_url')
                if dubbed_audio:
                    try:
                        response = await client.head(dubbed_audio)
                        if response.status_code == 200:
                            print(f"     ✓ Dubbed audio accessible")
                        else:
                            print(f"     ⚠ Dubbed audio returned {response.status_code}")
                    except Exception as e:
                        print(f"     ❌ Dubbed audio error: {str(e)}")


def list_demo_videos():
    """List all configured demo video pairs."""
    print("=" * 60)
    print("DEMO VIDEO LIBRARY")
    print("=" * 60)
    
    for video_key, video_data in DEMO_VIDEO_LIBRARY.items():
        print(f"\n📹 {video_data['title']}")
        print(f"   Key: {video_key}")
        print(f"   ID: {video_data['id']}")
        print(f"   Duration: {video_data.get('duration', 'N/A')}s")
        print(f"   Original: {video_data.get('original_url', 'N/A')}")
        
        languages = video_data.get('languages', {})
        if languages:
            print(f"   Languages available: {', '.join(languages.keys())}")
            for lang_code, lang_data in languages.items():
                print(f"     • {lang_code}:")
                print(f"       Video: {lang_data.get('dubbed_video_url', 'N/A')}")
                print(f"       Audio: {lang_data.get('dubbed_audio_url', 'N/A')}")
        else:
            print("   ⚠ No languages configured")
    
    print(f"\n{'=' * 60}")
    print(f"Total videos: {len(DEMO_VIDEO_LIBRARY)}")
    total_languages = sum(len(v.get('languages', {})) for v in DEMO_VIDEO_LIBRARY.values())
    print(f"Total language pairs: {total_languages}")


def add_demo_video_instructions():
    """Print instructions for adding a new demo video."""
    print("=" * 60)
    print("HOW TO ADD A NEW DEMO VIDEO")
    print("=" * 60)
    print("""
1. Upload your original video to S3/Supabase Storage
2. Upload dubbed versions (video + audio) for each language
3. Edit config.py and add to DEMO_VIDEO_LIBRARY:

Example:
    "video_002_example": {
        "id": "unique_video_id",
        "title": "Your Video Title",
        "description": "Video description",
        "original_url": "https://your-storage.com/original.mp4",
        "thumbnail": "https://your-storage.com/thumb.jpg",
        "duration": 120,
        "languages": {
            "es": {
                "dubbed_video_url": "https://your-storage.com/es.mov",
                "dubbed_audio_url": "https://your-storage.com/es-audio.mp3",
                "transcript": "Original transcript...",
                "translation": "Spanish translation...",
            },
            "fr": {
                "dubbed_video_url": "https://your-storage.com/fr.mov",
                "dubbed_audio_url": "https://your-storage.com/fr-audio.mp3",
                "transcript": "Original transcript...",
                "translation": "French translation...",
            },
        }
    }

4. Test the new video:
   python scripts/manage_demo_videos.py --test

5. Restart the backend server to load new configuration
""")


async def main():
    """Main CLI interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Manage demo video library")
    parser.add_argument('--list', action='store_true', help='List all demo videos')
    parser.add_argument('--test', action='store_true', help='Test video accessibility')
    parser.add_argument('--add-help', action='store_true', help='Show instructions for adding videos')
    
    args = parser.parse_args()
    
    if args.list:
        list_demo_videos()
    elif args.test:
        await test_demo_videos()
    elif args.add_help:
        add_demo_video_instructions()
    else:
        # Default: show all info
        list_demo_videos()
        print()
        add_demo_video_instructions()


if __name__ == "__main__":
    asyncio.run(main())
