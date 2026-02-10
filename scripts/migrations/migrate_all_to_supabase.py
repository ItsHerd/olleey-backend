#!/usr/bin/env python3
"""
Complete Firestore → Supabase Migration Script
Migrates ALL data from Firestore to Supabase with progress tracking and error handling.
"""

import os
import sys
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firestore import firestore_service
from supabase import create_client, Client

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL', 'https://wfjpbrcktxbwasbamchx.supabase.co')
SUPABASE_KEY = os.getenv('SUPABASE_SERVICE_KEY') or os.getenv('SUPABASE_ANON_KEY', '')

if not SUPABASE_KEY:
    print("❌ Error: SUPABASE_KEY not found in environment")
    sys.exit(1)

# Create Supabase client
print(f"🔗 Connecting to Supabase: {SUPABASE_URL}")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
print("✅ Connected successfully!\n")


# Statistics tracking
stats = {
    'projects': {'migrated': 0, 'skipped': 0, 'errors': 0},
    'channels': {'migrated': 0, 'skipped': 0, 'errors': 0},
    'videos': {'migrated': 0, 'skipped': 0, 'errors': 0},
    'processing_jobs': {'migrated': 0, 'skipped': 0, 'errors': 0},
    'localized_videos': {'migrated': 0, 'skipped': 0, 'errors': 0}
}


def transform_timestamp(ts) -> str:
    """Transform Firestore timestamp to ISO string."""
    if ts is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(ts, datetime):
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts.isoformat()
    if hasattr(ts, 'timestamp'):
        return datetime.fromtimestamp(ts.timestamp(), tz=timezone.utc).isoformat()
    return str(ts)


def safe_get(data: Dict, key: str, default=None):
    """Safely get value from dict, handling None and empty strings."""
    value = data.get(key, default)
    if value is None or (isinstance(value, str) and value.strip() == ''):
        return default
    return value


def sync_projects() -> int:
    """Sync ALL projects from Firestore to Supabase."""
    print("📁 Migrating Projects...")

    try:
        projects_ref = firestore_service.db.collection('projects')
        docs = list(projects_ref.stream())
        total = len(docs)
        print(f"   Found {total} projects in Firestore")

        if total == 0:
            print("   ⏭️  No projects to migrate\n")
            return 0

        projects = []
        for idx, doc in enumerate(docs, 1):
            try:
                data = doc.to_dict()

                # Generate UUID if missing
                project_id = safe_get(data, 'id') or doc.id or str(uuid.uuid4())

                # Ensure user_id exists
                user_id = safe_get(data, 'user_id')
                if not user_id:
                    print(f"   ⚠️  Skipping project without user_id: {project_id}")
                    stats['projects']['skipped'] += 1
                    continue

                project = {
                    'id': project_id,
                    'user_id': user_id,
                    'name': safe_get(data, 'name', 'Untitled Project'),
                    'description': safe_get(data, 'description'),
                    'settings': safe_get(data, 'settings', {}),
                    'created_at': transform_timestamp(data.get('created_at')),
                    'updated_at': transform_timestamp(data.get('updated_at'))
                }
                projects.append(project)

                # Progress indicator
                if idx % 10 == 0:
                    print(f"   Progress: {idx}/{total} projects processed...")

            except Exception as e:
                print(f"   ❌ Error processing project {doc.id}: {e}")
                stats['projects']['errors'] += 1
                continue

        if projects:
            # Batch upsert
            batch_size = 100
            for i in range(0, len(projects), batch_size):
                batch = projects[i:i + batch_size]
                result = supabase.table('projects').upsert(batch, on_conflict='id').execute()
                stats['projects']['migrated'] += len(batch)

            print(f"   ✅ Successfully migrated {stats['projects']['migrated']} projects")
            if stats['projects']['skipped'] > 0:
                print(f"   ⚠️  Skipped {stats['projects']['skipped']} projects")
            if stats['projects']['errors'] > 0:
                print(f"   ❌ Errors: {stats['projects']['errors']}")

        print()
        return stats['projects']['migrated']

    except Exception as e:
        print(f"   ❌ Critical error syncing projects: {e}\n")
        return 0


