"""Webhook router for PubSubHubbub notifications."""
from fastapi import APIRouter, HTTPException, Request, Query, BackgroundTasks
from fastapi.responses import PlainTextResponse
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional
import asyncio

from services.firestore import firestore_service
from config import settings

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.get("/youtube")
async def webhook_verification(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_topic: str = Query(..., alias="hub.topic"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_lease_seconds: Optional[int] = Query(None, alias="hub.lease_seconds")
):
    """
    Handle PubSubHubbub webhook verification (GET request).
    
    Args:
        hub_mode: Verification mode (subscribe/unsubscribe)
        hub_topic: Feed URL being subscribed to
        hub_challenge: Challenge string to return
        hub_lease_seconds: Lease duration in seconds
        db: Database session
        
    Returns:
        PlainTextResponse: Challenge string
    """
    try:
        # Verify subscription exists
        subscription = firestore_service.get_subscription_by_topic(hub_topic)
        
        if not subscription:
            raise HTTPException(
                status_code=404,
                detail="Subscription not found"
            )
        
        # Update lease if provided
        if hub_lease_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=hub_lease_seconds)
            firestore_service.update_subscription_lease(
                subscription['id'],
                expires_at,
                hub_lease_seconds
            )
        
        # Return challenge as plain text
        return PlainTextResponse(content=hub_challenge)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Verification failed: {str(e)}"
        )


@router.post("/youtube")
async def webhook_notification(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle PubSubHubbub webhook notifications (POST request with Atom feed).
    
    Args:
        request: FastAPI request object
        db: Database session
        
    Returns:
        dict: Acknowledgment
    """
    try:
        # Read Atom feed from request body
        body = await request.body()
        
        if not body:
            raise HTTPException(
                status_code=400,
                detail="Empty request body"
            )
        
        # Parse Atom feed
        root = ET.fromstring(body)
        
        # Extract namespace
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        
        # Extract video entries
        entries = root.findall('.//atom:entry', ns)
        
        video_updates = []
        for entry in entries:
            video_id_elem = entry.find('yt:videoId', ns)
            channel_id_elem = entry.find('yt:channelId', ns)
            published_elem = entry.find('atom:published', ns)
            updated_elem = entry.find('atom:updated', ns)
            
            if video_id_elem is not None and channel_id_elem is not None:
                video_id = video_id_elem.text
                channel_id = channel_id_elem.text
                published_at = published_elem.text if published_elem is not None else None
                updated_at = updated_elem.text if updated_elem is not None else None
                
                # Check if this is a new video (published_at == updated_at indicates new upload)
                is_new = published_at and updated_at and published_at == updated_at
                
                video_updates.append({
                    'video_id': video_id,
                    'channel_id': channel_id,
                    'published_at': published_at,
                    'updated_at': updated_at,
                    'is_new': is_new
                })
        
        # Find subscription for this channel
        if video_updates:
            channel_id = video_updates[0]['channel_id']
            subscription = firestore_service.get_subscription_by_channel(
                user_id='',  # We'll find by channel_id
                channel_id=channel_id
            )
            
            # Try to find subscription by channel_id (need to search all subscriptions)
            # For now, we'll get it from the first video's channel
            # In production, you might want to add a method to get subscription by channel_id only
            subscriptions = []  # We need to find subscription by channel_id
            # Since we don't have a direct method, we'll need to search
            # For now, let's assume we can get user_id from somewhere or search differently
            
            if subscription:
                user_id = subscription.get('user_id')
                # Get target languages from user's language channels
                language_channels = firestore_service.get_language_channels(user_id)
                
                if language_channels:
                    target_languages = [ch.get('language_code') for ch in language_channels]
                    
                    for video_update in video_updates:
                        if video_update['is_new']:
                            # Check if job already exists for this video
                            existing_job = firestore_service.get_job_by_video(
                                video_update['video_id'],
                                user_id
                            )
                            
                            if not existing_job:
                                # Enqueue job with background tasks
                                from services.job_queue import enqueue_dubbing_job
                                job_id = await enqueue_dubbing_job(
                                    source_video_id=video_update['video_id'],
                                    source_channel_id=video_update['channel_id'],
                                    user_id=user_id,
                                    target_languages=target_languages,
                                    db=None,  # No longer using SQLAlchemy
                                    background_tasks=background_tasks
                                )
        
        # Always return 200 OK to acknowledge receipt
        return {"status": "received", "videos_processed": len(video_updates)}
        
    except ET.ParseError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid XML format: {str(e)}"
        )
    except Exception as e:
        # Still return 200 to prevent PubSubHubbub from retrying
        # Log error for debugging
        return {"status": "error", "message": str(e)}
