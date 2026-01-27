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


class CreditSummary(BaseModel):
    """Summary of user credits."""
    used: int
    limit: int
    reset_date: Optional[datetime] = None


class WeeklyStats(BaseModel):
    """Mini-widget statistics for the current week."""
    videos_completed: int
    languages_added: int
    growth_percentage: float


class ActivityFeedItem(BaseModel):
    """Single item in the activity feed."""
    id: str
    action: str
    details: Optional[str] = None
    status: str
    timestamp: datetime
    project_id: Optional[str] = None


class ProcessingJobSummary(BaseModel):
    """Summary of processing job."""
    job_id: str
    source_video_id: str
    status: str
    progress: int
    target_languages: List[str]
    created_at: datetime


class ProjectSummary(BaseModel):
    """Summary of project."""
    id: str
    name: str
    created_at: datetime


class DashboardResponse(BaseModel):
    """Dashboard data response."""
    user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    auth_provider: str
    created_at: datetime
    
    # Statistics & Credits
    credits: CreditSummary
    weekly_stats: WeeklyStats
    
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
    
    # Projects
    projects: List[ProjectSummary] = []
    total_projects: int = 0
    
    # Activity
    recent_activity: List[ActivityFeedItem] = []
