"""Language channel management router."""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import asyncio

from services.firestore import firestore_service
from schemas.channels import (
    LanguageChannelRequest, LanguageChannelResponse, ChannelListResponse,
    ChannelGraphResponse, YouTubeConnectionNode, LanguageChannelNode, ChannelNodeStatus,
    UpdateChannelRequest
)
from routers.youtube_auth import get_youtube_service
from middleware.auth import get_current_user

router = APIRouter(prefix="/channels", tags=["channels"])


# Language name mapping
LANGUAGE_NAMES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "ar": "Arabic",
    "hi": "Hindi",
    "ru": "Russian"
}


def check_connection_status(connection: dict) -> ChannelNodeStatus:
    """Check YouTube connection status based on token expiry."""
    token_expiry = connection.get('token_expiry')
    access_token = connection.get('access_token', '')
    
    # Mock credentials detection
    if access_token.startswith('mock_'):
        return ChannelNodeStatus(
            status="active",  # Mock credentials are always "active" for testing
            last_checked=datetime.utcnow(),
            token_expires_at=None,
            permissions=["youtube.upload", "youtube.readonly", "youtube.force-ssl"]
        )
    
    # Check if token is expired
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
    
    # Active connection
    return ChannelNodeStatus(
        status="active",
        last_checked=datetime.utcnow(),
        token_expires_at=token_expiry if isinstance(token_expiry, datetime) else (datetime.fromtimestamp(token_expiry.timestamp()) if hasattr(token_expiry, 'timestamp') else None),
        permissions=["youtube.upload", "youtube.readonly", "youtube.force-ssl"]
    )


@router.get("/graph", response_model=ChannelGraphResponse)
async def get_channel_graph(
    current_user: dict = Depends(get_current_user)
) -> ChannelGraphResponse:
    """
    Get hierarchical channel relationship graph with status indicators.
    
    Returns master nodes (YouTube OAuth connections) and their satellite nodes
    (language-specific channels) with connection status for visualization.
    
    Args:
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        ChannelGraphResponse: Hierarchical channel graph with status
    """
    user_id = current_user["user_id"]
    
    # Get all YouTube connections (master nodes)
    youtube_connections = firestore_service.get_youtube_connections(user_id)
    
    # Get all language channels (satellite nodes)
    language_channels = firestore_service.get_language_channels(user_id)
    
    # Get job statistics for each connection
    all_jobs, _ = firestore_service.list_processing_jobs(user_id, limit=1000)
    
    master_nodes = []
    active_count = 0
    expired_count = 0
    
    for conn in youtube_connections:
        # Skip satellite connections - they should not appear as master nodes
        # Only master connections (without master_connection_id) should be in the graph
        if conn.get('master_connection_id'):
            continue  # Skip satellite connections
        
        # Check connection status
        status = check_connection_status(conn)
        
        if status.status == "active":
            active_count += 1
        elif status.status == "expired":
            expired_count += 1
        
        # Get connected language channels for this connection
        # Only include language channels that are associated with this master connection
        connection_id = conn.get('connection_id', '')
        if not connection_id:
            # Fallback to 'id' field if connection_id not present
            connection_id = conn.get('id', '')
        satellite_nodes = []
        
        for lang_ch in language_channels:
            # Check if this language channel is associated with this master connection
            lang_master_id = lang_ch.get('master_connection_id')
            if lang_master_id != connection_id:
                continue  # Skip language channels not associated with this master
            
            # Get language codes (support both old and new format)
            lang_codes = lang_ch.get('language_codes', [])
            if not lang_codes and lang_ch.get('language_code'):
                lang_codes = [lang_ch.get('language_code')]
            
            # Count videos for all languages in this channel
            videos_for_lang = []
            for lang_code in lang_codes:
                videos_for_lang.extend([
                    job for job in all_jobs
                    if lang_code in job.get('target_languages', [])
                    and job.get('status') == 'completed'
                ])
            # Remove duplicates by job_id
            unique_videos = {job.get('id'): job for job in videos_for_lang}.values()
            
            # Get language names
            language_names = [LANGUAGE_NAMES.get(lc, lc.upper()) for lc in lang_codes]
            
            created_at = lang_ch.get('created_at')
            if hasattr(created_at, 'timestamp'):
                created_at = datetime.fromtimestamp(created_at.timestamp())
            elif isinstance(created_at, (int, float)):
                created_at = datetime.fromtimestamp(created_at)
            
            satellite_nodes.append(LanguageChannelNode(
                id=lang_ch.get('id', ''),
                channel_id=lang_ch.get('channel_id', ''),
                channel_name=lang_ch.get('channel_name'),
                channel_avatar_url=lang_ch.get('channel_avatar_url'),
                language_code=lang_ch.get('language_code'),  # For backward compatibility (first language)
                language_codes=lang_codes,
                language_names=language_names,
                created_at=created_at or datetime.utcnow(),
                is_paused=lang_ch.get('is_paused', False),
                status=ChannelNodeStatus(
                    status="active",
                    last_checked=datetime.utcnow(),
                    token_expires_at=None,
                    permissions=["youtube.upload"]
                ),
                videos_count=len(unique_videos),
                last_upload=None
            ))
        
        # Count translations
        total_translations = sum(1 for job in all_jobs if job.get('status') == 'completed')
        
        # Format connected_at
        connected_at = conn.get('created_at')
        if hasattr(connected_at, 'timestamp'):
            connected_at = datetime.fromtimestamp(connected_at.timestamp())
        elif isinstance(connected_at, (int, float)):
            connected_at = datetime.fromtimestamp(connected_at)
        
        master_nodes.append(YouTubeConnectionNode(
            connection_id=connection_id,
            channel_id=conn.get('youtube_channel_id', ''),
            channel_name=conn.get('youtube_channel_name', 'Unknown Channel'),
            channel_avatar_url=conn.get('channel_avatar_url'),
            is_primary=conn.get('is_primary', False),
            connected_at=connected_at or datetime.utcnow(),
            status=status,
            language_channels=satellite_nodes,
            total_videos=len(all_jobs),
            total_translations=total_translations
        ))
    
    # Count only master connections (exclude satellites)
    master_connections_count = len([c for c in youtube_connections if not c.get('master_connection_id')])
    
    return ChannelGraphResponse(
        master_nodes=master_nodes,
        total_connections=master_connections_count,  # Only count master connections
        active_connections=active_count,
        expired_connections=expired_count
    )


