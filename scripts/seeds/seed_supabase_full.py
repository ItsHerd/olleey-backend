#!/usr/bin/env python3
"""
Canonical Supabase-only seed script.

Modes:
  --seed    Upsert deterministic demo data
  --reset   Delete deterministic demo data first (safe order)
  --verify  Run integrity and count checks

Examples:
  python scripts/seeds/seed_supabase_full.py --seed --verify
  python scripts/seeds/seed_supabase_full.py --reset
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

from supabase import Client, create_client


# Keep parent path import style consistent with existing seed scripts.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def utc_iso(days_ago: int = 0, minutes_offset: int = 0) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago) + timedelta(minutes=minutes_offset)
    return dt.isoformat()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed Supabase with complete deterministic demo data.")
    parser.add_argument("--seed", action="store_true", help="Upsert canonical seed data.")
    parser.add_argument("--reset", action="store_true", help="Delete canonical seed data first.")
    parser.add_argument("--verify", action="store_true", help="Verify seeded data integrity and counts.")
    parser.add_argument(
        "--env",
        default=".env",
        help="Path to env file (used only for display; vars are read from process environment).",
    )
    return parser.parse_args()


def get_client() -> Client:
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY/SUPABASE_ANON_KEY in environment.")
    return create_client(supabase_url, supabase_key)


@dataclass(frozen=True)
class SeedIds:
    user_primary: str = "096c8549-ce41-4b94-b7f7-25e39eb7578b"
    user_secondary: str = "2f1f4f29-4e56-4fe0-97be-a4a3c1b0f002"

    project_alpha: str = "3e1c4f29-4e56-4fe0-97be-a4a3c1b0f101"
    project_beta: str = "3e1c4f29-4e56-4fe0-97be-a4a3c1b0f102"
    project_secondary: str = "3e1c4f29-4e56-4fe0-97be-a4a3c1b0f103"

    # Source channels
    channel_master_en: str = "UCSEEDMASTEREN00000000001"
    channel_sat_es: str = "UCSEEDSATES0000000000001"
    channel_sat_fr: str = "UCSEEDSATFR0000000000001"
    channel_sat_de: str = "UCSEEDSATDE0000000000001"
    channel_secondary_en: str = "UCSEEDSECONDARY000000001"

    # YouTube connections
    conn_master: str = "4e1c4f29-4e56-4fe0-97be-a4a3c1b0f201"
    conn_es: str = "4e1c4f29-4e56-4fe0-97be-a4a3c1b0f202"
    conn_fr: str = "4e1c4f29-4e56-4fe0-97be-a4a3c1b0f203"
    conn_de: str = "4e1c4f29-4e56-4fe0-97be-a4a3c1b0f204"

    # Jobs
    job_completed: str = "5e1c4f29-4e56-4fe0-97be-a4a3c1b0f301"
    job_waiting: str = "5e1c4f29-4e56-4fe0-97be-a4a3c1b0f302"
    job_processing: str = "5e1c4f29-4e56-4fe0-97be-a4a3c1b0f303"
    job_failed: str = "5e1c4f29-4e56-4fe0-97be-a4a3c1b0f304"

    # Pipeline detail chain for completed job
    transcript_completed: str = "6e1c4f29-4e56-4fe0-97be-a4a3c1b0f401"
    translation_completed_es: str = "6e1c4f29-4e56-4fe0-97be-a4a3c1b0f402"
    dubbed_audio_completed_es: str = "6e1c4f29-4e56-4fe0-97be-a4a3c1b0f403"
    lipsync_completed_es: str = "6e1c4f29-4e56-4fe0-97be-a4a3c1b0f404"

    # Localized video IDs
    loc_completed_es: str = "7e1c4f29-4e56-4fe0-97be-a4a3c1b0f501"
    loc_waiting_fr: str = "7e1c4f29-4e56-4fe0-97be-a4a3c1b0f502"
    loc_processing_de: str = "7e1c4f29-4e56-4fe0-97be-a4a3c1b0f503"
    loc_failed_es: str = "7e1c4f29-4e56-4fe0-97be-a4a3c1b0f504"


IDS = SeedIds()


def seed_users() -> List[Dict[str, Any]]:
    return [
        {
            "id": IDS.user_primary,
            "user_id": IDS.user_primary,
            "email": "demo@olleey.com",
            "name": "Demo User",
            "access_token": "seed-access-token-demo",
            "refresh_token": "seed-refresh-token-demo",
            "token_expiry": utc_iso(days_ago=-7),
            "created_at": utc_iso(days_ago=60),
            "updated_at": utc_iso(days_ago=0),
        }
    ]


def seed_projects() -> List[Dict[str, Any]]:
    return [
        {
            "id": IDS.project_alpha,
            "user_id": IDS.user_primary,
            "name": "Global Creator Lab",
            "description": "Primary project for multilingual publication",
            "settings": {"default_visibility": "public", "auto_publish": False},
            "created_at": utc_iso(days_ago=40),
            "updated_at": utc_iso(days_ago=0),
        },
        {
            "id": IDS.project_beta,
            "user_id": IDS.user_primary,
            "name": "Shorts Expansion",
            "description": "Short-form localized content",
            "settings": {"default_visibility": "unlisted", "auto_publish": False},
            "created_at": utc_iso(days_ago=35),
            "updated_at": utc_iso(days_ago=1),
        }
    ]


def seed_channels() -> List[Dict[str, Any]]:
    return [
        {
            "channel_id": IDS.channel_master_en,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_alpha,
            "channel_name": "Olleey English Master",
            "language_code": "en",
            "language_name": "English",
            "is_master": True,
            "master_channel_id": None,
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
            "subscriber_count": 125000,
            "video_count": 284,
            "created_at": utc_iso(days_ago=40),
            "updated_at": utc_iso(days_ago=0),
        },
        {
            "channel_id": IDS.channel_sat_es,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_alpha,
            "channel_name": "Olleey Espanol",
            "language_code": "es",
            "language_name": "Spanish",
            "is_master": False,
            "master_channel_id": IDS.channel_master_en,
            "thumbnail_url": "https://i.ytimg.com/vi/9bZkp7q19f0/default.jpg",
            "subscriber_count": 44000,
            "video_count": 91,
            "created_at": utc_iso(days_ago=35),
            "updated_at": utc_iso(days_ago=0),
        },
        {
            "channel_id": IDS.channel_sat_fr,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_alpha,
            "channel_name": "Olleey Francais",
            "language_code": "fr",
            "language_name": "French",
            "is_master": False,
            "master_channel_id": IDS.channel_master_en,
            "thumbnail_url": "https://i.ytimg.com/vi/eY52Zsg-KVI/default.jpg",
            "subscriber_count": 18000,
            "video_count": 42,
            "created_at": utc_iso(days_ago=30),
            "updated_at": utc_iso(days_ago=0),
        },
        {
            "channel_id": IDS.channel_sat_de,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_alpha,
            "channel_name": "Olleey Deutsch",
            "language_code": "de",
            "language_name": "German",
            "is_master": False,
            "master_channel_id": IDS.channel_master_en,
            "thumbnail_url": "https://i.ytimg.com/vi/kJQP7kiw5Fk/default.jpg",
            "subscriber_count": 12000,
            "video_count": 29,
            "created_at": utc_iso(days_ago=25),
            "updated_at": utc_iso(days_ago=0),
        }
    ]


def seed_youtube_connections() -> List[Dict[str, Any]]:
    now = utc_iso(days_ago=0)
    return [
        {
            "connection_id": IDS.conn_master,
            "user_id": IDS.user_primary,
            "youtube_channel_id": IDS.channel_master_en,
            "youtube_channel_name": "Olleey English Master",
            "channel_avatar_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
            "access_token": "seed-yt-access-master",
            "refresh_token": "seed-yt-refresh-master",
            "token_expiry": utc_iso(days_ago=-6),
            "is_primary": True,
            "language_code": "en",
            "master_connection_id": None,
            "connection_type": "master",
            "created_at": utc_iso(days_ago=40),
            "updated_at": now,
        },
        {
            "connection_id": IDS.conn_es,
            "user_id": IDS.user_primary,
            "youtube_channel_id": IDS.channel_sat_es,
            "youtube_channel_name": "Olleey Espanol",
            "channel_avatar_url": "https://i.ytimg.com/vi/9bZkp7q19f0/default.jpg",
            "access_token": "seed-yt-access-es",
            "refresh_token": "seed-yt-refresh-es",
            "token_expiry": utc_iso(days_ago=-6),
            "is_primary": False,
            "language_code": "es",
            "master_connection_id": IDS.conn_master,
            "connection_type": "satellite",
            "created_at": utc_iso(days_ago=35),
            "updated_at": now,
        },
        {
            "connection_id": IDS.conn_fr,
            "user_id": IDS.user_primary,
            "youtube_channel_id": IDS.channel_sat_fr,
            "youtube_channel_name": "Olleey Francais",
            "channel_avatar_url": "https://i.ytimg.com/vi/eY52Zsg-KVI/default.jpg",
            "access_token": "seed-yt-access-fr",
            "refresh_token": "seed-yt-refresh-fr",
            "token_expiry": utc_iso(days_ago=-6),
            "is_primary": False,
            "language_code": "fr",
            "master_connection_id": IDS.conn_master,
            "connection_type": "satellite",
            "created_at": utc_iso(days_ago=30),
            "updated_at": now,
        },
        {
            "connection_id": IDS.conn_de,
            "user_id": IDS.user_primary,
            "youtube_channel_id": IDS.channel_sat_de,
            "youtube_channel_name": "Olleey Deutsch",
            "channel_avatar_url": "https://i.ytimg.com/vi/kJQP7kiw5Fk/default.jpg",
            "access_token": "seed-yt-access-de",
            "refresh_token": "seed-yt-refresh-de",
            "token_expiry": utc_iso(days_ago=-6),
            "is_primary": False,
            "language_code": "de",
            "master_connection_id": IDS.conn_master,
            "connection_type": "satellite",
            "created_at": utc_iso(days_ago=25),
            "updated_at": now,
        },
    ]


def seed_videos() -> List[Dict[str, Any]]:
    vids: List[Dict[str, Any]] = []
    base = [
        ("vid_seed_001", "How We Build Multilingual Workflows", 640, IDS.project_alpha, IDS.channel_master_en),
        ("vid_seed_002", "Startup Storytelling Frameworks", 420, IDS.project_alpha, IDS.channel_master_en),
        ("vid_seed_003", "Product Demo Deep Dive", 380, IDS.project_alpha, IDS.channel_master_en),
        ("vid_seed_004", "Shorts Growth Tactics", 78, IDS.project_beta, IDS.channel_master_en),
        ("vid_seed_005", "Creator Operations Checklist", 240, IDS.project_beta, IDS.channel_master_en),
    ]
    for idx, (video_id, title, duration, project_id, channel_id) in enumerate(base):
        vids.append(
            {
                "video_id": video_id,
                "user_id": IDS.user_primary,
                "project_id": project_id,
                "channel_id": channel_id,
                "channel_name": "Olleey English Master",
                "title": title,
                "description": f"Seeded source video {idx + 1} for integration testing.",
                "thumbnail_url": f"https://i.ytimg.com/vi/dQw4w9WgXcQ/{'hqdefault.jpg' if idx % 2 == 0 else 'mqdefault.jpg'}",
                "storage_url": f"https://olleey-videos.s3.us-west-1.amazonaws.com/{video_id}.mp4",
                "video_url": f"https://www.youtube.com/watch?v={video_id[:11]:<11}".replace(" ", "x"),
                "duration": duration,
                "view_count": 5000 + (idx * 777),
                "like_count": 400 + (idx * 31),
                "comment_count": 75 + (idx * 9),
                "status": "live",
                "language_code": "en",
                "published_at": utc_iso(days_ago=20 - idx),
                "created_at": utc_iso(days_ago=20 - idx),
                "updated_at": utc_iso(days_ago=1),
            }
        )
    return vids


def seed_processing_jobs() -> List[Dict[str, Any]]:
    return [
        {
            "id": IDS.job_completed,
            "job_id": IDS.job_completed,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_alpha,
            "source_video_id": "vid_seed_001",
            "source_channel_id": IDS.channel_master_en,
            "target_languages": ["es"],
            "status": "completed",
            "progress": 100,
            "workflow_state": {"metadata_extraction": {"status": "completed", "progress": 100}},
            "source_language": "en",
            "estimated_cost": 7.5,
            "actual_cost": 7.2,
            "cost_breakdown": {"transcription": 1.2, "translation": 0.9, "dubbing": 3.1, "lip_sync": 2.0},
            "current_stage": "completed",
            "dubbing_metadata": {"provider": "elevenlabs", "voice_profile": "standard"},
            "processing_time_seconds": 1800,
            "created_at": utc_iso(days_ago=8),
            "updated_at": utc_iso(days_ago=8, minutes_offset=35),
            "completed_at": utc_iso(days_ago=8, minutes_offset=40),
        },
        {
            "id": IDS.job_waiting,
            "job_id": IDS.job_waiting,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_alpha,
            "source_video_id": "vid_seed_002",
            "source_channel_id": IDS.channel_master_en,
            "target_languages": ["fr"],
            "status": "waiting_approval",
            "progress": 100,
            "workflow_state": {"review": {"status": "waiting_approval", "progress": 100}},
            "source_language": "en",
            "estimated_cost": 5.4,
            "actual_cost": 5.3,
            "cost_breakdown": {"transcription": 1.0, "translation": 0.8, "dubbing": 2.2, "lip_sync": 1.3},
            "current_stage": "waiting_approval",
            "dubbing_metadata": {"provider": "elevenlabs"},
            "processing_time_seconds": 1420,
            "created_at": utc_iso(days_ago=6),
            "updated_at": utc_iso(days_ago=6, minutes_offset=28),
        },
        {
            "id": IDS.job_processing,
            "job_id": IDS.job_processing,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_beta,
            "source_video_id": "vid_seed_004",
            "source_channel_id": IDS.channel_master_en,
            "target_languages": ["de"],
            "status": "processing",
            "progress": 58,
            "workflow_state": {"dubbing": {"status": "processing", "progress": 58}},
            "source_language": "en",
            "estimated_cost": 2.1,
            "actual_cost": None,
            "cost_breakdown": {"transcription": 0.3, "translation": 0.2, "dubbing": 0.7, "lip_sync": 0.9},
            "current_stage": "dubbing",
            "dubbing_metadata": {"provider": "elevenlabs"},
            "processing_time_seconds": 410,
            "created_at": utc_iso(days_ago=1),
            "updated_at": utc_iso(days_ago=0),
        },
        {
            "id": IDS.job_failed,
            "job_id": IDS.job_failed,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_beta,
            "source_video_id": "vid_seed_005",
            "source_channel_id": IDS.channel_master_en,
            "target_languages": ["es"],
            "status": "failed",
            "progress": 22,
            "workflow_state": {"translation": {"status": "failed", "progress": 22}},
            "source_language": "en",
            "estimated_cost": 3.0,
            "actual_cost": 1.1,
            "cost_breakdown": {"transcription": 0.4, "translation": 0.7, "dubbing": 0.0, "lip_sync": 0.0},
            "current_stage": "translating",
            "dubbing_metadata": {"provider": "elevenlabs", "error_stage": "translation"},
            "processing_time_seconds": 260,
            "error_message": "Translation provider timeout",
            "created_at": utc_iso(days_ago=3),
            "updated_at": utc_iso(days_ago=3, minutes_offset=14),
        },
    ]


def seed_transcripts() -> List[Dict[str, Any]]:
    return [
        {
            "id": IDS.transcript_completed,
            "job_id": IDS.job_completed,
            "video_id": "vid_seed_001",
            "user_id": IDS.user_primary,
            "language_code": "en",
            "transcript_text": "Welcome to this seeded transcript used for end-to-end flow validation.",
            "word_timestamps": [],
            "provider": "elevenlabs",
            "confidence_score": 0.97,
            "duration": 640,
            "status": "completed",
            "created_at": utc_iso(days_ago=8),
            "updated_at": utc_iso(days_ago=8, minutes_offset=10),
        }
    ]


def seed_translations() -> List[Dict[str, Any]]:
    return [
        {
            "id": IDS.translation_completed_es,
            "transcript_id": IDS.transcript_completed,
            "job_id": IDS.job_completed,
            "video_id": "vid_seed_001",
            "user_id": IDS.user_primary,
            "source_language": "en",
            "target_language": "es",
            "translated_text": "Bienvenido a este transcript de prueba para validar el flujo completo.",
            "word_timestamps": [],
            "provider": "elevenlabs",
            "confidence_score": 0.95,
            "status": "completed",
            "reviewed": True,
            "created_at": utc_iso(days_ago=8),
            "updated_at": utc_iso(days_ago=8, minutes_offset=14),
        }
    ]


def seed_dubbed_audio() -> List[Dict[str, Any]]:
    return [
        {
            "id": IDS.dubbed_audio_completed_es,
            "translation_id": IDS.translation_completed_es,
            "job_id": IDS.job_completed,
            "language_code": "es",
            "user_id": IDS.user_primary,
            "audio_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/vid_seed_001_es.mp3",
            "duration": 640,
            "file_size": 8_200_000,
            "format": "mp3",
            "voice_id": "voice_seed_es_01",
            "voice_name": "Lucia",
            "voice_settings": {"stability": 0.6, "style": 0.45},
            "segments": [],
            "provider": "elevenlabs",
            "status": "completed",
            "created_at": utc_iso(days_ago=8),
            "updated_at": utc_iso(days_ago=8, minutes_offset=19),
        }
    ]


def seed_lip_sync_jobs() -> List[Dict[str, Any]]:
    return [
        {
            "id": IDS.lipsync_completed_es,
            "job_id": IDS.job_completed,
            "dubbed_audio_id": IDS.dubbed_audio_completed_es,
            "language_code": "es",
            "user_id": IDS.user_primary,
            "synclabs_job_id": "syn_seed_completed_es_001",
            "status": "completed",
            "progress": 100,
            "input_video_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/vid_seed_001.mp4",
            "input_audio_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/vid_seed_001_es.mp3",
            "output_video_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/vid_seed_001_es.mov",
            "quality_score": 0.94,
            "processing_time_seconds": 420,
            "cost": 2.0,
            "created_at": utc_iso(days_ago=8),
            "completed_at": utc_iso(days_ago=8, minutes_offset=25),
        }
    ]


def seed_localized_videos() -> List[Dict[str, Any]]:
    return [
        {
            "id": IDS.loc_completed_es,
            "job_id": IDS.job_completed,
            "source_video_id": "vid_seed_001",
            "localized_video_id": "yt_seed_loc_es_001",
            "user_id": IDS.user_primary,
            "project_id": IDS.project_alpha,
            "channel_id": IDS.channel_sat_es,
            "language_code": "es",
            "title": "How We Build Multilingual Workflows (ES)",
            "description": "Version en espanol del video de muestra.",
            "video_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/vid_seed_001_es.mov",
            "storage_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/vid_seed_001_es.mov",
            "thumbnail_url": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
            "status": "live",
            "duration": 640,
            "transcript_id": IDS.transcript_completed,
            "translation_id": IDS.translation_completed_es,
            "dubbed_audio_id": IDS.dubbed_audio_completed_es,
            "lip_sync_job_id": IDS.lipsync_completed_es,
            "dubbed_audio_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/vid_seed_001_es.mp3",
            "created_at": utc_iso(days_ago=8),
            "updated_at": utc_iso(days_ago=8, minutes_offset=30),
        },
        {
            "id": IDS.loc_waiting_fr,
            "job_id": IDS.job_waiting,
            "source_video_id": "vid_seed_002",
            "localized_video_id": None,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_alpha,
            "channel_id": IDS.channel_sat_fr,
            "language_code": "fr",
            "title": "Startup Storytelling Frameworks (FR)",
            "description": "Version francaise en attente d'approbation.",
            "video_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/vid_seed_002_fr.mov",
            "storage_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/vid_seed_002_fr.mov",
            "thumbnail_url": "https://i.ytimg.com/vi/eY52Zsg-KVI/hqdefault.jpg",
            "status": "draft",
            "duration": 420,
            "created_at": utc_iso(days_ago=6),
            "updated_at": utc_iso(days_ago=6, minutes_offset=29),
        },
        {
            "id": IDS.loc_processing_de,
            "job_id": IDS.job_processing,
            "source_video_id": "vid_seed_004",
            "localized_video_id": None,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_beta,
            "channel_id": IDS.channel_sat_de,
            "language_code": "de",
            "title": "Shorts Growth Tactics (DE)",
            "description": "Deutsche Fassung in Bearbeitung.",
            "video_url": None,
            "storage_url": None,
            "thumbnail_url": "https://i.ytimg.com/vi/kJQP7kiw5Fk/hqdefault.jpg",
            "status": "processing",
            "duration": 78,
            "created_at": utc_iso(days_ago=1),
            "updated_at": utc_iso(days_ago=0),
        },
        {
            "id": IDS.loc_failed_es,
            "job_id": IDS.job_failed,
            "source_video_id": "vid_seed_005",
            "localized_video_id": None,
            "user_id": IDS.user_primary,
            "project_id": IDS.project_beta,
            "channel_id": IDS.channel_sat_es,
            "language_code": "es",
            "title": "Creator Operations Checklist (ES)",
            "description": "Version en espanol fallo durante traduccion.",
            "video_url": None,
            "storage_url": None,
            "thumbnail_url": "https://i.ytimg.com/vi/9bZkp7q19f0/hqdefault.jpg",
            "status": "failed",
            "duration": 240,
            "created_at": utc_iso(days_ago=3),
            "updated_at": utc_iso(days_ago=3, minutes_offset=15),
        },
    ]


def seed_activity_logs() -> List[Dict[str, Any]]:
    return [
        {
            "id": "8e1c4f29-4e56-4fe0-97be-a4a3c1b0f601",
            "user_id": IDS.user_primary,
            "project_id": IDS.project_alpha,
            "action": "Seeded completed run",
            "status": "success",
            "details": "Created full pipeline chain for job_completed",
            "timestamp": utc_iso(days_ago=8, minutes_offset=40),
        },
        {
            "id": "8e1c4f29-4e56-4fe0-97be-a4a3c1b0f602",
            "user_id": IDS.user_primary,
            "project_id": IDS.project_beta,
            "action": "Seeded failed run",
            "status": "error",
            "details": "Created failed translation scenario for QA coverage",
            "timestamp": utc_iso(days_ago=3, minutes_offset=15),
        },
    ]


def seed_subscriptions() -> List[Dict[str, Any]]:
    return [
        {
            "id": "9e1c4f29-4e56-4fe0-97be-a4a3c1b0f701",
            "user_id": IDS.user_primary,
            "channel_id": IDS.channel_master_en,
            "callback_url": "https://example.com/webhooks/youtube",
            "topic": f"https://www.youtube.com/xml/feeds/videos.xml?channel_id={IDS.channel_master_en}",
            "lease_seconds": 2592000,
            "expires_at": utc_iso(days_ago=-28),
            "secret": "seed-subscription-secret",
            "created_at": utc_iso(days_ago=20),
            "updated_at": utc_iso(days_ago=0),
        }
    ]


def upsert_rows(client: Client, table: str, rows: Sequence[Dict[str, Any]], conflict: Optional[str]) -> None:
    if not rows:
        return
    if conflict:
        client.table(table).upsert(list(rows), on_conflict=conflict).execute()
    else:
        # Fallback if conflict target is unknown; idempotency should be handled by deterministic reset + re-seed.
        client.table(table).upsert(list(rows)).execute()
    print(f"  upserted {len(rows):>3} rows into {table}")


def delete_eq(client: Client, table: str, column: str, values: Iterable[str]) -> None:
    vals = [v for v in values if v]
    if not vals:
        return
    try:
        client.table(table).delete().in_(column, vals).execute()
        print(f"  deleted {len(vals):>3} keys from {table}.{column}")
    except Exception as exc:
        print(f"  skipped delete on {table}.{column} ({exc})")


def table_exists(client: Client, table: str) -> bool:
    try:
        client.table(table).select("*").limit(1).execute()
        return True
    except Exception:
        return False


def run_reset(client: Client) -> None:
    print("\n🧹 Resetting canonical seed data...")

    # Children first.
    delete_eq(client, "localized_videos", "id", [IDS.loc_completed_es, IDS.loc_waiting_fr, IDS.loc_processing_de, IDS.loc_failed_es])
    delete_eq(client, "lip_sync_jobs", "id", [IDS.lipsync_completed_es])
    delete_eq(client, "dubbed_audio", "id", [IDS.dubbed_audio_completed_es])
    delete_eq(client, "translations", "id", [IDS.translation_completed_es])
    delete_eq(client, "transcripts", "id", [IDS.transcript_completed])
    delete_eq(client, "processing_jobs", "job_id", [IDS.job_completed, IDS.job_waiting, IDS.job_processing, IDS.job_failed])

    # Optional tables.
    if table_exists(client, "activity_logs"):
        delete_eq(
            client,
            "activity_logs",
            "id",
            ["8e1c4f29-4e56-4fe0-97be-a4a3c1b0f601", "8e1c4f29-4e56-4fe0-97be-a4a3c1b0f602"],
        )
    if table_exists(client, "subscriptions"):
        delete_eq(client, "subscriptions", "id", ["9e1c4f29-4e56-4fe0-97be-a4a3c1b0f701"])

    delete_eq(client, "videos", "video_id", [f"vid_seed_00{i}" for i in range(1, 7)])
    delete_eq(client, "youtube_connections", "connection_id", [IDS.conn_master, IDS.conn_es, IDS.conn_fr, IDS.conn_de])
    delete_eq(
        client,
        "channels",
        "channel_id",
        [IDS.channel_master_en, IDS.channel_sat_es, IDS.channel_sat_fr, IDS.channel_sat_de, IDS.channel_secondary_en],
    )
    delete_eq(client, "projects", "id", [IDS.project_alpha, IDS.project_beta, IDS.project_secondary])
    # Also clear by seed emails in case same emails exist under different UUIDs.
    delete_eq(client, "users", "email", ["demo@olleey.com", "qa@olleey.com"])
    delete_eq(client, "users", "id", [IDS.user_primary, IDS.user_secondary])


def run_seed(client: Client) -> None:
    print("\n🌱 Seeding canonical Supabase dataset...")
    upsert_rows(client, "users", seed_users(), "id")
    upsert_rows(client, "projects", seed_projects(), "id")
    upsert_rows(client, "channels", seed_channels(), "channel_id")
    upsert_rows(client, "youtube_connections", seed_youtube_connections(), "connection_id")
    upsert_rows(client, "videos", seed_videos(), "video_id")
    upsert_rows(client, "processing_jobs", seed_processing_jobs(), "job_id")
    upsert_rows(client, "transcripts", seed_transcripts(), "id")
    upsert_rows(client, "translations", seed_translations(), "id")
    upsert_rows(client, "dubbed_audio", seed_dubbed_audio(), "id")
    upsert_rows(client, "lip_sync_jobs", seed_lip_sync_jobs(), "id")
    upsert_rows(client, "localized_videos", seed_localized_videos(), "id")

    # Optional tables that may not exist in every environment yet.
    if table_exists(client, "activity_logs"):
        upsert_rows(client, "activity_logs", seed_activity_logs(), "id")
    else:
        print("  skipped activity_logs (table not found)")

    if table_exists(client, "subscriptions"):
        upsert_rows(client, "subscriptions", seed_subscriptions(), "id")
    else:
        print("  skipped subscriptions (table not found)")


def count_rows(client: Client, table: str, id_column: str, ids: Sequence[str]) -> int:
    result = client.table(table).select(id_column, count="exact").in_(id_column, list(ids)).execute()
    return result.count or 0


def verify_fk_presence(client: Client, table: str, key: str, values: Sequence[str], label: str) -> bool:
    result = client.table(table).select(key).in_(key, list(values)).execute()
    found = {row[key] for row in (result.data or []) if key in row}
    missing = [v for v in values if v not in found]
    if missing:
        print(f"  ✗ {label} missing: {missing}")
        return False
    print(f"  ✓ {label} present ({len(values)})")
    return True


def run_verify(client: Client) -> bool:
    print("\n🔎 Verifying seeded dataset...")
    ok = True

    checks = [
        ("users", "id", [IDS.user_primary], 1),
        ("projects", "id", [IDS.project_alpha, IDS.project_beta], 2),
        (
            "channels",
            "channel_id",
            [IDS.channel_master_en, IDS.channel_sat_es, IDS.channel_sat_fr, IDS.channel_sat_de],
            4,
        ),
        ("youtube_connections", "connection_id", [IDS.conn_master, IDS.conn_es, IDS.conn_fr, IDS.conn_de], 4),
        ("videos", "video_id", [f"vid_seed_00{i}" for i in range(1, 6)], 5),
        ("processing_jobs", "job_id", [IDS.job_completed, IDS.job_waiting, IDS.job_processing, IDS.job_failed], 4),
        ("localized_videos", "id", [IDS.loc_completed_es, IDS.loc_waiting_fr, IDS.loc_processing_de, IDS.loc_failed_es], 4),
        ("transcripts", "id", [IDS.transcript_completed], 1),
        ("translations", "id", [IDS.translation_completed_es], 1),
        ("dubbed_audio", "id", [IDS.dubbed_audio_completed_es], 1),
        ("lip_sync_jobs", "id", [IDS.lipsync_completed_es], 1),
    ]

    for table, col, ids, expected in checks:
        try:
            c = count_rows(client, table, col, ids)
            state = "✓" if c == expected else "✗"
            print(f"  {state} {table:<18} expected={expected} got={c}")
            ok = ok and (c == expected)
        except Exception as exc:
            print(f"  ✗ {table:<18} verify failed: {exc}")
            ok = False

    # FK-ish linkage checks
    ok = verify_fk_presence(client, "processing_jobs", "job_id", [IDS.job_completed], "completed job") and ok
    ok = verify_fk_presence(client, "transcripts", "job_id", [IDS.job_completed], "transcript->job link") and ok
    ok = verify_fk_presence(client, "translations", "job_id", [IDS.job_completed], "translation->job link") and ok
    ok = verify_fk_presence(client, "dubbed_audio", "job_id", [IDS.job_completed], "dubbed_audio->job link") and ok
    ok = verify_fk_presence(client, "lip_sync_jobs", "job_id", [IDS.job_completed], "lip_sync->job link") and ok
    ok = verify_fk_presence(client, "localized_videos", "job_id", [IDS.job_completed], "localized_video->job link") and ok

    # Dashboard-friendly checks
    try:
        runs = client.table("processing_jobs").select("job_id,status,progress").eq("user_id", IDS.user_primary).execute()
        statuses = {row["status"] for row in (runs.data or [])}
        needed = {"completed", "waiting_approval", "processing", "failed"}
        missing = needed - statuses
        if missing:
            print(f"  ✗ status coverage missing {sorted(missing)}")
            ok = False
        else:
            print("  ✓ status coverage for dashboard/runs view")
    except Exception as exc:
        print(f"  ✗ status coverage check failed: {exc}")
        ok = False

    print("\n✅ verify passed" if ok else "\n❌ verify failed")
    return ok


def main() -> int:
    args = parse_args()
    if not (args.seed or args.reset or args.verify):
        print("No mode selected. Use --seed, --reset, --verify (or combine).")
        return 1

    print("=".ljust(72, "="))
    print("Supabase Full Seed Utility")
    print("=".ljust(72, "="))
    print(f"env file hint: {args.env}")

    client = get_client()
    ok = True

    if args.reset:
        run_reset(client)
    if args.seed:
        run_seed(client)
    if args.verify:
        ok = run_verify(client) and ok

    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())

