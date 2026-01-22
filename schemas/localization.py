"""Localization-related Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional


class CaptionUploadRequest(BaseModel):
    """Request model for caption upload."""
    video_id: str
    language_code: str  # ISO 639-1 language code (e.g., 'es', 'de', 'fr')
    
    class Config:
        json_schema_extra = {
            "example": {
                "video_id": "dQw4w9WgXcQ",
                "language_code": "es"
            }
        }


class CaptionUploadResponse(BaseModel):
    """Response model for caption upload."""
    message: str
    caption_id: Optional[str] = None
    video_id: str
    language_code: str
