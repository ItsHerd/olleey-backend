"""Mock ElevenLabs Dubbing API for demo users."""
import asyncio
import uuid
from typing import Dict, List, Optional


async def mock_dubbing_api(
    video_url: str,
    source_language: str,
    target_languages: List[str],
    user_id: Optional[str] = None
) -> Dict:
    """
    Mock ElevenLabs Dubbing API.
    
    This simulates the ElevenLabs dubbing API which handles transcription,
    translation, and dubbed audio generation in one call.
    
    Args:
        video_url: URL to the source video
        source_language: Source language code (e.g., 'en')
        target_languages: List of target language codes
        user_id: User ID for demo check
        
    Returns:
        Dict containing job_id, status, and results per language
        
    Raises:
        ValueError: If not demo user or video not found
    """
    from services.demo_simulator import demo_simulator
    
    if not user_id or not demo_simulator.is_demo_user(user_id):
        raise ValueError("Mock dubbing only available for demo user")
    
    job_id = f"mock_elevenlabs_{uuid.uuid4().hex[:8]}"
    
    print(f"[MOCK_ELEVENLABS] Starting dubbing job {job_id}")
    print(f"  Video: {video_url}")
    print(f"  Source: {source_language}")
    print(f"  Targets: {', '.join(target_languages)}")
    
    # Simulate API delay (3s per language)
    delay = 3 * len(target_languages)
    print(f"[MOCK_ELEVENLABS] Simulating {delay}s processing...")
    await asyncio.sleep(delay)
    
    # Look up in demo library
    from config import DEMO_VIDEO_LIBRARY
    results = {}
    
    for video_data in DEMO_VIDEO_LIBRARY.values():
        if video_url in video_data.get("original_url", ""):
            for lang in target_languages:
                lang_data = video_data["languages"].get(lang, {})
                results[lang] = {
                    "audio_url": lang_data.get("dubbed_audio_url"),
                    "transcript": lang_data.get("transcript", ""),
                    "translation": lang_data.get("translation", "")
                }
            break
    
    if not results:
        # Fallback if video not in library
        for lang in target_languages:
            results[lang] = {
                "audio_url": None,
                "transcript": "Mock transcript",
                "translation": f"Mock translation for {lang}"
            }
    
    print(f"[MOCK_ELEVENLABS] ✅ Dubbing complete: {len(results)} languages")
    
    return {
        "job_id": job_id,
        "status": "completed",
        "results": results
    }
