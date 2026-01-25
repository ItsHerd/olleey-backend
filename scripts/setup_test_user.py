#!/usr/bin/env python3
"""
Setup script to create a test user with mock YouTube credentials.

This creates a test user in Firestore with mock credentials that will
trigger mock mode for all YouTube API interactions.
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firestore import firestore_service
from datetime import datetime, timedelta

def create_test_user_with_mock_credentials():
    """Create a test user with mock YouTube credentials."""
    
    print("=" * 60)
    print("Creating Test User with Mock Credentials")
    print("=" * 60)
    
    # Test user details
    test_user_id = "test_user_mock_123"
    test_email = "test@example.com"
    
    print(f"\nTest User ID: {test_user_id}")
    print(f"Test Email: {test_email}")
    
    # Create or update user
    print("\n[1/4] Creating user...")
    firestore_service.create_or_update_user(
        user_id=test_user_id,
        email=test_email,
        access_token="mock_user_token",
        refresh_token="mock_user_refresh",
        token_expiry=datetime.utcnow() + timedelta(days=365)
    )
    print("✓ User created")
    
    # Create mock YouTube connection
    print("\n[2/4] Creating mock YouTube connection...")
    connection_id = firestore_service.create_youtube_connection(
        user_id=test_user_id,
        youtube_channel_id="UCmock_main_channel_123",
        youtube_channel_name="Test Main Channel",
        access_token="mock_test_token_12345",  # Must start with "mock_"
        refresh_token="mock_refresh_token",
        is_primary=True,
        channel_avatar_url="https://via.placeholder.com/150"
    )
    print(f"✓ YouTube connection created: {connection_id}")
    
    # Create test project
    print("\n[3/4] Creating test project...")
    project_id = firestore_service.create_project(
        user_id=test_user_id,
        name="Test Project",
        master_connection_id=connection_id
    )
    print(f"✓ Project created: {project_id}")
    
    # Create language channels
    print("\n[4/4] Creating language channels...")
    
    languages = [
        {"code": "es", "name": "Spanish", "channel_id": "UCmock_spanish_456"},
        {"code": "de", "name": "German", "channel_id": "UCmock_german_789"},
        {"code": "fr", "name": "French", "channel_id": "UCmock_french_012"},
        {"code": "it", "name": "Italian", "channel_id": "UCmock_italian_345"},
    ]
    
    channel_ids = []
    for lang in languages:
        channel_doc_id = firestore_service.create_language_channel(
            user_id=test_user_id,
            channel_id=lang["channel_id"],
            language_code=lang["code"],
            language_codes=[lang["code"]],  # Can support multiple
            channel_name=f"Test {lang['name']} Channel",
            master_connection_id=connection_id,
            project_id=project_id
        )
        channel_ids.append(channel_doc_id)
        print(f"  ✓ {lang['name']} channel: {channel_doc_id}")
    
    # Summary
    print("\n" + "=" * 60)
    print("Test User Setup Complete!")
    print("=" * 60)
    print(f"\n📋 Test User Details:")
    print(f"   User ID: {test_user_id}")
    print(f"   Email: {test_email}")
    print(f"   YouTube Connection: {connection_id}")
    print(f"   Project ID: {project_id}")
    print(f"   Language Channels: {len(channel_ids)}")
    
    print(f"\n🔑 Mock Credentials:")
    print(f"   Access Token: mock_test_token_12345")
    print(f"   (Starts with 'mock_' to trigger mock mode)")
    
    print(f"\n📺 Channel IDs for Testing:")
    for i, channel_id in enumerate(channel_ids):
        print(f"   {i+1}. {channel_id} ({languages[i]['name']})")
    
    print(f"\n🧪 Test API Calls:")
    print(f"   1. List videos:")
    print(f"      GET /videos/list")
    print(f"      (Will return mock videos)")
    
    print(f"\n   2. Create manual job:")
    print(f"      POST /jobs/manual")
    print(f"      -F source_channel_id=UCmock_main_channel_123")
    print(f"      -F target_channel_ids={channel_ids[0]},{channel_ids[1]}")
    print(f"      -F video_url=https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    print(f"\n✅ All YouTube API calls will now return mock data!")
    print(f"   No actual YouTube API calls will be made.")
    print(f"   No quota will be consumed.")
    
    print("\n" + "=" * 60)
    
    return {
        "user_id": test_user_id,
        "email": test_email,
        "connection_id": connection_id,
        "project_id": project_id,
        "channel_ids": channel_ids
    }


def cleanup_test_user():
    """Remove the test user and all associated data."""
    test_user_id = "test_user_mock_123"
    
    print("\n🗑️  Cleaning up test user...")
    
    # Note: You would need to implement cleanup methods in firestore_service
    # For now, this is a placeholder
    print(f"   To manually delete, remove user: {test_user_id}")
    print(f"   from Firestore console")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup test user with mock credentials")
    parser.add_argument("--cleanup", action="store_true", help="Remove test user")
    args = parser.parse_args()
    
    if args.cleanup:
        cleanup_test_user()
    else:
        try:
            result = create_test_user_with_mock_credentials()
            print("\n✨ Setup successful! You can now test with mock mode.")
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
