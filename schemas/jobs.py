"""Processing job-related Pydantic schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class CreateJobRequest(BaseModel):
    """Request model for creating a dubbing job."""
    source_video_id: str = Field(..., description="YouTube video ID to dub")
    source_channel_id: str = Field(..., description="YouTube channel ID where video is published")
    target_languages: List[str] = Field(..., description="List of language codes to create dubs for (e.g., ['es', 'de', 'fr'])")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_video_id": "dQw4w9WgXcQ",
                "source_channel_id": "UCxxxxxx",
                "target_languages": ["es", "de", "fr"]
            }
        }


class ProcessingJobResponse(BaseModel):
    """Response model for processing job."""
    job_id: str
    status: str
    progress: Optional[int] = None
    source_video_id: str
    source_channel_id: str
    target_languages: List[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobListResponse(BaseModel):
    """Response model for job list."""
    jobs: List[ProcessingJobResponse]
    total: int
