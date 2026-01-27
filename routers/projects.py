"""Project management router."""
from fastapi import APIRouter, HTTPException, Depends, Body, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

from services.firestore import firestore_service
from middleware.auth import get_current_user
from schemas.projects import CreateProjectRequest, ProjectResponse, ActivityLogResponse

router = APIRouter(prefix="/projects", tags=["projects"])

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
    
    # Log activity
    firestore_service.log_activity(
        user_id=user_id,
        project_id=project_id,
        action="Created project",
        details=f"Project '{request.name}' created."
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
    log_details = []
    if name:
        updates['name'] = name
        log_details.append(f"Name updated to '{name}'")
        
    if master_connection_id:
        # Verify ownership
        conn = firestore_service.get_youtube_connection(master_connection_id, user_id)
        if not conn:
             raise HTTPException(status_code=400, detail="Invalid master_connection_id")
        updates['master_connection_id'] = master_connection_id
        log_details.append(f"Master connection updated to {master_connection_id}")
        
    if updates:
        firestore_service.update_project(project_id, **updates)
        # Log activity
        firestore_service.log_activity(
            user_id=user_id,
            project_id=project_id,
            action="Updated project",
            details=", ".join(log_details)
        )
        
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
    
    project_name = project.get('name', 'Untitled Project')
    
    firestore_service.delete_project(project_id)
    
    # Log activity (orphan log since project is deleted, but user_id remains)
    firestore_service.log_activity(
        user_id=user_id,
        project_id=project_id,
        action="Deleted project",
        details=f"Project '{project_name}' deleted."
    )
    
    return {"status": "deleted"}

@router.get("/{project_id}/activity", response_model=List[ActivityLogResponse])
async def list_project_activity(
    project_id: str,
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(get_current_user)
):
    """List activity logs for a specific project."""
    user_id = current_user["user_id"]
    
    # Verify project ownership
    project = firestore_service.get_project(project_id)
    if not project or project.get('user_id') != user_id:
        raise HTTPException(status_code=404, detail="Project not found")
        
    logs = firestore_service.list_activity_logs(user_id=user_id, project_id=project_id, limit=limit)
    
    # Convert timestamps
    for log in logs:
        if hasattr(log.get('timestamp'), 'timestamp'):
            log['timestamp'] = datetime.fromtimestamp(log['timestamp'].timestamp())
            
    return logs
