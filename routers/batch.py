"""Batch upload router — playlist fetch and AI autofill."""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import httpx
import re
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batch", tags=["batch"])

MAX_BATCH_VIDEOS = 15


# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _extract_video_id(url: str) -> Optional[str]:
    url = url.strip()
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/v\/)([a-zA-Z0-9_-]{11})',
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url):
        return url
    return None


def _extract_playlist_id(url: str) -> Optional[str]:
    url = url.strip()
    m = re.search(r'[?&]list=([a-zA-Z0-9_-]+)', url)
    return m.group(1) if m else None


async def _oembed_fetch(video_id: str, client: httpx.AsyncClient) -> dict:
    """Fetch basic metadata for a single video via YouTube oEmbed (no API key needed)."""
    try:
        yt_url = f"https://www.youtube.com/watch?v={video_id}"
        r = await client.get(
            "https://www.youtube.com/oembed",
            params={"url": yt_url, "format": "json"},
            timeout=8,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "video_id": video_id,
                "title": data.get("title", ""),
                "description": "",
                "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
                "channel_title": data.get("author_name", ""),
                "url": yt_url,
            }
    except Exception as e:
        logger.warning(f"oEmbed failed for {video_id}: {e}")
    return {
        "video_id": video_id,
        "title": "",
        "description": "",
        "thumbnail_url": f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
        "channel_title": "",
        "url": f"https://www.youtube.com/watch?v={video_id}",
    }


# ──────────────────────────────────────────────
# Schemas
# ──────────────────────────────────────────────

class VideoMetadata(BaseModel):
    video_id: str
    title: str
    description: str
    thumbnail_url: str
    channel_title: str
    url: str


class PlaylistResponse(BaseModel):
    playlist_id: Optional[str]
    videos: List[VideoMetadata]
    total_fetched: int
    truncated: bool


class AutofillRequest(BaseModel):
    videos: List[VideoMetadata]
    target_languages: List[str]


class AutofilledVideo(BaseModel):
    video_id: str
    original_title: str
    original_description: str
    suggested_title: str
    suggested_description: str


class AutofillResponse(BaseModel):
    videos: List[AutofilledVideo]


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("/playlist", response_model=PlaylistResponse)
async def fetch_playlist(
    url: str = Query(..., description="YouTube playlist URL or individual video URL"),
):
    """
    Fetch up to 15 videos from a YouTube playlist URL.
    Falls back to oEmbed for individual video URLs.
    """
    from config import settings

    playlist_id = _extract_playlist_id(url)
    video_id_direct = _extract_video_id(url) if not playlist_id else None

    api_key = getattr(settings, "youtube_api_key", None)
    has_real_api_key = bool(api_key) and api_key != "your_api_key_here"

    async with httpx.AsyncClient() as client:
        # ── Single video URL ──────────────────
        if video_id_direct and not playlist_id:
            meta = await _oembed_fetch(video_id_direct, client)
            return PlaylistResponse(
                playlist_id=None,
                videos=[VideoMetadata(**meta)],
                total_fetched=1,
                truncated=False,
            )

        # ── Playlist via YouTube Data API ─────
        if playlist_id and has_real_api_key:
            try:
                videos: List[VideoMetadata] = []
                next_page_token = None

                while len(videos) < MAX_BATCH_VIDEOS:
                    params: dict = {
                        "part": "snippet",
                        "playlistId": playlist_id,
                        "maxResults": min(50, MAX_BATCH_VIDEOS - len(videos)),
                        "key": api_key,
                    }
                    if next_page_token:
                        params["pageToken"] = next_page_token

                    r = await client.get(
                        "https://www.googleapis.com/youtube/v3/playlistItems",
                        params=params,
                        timeout=10,
                    )
                    if r.status_code != 200:
                        raise HTTPException(
                            status_code=r.status_code,
                            detail=f"YouTube API error: {r.text[:200]}",
                        )
                    data = r.json()
                    items = data.get("items", [])
                    for item in items:
                        sn = item.get("snippet", {})
                        vid = sn.get("resourceId", {}).get("videoId", "")
                        if not vid:
                            continue
                        thumbs = sn.get("thumbnails", {})
                        thumb_url = (
                            thumbs.get("maxres", {}).get("url")
                            or thumbs.get("high", {}).get("url")
                            or thumbs.get("default", {}).get("url")
                            or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
                        )
                        videos.append(
                            VideoMetadata(
                                video_id=vid,
                                title=sn.get("title", ""),
                                description=sn.get("description", ""),
                                thumbnail_url=thumb_url,
                                channel_title=sn.get("channelTitle", ""),
                                url=f"https://www.youtube.com/watch?v={vid}",
                            )
                        )
                        if len(videos) >= MAX_BATCH_VIDEOS:
                            break

                    next_page_token = data.get("nextPageToken")
                    if not next_page_token or len(videos) >= MAX_BATCH_VIDEOS:
                        break

                total_in_playlist = data.get("pageInfo", {}).get("totalResults", len(videos))
                return PlaylistResponse(
                    playlist_id=playlist_id,
                    videos=videos,
                    total_fetched=len(videos),
                    truncated=total_in_playlist > MAX_BATCH_VIDEOS,
                )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"YouTube Data API playlist fetch failed: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # ── Playlist but no API key — ask client to supply individual IDs ──
        if playlist_id and not has_real_api_key:
            raise HTTPException(
                status_code=422,
                detail=(
                    "Playlist import requires a YouTube Data API key. "
                    "Please paste individual video URLs instead."
                ),
            )

        raise HTTPException(status_code=422, detail="Could not parse a video ID or playlist ID from the provided URL.")


