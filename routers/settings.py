"""User settings management router."""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional

from services.supabase_db import supabase_service as firestore_service
from schemas.settings import UserSettings, UpdateUserSettingsRequest, NotificationSettings
from middleware.auth import get_current_user

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettings)
async def get_user_settings(
    current_user: dict = Depends(get_current_user)
) -> UserSettings:
    """
    Get user settings.
    
    Args:
        current_user: Current authenticated user from Firebase Auth
        
    Returns:
        UserSettings: User's current settings
    """
    user_id = current_user["user_id"]
    
    settings = firestore_service.get_user_settings(user_id)
    
    # Return default settings if none exist
    if not settings:
        return UserSettings(
            theme="dark",
            timezone="America/Los_Angeles",
            auto_approve_jobs=False,
            detected_upload_window="last_7_days",
            notifications=NotificationSettings(
                email_notifications=True,
                distribution_updates=True,
                error_alerts=True
            )
        )
    
    # Parse notifications if it's a dict
    notifications = settings.get('notifications', {})
    if isinstance(notifications, dict):
        notifications = NotificationSettings(**notifications)
    elif notifications is None:
        notifications = NotificationSettings()
    
    return UserSettings(
        theme=settings.get('theme', 'dark'),
        timezone=settings.get('timezone', 'America/Los_Angeles'),
        auto_approve_jobs=bool(settings.get('auto_approve_jobs', False)),
        detected_upload_window=settings.get('detected_upload_window', 'last_7_days'),
        notifications=notifications
    )


@router.patch("", response_model=UserSettings)
async def update_user_settings(
    request: UpdateUserSettingsRequest,
    current_user: dict = Depends(get_current_user)
) -> UserSettings:
    """
    Update user settings.
    
    Args:
        request: Settings update request
        current_user: Current authenticated user from Firebase Auth
        
    Returns:
        UserSettings: Updated settings
    """
    user_id = current_user["user_id"]
    
    # Build updates dict
    updates = {}
    if request.theme is not None:
        if request.theme not in ['light', 'dark']:
            raise HTTPException(
                status_code=400,
                detail="Theme must be 'light' or 'dark'"
            )
        updates['theme'] = request.theme
    
    if request.timezone is not None:
        updates['timezone'] = request.timezone
    
    if request.notifications is not None:
        updates['notifications'] = request.notifications.dict()

    if request.auto_approve_jobs is not None:
        updates['auto_approve_jobs'] = request.auto_approve_jobs
    
    if request.detected_upload_window is not None:
        allowed_windows = ['last_1_day', 'last_7_days', 'last_31_days']
        if request.detected_upload_window not in allowed_windows:
            raise HTTPException(
                status_code=400,
                detail=f"detected_upload_window must be one of {allowed_windows}"
            )
        updates['detected_upload_window'] = request.detected_upload_window
    
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No updates provided"
        )
    
    # Update settings
    firestore_service.update_user_settings(user_id, **updates)
    
    # Get updated settings
    updated_settings = firestore_service.get_user_settings(user_id)
    
    # Parse notifications
    notifications = updated_settings.get('notifications', {}) if updated_settings else {}
    if isinstance(notifications, dict):
        notifications = NotificationSettings(**notifications)
    elif notifications is None:
        notifications = NotificationSettings()
    
    return UserSettings(
        theme=updated_settings.get('theme', 'dark') if updated_settings else 'dark',
        timezone=updated_settings.get('timezone', 'America/Los_Angeles') if updated_settings else 'America/Los_Angeles',
        auto_approve_jobs=bool(updated_settings.get('auto_approve_jobs', False)) if updated_settings else False,
        detected_upload_window=updated_settings.get('detected_upload_window', 'last_7_days') if updated_settings else 'last_7_days',
        notifications=notifications
    )
