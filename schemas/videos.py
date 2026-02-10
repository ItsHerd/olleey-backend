"""Video-related Pydantic schemas."""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class LocalizationStatus(BaseModel):
    """Status info for a specific target language."""
    status: str  # processing, draft, live
    language_code: str
    video_id: Optional[str] = None  # YouTube ID of the localized video if live
    job_id: Optional[str] = None  # Processing job ID for approval flow
    channel_id: Optional[str] = None  # Target channel for this language
    published_at: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None  # Thumbnail URL for the localized video
    video_url: Optional[str] = None  # Storage URL for the localized video


class VideoItem(BaseModel):
    """Single video item model."""
    video_id: str
    title: str
    thumbnail_url: Optional[str] = None
    published_at: datetime
    view_count: int = 0
    channel_id: str  # YouTube channel ID where video is published
    channel_name: str  # YouTube channel name
    video_type: str = "all"  # "all", "original", or "translated"
    source_video_id: Optional[str] = None  # If translated, link to original video
    storage_url: Optional[str] = None  # S3 or storage URL for the video file
    localizations: List[LocalizationStatus] = []
    translated_languages: list[str] = []  # For backward compatibility


class VideoListResponse(BaseModel):
    """Response model for video list."""
    videos: list[VideoItem]
    total: int


class VideoUploadRequest(BaseModel):
    """Request model for video upload."""
    title: str
    description: str = ""
    privacy_status: str = "private"  # private, unlisted, public
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "My Video Title",
                "description": "Video description",
                "privacy_status": "private"
            }
        }


class VideoUploadResponse(BaseModel):
    """Response model for video upload."""
    message: str
    video_id: str
    title: str
    privacy_status: str


class SubscriptionRequest(BaseModel):
    """Request model for PubSubHubbub subscription."""
    channel_id: str
    callback_url: Optional[str] = None
    lease_seconds: int = 2592000  # 30 days default


class SubscriptionResponse(BaseModel):
    """Response model for PubSubHubbub subscription."""
    subscription_id: str
    channel_id: str
    expires_at: Optional[datetime] = None
    message: str


class UnsubscribeRequest(BaseModel):
    """Request model for unsubscribing from PubSubHubbub."""
    channel_id: Optional[str] = None
    subscription_id: Optional[str] = None