@router.get("/video", response_model=VideoMetadata)
async def fetch_single_video(
    url: str = Query(..., description="YouTube video URL or ID"),
):
    """Fetch metadata for a single YouTube video via oEmbed."""
    video_id = _extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=422, detail="Could not extract a YouTube video ID from the URL.")
    async with httpx.AsyncClient() as client:
        meta = await _oembed_fetch(video_id, client)
    return VideoMetadata(**meta)


class AutofillRequest(BaseModel):
    videos: List[VideoMetadata]
    target_languages: List[str]
    source_language: Optional[str] = "en"


@router.post("/autofill", response_model=AutofillResponse)
async def autofill_metadata(body: AutofillRequest):
    """
    Use Gemini to suggest optimised titles and descriptions for each video,
    taking the target translation languages into account.
    """
    from config import settings
    import json

    gemini_key = getattr(settings, "gemini_api_key", None)
    if not gemini_key:
        raise HTTPException(status_code=503, detail="Gemini API key not configured.")

    lang_list = ", ".join(body.target_languages) if body.target_languages else "multiple languages"

    results: List[AutofilledVideo] = []

    async with httpx.AsyncClient() as client:
        for video in body.videos:
            prompt = f"""You are a YouTube content localisation expert.

Given this video:
Title: {video.title or "(no title)"}
Description: {video.description or "(no description)"}
Channel: {video.channel_title or "unknown"}

This video will be dubbed into these languages: {lang_list}.

Produce an improved English title and description that will work well as a base for translation into those languages.
Guidelines:
- Title: concise, compelling, ≤ 80 characters, no emojis
- Description: 2-4 sentences, clear, informative, SEO-friendly, suitable for a translated audience

Respond with valid JSON only — no markdown fences, no extra text:
{{"title": "...", "description": "..."}}"""

            try:
                r = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}",
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 512},
                    },
                    timeout=20,
                )
                if r.status_code != 200:
                    logger.warning(f"Gemini error for {video.video_id}: {r.text[:200]}")
                    results.append(AutofilledVideo(
                        video_id=video.video_id,
                        original_title=video.title,
                        original_description=video.description,
                        suggested_title=video.title,
                        suggested_description=video.description,
                    ))
                    continue

                data = r.json()
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Strip markdown fences if present
                raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
                raw_text = re.sub(r"\n?```$", "", raw_text)
                parsed = json.loads(raw_text)

                results.append(AutofilledVideo(
                    video_id=video.video_id,
                    original_title=video.title,
                    original_description=video.description,
                    suggested_title=parsed.get("title", video.title),
                    suggested_description=parsed.get("description", video.description),
                ))
            except Exception as e:
                logger.error(f"Autofill failed for {video.video_id}: {e}")
                results.append(AutofilledVideo(
                    video_id=video.video_id,
                    original_title=video.title,
                    original_description=video.description,
                    suggested_title=video.title,
                    suggested_description=video.description,
                ))

    return AutofillResponse(videos=results)
