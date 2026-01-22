"""Dashboard-related Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class YouTubeConnectionSummary(BaseModel):
    """Summary of YouTube connection."""
    connection_id: str
    youtube_channel_id: str
    youtube_channel_name: Optional[str] = None
    is_primary: bool
    connected_at: datetime


class ProcessingJobSummary(BaseModel):
    """Summary of processing job."""
    job_id: str
    source_video_id: str
    status: str
    progress: int
    target_languages: List[str]
    created_at: datetime


class DashboardResponse(BaseModel):
    """Dashboard data response."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    auth_provider: str
    created_at: datetime
    
    # YouTube connections
    youtube_connections: List[YouTubeConnectionSummary] = []
    has_youtube_connection: bool = False
    connections_count: int = 0
    
    # Processing jobs summary
    total_jobs: int = 0
    active_jobs: int = 0
    completed_jobs: int = 0
    recent_jobs: List[ProcessingJobSummary] = []
    
    # Language channels
    language_channels: List[dict] = []
    total_language_channels: int = 0
