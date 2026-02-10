#!/usr/bin/env python3
"""
Update all seeded data to use a specific user_id.
This fixes the issue where dashboard is empty because data belongs to a different user.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.supabase_db import supabase_service

def update_all_user_ids(old_user_id: str, new_user_id: str):
    """Update user_id across all tables."""

    print(f"\n🔄 Updating user_id from {old_user_id} to {new_user_id}...")

    # Update projects
    try:
        result = supabase_service.client.table('projects').update({
            'user_id': new_user_id
        }).eq('user_id', old_user_id).execute()
        print(f"✅ Updated {len(result.data)} projects")
    except Exception as e:
        print(f"⚠️  Projects: {e}")

    # Update videos
    try:
        result = supabase_service.client.table('videos').update({
            'user_id': new_user_id
        }).eq('user_id', old_user_id).execute()
        print(f"✅ Updated {len(result.data)} videos")
    except Exception as e:
        print(f"⚠️  Videos: {e}")

    # Update processing_jobs
    try:
        result = supabase_service.client.table('processing_jobs').update({
            'user_id': new_user_id
        }).eq('user_id', old_user_id).execute()
        print(f"✅ Updated {len(result.data)} processing jobs")
    except Exception as e:
        print(f"⚠️  Processing jobs: {e}")

    # Update channels
    try:
        result = supabase_service.client.table('channels').update({
            'user_id': new_user_id
        }).eq('user_id', old_user_id).execute()
        print(f"✅ Updated {len(result.data)} channels")
    except Exception as e:
        print(f"⚠️  Channels: {e}")

    # Update localized_videos
    try:
        result = supabase_service.client.table('localized_videos').update({
            'user_id': new_user_id
        }).eq('user_id', old_user_id).execute()
        print(f"✅ Updated {len(result.data)} localized videos")
    except Exception as e:
        print(f"⚠️  Localized videos: {e}")

    print("\n✅ User ID update complete!")

    # Verify
    print("\n📊 Verification:")
    projects = supabase_service.list_projects(new_user_id)
    videos, total_videos = supabase_service.list_videos(user_id=new_user_id)
    jobs, total_jobs = supabase_service.list_processing_jobs(user_id=new_user_id)
    channels = supabase_service.get_language_channels(new_user_id)

    print(f"  - Projects: {len(projects)}")
    print(f"  - Videos: {total_videos}")
    print(f"  - Processing Jobs: {total_jobs}")
    print(f"  - Channels: {len(channels)}")

if __name__ == "__main__":
    # Current seeded user_id
    OLD_USER_ID = "M8yD1YEve9OaW2Q2HhVh3tSCmGo2"

    print("=" * 60)
    print("Update User ID for Seeded Data")
    print("=" * 60)

    if len(sys.argv) > 1:
        NEW_USER_ID = sys.argv[1]
    else:
        print("\nCurrent seeded data belongs to: M8yD1YEve9OaW2Q2HhVh3tSCmGo2")
        print("\nEnter your Firebase user ID (or press Enter to use test user):")
        print("You can find this in:")
        print("  1. Browser DevTools > Application > Local Storage > firebaseLocalStorageDb")
        print("  2. Or run: firebase auth:export users.json --project your-project")
        NEW_USER_ID = input("> ").strip()

        if not NEW_USER_ID:
            print("\n❌ No user ID provided. Exiting.")
            sys.exit(1)

    # Confirm
    print(f"\n⚠️  This will update ALL records from {OLD_USER_ID} to {NEW_USER_ID}")
    confirm = input("Continue? (yes/no): ").strip().lower()

    if confirm != 'yes':
        print("❌ Cancelled")
        sys.exit(0)

    update_all_user_ids(OLD_USER_ID, NEW_USER_ID)
