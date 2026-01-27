"""Language channel-related Pydantic schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class LanguageChannelRequest(BaseModel):
    """Request model for language channel registration."""
    channel_id: str
    language_code: str = Field(..., description="ISO 639-1 language code for this channel")
    channel_name: Optional[str] = None
    master_connection_id: Optional[str] = None  # Master YouTube connection to associate with
    project_id: Optional[str] = None  # Project ID to associate with
    
    class Config:
        json_schema_extra = {
            "example": {
                "channel_id": "UCxxxxxxxxxxxxxxxxxxxxxx",
                "language_codes": ["es", "fr", "de"],
                "channel_name": "Multi-Language Channel",
                "master_connection_id": "conn_abc123"
            }
        }


class LanguageChannelResponse(BaseModel):
    """Response model for language channel."""
    id: str
    channel_id: str
    language_code: str
    language_name: Optional[str] = None
    channel_name: Optional[str] = None
    channel_avatar_url: Optional[str] = None
    is_paused: bool = False
    project_id: Optional[str] = None
    created_at: datetime


class UpdateChannelRequest(BaseModel):
    """Request model for updating language channel."""
    channel_name: Optional[str] = None
    language_code: Optional[str] = None  # Update associated language
    is_paused: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "channel_name": "Updated Multi-Language Channel",
                "language_codes": ["es", "fr", "de"],
                "is_paused": True
            }
        }


class ChannelListResponse(BaseModel):
    """Response model for channel list."""
    channels: List[LanguageChannelResponse]


class ChannelNodeStatus(BaseModel):
    """Channel node status indicator."""
    status: str  # "active", "expired", "restricted", "disconnected"
    last_checked: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None
    permissions: List[str] = []  # e.g., ["youtube.upload", "youtube.readonly"]


class LanguageChannelNode(BaseModel):
    """Language channel satellite node."""
    id: str
    channel_id: str
    channel_name: Optional[str] = None
    channel_avatar_url: Optional[str] = None
    language_code: str
    language_name: Optional[str] = None
    created_at: datetime
    is_paused: bool = False
    status: ChannelNodeStatus
    # Stats
    videos_count: int = 0
    last_upload: Optional[datetime] = None


class YouTubeConnectionNode(BaseModel):
    """YouTube connection master node."""
    connection_id: str
    channel_id: str
    channel_name: str
    channel_avatar_url: Optional[str] = None
    is_primary: bool
    connected_at: datetime
    status: ChannelNodeStatus
    # Connected language channels (satellites)
    language_channels: List[LanguageChannelNode]
    # Language assigned directly to this connection
    language_code: Optional[str] = None
    language_name: Optional[str] = None
    # Stats
    total_videos: int = 0
    total_translations: int = 0


class ChannelGraphResponse(BaseModel):
    """Response model for channel relationship graph."""
    master_nodes: List[YouTubeConnectionNode]  # YouTube OAuth connections
    total_connections: int
    active_connections: int
    expired_connections: int
