"""Pipeline tracking service - stores detailed data in tracking tables."""
from typing import Dict, Optional, Any
from services.supabase_db import supabase_service
from services.cost_tracking import get_cost_tracker


class PipelineTracker:
    """Track dubbing pipeline progress in detail tables."""

    def __init__(self, job_id: str, user_id: str, video_id: str):
        """Initialize tracker for a specific job."""
        self.job_id = job_id
        self.user_id = user_id
        self.video_id = video_id

    def track_transcript(
        self,
        transcript_text: str,
        language_code: str,
        provider: str = "elevenlabs",
        word_timestamps: Optional[list] = None,
        confidence_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """Store transcript in database."""
        print(f"[PIPELINE_TRACKER] Storing transcript for job {self.job_id}")

        transcript_data = {
            'job_id': self.job_id,
            'video_id': self.video_id,
            'user_id': self.user_id,
            'language_code': language_code,
            'transcript_text': transcript_text,
            'word_timestamps': word_timestamps or [],
            'provider': provider,
            'confidence_score': confidence_score,
            'status': 'completed'
        }

        try:
            result = supabase_service.create_transcript(transcript_data)
            print(f"[PIPELINE_TRACKER] ✓ Transcript stored: {result.get('id')}")
            return result
        except Exception as e:
            print(f"[PIPELINE_TRACKER] ✗ Failed to store transcript: {e}")
            return {}

    def track_translation(
        self,
        source_language: str,
        target_language: str,
        translated_text: str,
        transcript_id: Optional[str] = None,
        provider: str = "elevenlabs",
        word_timestamps: Optional[list] = None,
        confidence_score: Optional[float] = None
    ) -> Dict[str, Any]:
        """Store translation in database."""
        print(f"[PIPELINE_TRACKER] Storing translation {target_language} for job {self.job_id}")

        translation_data = {
            'transcript_id': transcript_id,
            'job_id': self.job_id,
            'video_id': self.video_id,
            'user_id': self.user_id,
            'source_language': source_language,
            'target_language': target_language,
            'translated_text': translated_text,
            'word_timestamps': word_timestamps or [],
            'provider': provider,
            'confidence_score': confidence_score,
            'status': 'completed',
            'reviewed': False
        }

        try:
            result = supabase_service.create_translation(translation_data)
            print(f"[PIPELINE_TRACKER] ✓ Translation stored: {result.get('id')}")
            return result
        except Exception as e:
            print(f"[PIPELINE_TRACKER] ✗ Failed to store translation: {e}")
            return {}

    def track_dubbed_audio(
        self,
        language_code: str,
        audio_url: str,
        translation_id: Optional[str] = None,
        provider: str = "elevenlabs",
        duration: Optional[int] = None,
        voice_id: Optional[str] = None,
        voice_name: Optional[str] = None,
        voice_settings: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Store dubbed audio record in database."""
        print(f"[PIPELINE_TRACKER] Storing dubbed audio {language_code} for job {self.job_id}")

        audio_data = {
            'translation_id': translation_id,
            'job_id': self.job_id,
            'language_code': language_code,
            'user_id': self.user_id,
            'audio_url': audio_url,
            'duration': duration,
            'provider': provider,
            'voice_id': voice_id,
            'voice_name': voice_name,
            'voice_settings': voice_settings or {},
            'format': 'mp3',  # Default format
            'status': 'completed'
        }

        try:
            result = supabase_service.create_dubbed_audio(audio_data)
            print(f"[PIPELINE_TRACKER] ✓ Dubbed audio stored: {result.get('id')}")
            return result
        except Exception as e:
            print(f"[PIPELINE_TRACKER] ✗ Failed to store dubbed audio: {e}")
            return {}

    def track_lip_sync_job(
        self,
        language_code: str,
        input_video_url: str,
        input_audio_url: str,
        synclabs_job_id: Optional[str] = None,
        dubbed_audio_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create lip sync job record."""
        print(f"[PIPELINE_TRACKER] Creating lip sync job {language_code} for job {self.job_id}")

        lipsync_data = {
            'job_id': self.job_id,
            'dubbed_audio_id': dubbed_audio_id,
            'language_code': language_code,
            'user_id': self.user_id,
            'synclabs_job_id': synclabs_job_id,
            'status': 'pending',
            'progress': 0,
            'input_video_url': input_video_url,
            'input_audio_url': input_audio_url
        }

        try:
            result = supabase_service.create_lip_sync_job(lipsync_data)
            print(f"[PIPELINE_TRACKER] ✓ Lip sync job created: {result.get('id')}")
            return result
        except Exception as e:
            print(f"[PIPELINE_TRACKER] ✗ Failed to create lip sync job: {e}")
            return {}

    def update_lip_sync_job(
        self,
        lipsync_id: str,
        status: Optional[str] = None,
        progress: Optional[int] = None,
        output_video_url: Optional[str] = None,
        quality_score: Optional[float] = None,
        processing_time_seconds: Optional[int] = None,
        cost: Optional[float] = None
    ) -> Dict[str, Any]:
        """Update lip sync job with progress/completion."""
        updates = {}

        if status:
            updates['status'] = status
        if progress is not None:
            updates['progress'] = progress
        if output_video_url:
            updates['output_video_url'] = output_video_url
        if quality_score is not None:
            updates['quality_score'] = quality_score
        if processing_time_seconds is not None:
            updates['processing_time_seconds'] = processing_time_seconds
        if cost is not None:
            updates['cost'] = cost

        if status == 'completed':
            from datetime import datetime, timezone
            updates['completed_at'] = datetime.now(timezone.utc).isoformat()

        try:
            result = supabase_service.update_lip_sync_job(lipsync_id, updates)
            print(f"[PIPELINE_TRACKER] ✓ Lip sync job updated")
            return result
        except Exception as e:
            print(f"[PIPELINE_TRACKER] ✗ Failed to update lip sync job: {e}")
            return {}

    def update_job_with_cost(
        self,
        video_duration_minutes: float,
        num_languages: int
    ) -> None:
        """Update job with cost estimate."""
        try:
            cost_tracker = get_cost_tracker(self.user_id)
            cost_estimate = cost_tracker.calculate_dubbing_cost(
                video_duration_minutes=video_duration_minutes,
                num_languages=num_languages,
                include_lipsync=True
            )

            print(f"[PIPELINE_TRACKER] Estimated cost: ${cost_estimate['total']}")

            supabase_service.update_processing_job(self.job_id, {
                'estimated_cost': cost_estimate['total'],
                'cost_breakdown': cost_estimate
            })
        except Exception as e:
            print(f"[PIPELINE_TRACKER] Warning: Could not update cost: {e}")

    def update_job_stage(self, stage: str, progress: Optional[int] = None) -> None:
        """Update current pipeline stage."""
        updates = {'current_stage': stage}
        if progress is not None:
            updates['progress'] = progress

        try:
            supabase_service.update_processing_job(self.job_id, updates)
            print(f"[PIPELINE_TRACKER] Stage updated: {stage} ({progress}%)")
        except Exception as e:
            print(f"[PIPELINE_TRACKER] Warning: Could not update stage: {e}")
