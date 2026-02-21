"""YouTube channel connection router."""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request as GoogleRequest
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import Optional
import httpx
import requests

from config import settings
from schemas.auth import YouTubeConnectionResponse, YouTubeConnectionListResponse, UpdateConnectionRequest
from schemas.channels import ChannelGraphResponse, YouTubeConnectionNode, LanguageChannelNode, ChannelNodeStatus
from services.supabase_db import supabase_service as firestore_service
from middleware.auth import get_current_user, get_optional_user
from utils.languages import LANGUAGE_NAMES

router = APIRouter(prefix="/youtube", tags=["youtube-connection"])


def check_connection_status(connection: dict) -> ChannelNodeStatus:
    """Check YouTube connection status based on token expiry."""
    token_expiry = connection.get('token_expiry')
    access_token = connection.get('access_token', '')
    
    if access_token.startswith('mock_'):
        return ChannelNodeStatus(
            status="active",
            last_checked=datetime.utcnow(),
            token_expires_at=None,
            permissions=["youtube.upload", "youtube.readonly", "youtube.force-ssl"]
        )
    
    if token_expiry:
        if isinstance(token_expiry, datetime):
            is_expired = token_expiry < datetime.utcnow()
        elif hasattr(token_expiry, 'timestamp'):
            is_expired = datetime.fromtimestamp(token_expiry.timestamp()) < datetime.utcnow()
        else:
            is_expired = False
        
        if is_expired:
            return ChannelNodeStatus(
                status="expired",
                last_checked=datetime.utcnow(),
                token_expires_at=token_expiry if isinstance(token_expiry, datetime) else datetime.fromtimestamp(token_expiry.timestamp()),
                permissions=[]
            )
    
    return ChannelNodeStatus(
        status="active",
        last_checked=datetime.utcnow(),
        token_expires_at=token_expiry if isinstance(token_expiry, datetime) else (datetime.fromtimestamp(token_expiry.timestamp()) if hasattr(token_expiry, 'timestamp') else None),
        permissions=["youtube.upload", "youtube.readonly", "youtube.force-ssl"]
    )


@router.get("/channel_graph", response_model=ChannelGraphResponse)
async def get_channel_graph(
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> ChannelGraphResponse:
    """
    Get channel relationship graph.
    HYBRID: YouTube connections from Firestore, channels and jobs from Supabase
    """
    from services.supabase_db import supabase_service

    user_id = current_user["user_id"]
    # YouTube OAuth connections still in Firestore (not migrated)
    youtube_connections = firestore_service.get_youtube_connections(user_id)
    # Channels and jobs now in Supabase
    language_channels = supabase_service.get_language_channels(user_id, project_id=project_id)
    all_jobs, _ = supabase_service.list_processing_jobs(user_id, limit=1000, project_id=project_id)
    
    master_nodes = []
    active_count = 0
    expired_count = 0
    
    for conn in youtube_connections:
        if conn.get('master_connection_id'):
            continue  # Skip satellite connections
        
        status = check_connection_status(conn)
        if status.status == "active":
            active_count += 1
        elif status.status == "expired":
            expired_count += 1
            
        satellites = []
        for channel in language_channels:
            if channel.get('master_connection_id') == conn['connection_id']:
                satellites.append(LanguageChannelNode(
                    id=channel['id'],
                    channel_id=channel['channel_id'],
                    channel_name=channel.get('channel_name'),
                    channel_avatar_url=channel.get('channel_avatar_url'),
                    language_code=channel['language_code'],
                    language_name=LANGUAGE_NAMES.get(channel['language_code'], channel['language_code'].upper()),
                    created_at=channel.get('created_at', datetime.utcnow()),
                    is_paused=channel.get('is_paused', False),
                    status=status,
                    videos_count=0
                ))
        
        master_nodes.append(YouTubeConnectionNode(
            connection_id=conn['connection_id'],
            channel_id=conn['youtube_channel_id'],
            channel_name=conn.get('youtube_channel_name', 'Unknown Channel'),
            channel_avatar_url=conn.get('channel_avatar_url'),
            is_primary=conn.get('is_primary', False),
            connected_at=conn.get('created_at', datetime.utcnow()),
            status=status,
            language_channels=satellites,
            language_code=conn.get('language_code'),
            language_name=LANGUAGE_NAMES.get(conn.get('language_code', ''), conn.get('language_code', '').upper()) if conn.get('language_code') else None,
            total_videos=0,
            total_translations=len(satellites)
        ))
        
    return ChannelGraphResponse(
        master_nodes=master_nodes,
        total_connections=len(master_nodes),
        active_connections=active_count,
        expired_connections=expired_count
    )


def get_youtube_oauth_flow() -> Flow:
    """
    Create and return OAuth 2.0 flow for YouTube channel connection.
    
    Returns:
        Flow: Configured OAuth flow for YouTube authentication
    """
    # Use the environment variable directly. If it's a full URL, it must match Google Console exactly.
    # If it's just a base URL, we ensure the /youtube/connect/callback path is present.
    youtube_callback_uri = settings.google_redirect_uri
    if not youtube_callback_uri.endswith("/youtube/connect/callback"):
        from urllib.parse import urlparse
        parsed = urlparse(youtube_callback_uri)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        youtube_callback_uri = f"{base_url}/youtube/connect/callback"
    
    print(f"[YOUTUBE_AUTH] Generated Redirect URI: {youtube_callback_uri}")
    
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [youtube_callback_uri]
        }
    }
    
    flow = Flow.from_client_config(
        client_config,
        scopes=settings.youtube_scopes,
        redirect_uri=youtube_callback_uri
    )
    
    return flow


