
"""Project management router."""
from fastapi import APIRouter, HTTPException, Depends, Body
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from services.firestore import firestore_service
from middleware.auth import get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])

class CreateProjectRequest(BaseModel):
    name: str
    master_connection_id: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    master_connection_id: Optional[str] = None
    created_at: Optional[datetime] = None
    
@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    current_user: dict = Depends(get_current_user)
):
    """List all projects for the current user."""
    user_id = current_user["user_id"]
    projects = firestore_service.list_projects(user_id)
    return projects

@router.post("", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    current_user: dict = Depends(get_current_user)
):
    """Create a new project."""
    user_id = current_user["user_id"]
    
    # If master_connection_id provided, verify ownership
    if request.master_connection_id:
        conn = firestore_service.get_youtube_connection(request.master_connection_id, user_id)
        if not conn:
            raise HTTPException(status_code=400, detail="Invalid master_connection_id")

    project_id = firestore_service.create_project(
        user_id=user_id,
        name=request.name,
        master_connection_id=request.master_connection_id
    )
    
    return firestore_service.get_project(project_id)

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get project details."""
    user_id = current_user["user_id"]
    project = firestore_service.get_project(project_id)
    
    if not project or project.get('user_id') != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
        
    return project

@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    master_connection_id: Optional[str] = Body(None),
    name: Optional[str] = Body(None),
    current_user: dict = Depends(get_current_user)
):
    """Update project details (e.g. change master account)."""
    user_id = current_user["user_id"]
    project = firestore_service.get_project(project_id)
    
    if not project or project.get('user_id') != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    updates = {}
    if name:
        updates['name'] = name
        
    if master_connection_id:
        # Verify ownership
        conn = firestore_service.get_youtube_connection(master_connection_id, user_id)
        if not conn:
             raise HTTPException(status_code=400, detail="Invalid master_connection_id")
        updates['master_connection_id'] = master_connection_id
        
    if updates:
        firestore_service.update_project(project_id, **updates)
        
    return firestore_service.get_project(project_id)

@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a project."""
    user_id = current_user["user_id"]
    project = firestore_service.get_project(project_id)
    if not project or project.get('user_id') != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # TODO: Handle cascade delete logic here if strictly needed, or just soft delete
    firestore_service.delete_project(project_id)
    return {"status": "deleted"}