@router.get("", response_model=ChannelListResponse)
async def list_channels(
    project_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
) -> ChannelListResponse:
    """
    List all language channels for authenticated user.
    
    Args:
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        ChannelListResponse: List of language channels
    """
    user_id = current_user["user_id"]
    channels = firestore_service.get_language_channels(user_id, project_id=project_id)
    
    channel_responses = []
    for ch in channels:
        created_at = ch.get('created_at')
        # Handle Firestore timestamp
        if hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp())
        elif isinstance(created_at, (int, float)):
            created_at = datetime.fromtimestamp(created_at)
        
        # Get language codes (support both old and new format)
        language_codes = ch.get('language_codes', [])
        if not language_codes and ch.get('language_code'):
            language_codes = [ch.get('language_code')]
        
        channel_responses.append(LanguageChannelResponse(
            id=ch['id'],
            channel_id=ch.get('channel_id'),
            language_code=ch.get('language_code'),  # For backward compatibility
            language_codes=language_codes,
            channel_name=ch.get('channel_name'),
            channel_avatar_url=ch.get('channel_avatar_url'),
            is_paused=ch.get('is_paused', False),
            project_id=ch.get('project_id'),
            created_at=created_at or datetime.utcnow()
        ))
    
    return ChannelListResponse(channels=channel_responses)


