"""Helper functions for YouTube authentication using connected channels."""
from typing import Optional
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from fastapi import HTTPException

from config import settings
from services.supabase_db import supabase_service as firestore_service


def get_youtube_credentials(user_id: str, connection_id: Optional[str] = None) -> Optional[Credentials]:
    """
    Get valid OAuth credentials for a user's YouTube connection.
    Refreshes token if expired.
    
    Args:
        user_id: Firebase Auth user ID
        connection_id: Optional specific connection ID, otherwise uses primary
        
    Returns:
        Credentials: Valid OAuth credentials or None if not found
    """
    # Get connection from Firestore
    conn_data = firestore_service.get_youtube_credentials(user_id, connection_id)
    
    if not conn_data or not conn_data.get('refresh_token'):
        return None
    
    credentials = Credentials(
        token=conn_data.get('access_token'),
        refresh_token=conn_data.get('refresh_token'),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret
    )
    
    # Refresh token if expired (or if it's a mock token)
    # Mock tokens will have "mock_" prefix
    if conn_data.get('access_token', '').startswith('mock_'):
        # This is a mock/test connection, return None to indicate invalid credentials
        print(f"[YOUTUBE_AUTH] Mock credentials detected for user {user_id}, cannot access real YouTube API")
        return None
    
    if credentials.expired and credentials.refresh_token:
        try:
            credentials.refresh(GoogleRequest())
            
            # Update Firestore with new token
            firestore_service.update_youtube_connection(
                conn_data['connection_id'],
                access_token=credentials.token,
                token_expiry=credentials.expiry if credentials.expiry else None
            )
        except Exception as e:
            # Token refresh failed
            print(f"[YOUTUBE_AUTH] Token refresh failed for user {user_id}: {str(e)}")
            return None
    
    return credentials


def get_youtube_service(user_id: str, connection_id: Optional[str] = None, raise_on_mock: bool = True):
    """
    Build and return YouTube Data API v3 service with user's connected channel credentials.
    
    Args:
        user_id: Firebase Auth user ID
        connection_id: Optional specific connection ID, otherwise uses primary
        raise_on_mock: If False, returns None for mock credentials instead of raising
        
    Returns:
        YouTube service instance or None if mock credentials and raise_on_mock=False
        
    Raises:
        HTTPException: If authentication fails or no connection found
    """
    credentials = get_youtube_credentials(user_id, connection_id)
    
    if not credentials:
        if not raise_on_mock:
            return None
        raise HTTPException(
            status_code=401,
            detail="No YouTube channel connected. Please connect a YouTube channel first."
        )
    
    return build('youtube', 'v3', credentials=credentials)
