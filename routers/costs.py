"""Cost estimation and tracking endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from services.cost_tracking import get_cost_tracker
from services.supabase_db import supabase_service as firestore_service
from routers.auth import get_current_user

router = APIRouter(prefix="/api/costs", tags=["costs"])


class CostEstimateRequest(BaseModel):
    """Request model for cost estimation."""
    video_duration_minutes: float = Field(..., gt=0, description="Video duration in minutes")
    target_languages: List[str] = Field(..., min_items=1, description="Target language codes")
    include_lipsync: bool = Field(True, description="Include lip sync processing")


class CostEstimateResponse(BaseModel):
    """Response model for cost estimation."""
    total: float
    per_language: float
    dubbing: float
    lipsync: float
    breakdown: dict
    is_demo: bool = False


class UserCostSummary(BaseModel):
    """User's cost summary."""
    total_cost: float
    total_jobs: int
    avg_cost_per_job: float
    total_languages: int
    avg_cost_per_language: float
    period: str = "all_time"


@router.post("/estimate", response_model=CostEstimateResponse)
async def estimate_cost(
    request: CostEstimateRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Estimate cost for a dubbing job before submission.

    Useful for showing users the estimated cost upfront.
    """
    try:
        user_id = current_user.get("id")
        cost_tracker = get_cost_tracker(user_id)

        costs = cost_tracker.calculate_dubbing_cost(
            video_duration_minutes=request.video_duration_minutes,
            num_languages=len(request.target_languages),
            include_lipsync=request.include_lipsync
        )

        return CostEstimateResponse(
            total=costs["total"],
            per_language=costs["per_language"],
            dubbing=costs["dubbing"],
            lipsync=costs["lipsync"],
            breakdown=costs,
            is_demo=costs.get("is_demo", False)
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/summary", response_model=UserCostSummary)
async def get_cost_summary(
    current_user: dict = Depends(get_current_user)
):
    """
    Get user's cost summary across all jobs.

    Returns total costs, averages, and usage statistics.
    """
    try:
        user_id = current_user.get("id")

        # Get all jobs for user
        jobs = firestore_service.get_user_processing_jobs(user_id)

        # Extract cost records
        cost_records = []
        for job in jobs:
            if job.get('estimated_cost'):
                cost_records.append({
                    "job_id": job.get("id"),
                    "actual_cost": job.get('estimated_cost', 0),
                    "num_languages": len(job.get('target_languages', []))
                })

        # Calculate summary
        cost_tracker = get_cost_tracker(user_id)
        summary = cost_tracker.get_monthly_cost_summary(cost_records)

        return UserCostSummary(
            total_cost=summary["total_cost"],
            total_jobs=summary["total_jobs"],
            avg_cost_per_job=summary["avg_cost_per_job"],
            total_languages=summary["total_languages"],
            avg_cost_per_language=summary["avg_cost_per_language"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/job/{job_id}")
async def get_job_cost(
    job_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Get cost details for a specific job.
    """
    try:
        user_id = current_user.get("id")
        job = firestore_service.get_processing_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

        if job.get("user_id") != user_id:
            raise HTTPException(status_code=403, detail="Access denied")

        return {
            "job_id": job_id,
            "estimated_cost": job.get("estimated_cost", 0),
            "actual_cost": job.get("actual_cost", job.get("estimated_cost", 0)),
            "breakdown": job.get("cost_breakdown", {}),
            "num_languages": len(job.get("target_languages", [])),
            "status": job.get("status"),
            "created_at": job.get("created_at")
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
