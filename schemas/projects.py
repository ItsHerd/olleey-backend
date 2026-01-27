from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class CreateProjectRequest(BaseModel):
    name: str
    master_connection_id: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    master_connection_id: Optional[str] = None
    created_at: Optional[datetime] = None

class ActivityLogResponse(BaseModel):
    id: str
    project_id: Optional[str] = None
    action: str
    status: str
    details: Optional[str] = None
    timestamp: datetime
