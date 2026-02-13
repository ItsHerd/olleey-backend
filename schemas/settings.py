"""User settings-related Pydantic schemas."""
from pydantic import BaseModel
from typing import Optional, List


class NotificationSettings(BaseModel):
    """Notification preferences."""
    email_notifications: bool = True
    distribution_updates: bool = True  # Alerts when dubbing jobs finish
    error_alerts: bool = True  # Alerts when jobs fail or connections break


class UserSettings(BaseModel):
    """User settings model."""
    theme: str = "dark"  # "light" or "dark"
    timezone: str = "America/Los_Angeles"  # IANA timezone
    notifications: NotificationSettings = NotificationSettings()  # Default notification settings
    auto_approve_jobs: bool = False
    
    class Config:
        json_schema_extra = {
            "example": {
                "theme": "dark",
                "timezone": "America/Los_Angeles",
                "auto_approve_jobs": False,
                "notifications": {
                    "email_notifications": True,
                    "distribution_updates": True,
                    "error_alerts": True
                }
            }
        }


class UpdateUserSettingsRequest(BaseModel):
    """Request model for updating user settings."""
    theme: Optional[str] = None  # "light" or "dark"
    timezone: Optional[str] = None  # IANA timezone
    notifications: Optional[NotificationSettings] = None
    auto_approve_jobs: Optional[bool] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "theme": "light",
                "timezone": "America/New_York",
                "auto_approve_jobs": True,
                "notifications": {
                    "email_notifications": False,
                    "distribution_updates": True,
                    "error_alerts": True
                }
            }
        }
