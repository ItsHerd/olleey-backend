"""Processing job-related Pydantic schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class CreateJobRequest(BaseModel):
    """Request model for creating a dubbing job."""
    source_video_id: Optional[str] = Field(None, description="YouTube video ID to dub (optional if video_url is provided)")
    source_video_url: Optional[str] = Field(None, description="YouTube video URL (alternative to source_video_id)")
    source_channel_id: str = Field(..., description="YouTube channel ID where video is published")
    target_channel_ids: List[str] = Field(..., description="List of target channel IDs to publish dubs to (each channel is connected to one or more languages)")
    project_id: Optional[str] = Field(None, description="Project ID to assign job to")
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_video_id": "dQw4w9WgXcQ",
                "source_channel_id": "UCxxxxxx",
                "target_channel_ids": ["channel_doc_id_1", "channel_doc_id_2"],
                "project_id": "proj_123"
            }
        }


class CreateManualJobRequest(BaseModel):
    """Request model for creating a manual dubbing job with video upload or URL."""
    source_channel_id: str = Field(..., description="YouTube channel ID where video is published")
    target_channel_ids: List[str] = Field(..., description="List of target channel IDs to publish dubs to (each channel is connected to one or more languages)")
    project_id: Optional[str] = Field(None, description="Project ID to assign job to")
    # Note: video_url or video file will be provided via Form data in the endpoint
    
    class Config:
        json_schema_extra = {
            "example": {
                "source_channel_id": "UCxxxxxx",
                "target_channel_ids": ["channel_doc_id_1", "channel_doc_id_2"],
                "project_id": "proj_123"
            }
        }


class ProcessingJobResponse(BaseModel):
    """Response model for processing job."""
    job_id: str
    status: str
    progress: Optional[int] = None
    source_video_id: str
    source_channel_id: str
    project_id: Optional[str] = None
    target_languages: List[str]
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class JobListResponse(BaseModel):
    """Response model for job list."""
    jobs: List[ProcessingJobResponse]
    total: int


class LocalizedVideoResponse(BaseModel):
    """Response model for localized video details."""
    id: str
    job_id: str
    source_video_id: str
    language_code: str
    status: str
    storage_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime
