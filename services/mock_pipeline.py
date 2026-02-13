"""Mock pipeline for demo users - simulates full dubbing workflow."""
import asyncio
import uuid
from typing import Dict, List, Optional, Callable
from config import DEMO_VIDEO_LIBRARY, DEMO_PIPELINE_TIMING


class MockPipeline:
    """Simulates complete dubbing pipeline with realistic timing."""
    
    async def process_job(
        self,
        job_id: str,
        video_id: str,
        target_languages: List[str],
        user_id: str,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Execute full mock pipeline with progress updates.
        
        Stages:
        1. Transcription (5s) - 0% → 25%
        2. Translation (3s per language) - 25% → 50%
        3. Dubbing (8s per language) - 50% → 75%
        4. Lip Sync (10s per language) - 75% → 100%
        
        Args:
            job_id: Processing job ID
            video_id: Source video ID
            target_languages: List of language codes to generate
            user_id: User ID for permissions check
            progress_callback: Optional callback for progress updates
            
        Returns:
            Dict mapping language codes to results
        """
        print(f"[MOCK_PIPELINE] Starting pipeline for job {job_id}")
        print(f"  Video: {video_id}")
        print(f"  Languages: {', '.join(target_languages)}")
        
        # Find video in library
        video_data = self._find_video(video_id)
        if not video_data:
            raise ValueError(f"Video {video_id} not in demo library")
        
        results = {}
        
        # Stage 1: Transcription
        print(f"[MOCK_PIPELINE] Stage 1/4: Transcribing...")
        await self._update_progress(job_id, 0, "transcribing", progress_callback)
        await asyncio.sleep(DEMO_PIPELINE_TIMING["transcription"])
        transcript = video_data.get("transcript", "This is the transcribed text from the video...")
        await self._update_progress(job_id, 25, "transcribed", progress_callback)
        print(f"[MOCK_PIPELINE] ✓ Transcription complete")
        
        # Process each language
        num_languages = len(target_languages)
        for idx, lang in enumerate(target_languages):
            print(f"[MOCK_PIPELINE] Processing language {idx + 1}/{num_languages}: {lang}")
            
            lang_data = video_data["languages"].get(lang)
            if not lang_data:
                # If language not in library, use placeholder
                print(f"  Warning: {lang} not in library, using placeholder")
                lang_data = self._create_placeholder_result(video_data, lang)
            
            # Stage 2: Translation
            progress = 25 + (idx / num_languages) * 25
            await self._update_progress(job_id, int(progress), f"translating_{lang}", progress_callback)
            await asyncio.sleep(DEMO_PIPELINE_TIMING["translation"])
            translation = lang_data.get("translation", f"[Mock translation for {lang}]")
            print(f"  ✓ Translation complete")
            
            # Stage 3: Dubbing (ElevenLabs mock)
            progress = 50 + (idx / num_languages) * 25
            await self._update_progress(job_id, int(progress), f"dubbing_{lang}", progress_callback)
            await asyncio.sleep(DEMO_PIPELINE_TIMING["dubbing"])
            dubbed_audio = lang_data.get("dubbed_audio_url")
            print(f"  ✓ Dubbing complete")
            
            # Stage 4: Lip Sync (SyncLabs mock)
            progress = 75 + (idx / num_languages) * 25
            await self._update_progress(job_id, int(progress), f"lip_syncing_{lang}", progress_callback)
            await asyncio.sleep(DEMO_PIPELINE_TIMING["lip_sync"])
            dubbed_video = lang_data.get("dubbed_video_url")
            print(f"  ✓ Lip sync complete")
            
            results[lang] = {
                "transcript": transcript,
                "translation": translation,
                "dubbed_audio_url": dubbed_audio,
                "dubbed_video_url": dubbed_video,
                "status": "completed"
            }
        
        await self._update_progress(job_id, 100, "completed", progress_callback)
        print(f"[MOCK_PIPELINE] ✅ Pipeline complete for job {job_id}")
        return results
    
    def _find_video(self, video_id: str) -> Optional[Dict]:
        """Find video in demo library by ID."""
        for video_key, video_data in DEMO_VIDEO_LIBRARY.items():
            if video_data["id"] == video_id:
                return video_data
        return None
    
    async def _update_progress(
        self, 
        job_id: str, 
        progress: int, 
        stage: str, 
        callback: Optional[Callable]
    ):
        """Update job progress in database and call callback."""
        # Call optional callback first
        if callback:
            try:
                await callback(job_id, progress, stage)
            except Exception as e:
                print(f"[MOCK_PIPELINE] Warning: Callback failed: {e}")
        
        # Update database
        try:
            from services.supabase_db import supabase_db
            await supabase_db.update_job_progress(job_id, progress, stage)
        except Exception as e:
            print(f"[MOCK_PIPELINE] Warning: Database update failed: {e}")
    
    def _create_placeholder_result(self, video_data: Dict, lang: str) -> Dict:
        """Create placeholder for language not in library."""
        return {
            "dubbed_video_url": video_data["original_url"],  # Fallback to original
            "dubbed_audio_url": None,
            "translation": f"[Placeholder translation for {lang}]",
            "transcript": video_data.get("transcript", "Original transcript"),
        }


# Global instance
mock_pipeline = MockPipeline()