@router.get("/connect")
async def initiate_youtube_connection(
    token: Optional[str] = Query(None, description="Firebase ID token (for OAuth redirect flows)"),
    master_connection_id: Optional[str] = Query(None, description="Master connection ID to associate language channel with"),
    request: Request = None,
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Initiate YouTube OAuth flow for channel connection.
    
    Redirects user to Google OAuth consent screen with YouTube scopes.
    """
    print(f"\n[INITIATE_CONNECT] Starting connection flow...")
    print(f"[INITIATE_CONNECT] Token in Query: {'Yes' if token else 'No'}")
    print(f"[INITIATE_CONNECT] Current User from Middleware: {'Yes' if current_user else 'No'}")
    print(f"[INITIATE_CONNECT] master_connection_id: {master_connection_id}")
    print(f"[INITIATE_CONNECT] X-Forwarded-Proto: {request.headers.get('x-forwarded-proto') if request else 'No Request'}")
    print(f"[INITIATE_CONNECT] Request URL Scheme: {request.url.scheme if request else 'No Request'}")
    user_token = None
    user_id = None
    
    # Try to get token from Authorization header first
    if current_user:
        user_id = current_user["user_id"]
        # Extract token from Authorization header
        if request:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                user_token = auth_header.replace("Bearer ", "")
    
    # If not, try query parameter
    if token:
        try:
            # Verify Supabase token
            user_response = firestore_service.client.auth.get_user(token)
            if user_response.user:
                user_id = user_response.user.id
                user_token = token  # Store the actual token
            else:
                raise Exception("Invalid token")
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f"Invalid token: {str(e)}"
            )
    
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide token via Authorization header (Bearer) or ?token= query parameter"
        )
    
    # If we have current_user but no token string, we can't store it in state
    # So we require token to be passed as query param for OAuth flows
    if not user_token:
        raise HTTPException(
            status_code=400,
            detail="Token must be provided as query parameter (?token=) for OAuth flow to work. The token will be stored in OAuth state for the callback."
        )
    
    # Validate master_connection_id if provided
    if master_connection_id:
        # Verify master connection exists and belongs to user
        master_conn = firestore_service.get_youtube_connection(master_connection_id, user_id)
        if not master_conn:
            raise HTTPException(
                status_code=404,
                detail=f"Master connection not found: {master_connection_id}"
            )
        # Verify it's not a satellite connection (satellites cannot have children)
        if master_conn.get('master_connection_id'):
            raise HTTPException(
                status_code=400,
                detail="Satellite channels cannot have child channels. Only master connections can have language channels associated with them."
            )
    
    try:
        flow = get_youtube_oauth_flow()
        # Include user token and master_connection_id in state so callback can retrieve it
        import base64
        import json
        state_data = {
            "user_token": user_token,
            "master_connection_id": master_connection_id  # Store master connection ID
        }
        state_encoded = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        
        authorization_url, oauth_state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',  # Force consent to get refresh token
            state=state_encoded  # Include token and master_connection_id in state
        )
        
        print(f"[INITIATE_CONNECT] Redirecting to Google Auth URL")
        print(f"[INITIATE_CONNECT] Full Google Auth URL: {authorization_url}")
        
        return RedirectResponse(url=authorization_url)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to initiate YouTube OAuth flow: {str(e)}"
        )


@router.get("/connect/callback")
async def youtube_connection_callback(
    code: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None,
    token: Optional[str] = Query(None, description="Supabase ID token (passed from frontend via state or stored in session)"),
    current_user: Optional[dict] = Depends(get_optional_user)
):
    """
    Handle YouTube OAuth callback and store channel connection.
    """
    print(f"\n[CALLBACK] Received callback from Google...")
    print(f"[CALLBACK] code present: {'Yes' if code else 'No'}")
    print(f"[CALLBACK] error: {error}")
    print(f"[CALLBACK] state present: {'Yes' if state else 'No'}")
    print(f"[CALLBACK] token present: {'Yes' if token else 'No'}")
    print(f"[CALLBACK] current_user present: {'Yes' if current_user else 'No'}")
    
    if error:
        # Redirect to frontend with error message
        frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
        if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
            frontend_url = f"http://{frontend_url}"
        from urllib.parse import quote
        error_message = quote(error, safe='')
        redirect_url = f"{frontend_url}/youtube/connect/error?error={error_message}"
        print(f"[DEBUG] OAuth error, redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    
    if not code:
        # Redirect to frontend with error message
        frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
        if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
            frontend_url = f"http://{frontend_url}"
        redirect_url = f"{frontend_url}/youtube/connect/error?error=Authorization%20code%20not%20provided"
        print(f"[DEBUG] No code, redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    
    # Get user ID from token, current_user, or state parameter
    user_id = None
    
    # Try to get from Authorization header first
    if current_user:
        user_id = current_user["user_id"]
    # Try query parameter
    elif token:
        try:
            # Verify Supabase token
            user_response = firestore_service.client.auth.get_user(token)
            if user_response.user:
                user_id = user_response.user.id
            else:
                raise Exception("Invalid token")
        except Exception as e:
            frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
            if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
                frontend_url = f"http://{frontend_url}"
            redirect_url = f"{frontend_url}/youtube/connect/error?error=Invalid%20authentication%20token"
            print(f"[DEBUG] Invalid token, redirecting to: {redirect_url}")
            return RedirectResponse(url=redirect_url, status_code=303)
    # Try to extract from state parameter (where we stored it during OAuth initiation)
    master_connection_id = None
    if state:
        try:
            import base64
            import json
            state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
            user_token = state_data.get("user_token")
            master_connection_id = state_data.get("master_connection_id")  # Extract master connection ID
            if user_token:
                # Verify Supabase token from state
                user_response = firestore_service.client.auth.get_user(user_token)
                if user_response.user:
                    user_id = user_response.user.id
                    print(f"[CALLBACK] Identified User ID from state: {user_id}")
        except Exception as e:
            print(f"[CALLBACK] Failed to parse state or verify token: {str(e)}")
            pass  # State might not contain token, that's okay
    
    if not user_id:
        # Redirect to frontend with error - authentication required
        frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
        if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
            frontend_url = f"http://{frontend_url}"
        redirect_url = f"{frontend_url}/youtube/connect/error?error=Authentication%20required"
        print(f"[DEBUG] No user_id, redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    
    try:
            print(f"[DEBUG] Starting OAuth token exchange for user_id: {user_id}")
            flow = get_youtube_oauth_flow()
            
            # CRITICAL: flow.fetch_token() consumes the authorization code even if it throws an exception
            # So we'll manually fetch the token first to avoid wasting the code on scope validation errors
            credentials = None
            
            # Manually fetch token to avoid scope validation consuming the code
            redirect_uri_used = flow.redirect_uri
            print(f"[DEBUG] Manually fetching token with redirect_uri: {redirect_uri_used}")
            
            token_url = "https://oauth2.googleapis.com/token"
            token_data = {
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri_used,
                "grant_type": "authorization_code"
            }
            
            async with httpx.AsyncClient() as client:
                token_response = await client.post(token_url, data=token_data, timeout=30.0)
                
                if token_response.status_code == 200:
                    token_json = token_response.json()
                    access_token = token_json.get("access_token")
                    refresh_token = token_json.get("refresh_token")
                    granted_scopes = token_json.get("scope", "").split() if token_json.get("scope") else []
                    
                    print(f"[DEBUG] Token fetched successfully, granted scopes: {granted_scopes}")
                    
                    # Create credentials manually - accept whatever scopes Google granted
                    credentials = Credentials(
                        token=access_token,
                        refresh_token=refresh_token,
                        token_uri=token_url,
                        client_id=settings.google_client_id,
                        client_secret=settings.google_client_secret,
                        scopes=granted_scopes  # Use granted scopes, not requested ones
                    )
                    
                    # Note: We don't need to set flow.credentials since we're using credentials directly
                else:
                    error_detail = token_response.text
                    print(f"[DEBUG] Manual token fetch failed: {token_response.status_code} - {error_detail}")
                    # Try to parse error JSON
                    try:
                        error_json = token_response.json()
                        error_type = error_json.get('error', 'unknown')
                        error_msg_parsed = error_json.get('error_description', error_json.get('error', error_detail))
                        
                        if error_type == "invalid_grant":
                            error_msg_parsed = "Authorization code expired or already used. Please try connecting again."
                    except:
                        error_msg_parsed = error_detail
                    
                    # Redirect to frontend with error
                    frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
                    if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
                        frontend_url = f"http://{frontend_url}"
                    from urllib.parse import quote
                    error_message = quote(error_msg_parsed, safe='')
                    redirect_url = f"{frontend_url}/youtube/connect/error?error={error_message}"
                    return RedirectResponse(url=redirect_url, status_code=303)
            
            # If we still don't have credentials, something went wrong
            if not credentials or not hasattr(credentials, 'token') or not credentials.token:
                frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
                if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
                    frontend_url = f"http://{frontend_url}"
                from urllib.parse import quote
                error_message = quote("Failed to obtain access token", safe='')
                redirect_url = f"{frontend_url}/youtube/connect/error?error={error_message}"
                return RedirectResponse(url=redirect_url, status_code=303)
            
            print(f"[DEBUG] Token exchange successful, has token: {credentials.token is not None}")
            
            # Ensure we have credentials before proceeding
            if not credentials or not hasattr(credentials, 'token') or not credentials.token:
                frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
                if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
                    frontend_url = f"http://{frontend_url}"
                redirect_url = f"{frontend_url}/youtube/connect/error?error=Failed%20to%20obtain%20access%20token"
                print(f"[DEBUG] No token after exchange, redirecting to: {redirect_url}")
                return RedirectResponse(url=redirect_url, status_code=303)
            
            # Get YouTube channel information
            youtube_service = build('youtube', 'v3', credentials=credentials)
            channels_response = youtube_service.channels().list(
                part='snippet,statistics',
                mine=True
            ).execute()
            
            if not channels_response.get('items'):
                frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
                if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
                    frontend_url = f"http://{frontend_url}"
                redirect_url = f"{frontend_url}/youtube/connect/error?error=No%20YouTube%20channel%20found%20for%20this%20account"
                print(f"[DEBUG] No channel, redirecting to: {redirect_url}")
                return RedirectResponse(url=redirect_url, status_code=303)
            
            channel = channels_response['items'][0]
            youtube_channel_id = channel['id']
            youtube_channel_name = channel['snippet'].get('title')
            channel_stats = channel.get('statistics', {}) or {}
            subscriber_count = int(channel_stats.get('subscriberCount', 0) or 0)
            video_count = int(channel_stats.get('videoCount', 0) or 0)
            
            # Extract channel avatar (use high quality if available)
            thumbnails = channel['snippet'].get('thumbnails', {})
            channel_avatar_url = (
                thumbnails.get('high', {}).get('url') or
                thumbnails.get('medium', {}).get('url') or
                thumbnails.get('default', {}).get('url')
            )
            
            # Check if this is for a language channel (master_connection_id provided)
            if master_connection_id:
                # Verify master connection exists
                master_conn = firestore_service.get_youtube_connection(master_connection_id, user_id)
                if not master_conn:
                    frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
                    if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
                        frontend_url = f"http://{frontend_url}"
                    redirect_url = f"{frontend_url}/youtube/connect/error?error=Master%20connection%20not%20found"
                    return RedirectResponse(url=redirect_url, status_code=303)
                
                # Verify it's not a satellite connection (satellites cannot have children)
                if master_conn.get('master_connection_id'):
                    frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
                    if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
                        frontend_url = f"http://{frontend_url}"
                    redirect_url = f"{frontend_url}/youtube/connect/error?error=Satellite%20channels%20cannot%20have%20child%20channels"
                    return RedirectResponse(url=redirect_url, status_code=303)
                
                # Check if language channel already exists for this channel_id
                existing_lang_channel = None
                language_channels = firestore_service.get_language_channels(user_id)
                for lang_ch in language_channels:
                    if lang_ch.get('channel_id') == youtube_channel_id:
                        existing_lang_channel = lang_ch
                        break
                
                if existing_lang_channel:
                    # Update existing language channel
                    firestore_service.update_language_channel(
                        youtube_channel_id,
                        user_id,
                        channel_name=youtube_channel_name,
                        channel_avatar_url=channel_avatar_url
                    )
                    language_channel_id = existing_lang_channel.get('id')
                else:
                    # Determine language code from channel name or use a default
                    # For now, we'll need to prompt user or use a default
                    # This is a limitation - we need language code to create language channel
                    # For now, create as a master connection and let user update it
                    print(f"[DEBUG] master_connection_id provided but language code unknown. Creating as master connection.")
                    # Fall through to create master connection
                    master_connection_id = None
            
            # If not creating language channel, create/update master connection
            if not master_connection_id:
                # Check if connection already exists
                existing = firestore_service.get_youtube_connection_by_channel(
                    user_id, youtube_channel_id
                )
                
                if existing:
                    # Update existing connection
                    firestore_service.update_youtube_connection(
                        existing['connection_id'],
                        access_token=credentials.token,
                        refresh_token=credentials.refresh_token,
                        token_expiry=credentials.expiry if credentials.expiry else None,
                        youtube_channel_name=youtube_channel_name,
                        channel_avatar_url=channel_avatar_url
                    )
                    connection_id = existing['connection_id']
                else:
                    # Check if this is the first connection (make it primary)
                    existing_connections = firestore_service.get_youtube_connections(user_id)
                    is_primary = len(existing_connections) == 0
                    
                    # Create new connection (store master_connection_id if provided)
                    connection_id = firestore_service.create_youtube_connection(
                        user_id=user_id,
                        youtube_channel_id=youtube_channel_id,
                        youtube_channel_name=youtube_channel_name,
                        access_token=credentials.token,
                        refresh_token=credentials.refresh_token,
                        token_expiry=credentials.expiry if credentials.expiry else None,
                        is_primary=is_primary,
                        channel_avatar_url=channel_avatar_url,
                        master_connection_id=master_connection_id  # Store master connection ID
                    )

                    # Auto-create project if none exist
                    existing_projects = firestore_service.list_projects(user_id)
                    if not existing_projects:
                        print(f"[DEBUG] No projects found for user {user_id}. Creating 'Default Project'.")
                        # If this is a master connection (no master_connection_id), use its connection_id
                        # If it's a satellite connection (has master_connection_id), use that instead
                        project_master_id = master_connection_id if master_connection_id else connection_id
                        
                        project_result = firestore_service.create_project({
                            "user_id": user_id,
                            "name": "Default Project",
                        })
                        target_project_id = project_result.get("id") if isinstance(project_result, dict) else None
                        
                        # Log the auto-creation
                        firestore_service.log_activity(
                            user_id=user_id,
                            project_id=target_project_id,
                            action="Created project",
                            details="Default Project created automatically during YouTube connection."
                        )

                # Ensure connected channel is represented in `channels` table so
                # frontend channel selectors (which query `channels`) include it.
                projects = firestore_service.list_projects(user_id)
                target_project_id = projects[0].get('id') if projects else None

                # channel_id is globally unique in DB; check globally, not only by user.
                # If another user already has this channel row, we still allow the OAuth
                # connection for current user but skip creating/updating channels table.
                existing_channel = firestore_service.get_channel(youtube_channel_id)
                channel_owned_by_other_user = bool(
                    existing_channel
                    and existing_channel.get("user_id")
                    and existing_channel.get("user_id") != user_id
                )

                channel_updates = {
                    'channel_name': youtube_channel_name,
                    'thumbnail_url': channel_avatar_url,
                    'subscriber_count': subscriber_count,
                    'video_count': video_count,
                    'project_id': target_project_id,
                    'is_master': True,
                    'language_code': existing_channel.get('language_code') if (existing_channel and not channel_owned_by_other_user) else 'en',
                    'language_name': existing_channel.get('language_name') if (existing_channel and not channel_owned_by_other_user) else 'English',
                }

                if existing_channel and not channel_owned_by_other_user:
                    firestore_service.update_channel(youtube_channel_id, channel_updates)
                elif not existing_channel:
                    try:
                        firestore_service.create_channel({
                            'user_id': user_id,
                            'channel_id': youtube_channel_id,
                            'project_id': target_project_id,
                            'channel_name': youtube_channel_name,
                            'thumbnail_url': channel_avatar_url,
                            'subscriber_count': subscriber_count,
                            'video_count': video_count,
                            'is_master': True,
                            'language_code': 'en',
                            'language_name': 'English',
                        })
                    except Exception as create_channel_error:
                        # Handle race condition where channel was inserted after our existence check.
                        err_msg = str(create_channel_error)
                        if "23505" in err_msg or "channels_channel_id_key" in err_msg:
                            existing_channel_after_conflict = firestore_service.get_channel(youtube_channel_id)
                            if existing_channel_after_conflict and existing_channel_after_conflict.get("user_id") == user_id:
                                firestore_service.update_channel(youtube_channel_id, channel_updates)
                            else:
                                # Channel now belongs to another user. Keep OAuth connection and continue.
                                print(
                                    f"[YOUTUBE_CONNECT] Channel row {youtube_channel_id} owned by another user after race; "
                                    "skipping channels table update for current user."
                                )
                        else:
                            raise
                else:
                    # Channel exists for another user; keep OAuth connection but don't mutate shared channel row.
                    print(
                        f"[YOUTUBE_CONNECT] Channel row {youtube_channel_id} belongs to another user. "
                        "Proceeding with connection without channels table update."
                    )
            
            # Redirect to frontend with success message
            # Get frontend URL from settings or use default
            frontend_url = getattr(settings, 'frontend_url', None)
            if not frontend_url:
                frontend_url = "http://localhost:3000"
            
            # Ensure it's a full URL (not relative)
            if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
                frontend_url = f"http://{frontend_url}"
            
            # URL encode channel name
            from urllib.parse import quote
            channel_name_encoded = quote(youtube_channel_name or '', safe='')
            connection_type = "satellite" if master_connection_id else "master"
            redirect_params = f"connection_id={connection_id}&channel_id={youtube_channel_id}&channel_name={channel_name_encoded}&connection_type={connection_type}"
            if master_connection_id:
                redirect_params += f"&master_connection_id={master_connection_id}"
            redirect_url = f"{frontend_url}/youtube/connect/success?{redirect_params}"
            
            # Debug logging
            print(f"[DEBUG] Redirecting to frontend: {redirect_url}")
            print(f"[DEBUG] Frontend URL from settings: {getattr(settings, 'frontend_url', 'NOT SET')}")
            
            # Use HTML page with JavaScript redirect (more reliable for cross-origin)
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>YouTube Connection Successful</title>
                <meta http-equiv="refresh" content="0;url={redirect_url}">
            </head>
            <body>
                <p>YouTube channel connected successfully! Redirecting...</p>
                <script>
                    window.location.href = "{redirect_url}";
                </script>
                <p>If you are not redirected automatically, <a href="{redirect_url}">click here</a>.</p>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content, status_code=200)
    except HTTPException as http_ex:
        # Catch HTTPException first (before generic Exception)
        frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
        if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
            frontend_url = f"http://{frontend_url}"
        from urllib.parse import quote
        error_message = quote(str(http_ex.detail), safe='')
        redirect_url = f"{frontend_url}/youtube/connect/error?error={error_message}"
        print(f"[DEBUG] HTTPException caught, redirecting to: {redirect_url}")
        return RedirectResponse(url=redirect_url, status_code=303)
    except Exception as e:
        # Handle any unexpected errors during token exchange
        error_msg = str(e)
        print(f"[DEBUG] Exception during token exchange: {error_msg}")
        frontend_url = getattr(settings, 'frontend_url', None) or "http://localhost:3000"
        if not frontend_url.startswith('http://') and not frontend_url.startswith('https://'):
            frontend_url = f"http://{frontend_url}"
        from urllib.parse import quote
        error_message = quote(f"Token exchange failed: {error_msg}", safe='')
        redirect_url = f"{frontend_url}/youtube/connect/error?error={error_message}"
        return RedirectResponse(url=redirect_url, status_code=303)


from utils.languages import LANGUAGE_NAMES


@router.get("/connections", response_model=YouTubeConnectionListResponse)
async def list_youtube_connections(
    current_user: dict = Depends(get_current_user)
):
    """
    List all YouTube channel connections for the current user.
    
    Args:
        current_user: Current authenticated user from Firebase Auth
        
    Returns:
        YouTubeConnectionListResponse: List of connected channels
    """
    user_id = current_user["user_id"]
    connections = firestore_service.get_youtube_connections(user_id)
    
    connection_responses = []
    for conn in connections:
        # Determine connection type
        master_conn_id = conn.get('master_connection_id')
        connection_type = "satellite" if master_conn_id else "master"
        
        # Handle timestamp conversion
        connected_at = conn.get('created_at')
        if hasattr(connected_at, 'timestamp'):
            connected_at = datetime.fromtimestamp(connected_at.timestamp())
        elif isinstance(connected_at, (int, float)):
            connected_at = datetime.fromtimestamp(connected_at)
        
        # Get language data
        lang_code = conn.get('language_code')
        lang_name = LANGUAGE_NAMES.get(lang_code, lang_code.upper()) if lang_code else None
        
        connection_responses.append(YouTubeConnectionResponse(
            connection_id=conn['connection_id'],
            youtube_channel_id=conn['youtube_channel_id'],
            youtube_channel_name=conn.get('youtube_channel_name'),
            channel_avatar_url=conn.get('channel_avatar_url'),
            is_primary=conn.get('is_primary', False),
            connected_at=connected_at or datetime.utcnow(),
            connection_type=connection_type,
            master_connection_id=master_conn_id,
            language_code=lang_code,
            language_name=lang_name
        ))
    
    return YouTubeConnectionListResponse(
        connections=connection_responses,
        total=len(connection_responses)
    )


@router.patch("/connections/{connection_id}")
async def update_youtube_connection(
    connection_id: str,
    request: UpdateConnectionRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update YouTube connection settings.
    
    Args:
        connection_id: Connection ID to update
        request: Update request with settings
        current_user: Current authenticated user from Firebase Auth
        
    Returns:
        dict: Update result
        
    Raises:
        HTTPException: If connection not found or update fails
    """
    user_id = current_user["user_id"]
    
    # Verify connection exists and belongs to user
    connection = firestore_service.get_youtube_connection(connection_id, user_id)
    if not connection:
        raise HTTPException(
            status_code=404,
            detail="Connection not found or access denied"
        )
    
    updates = {}
    
    # Handle primary connection change
    if request.is_primary is not None:
        if request.is_primary:
            success = firestore_service.set_primary_connection(connection_id, user_id)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to set primary connection"
                )
        else:
            # Unset primary (but ensure at least one primary exists)
            updates['is_primary'] = False
            
    # Handle language update
    if request.language_code is not None:
        updates['language_code'] = request.language_code
        
    if updates:
        firestore_service.update_youtube_connection(connection_id, **updates)
    
    return {"message": "Connection updated successfully"}