@router.post("", response_model=LanguageChannelResponse)
async def create_channel(
    request: LanguageChannelRequest,
    current_user: dict = Depends(get_current_user)
) -> LanguageChannelResponse:
    """
    Register a new language-specific channel.
    
    Args:
        request: Channel registration request
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        LanguageChannelResponse: Created channel information
        
    Raises:
        HTTPException: If channel not found or access denied
    """
    user_id = current_user["user_id"]
    
    try:
        # Verify user has access to channel via YouTube API
        youtube = await asyncio.to_thread(get_youtube_service, user_id)
        channels_response = await asyncio.to_thread(
            youtube.channels().list(part='snippet', id=request.channel_id).execute
        )
        
        if not channels_response.get('items'):
            raise HTTPException(
                status_code=404,
                detail=f"Channel not found: {request.channel_id}"
            )
        
        # Extract channel avatar
        channel_data = channels_response['items'][0]
        thumbnails = channel_data['snippet'].get('thumbnails', {})
        channel_avatar_url = (
            thumbnails.get('high', {}).get('url') or
            thumbnails.get('medium', {}).get('url') or
            thumbnails.get('default', {}).get('url')
        )
        
        # Validate master_connection_id if provided
        master_connection_id = request.master_connection_id
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
            # Check if the channel_id matches a YouTube connection with this master_connection_id
            # This handles the case where user connected via OAuth with master_connection_id
            youtube_conn = firestore_service.get_youtube_connection_by_channel(user_id, request.channel_id)
            if youtube_conn and youtube_conn.get('master_connection_id') == master_connection_id:
                # This connection was created for this master, use it
                pass
        else:
            # If no master_connection_id provided, check if channel_id matches a YouTube connection
            # that has a master_connection_id set (from OAuth flow)
            youtube_conn = firestore_service.get_youtube_connection_by_channel(user_id, request.channel_id)
            if youtube_conn and youtube_conn.get('master_connection_id'):
                # Verify the master connection is not itself a satellite
                master_conn_id = youtube_conn.get('master_connection_id')
                master_conn = firestore_service.get_youtube_connection(master_conn_id, user_id)
                if master_conn and master_conn.get('master_connection_id'):
                    raise HTTPException(
                        status_code=400,
                        detail="Cannot create language channel: The associated connection is a satellite channel, which cannot have children."
                    )
                # Use the master_connection_id from the YouTube connection
                master_connection_id = master_conn_id
        
        # Validate language codes
        if not request.language_codes and not request.language_code:
            raise HTTPException(
                status_code=400,
                detail="Either language_code or language_codes must be provided"
            )
        
        # Normalize to language_codes list
        language_codes = request.language_codes or []
        if request.language_code:
            if request.language_code not in language_codes:
                language_codes = [request.language_code] + language_codes
        
        # Check if channel already exists for this channel_id
        existing_channels = firestore_service.get_language_channels(user_id)
        existing = None
        for ch in existing_channels:
            if ch.get('channel_id') == request.channel_id:
                existing = ch
                break
        
        if existing:
            # Check if existing channel is orphaned (no master_connection_id)
            existing_master_id = existing.get('master_connection_id')
            
            if existing_master_id is None:
                # Channel exists but is orphaned - update it instead of creating new one
                print(f"[DEBUG] Found orphaned language channel, reassigning to master: {master_connection_id}")
                
                # Update the existing language channel
                firestore_service.update_language_channel(
                    request.channel_id,
                    user_id,
                    language_code=request.language_code,  # For backward compatibility
                    language_codes=language_codes,
                    channel_name=request.channel_name,
                    channel_avatar_url=channel_avatar_url,
                    master_connection_id=master_connection_id  # Reassign to master
                )
                
                # Get updated channel to return
                channels = firestore_service.get_language_channels(user_id)
                updated_channel = None
                for ch in channels:
                    if ch.get('id') == existing.get('id'):
                        updated_channel = ch
                        break
                
                if not updated_channel:
                    raise HTTPException(
                        status_code=500,
                        detail="Channel updated but could not be retrieved"
                    )
                
                created_at = updated_channel.get('created_at')
                if hasattr(created_at, 'timestamp'):
                    created_at = datetime.fromtimestamp(created_at.timestamp())
                elif isinstance(created_at, (int, float)):
                    created_at = datetime.fromtimestamp(created_at)
                
                # Get language codes
                updated_language_codes = updated_channel.get('language_codes', [])
                if not updated_language_codes and updated_channel.get('language_code'):
                    updated_language_codes = [updated_channel.get('language_code')]
                
                return LanguageChannelResponse(
                    id=updated_channel['id'],
                    channel_id=updated_channel.get('channel_id'),
                    language_code=updated_channel.get('language_code'),
                    language_codes=updated_language_codes,
                    channel_name=updated_channel.get('channel_name'),
                    channel_avatar_url=updated_channel.get('channel_avatar_url'),
                    is_paused=updated_channel.get('is_paused', False),
                    project_id=updated_channel.get('project_id'),
                    created_at=created_at or datetime.utcnow()
                )
            else:
                # Channel exists and is already assigned to a master
                raise HTTPException(
                    status_code=400,
                    detail=f"Channel already registered: {request.channel_id}. It is already associated with a master connection."
                )
        
        # Create new language channel record in Firestore
        channel_id = firestore_service.create_language_channel(
            user_id=user_id,
            channel_id=request.channel_id,
            language_code=request.language_code,  # For backward compatibility
            language_codes=language_codes,
            channel_name=request.channel_name,
            channel_avatar_url=channel_avatar_url,
            master_connection_id=master_connection_id,  # Associate with master
            project_id=request.project_id
        )
        
        # Get created channel to return
        channels = firestore_service.get_language_channels(user_id)
        channel = None
        for ch in channels:
            if ch.get('id') == channel_id:
                channel = ch
                break
        
        if not channel:
            raise HTTPException(
                status_code=500,
                detail="Channel created but could not be retrieved"
            )
        
        created_at = channel.get('created_at')
        if hasattr(created_at, 'timestamp'):
            created_at = datetime.fromtimestamp(created_at.timestamp())
        elif isinstance(created_at, (int, float)):
            created_at = datetime.fromtimestamp(created_at)
        
        # Get language codes (support both old and new format)
        language_codes = channel.get('language_codes', [])
        if not language_codes and channel.get('language_code'):
            language_codes = [channel.get('language_code')]
        
        return LanguageChannelResponse(
            id=channel['id'],
            channel_id=channel.get('channel_id'),
            language_code=channel.get('language_code'),  # For backward compatibility
            language_codes=language_codes,
            channel_name=channel.get('channel_name'),
            channel_avatar_url=channel.get('channel_avatar_url'),
            is_paused=channel.get('is_paused', False),
            project_id=channel.get('project_id'),
            created_at=created_at or datetime.utcnow()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create channel: {str(e)}"
        )


