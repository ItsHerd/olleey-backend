"""Cost tracking service for dubbing pipeline operations."""
from typing import Dict, Optional
from datetime import datetime


class CostTracker:
    """Track and estimate costs for video processing operations."""

    # Cost per minute (USD) - adjust these based on actual API pricing
    COSTS = {
        "elevenlabs_dubbing": 0.10,  # $0.10 per minute of video
        "synclabs_lipsync": 0.15,     # $0.15 per minute of video
        "storage_per_gb": 0.023,       # $0.023 per GB/month (S3 standard)
        "transcription": 0.006,        # $0.006 per minute
        "translation": 0.05,           # $0.05 per 1000 characters
    }

    def calculate_dubbing_cost(
        self,
        video_duration_minutes: float,
        num_languages: int,
        include_lipsync: bool = True
    ) -> Dict:
        """
        Calculate estimated cost for dubbing job.

        Args:
            video_duration_minutes: Video duration in minutes
            num_languages: Number of target languages
            include_lipsync: Whether to include lip sync cost

        Returns:
            Dict with cost breakdown
        """
        costs = {}

        # ElevenLabs dubbing cost (per language)
        dubbing_cost = self.COSTS["elevenlabs_dubbing"] * video_duration_minutes * num_languages
        costs["dubbing"] = round(dubbing_cost, 2)

        # Lip sync cost (per language)
        if include_lipsync:
            lipsync_cost = self.COSTS["synclabs_lipsync"] * video_duration_minutes * num_languages
            costs["lipsync"] = round(lipsync_cost, 2)
        else:
            costs["lipsync"] = 0.0

        # Total estimated cost
        total = costs["dubbing"] + costs["lipsync"]
        costs["total"] = round(total, 2)
        costs["per_language"] = round(total / num_languages, 2) if num_languages > 0 else 0

        return costs

    def estimate_storage_cost(self, file_size_gb: float, months: int = 1) -> float:
        """
        Estimate storage cost.

        Args:
            file_size_gb: File size in GB
            months: Number of months to store

        Returns:
            Estimated cost in USD
        """
        cost = self.COSTS["storage_per_gb"] * file_size_gb * months
        return round(cost, 4)

    def create_cost_record(
        self,
        job_id: str,
        video_duration_minutes: float,
        num_languages: int,
        actual_cost: Optional[float] = None
    ) -> Dict:
        """
        Create a cost record for a job.

        Args:
            job_id: Processing job ID
            video_duration_minutes: Video duration
            num_languages: Number of languages processed
            actual_cost: Actual cost if known (from API responses)

        Returns:
            Cost record dict
        """
        estimated_costs = self.calculate_dubbing_cost(
            video_duration_minutes,
            num_languages,
            include_lipsync=True
        )

        return {
            "job_id": job_id,
            "estimated_cost": estimated_costs["total"],
            "actual_cost": actual_cost if actual_cost is not None else estimated_costs["total"],
            "breakdown": estimated_costs,
            "video_duration_minutes": video_duration_minutes,
            "num_languages": num_languages,
            "created_at": datetime.utcnow().isoformat()
        }

    def get_monthly_cost_summary(self, job_records: list) -> Dict:
        """
        Calculate monthly cost summary from job records.

        Args:
            job_records: List of job cost records

        Returns:
            Summary dict with totals and averages
        """
        if not job_records:
            return {
                "total_cost": 0,
                "total_jobs": 0,
                "avg_cost_per_job": 0,
                "total_languages": 0
            }

        total_cost = sum(record.get("actual_cost", 0) for record in job_records)
        total_languages = sum(record.get("num_languages", 0) for record in job_records)

        return {
            "total_cost": round(total_cost, 2),
            "total_jobs": len(job_records),
            "avg_cost_per_job": round(total_cost / len(job_records), 2),
            "total_languages": total_languages,
            "avg_cost_per_language": round(total_cost / total_languages, 2) if total_languages > 0 else 0
        }


# Global instance
cost_tracker = CostTracker()


# Mock implementation for demo users
class MockCostTracker(CostTracker):
    """Mock cost tracker that returns zero costs for demo users."""

    def calculate_dubbing_cost(
        self,
        video_duration_minutes: float,
        num_languages: int,
        include_lipsync: bool = True
    ) -> Dict:
        """Return zero costs for demo users."""
        return {
            "dubbing": 0.0,
            "lipsync": 0.0,
            "total": 0.0,
            "per_language": 0.0,
            "is_demo": True
        }

    def create_cost_record(
        self,
        job_id: str,
        video_duration_minutes: float,
        num_languages: int,
        actual_cost: Optional[float] = None
    ) -> Dict:
        """Create demo cost record."""
        return {
            "job_id": job_id,
            "estimated_cost": 0.0,
            "actual_cost": 0.0,
            "breakdown": self.calculate_dubbing_cost(video_duration_minutes, num_languages),
            "video_duration_minutes": video_duration_minutes,
            "num_languages": num_languages,
            "created_at": datetime.utcnow().isoformat(),
            "is_demo": True
        }


# Factory function to get appropriate cost tracker
def get_cost_tracker(user_id: Optional[str] = None) -> CostTracker:
    """
    Get cost tracker instance based on user type.

    Args:
        user_id: User ID to check if demo user

    Returns:
        CostTracker or MockCostTracker instance
    """
    if user_id:
        from services.demo_simulator import demo_simulator
        if demo_simulator.is_demo_user(user_id):
            return MockCostTracker()

    return cost_tracker