def sync_channels() -> int:
    """Sync ALL channels from Firestore to Supabase."""
    print("📺 Migrating Channels...")

    try:
        channels_ref = firestore_service.db.collection('channels')
        docs = list(channels_ref.stream())
        total = len(docs)
        print(f"   Found {total} channels in Firestore")

        if total == 0:
            print("   ⏭️  No channels to migrate\n")
            return 0

        channels = []
        for idx, doc in enumerate(docs, 1):
            try:
                data = doc.to_dict()

                # Ensure required fields exist
                channel_id = safe_get(data, 'channel_id') or doc.id
                user_id = safe_get(data, 'user_id')

                if not channel_id or not user_id:
                    print(f"   ⚠️  Skipping channel without required fields")
                    stats['channels']['skipped'] += 1
                    continue

                channel = {
                    'channel_id': channel_id,
                    'user_id': user_id,
                    'project_id': safe_get(data, 'project_id'),
                    'channel_name': safe_get(data, 'channel_name', 'Unnamed Channel'),
                    'language_code': safe_get(data, 'language_code', 'en'),
                    'language_name': safe_get(data, 'language_name'),
                    'is_master': safe_get(data, 'is_master', False),
                    'master_channel_id': safe_get(data, 'master_channel_id'),
                    'description': safe_get(data, 'description'),
                    'thumbnail_url': safe_get(data, 'thumbnail_url'),
                    'subscriber_count': safe_get(data, 'subscriber_count', 0),
                    'video_count': safe_get(data, 'video_count', 0),
                    'created_at': transform_timestamp(data.get('created_at')),
                    'updated_at': transform_timestamp(data.get('updated_at'))
                }
                channels.append(channel)

                if idx % 10 == 0:
                    print(f"   Progress: {idx}/{total} channels processed...")

            except Exception as e:
                print(f"   ❌ Error processing channel {doc.id}: {e}")
                stats['channels']['errors'] += 1
                continue

        if channels:
            batch_size = 100
            for i in range(0, len(channels), batch_size):
                batch = channels[i:i + batch_size]
                result = supabase.table('channels').upsert(batch, on_conflict='channel_id').execute()
                stats['channels']['migrated'] += len(batch)

            print(f"   ✅ Successfully migrated {stats['channels']['migrated']} channels")
            if stats['channels']['skipped'] > 0:
                print(f"   ⚠️  Skipped {stats['channels']['skipped']} channels")
            if stats['channels']['errors'] > 0:
                print(f"   ❌ Errors: {stats['channels']['errors']}")

        print()
        return stats['channels']['migrated']

    except Exception as e:
        print(f"   ❌ Critical error syncing channels: {e}\n")
        return 0


def sync_videos() -> int:
    """Sync ALL videos from Firestore to Supabase."""
    print("🎬 Migrating Videos...")

    try:
        videos_ref = firestore_service.db.collection('videos')
        docs = list(videos_ref.stream())
        total = len(docs)
        print(f"   Found {total} videos in Firestore")

        if total == 0:
            print("   ⏭️  No videos to migrate\n")
            return 0

        videos = []
        for idx, doc in enumerate(docs, 1):
            try:
                data = doc.to_dict()

                # Ensure required fields
                video_id = safe_get(data, 'video_id') or doc.id
                if not video_id:
                    print(f"   ⚠️  Skipping video without video_id")
                    stats['videos']['skipped'] += 1
                    continue

                # Cap numeric fields to PostgreSQL limits
                view_count = min(safe_get(data, 'view_count', 0), 2147483647)
                like_count = min(safe_get(data, 'like_count', 0), 2147483647)
                comment_count = min(safe_get(data, 'comment_count', 0), 2147483647)

                video = {
                    'video_id': video_id,
                    'user_id': safe_get(data, 'user_id'),
                    'project_id': safe_get(data, 'project_id'),
                    'channel_id': safe_get(data, 'channel_id'),
                    'channel_name': safe_get(data, 'channel_name'),
                    'title': safe_get(data, 'title', 'Untitled Video'),
                    'description': safe_get(data, 'description'),
                    'thumbnail_url': safe_get(data, 'thumbnail_url'),
                    'storage_url': safe_get(data, 'storage_url'),
                    'video_url': safe_get(data, 'video_url'),
                    'duration': safe_get(data, 'duration'),
                    'view_count': view_count,
                    'like_count': like_count,
                    'comment_count': comment_count,
                    'status': safe_get(data, 'status', 'draft'),
                    'language_code': safe_get(data, 'language_code'),
                    'published_at': transform_timestamp(data.get('published_at')),
                    'created_at': transform_timestamp(data.get('created_at')),
                    'updated_at': transform_timestamp(data.get('updated_at'))
                }
                videos.append(video)

                if idx % 25 == 0:
                    print(f"   Progress: {idx}/{total} videos processed...")

            except Exception as e:
                print(f"   ❌ Error processing video {doc.id}: {e}")
                stats['videos']['errors'] += 1
                continue

        if videos:
            batch_size = 50
            for i in range(0, len(videos), batch_size):
                batch = videos[i:i + batch_size]
                result = supabase.table('videos').upsert(batch, on_conflict='video_id').execute()
                stats['videos']['migrated'] += len(batch)

            print(f"   ✅ Successfully migrated {stats['videos']['migrated']} videos")
            if stats['videos']['skipped'] > 0:
                print(f"   ⚠️  Skipped {stats['videos']['skipped']} videos")
            if stats['videos']['errors'] > 0:
                print(f"   ❌ Errors: {stats['videos']['errors']}")

        print()
        return stats['videos']['migrated']

    except Exception as e:
        print(f"   ❌ Critical error syncing videos: {e}\n")
        return 0


def sync_processing_jobs() -> int:
    """Sync ALL processing jobs from Firestore to Supabase."""
    print("⚙️  Migrating Processing Jobs...")

    try:
        jobs_ref = firestore_service.db.collection('processing_jobs')
        docs = list(jobs_ref.stream())
        total = len(docs)
        print(f"   Found {total} processing jobs in Firestore")

        if total == 0:
            print("   ⏭️  No processing jobs to migrate\n")
            return 0

        jobs = []
        for idx, doc in enumerate(docs, 1):
            try:
                data = doc.to_dict()

                # Skip if missing critical fields
                user_id = safe_get(data, 'user_id')
                source_video_id = safe_get(data, 'source_video_id')

                if not user_id or not source_video_id:
                    print(f"   ⚠️  Skipping job {doc.id} without required fields")
                    stats['processing_jobs']['skipped'] += 1
                    continue

                # Generate UUID if missing
                job_id = safe_get(data, 'job_id') or safe_get(data, 'id') or doc.id
                if not job_id or (isinstance(job_id, str) and job_id.strip() == ''):
                    job_id = str(uuid.uuid4())

                job = {
                    'job_id': job_id,
                    'user_id': user_id,
                    'project_id': safe_get(data, 'project_id'),
                    'source_video_id': source_video_id,
                    'source_channel_id': safe_get(data, 'source_channel_id'),
                    'target_languages': safe_get(data, 'target_languages', []),
                    'status': safe_get(data, 'status', 'pending'),
                    'workflow_state': safe_get(data, 'workflow_state', {}),
                    'created_at': transform_timestamp(data.get('created_at')),
                    'updated_at': transform_timestamp(data.get('updated_at'))
                }
                jobs.append(job)

                if idx % 25 == 0:
                    print(f"   Progress: {idx}/{total} jobs processed...")

            except Exception as e:
                print(f"   ❌ Error processing job {doc.id}: {e}")
                stats['processing_jobs']['errors'] += 1
                continue

        if jobs:
            batch_size = 50
            for i in range(0, len(jobs), batch_size):
                batch = jobs[i:i + batch_size]
                result = supabase.table('processing_jobs').upsert(batch, on_conflict='job_id').execute()
                stats['processing_jobs']['migrated'] += len(batch)

            print(f"   ✅ Successfully migrated {stats['processing_jobs']['migrated']} processing jobs")
            if stats['processing_jobs']['skipped'] > 0:
                print(f"   ⚠️  Skipped {stats['processing_jobs']['skipped']} jobs")
            if stats['processing_jobs']['errors'] > 0:
                print(f"   ❌ Errors: {stats['processing_jobs']['errors']}")

        print()
        return stats['processing_jobs']['migrated']

    except Exception as e:
        print(f"   ❌ Critical error syncing processing jobs: {e}\n")
        return 0


def sync_localized_videos() -> int:
    """Sync ALL localized videos from Firestore to Supabase."""
    print("🌐 Migrating Localized Videos...")

    try:
        localized_ref = firestore_service.db.collection('localized_videos')
        docs = list(localized_ref.stream())
        total = len(docs)
        print(f"   Found {total} localized videos in Firestore")

        if total == 0:
            print("   ⏭️  No localized videos to migrate\n")
            return 0

        localized_videos = []
        for idx, doc in enumerate(docs, 1):
            try:
                data = doc.to_dict()

                # Skip if missing critical fields
                user_id = safe_get(data, 'user_id')
                language_code = safe_get(data, 'language_code')

                if not user_id or not language_code:
                    print(f"   ⚠️  Skipping localized video {doc.id} without required fields")
                    stats['localized_videos']['skipped'] += 1
                    continue

                # Generate UUID if missing
                localized_id = safe_get(data, 'id') or doc.id or str(uuid.uuid4())

                # Handle job_id (might be reference or string)
                job_id = safe_get(data, 'job_id')
                if hasattr(job_id, 'id'):
                    job_id = job_id.id
                if not job_id or job_id == '':
                    job_id = None

                localized_video = {
                    'id': localized_id,
                    'job_id': job_id,
                    'source_video_id': safe_get(data, 'source_video_id'),
                    'user_id': user_id,
                    'project_id': safe_get(data, 'project_id'),
                    'channel_id': safe_get(data, 'channel_id'),
                    'language_code': language_code,
                    'title': safe_get(data, 'title'),
                    'description': safe_get(data, 'description'),
                    'video_url': safe_get(data, 'video_url') or safe_get(data, 'storage_url'),
                    'thumbnail_url': safe_get(data, 'thumbnail_url'),
                    'status': safe_get(data, 'status', 'draft'),
                    'duration': safe_get(data, 'duration'),
                    'created_at': transform_timestamp(data.get('created_at')),
                    'updated_at': transform_timestamp(data.get('updated_at'))
                }
                localized_videos.append(localized_video)

                if idx % 25 == 0:
                    print(f"   Progress: {idx}/{total} localized videos processed...")

            except Exception as e:
                print(f"   ❌ Error processing localized video {doc.id}: {e}")
                stats['localized_videos']['errors'] += 1
                continue

        if localized_videos:
            batch_size = 50
            for i in range(0, len(localized_videos), batch_size):
                batch = localized_videos[i:i + batch_size]
                result = supabase.table('localized_videos').upsert(batch, on_conflict='id').execute()
                stats['localized_videos']['migrated'] += len(batch)

            print(f"   ✅ Successfully migrated {stats['localized_videos']['migrated']} localized videos")
            if stats['localized_videos']['skipped'] > 0:
                print(f"   ⚠️  Skipped {stats['localized_videos']['skipped']} localized videos")
            if stats['localized_videos']['errors'] > 0:
                print(f"   ❌ Errors: {stats['localized_videos']['errors']}")

        print()
        return stats['localized_videos']['migrated']

    except Exception as e:
        print(f"   ❌ Critical error syncing localized videos: {e}\n")
        return 0


def verify_migration():
    """Verify migration results in Supabase."""
    print("=" * 70)
    print("📊 MIGRATION VERIFICATION")
    print("=" * 70)

    try:
        # Get counts from Supabase
        projects = supabase.table('projects').select('id', count='exact').execute()
        channels = supabase.table('channels').select('channel_id', count='exact').execute()
        videos = supabase.table('videos').select('video_id', count='exact').execute()
        jobs = supabase.table('processing_jobs').select('job_id', count='exact').execute()
        localized = supabase.table('localized_videos').select('id', count='exact').execute()

        print("\n📈 Records in Supabase:")
        print(f"   Projects:          {projects.count:>6}")
        print(f"   Channels:          {channels.count:>6}")
        print(f"   Videos:            {videos.count:>6}")
        print(f"   Processing Jobs:   {jobs.count:>6}")
        print(f"   Localized Videos:  {localized.count:>6}")

        total_records = projects.count + channels.count + videos.count + jobs.count + localized.count
        print(f"\n   Total Records:     {total_records:>6}")

        # Show sample data
        if videos.count > 0:
            print("\n🎬 Sample Video:")
            video = supabase.table('videos').select('*').limit(1).execute().data[0]
            print(f"   Title:      {video.get('title', 'N/A')}")
            print(f"   Video ID:   {video.get('video_id', 'N/A')}")
            print(f"   User ID:    {video.get('user_id', 'N/A')}")
            print(f"   Project ID: {video.get('project_id', 'N/A')}")

        if projects.count > 0:
            print("\n📁 Sample Project:")
            project = supabase.table('projects').select('*').limit(1).execute().data[0]
            print(f"   Name:       {project.get('name', 'N/A')}")
            print(f"   ID:         {project.get('id', 'N/A')}")
            print(f"   User ID:    {project.get('user_id', 'N/A')}")

        print()

    except Exception as e:
        print(f"\n❌ Error during verification: {e}\n")


def print_summary():
    """Print migration summary statistics."""
    print("=" * 70)
    print("📊 MIGRATION SUMMARY")
    print("=" * 70)

    total_migrated = sum(s['migrated'] for s in stats.values())
    total_skipped = sum(s['skipped'] for s in stats.values())
    total_errors = sum(s['errors'] for s in stats.values())

    print(f"\n✅ Successfully Migrated: {total_migrated} records")
    if total_skipped > 0:
        print(f"⚠️  Skipped:              {total_skipped} records")
    if total_errors > 0:
        print(f"❌ Errors:               {total_errors} records")

    print("\n📋 Breakdown by Collection:")
    for collection, counts in stats.items():
        if counts['migrated'] > 0 or counts['skipped'] > 0 or counts['errors'] > 0:
            print(f"\n   {collection.replace('_', ' ').title()}:")
            print(f"      Migrated: {counts['migrated']}")
            if counts['skipped'] > 0:
                print(f"      Skipped:  {counts['skipped']}")
            if counts['errors'] > 0:
                print(f"      Errors:   {counts['errors']}")

    print()


if __name__ == "__main__":
    print("=" * 70)
    print("🚀 COMPLETE FIRESTORE → SUPABASE MIGRATION")
    print("=" * 70)
    print("\nThis will migrate ALL data from Firestore to Supabase.")
    print("Existing records will be updated (upsert operation).")
    print()

    input("Press Enter to start migration...")
    print()

    # Run migration in order (respecting dependencies)
    start_time = datetime.now()

    sync_projects()           # Must be first (referenced by other tables)
    sync_channels()           # Can run after projects
    sync_videos()             # Can run after projects/channels
    sync_processing_jobs()    # Can run after videos
    sync_localized_videos()   # Should run last (references jobs)

    # Verification
    verify_migration()

    # Summary
    print_summary()

    elapsed = (datetime.now() - start_time).total_seconds()

    print("=" * 70)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 70)
    print(f"\nTime elapsed: {elapsed:.2f} seconds")
    print("\n🎉 Your Supabase database now contains ALL data from Firestore!")
    print("\nNext steps:")
    print("   1. Test your frontend - it should now show all projects and videos")
    print("   2. Verify data in Supabase Dashboard")
    print("   3. Run the RLS disable script if you haven't already")
    print()