@router.patch("/{channel_id}")
async def update_channel(
    channel_id: str,
    request: UpdateChannelRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Update language channel settings.
    
    Args:
        channel_id: Channel ID to update
        request: Update request with new settings
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        LanguageChannelResponse: Updated channel information
        
    Raises:
        HTTPException: If channel not found or update fails
    """
    user_id = current_user["user_id"]
    
    # Build updates dict from request
    updates = {}
    if request.channel_name is not None:
        updates['channel_name'] = request.channel_name
    if request.is_paused is not None:
        updates['is_paused'] = request.is_paused
    
    # Handle language codes (language_codes takes precedence over language_code)
    if request.language_codes is not None:
        updates['language_codes'] = request.language_codes
        # Also update language_code for backward compatibility (use first language)
        if request.language_codes:
            updates['language_code'] = request.language_codes[0]
    elif request.language_code is not None:
        # If only language_code provided, update both fields
        updates['language_code'] = request.language_code
        # Get existing language_codes and add/update
        existing_channels = firestore_service.get_language_channels(user_id)
        existing = None
        for ch in existing_channels:
            if ch.get('id') == channel_id:
                existing = ch
                break
        if existing:
            existing_codes = existing.get('language_codes', [])
            if existing.get('language_code') and existing.get('language_code') not in existing_codes:
                existing_codes = [existing.get('language_code')] + existing_codes
            if request.language_code not in existing_codes:
                updates['language_codes'] = [request.language_code] + existing_codes
            else:
                updates['language_codes'] = existing_codes
        else:
            updates['language_codes'] = [request.language_code]
    
    if not updates:
        raise HTTPException(
            status_code=400,
            detail="No updates provided"
        )
    
    # Update channel
    success = firestore_service.update_language_channel(channel_id, user_id, **updates)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Channel not found or access denied"
        )
    
    # Get updated channel to return
    channels = firestore_service.get_language_channels(user_id)
    channel = next((ch for ch in channels if ch.get('channel_id') == channel_id), None)
    
    if not channel:
        raise HTTPException(
            status_code=404,
            detail="Channel not found"
        )
    
    created_at = channel.get('created_at')
    if hasattr(created_at, 'timestamp'):
        created_at = datetime.fromtimestamp(created_at.timestamp())
    elif isinstance(created_at, (int, float)):
        created_at = datetime.fromtimestamp(created_at)
    
    # Get language codes (support both old and new format)
    language_codes = channel.get('language_codes', [])
    if not language_codes and channel.get('language_code'):
        language_codes = [channel.get('language_code')]
    
    return LanguageChannelResponse(
        id=channel['id'],
        channel_id=channel.get('channel_id'),
        language_code=channel.get('language_code'),  # For backward compatibility
        language_codes=language_codes,
        channel_name=channel.get('channel_name'),
        channel_avatar_url=channel.get('channel_avatar_url'),
        is_paused=channel.get('is_paused', False),
        project_id=channel.get('project_id'),
        created_at=created_at or datetime.utcnow()
    )


@router.put("/{channel_id}/pause")
async def pause_channel(
    channel_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Pause a language channel (stop dubbing to this channel).
    
    Args:
        channel_id: Channel ID to pause
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        dict: Pause result
    """
    user_id = current_user["user_id"]
    
    success = firestore_service.update_language_channel(channel_id, user_id, is_paused=True)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Channel not found or access denied"
        )
    
    return {"message": "Channel paused successfully"}


@router.put("/{channel_id}/unpause")
async def unpause_channel(
    channel_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Unpause a language channel (resume dubbing to this channel).
    
    Args:
        channel_id: Channel ID to unpause
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        dict: Unpause result
    """
    user_id = current_user["user_id"]
    
    success = firestore_service.update_language_channel(channel_id, user_id, is_paused=False)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Channel not found or access denied"
        )
    
    return {"message": "Channel unpaused successfully"}


@router.delete("/{channel_id}")
async def delete_channel(
    channel_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Remove language channel association.
    
    Args:
        channel_id: Channel ID to remove
        current_user: Current authenticated user from Firebase Auth token
        
    Returns:
        dict: Deletion result
    """
    user_id = current_user["user_id"]
    
    # Check if channel exists
    channels = firestore_service.get_language_channels(user_id)
    channel_exists = any(ch.get('channel_id') == channel_id for ch in channels)
    
    if not channel_exists:
        raise HTTPException(
            status_code=404,
            detail="Channel not found"
        )
    
    firestore_service.delete_language_channel(channel_id, user_id)
    
    return {"message": "Channel removed successfully"}
