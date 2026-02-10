#!/usr/bin/env python3
"""
Seed Supabase database with data from Firestore.
Can also be used to continuously sync Firestore → Supabase.
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firestore import firestore_service
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://wfjpbrcktxbwasbamchx.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY', '')  # Use service role key for admin operations

if not SUPABASE_KEY:
    print("⚠️  Warning: SUPABASE_SERVICE_KEY not set. Using anon key (limited permissions).")
    SUPABASE_KEY = os.getenv('SUPABASE_ANON_KEY', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6IndmanBicmNrdHhid2FzYmFtY2h4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzA0NDA0OTgsImV4cCI6MjA4NjAxNjQ5OH0.9NY10smFlvcjABQ_V1t1SmacxWpnLaNr96LOtQV5TjI')

# Create Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print(f"🔗 Connected to Supabase: {SUPABASE_URL}")


def transform_timestamp(ts) -> str:
    """Transform Firestore timestamp to ISO string."""
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts, datetime):
        return ts.isoformat()
    if hasattr(ts, 'timestamp'):
        return datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc).isoformat()
    return str(ts)


def sync_projects():
    """Sync projects from Firestore to Supabase."""
    print("\n📁 Syncing Projects...")

    try:
        projects_ref = firestore_service.db.collection('projects')
        docs = projects_ref.stream()

        projects = []
        for doc in docs:
            data = doc.to_dict()
            # Generate UUID if missing
            project_id = data.get('id') or str(uuid.uuid4())

            project = {
                'id': project_id,
                'user_id': data.get('user_id'),
                'name': data.get('name'),
                'description': data.get('description'),
                'settings': data.get('settings', {}),
                'created_at': transform_timestamp(data.get('created_at')),
                'updated_at': transform_timestamp(data.get('updated_at'))
            }
            projects.append(project)

        if projects:
            result = supabase.table('projects').upsert(projects, on_conflict='id').execute()
            print(f"✓ Synced {len(projects)} projects")
        else:
            print("  No projects found")

    except Exception as e:
        print(f"✗ Error syncing projects: {e}")


def sync_channels():
    """Sync channels from Firestore to Supabase."""
    print("\n📺 Syncing Channels...")

    try:
        channels_ref = firestore_service.db.collection('channels')
        docs = channels_ref.stream()

        channels = []
        for doc in docs:
            data = doc.to_dict()
            channel = {
                'channel_id': data.get('channel_id'),
                'user_id': data.get('user_id'),
                'project_id': data.get('project_id'),
                'channel_name': data.get('channel_name'),
                'language_code': data.get('language_code'),
                'language_name': data.get('language_name'),
                'is_master': data.get('is_master', False),
                'master_channel_id': data.get('master_channel_id'),
                'description': data.get('description'),
                'thumbnail_url': data.get('thumbnail_url'),
                'subscriber_count': data.get('subscriber_count', 0),
                'video_count': data.get('video_count', 0),
                'created_at': transform_timestamp(data.get('created_at')),
                'updated_at': transform_timestamp(data.get('updated_at'))
            }
            channels.append(channel)

        if channels:
            result = supabase.table('channels').upsert(channels, on_conflict='channel_id').execute()
            print(f"✓ Synced {len(channels)} channels")
        else:
            print("  No channels found")

    except Exception as e:
        print(f"✗ Error syncing channels: {e}")


def sync_videos():
    """Sync videos from Firestore to Supabase."""
    print("\n🎬 Syncing Videos...")

    try:
        videos_ref = firestore_service.db.collection('videos')
        docs = videos_ref.stream()

        videos = []
        for doc in docs:
            data = doc.to_dict()

            # Cap view counts to PostgreSQL integer max (2147483647)
            view_count = min(data.get('view_count', 0), 2147483647)
            like_count = min(data.get('like_count', 0), 2147483647)
            comment_count = min(data.get('comment_count', 0), 2147483647)

            video = {
                'video_id': data.get('video_id'),
                'user_id': data.get('user_id'),
                'project_id': data.get('project_id'),
                'channel_id': data.get('channel_id'),
                'channel_name': data.get('channel_name'),
                'title': data.get('title'),
                'description': data.get('description'),
                'thumbnail_url': data.get('thumbnail_url'),
                'storage_url': data.get('storage_url'),
                'video_url': data.get('video_url'),
                'duration': data.get('duration'),
                'view_count': view_count,
                'like_count': like_count,
                'comment_count': comment_count,
                'status': data.get('status', 'draft'),
                'language_code': data.get('language_code'),
                'published_at': transform_timestamp(data.get('published_at')),
                'created_at': transform_timestamp(data.get('created_at')),
                'updated_at': transform_timestamp(data.get('updated_at'))
            }
            videos.append(video)

        if videos:
            result = supabase.table('videos').upsert(videos, on_conflict='video_id').execute()
            print(f"✓ Synced {len(videos)} videos")
        else:
            print("  No videos found")

    except Exception as e:
        print(f"✗ Error syncing videos: {e}")


def sync_processing_jobs():
    """Sync processing jobs from Firestore to Supabase."""
    print("\n⚙️  Syncing Processing Jobs...")

    try:
        jobs_ref = firestore_service.db.collection('processing_jobs')
        docs = jobs_ref.stream()

        jobs = []
        for doc in docs:
            data = doc.to_dict()

            # Skip if missing required fields
            if not data.get('user_id') or not data.get('source_video_id'):
                print(f"  Skipping job with missing required fields: {doc.id}")
                continue

            # Generate UUID if missing or empty
            job_id = data.get('job_id') or data.get('id')
            if not job_id or (isinstance(job_id, str) and job_id.strip() == ''):
                job_id = str(uuid.uuid4())

            job = {
                'job_id': job_id,
                'user_id': data.get('user_id'),
                'project_id': data.get('project_id'),
                'source_video_id': data.get('source_video_id'),
                'source_channel_id': data.get('source_channel_id'),
                'target_languages': data.get('target_languages', []),
                'status': data.get('status', 'pending'),
                'workflow_state': data.get('workflow_state', {}),
                'created_at': transform_timestamp(data.get('created_at')),
                'updated_at': transform_timestamp(data.get('updated_at'))
            }
            jobs.append(job)

        if jobs:
            result = supabase.table('processing_jobs').upsert(jobs, on_conflict='job_id').execute()
            print(f"✓ Synced {len(jobs)} processing jobs")
        else:
            print("  No processing jobs found")

    except Exception as e:
        print(f"✗ Error syncing processing jobs: {e}")


def sync_localized_videos():
    """Sync localized videos from Firestore to Supabase."""
    print("\n🌐 Syncing Localized Videos...")

    try:
        localized_ref = firestore_service.db.collection('localized_videos')
        docs = localized_ref.stream()

        localized_videos = []
        for doc in docs:
            data = doc.to_dict()

            # Skip if missing required fields
            if not data.get('user_id') or not data.get('language_code'):
                print(f"  Skipping localized video with missing required fields: {doc.id}")
                continue

            # Generate UUID if missing
            localized_id = data.get('id') or str(uuid.uuid4())

            # Get job_id - might be stored as UUID or reference
            job_id = data.get('job_id')
            if hasattr(job_id, 'id'):
                job_id = job_id.id
            if not job_id or job_id == '':
                job_id = None  # Allow null if job doesn't exist

            localized_video = {
                'id': localized_id,
                'job_id': job_id,
                'source_video_id': data.get('source_video_id'),
                'user_id': data.get('user_id'),
                'project_id': data.get('project_id'),
                'channel_id': data.get('channel_id'),
                'language_code': data.get('language_code'),
                'title': data.get('title'),
                'description': data.get('description'),
                'video_url': data.get('video_url') or data.get('storage_url'),
                'thumbnail_url': data.get('thumbnail_url'),
                'status': data.get('status', 'draft'),
                'duration': data.get('duration'),
                'created_at': transform_timestamp(data.get('created_at')),
                'updated_at': transform_timestamp(data.get('updated_at'))
            }
            localized_videos.append(localized_video)

        if localized_videos:
            result = supabase.table('localized_videos').upsert(localized_videos, on_conflict='id').execute()
            print(f"✓ Synced {len(localized_videos)} localized videos")
        else:
            print("  No localized videos found")

    except Exception as e:
        print(f"✗ Error syncing localized videos: {e}")


def verify_sync():
    """Verify data in Supabase."""
    print("\n📊 Verifying Supabase Data...")

    try:
        # Count records in each table
        projects_count = len(supabase.table('projects').select('id').execute().data)
        channels_count = len(supabase.table('channels').select('channel_id').execute().data)
        videos_count = len(supabase.table('videos').select('video_id').execute().data)
        jobs_count = len(supabase.table('processing_jobs').select('job_id').execute().data)
        localized_count = len(supabase.table('localized_videos').select('id').execute().data)

        print(f"  Projects: {projects_count}")
        print(f"  Channels: {channels_count}")
        print(f"  Videos: {videos_count}")
        print(f"  Processing Jobs: {jobs_count}")
        print(f"  Localized Videos: {localized_count}")

        if videos_count > 0:
            print("\n📹 Sample Video:")
            video = supabase.table('videos').select('*').limit(1).execute().data[0]
            print(f"  Title: {video['title']}")
            print(f"  Video ID: {video['video_id']}")
            print(f"  User ID: {video['user_id']}")
            print(f"  Status: {video['status']}")

    except Exception as e:
        print(f"✗ Error verifying data: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🌱 SUPABASE DATA SEEDING")
    print("=" * 60)

    # Sync all collections
    sync_projects()
    sync_channels()
    sync_videos()
    sync_processing_jobs()
    sync_localized_videos()

    # Verify
    verify_sync()

    print("\n" + "=" * 60)
    print("✅ SEEDING COMPLETE!")
    print("=" * 60)
    print("\nYour Supabase database is now populated with data from Firestore.")
    print("You can now use the frontend Supabase hooks to query this data.")
    print("\nNext steps:")
    print("  1. Test the SupabaseExample component")
    print("  2. Replace API calls with Supabase hooks")
    print("  3. Enable real-time updates in your components")
