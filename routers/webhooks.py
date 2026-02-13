"""Webhook router for PubSubHubbub notifications."""
import hashlib
import hmac
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import asyncio

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse

from routers.youtube_auth import get_youtube_service
from services.supabase_db import supabase_service as firestore_service

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
        subscription = firestore_service.get_subscription_by_topic(hub_topic)
        if not subscription:
            raise HTTPException(status_code=404, detail="Subscription not found")

        if hub_lease_seconds:
            expires_at = datetime.now(timezone.utc) + timedelta(seconds=hub_lease_seconds)
            firestore_service.update_subscription_lease(
                subscription["id"],
                expires_at,
                hub_lease_seconds,
            )

        return PlainTextResponse(content=hub_challenge)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")


def _verify_hub_signature(raw_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify X-Hub-Signature or X-Hub-Signature-256 value."""
    if not signature_header or "=" not in signature_header or not secret:
        return False
    algo, sent_digest = signature_header.split("=", 1)
    algo = algo.lower().strip()
    sent_digest = sent_digest.strip()
    if algo == "sha1":
        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha1).hexdigest()
    elif algo == "sha256":
        digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    else:
        return False
    return hmac.compare_digest(digest, sent_digest)


async def _fetch_video_metadata(user_id: str, video_id: str) -> Optional[Dict[str, Any]]:
    """Fetch source video metadata via YouTube Data API."""
    try:
        youtube = await asyncio.to_thread(get_youtube_service, user_id, None, False)
        if not youtube:
            return None
        req = youtube.videos().list(part="snippet,contentDetails,statistics", id=video_id)
        response = await asyncio.to_thread(req.execute)
        items = response.get("items", [])
        if not items:
            return None
        item = items[0]
        snippet = item.get("snippet", {})
        thumbnails = snippet.get("thumbnails", {})
        preferred_thumb = (
            thumbnails.get("maxres")
            or thumbnails.get("standard")
            or thumbnails.get("high")
            or thumbnails.get("medium")
            or thumbnails.get("default")
            or {}
        )
        return {
            "title": snippet.get("title"),
            "description": snippet.get("description"),
            "thumbnail_url": preferred_thumb.get("url"),
            "published_at": snippet.get("publishedAt"),
            "channel_name": snippet.get("channelTitle"),
            "duration": item.get("contentDetails", {}).get("duration"),
            "view_count": item.get("statistics", {}).get("viewCount"),
            "like_count": item.get("statistics", {}).get("likeCount"),
            "comment_count": item.get("statistics", {}).get("commentCount"),
            "language_code": snippet.get("defaultAudioLanguage") or snippet.get("defaultLanguage"),
        }
    except Exception:
        return None


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
        body = await request.body()
        if not body:
            raise HTTPException(status_code=400, detail="Empty request body")

        root = ET.fromstring(body)
        ns = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
        entries = root.findall(".//atom:entry", ns)

        video_updates = []
        for entry in entries:
            video_id_elem = entry.find("yt:videoId", ns)
            channel_id_elem = entry.find("yt:channelId", ns)
            published_elem = entry.find("atom:published", ns)
            updated_elem = entry.find("atom:updated", ns)
            title_elem = entry.find("atom:title", ns)
            if video_id_elem is None or channel_id_elem is None:
                continue

            published_at = published_elem.text if published_elem is not None else None
            updated_at = updated_elem.text if updated_elem is not None else None
            video_updates.append(
                {
                    "video_id": video_id_elem.text,
                    "channel_id": channel_id_elem.text,
                    "published_at": published_at,
                    "updated_at": updated_at,
                    "title": title_elem.text if title_elem is not None else None,
                    "is_new": bool(published_at and updated_at and published_at == updated_at),
                }
            )

        if not video_updates:
            return {"status": "received", "videos_processed": 0, "jobs_created": 0}

        channel_id = video_updates[0]["channel_id"]
        subscription = firestore_service.get_subscription_by_channel(user_id="", channel_id=channel_id)
        if not subscription:
            return {"status": "received", "videos_processed": len(video_updates), "jobs_created": 0}

        secret = subscription.get("secret")
        if secret:
            signature = request.headers.get("x-hub-signature-256") or request.headers.get("x-hub-signature")
            if not signature or not _verify_hub_signature(body, signature, secret):
                raise HTTPException(status_code=401, detail="Invalid webhook signature")

        user_id = subscription.get("user_id")
        if not user_id:
            return {"status": "received", "videos_processed": len(video_updates), "jobs_created": 0}

        language_channels = firestore_service.get_language_channels(user_id)
        target_languages = sorted({ch.get("language_code") for ch in language_channels if ch.get("language_code")})
        if not target_languages:
            return {"status": "received", "videos_processed": len(video_updates), "jobs_created": 0}

        user_settings = firestore_service.get_user_settings(user_id) or {}
        auto_approve = bool(user_settings.get("auto_approve_jobs", False))
        default_project_id = next((ch.get("project_id") for ch in language_channels if ch.get("project_id")), None)

        jobs_created = 0
        from services.job_queue import enqueue_dubbing_job

        for video_update in video_updates:
            if not video_update["is_new"]:
                continue
            video_id = video_update["video_id"]
            existing_job = firestore_service.get_job_by_video(video_id, user_id)
            if existing_job:
                continue

            metadata = await _fetch_video_metadata(user_id, video_id) or {}
            if not metadata:
                firestore_service.log_activity(
                    user_id=user_id,
                    project_id=default_project_id,
                    action="Webhook metadata fetch failed",
                    status="warning",
                    details=f"Could not fetch YouTube metadata for video {video_id}; using fallback values.",
                )

            # Persist source video context for approval UI.
            firestore_service.upsert_video(
                {
                    "video_id": video_id,
                    "source_video_id": video_id,
                    "user_id": user_id,
                    "project_id": default_project_id,
                    "channel_id": video_update["channel_id"],
                    "title": metadata.get("title") or video_update.get("title") or f"Video {video_id}",
                    "description": metadata.get("description") or "",
                    "thumbnail_url": metadata.get("thumbnail_url") or f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                    "published_at": metadata.get("published_at") or video_update.get("published_at"),
                    "duration": metadata.get("duration"),
                    "view_count": metadata.get("view_count"),
                    "like_count": metadata.get("like_count"),
                    "comment_count": metadata.get("comment_count"),
                    "language_code": metadata.get("language_code"),
                    "channel_name": metadata.get("channel_name"),
                    "status": "detected",
                    "video_type": "youtube",
                }
            )

            await enqueue_dubbing_job(
                source_video_id=video_id,
                source_channel_id=video_update["channel_id"],
                user_id=user_id,
                target_languages=target_languages,
                project_id=default_project_id,
                auto_approve=auto_approve,
                metadata={
                    "detected_via": "youtube_webhook",
                    "published_at": video_update.get("published_at"),
                    "updated_at": video_update.get("updated_at"),
                    "title": metadata.get("title") or video_update.get("title"),
                },
                db=None,
                background_tasks=background_tasks,
            )
            jobs_created += 1

        return {"status": "received", "videos_processed": len(video_updates), "jobs_created": jobs_created}
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML format: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "message": str(e)}
