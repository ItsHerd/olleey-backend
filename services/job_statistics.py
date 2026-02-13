"""Job statistics and monitoring service."""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict


class JobStatistics:
    """Calculate statistics and metrics for processing jobs."""

    def calculate_job_metrics(self, jobs: List[Dict]) -> Dict:
        """
        Calculate comprehensive job metrics.

        Args:
            jobs: List of processing job records

        Returns:
            Dict with various metrics and statistics
        """
        if not jobs:
            return {
                "total_jobs": 0,
                "by_status": {},
                "success_rate": 0,
                "avg_processing_time_minutes": 0,
                "total_languages_processed": 0
            }

        # Status breakdown
        status_counts = defaultdict(int)
        for job in jobs:
            status = job.get("status", "unknown")
            status_counts[status] += 1

        # Success rate
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        total_finished = completed + failed
        success_rate = (completed / total_finished * 100) if total_finished > 0 else 0

        # Processing time analysis
        processing_times = []
        for job in jobs:
            if job.get("completed_at") and job.get("created_at"):
                try:
                    created = datetime.fromisoformat(job["created_at"])
                    completed_time = datetime.fromisoformat(job["completed_at"])
                    duration = (completed_time - created).total_seconds() / 60
                    processing_times.append(duration)
                except (ValueError, TypeError):
                    pass

        avg_time = sum(processing_times) / len(processing_times) if processing_times else 0

        # Language stats
        total_languages = sum(
            len(job.get("target_languages", [])) for job in jobs
        )

        return {
            "total_jobs": len(jobs),
            "by_status": dict(status_counts),
            "success_rate": round(success_rate, 2),
            "avg_processing_time_minutes": round(avg_time, 2),
            "total_languages_processed": total_languages,
            "fastest_job_minutes": round(min(processing_times), 2) if processing_times else 0,
            "slowest_job_minutes": round(max(processing_times), 2) if processing_times else 0
        }

    def get_recent_activity(self, jobs: List[Dict], days: int = 7) -> Dict:
        """
        Get activity metrics for recent period.

        Args:
            jobs: List of all jobs
            days: Number of days to analyze

        Returns:
            Dict with recent activity metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        recent_jobs = []
        for job in jobs:
            try:
                created = datetime.fromisoformat(job.get("created_at", ""))
                if created >= cutoff_date:
                    recent_jobs.append(job)
            except (ValueError, TypeError):
                pass

        metrics = self.calculate_job_metrics(recent_jobs)
        metrics["period_days"] = days

        # Daily breakdown
        daily_counts = defaultdict(int)
        for job in recent_jobs:
            try:
                created = datetime.fromisoformat(job["created_at"])
                date_key = created.strftime("%Y-%m-%d")
                daily_counts[date_key] += 1
            except (ValueError, TypeError, KeyError):
                pass

        metrics["daily_breakdown"] = dict(daily_counts)

        return metrics

    def get_error_summary(self, jobs: List[Dict]) -> Dict:
        """
        Analyze failed jobs and common errors.

        Args:
            jobs: List of all jobs

        Returns:
            Dict with error analysis
        """
        failed_jobs = [job for job in jobs if job.get("status") == "failed"]

        if not failed_jobs:
            return {
                "total_failures": 0,
                "common_errors": [],
                "failure_rate": 0
            }

        # Categorize errors
        error_messages = defaultdict(int)
        for job in failed_jobs:
            error = job.get("error_message", "Unknown error")
            # Simplify error message for grouping
            simplified = error.split(":")[0] if ":" in error else error
            error_messages[simplified] += 1

        # Sort by frequency
        common_errors = sorted(
            [{"error": err, "count": count} for err, count in error_messages.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:5]  # Top 5 errors

        failure_rate = (len(failed_jobs) / len(jobs) * 100) if jobs else 0

        return {
            "total_failures": len(failed_jobs),
            "common_errors": common_errors,
            "failure_rate": round(failure_rate, 2)
        }

    def get_language_popularity(self, jobs: List[Dict]) -> Dict:
        """
        Analyze which languages are most commonly requested.

        Args:
            jobs: List of all jobs

        Returns:
            Dict with language statistics
        """
        language_counts = defaultdict(int)

        for job in jobs:
            for lang in job.get("target_languages", []):
                language_counts[lang] += 1

        # Sort by popularity
        sorted_languages = sorted(
            language_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return {
            "total_unique_languages": len(language_counts),
            "most_popular": [
                {"language": lang, "count": count}
                for lang, count in sorted_languages[:10]
            ],
            "language_distribution": dict(language_counts)
        }

    def get_performance_insights(self, jobs: List[Dict]) -> Dict:
        """
        Generate performance insights and recommendations.

        Args:
            jobs: List of all jobs

        Returns:
            Dict with insights and recommendations
        """
        metrics = self.calculate_job_metrics(jobs)
        errors = self.get_error_summary(jobs)

        insights = []
        recommendations = []

        # Success rate insights
        if metrics["success_rate"] < 80:
            insights.append({
                "type": "warning",
                "message": f"Success rate is {metrics['success_rate']}%, which is below optimal"
            })
            recommendations.append("Review failed jobs and address common errors")

        if metrics["success_rate"] >= 95:
            insights.append({
                "type": "success",
                "message": f"Excellent success rate of {metrics['success_rate']}%"
            })

        # Processing time insights
        if metrics["avg_processing_time_minutes"] > 15:
            insights.append({
                "type": "info",
                "message": f"Average processing time is {metrics['avg_processing_time_minutes']} minutes"
            })
            recommendations.append("Consider optimizing video preprocessing or using faster API tiers")

        # Error insights
        if errors["failure_rate"] > 10:
            insights.append({
                "type": "warning",
                "message": f"Failure rate of {errors['failure_rate']}% needs attention"
            })
            if errors["common_errors"]:
                top_error = errors["common_errors"][0]["error"]
                recommendations.append(f"Top error: '{top_error}' - investigate and fix")

        return {
            "insights": insights,
            "recommendations": recommendations,
            "health_score": self._calculate_health_score(metrics, errors)
        }

    def _calculate_health_score(self, metrics: Dict, errors: Dict) -> int:
        """
        Calculate overall system health score (0-100).

        Args:
            metrics: Job metrics
            errors: Error summary

        Returns:
            Health score between 0 and 100
        """
        score = 100

        # Deduct for low success rate
        if metrics["success_rate"] < 95:
            score -= (95 - metrics["success_rate"])

        # Deduct for high failure rate
        if errors["failure_rate"] > 5:
            score -= (errors["failure_rate"] - 5) * 2

        # Cap at 0 minimum
        return max(0, int(score))


# Global instance
job_statistics = JobStatistics()