@router.put("/connections/{connection_id}/set-primary")
async def set_primary_connection(
    connection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Set a YouTube connection as the primary connection.
    This will unset any other primary connections.
    
    Args:
        connection_id: Connection ID to set as primary
        current_user: Current authenticated user from Firebase Auth
        
    Returns:
        dict: Update result
        
    Raises:
        HTTPException: If connection not found
    """
    user_id = current_user["user_id"]
    
    success = firestore_service.set_primary_connection(connection_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Connection not found or access denied"
        )
    
    return {"message": "Primary connection updated successfully"}


@router.delete("/connections/{connection_id}/unset-primary")
async def unset_primary_connection(
    connection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Unset a YouTube connection as the primary connection.
    
    Args:
        connection_id: Connection ID to unset as primary
        current_user: Current authenticated user from Firebase Auth
        
    Returns:
        dict: Update result
        
    Raises:
        HTTPException: If connection not found or not primary
    """
    user_id = current_user["user_id"]
    
    # Verify connection exists and belongs to user
    connection = firestore_service.get_youtube_connection(connection_id, user_id)
    if not connection:
        raise HTTPException(
            status_code=404,
            detail="Connection not found or access denied"
        )
    
    # Check if it's currently primary
    if not connection.get('is_primary', False):
        raise HTTPException(
            status_code=400,
            detail="Connection is not currently set as primary"
        )
    
    # Unset primary status
    firestore_service.update_youtube_connection(connection_id, is_primary=False)
    
    return {"message": "Primary connection unset successfully"}


@router.delete("/connections/{connection_id}")
async def disconnect_youtube_channel(
    connection_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Disconnect a YouTube channel.
    
    Args:
        connection_id: Connection ID to disconnect
        current_user: Current authenticated user from Firebase Auth
        
    Returns:
        dict: Disconnection result
    """
    user_id = current_user["user_id"]
    
    # Get connection info before deletion to check if it's a satellite
    connection = firestore_service.get_youtube_connection(connection_id, user_id)
    if not connection:
        raise HTTPException(
            status_code=404,
            detail="Connection not found or access denied"
        )
    
    is_satellite = bool(connection.get('master_connection_id'))
    youtube_channel_id = connection.get('youtube_channel_id')
    master_connection_id = connection.get('master_connection_id')
    
    # Count language channels that will be unassigned
    language_channels_count = 0
    if youtube_channel_id:
        # Check how many language channels will be unassigned
        all_language_channels = firestore_service.get_language_channels(user_id)
        matching_channels = [
            ch for ch in all_language_channels 
            if ch.get('channel_id') == youtube_channel_id
        ]
        if master_connection_id:
            # Only count channels associated with this master
            matching_channels = [
                ch for ch in matching_channels
                if ch.get('master_connection_id') == master_connection_id
            ]
        language_channels_count = len(matching_channels)
    
    # Delete the connection (this also unassigns associated language channels)
    success = firestore_service.delete_youtube_connection(connection_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete connection"
        )
    
    response = {
        "message": "Channel disconnected successfully",
        "connection_id": connection_id,
        "connection_type": "satellite" if is_satellite else "master"
    }
    
    if language_channels_count > 0:
        response["unassigned_language_channels"] = language_channels_count
        response["message"] = f"Channel disconnected successfully. {language_channels_count} associated language channel(s) were unassigned from the master connection."
    
    return response
