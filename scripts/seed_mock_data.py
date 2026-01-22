"""Script to seed Firebase Auth and Firestore with mock data for testing."""
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from firebase_admin import auth
from services.firestore import firestore_service
from config import settings


def create_mock_user(email: str, password: str, name: str = None):
    """
    Create a mock user in Firebase Auth.
    
    Args:
        email: User email
        password: User password
        name: Optional display name
        
    Returns:
        str: Firebase user ID (UID)
    """
    try:
        # Check if user already exists
        try:
            existing_user = auth.get_user_by_email(email)
            print(f"⚠️  User {email} already exists with UID: {existing_user.uid}")
            return existing_user.uid
        except auth.UserNotFoundError:
            pass
        
        # Create new user
        user_record = auth.create_user(
            email=email,
            password=password,
            display_name=name or email.split('@')[0],
            email_verified=False
        )
        
        print(f"✅ Created Firebase Auth user: {email} (UID: {user_record.uid})")
        return user_record.uid
        
    except Exception as e:
        print(f"❌ Failed to create user {email}: {str(e)}")
        raise


def create_mock_users():
    """Create mock users in Firebase Auth."""
    print("👤 Creating mock users in Firebase Auth...\n")
    
    users = [
        {
            "email": "user1@gmail.com",
            "password": "123456",  # Firebase requires min 6 characters
            "name": "User One",
            "has_youtube": False  # New user, no YouTube connection
        }
    ]
    
    user_ids = {}
    
    for user_data in users:
        try:
            uid = create_mock_user(
                email=user_data["email"],
                password=user_data["password"],
                name=user_data["name"]
            )
            user_ids[user_data["email"]] = {
                "uid": uid,
                "has_youtube": user_data["has_youtube"]
            }
        except Exception as e:
            print(f"❌ Error creating user {user_data['email']}: {str(e)}")
    
    print()
    return user_ids


def create_mock_youtube_connections(user_ids: dict):
    """Create mock YouTube connections for users who have YouTube."""
    print("📺 Creating mock YouTube connections...\n")
    
    # Only create connections for users who have YouTube
    connections_created = 0
    
    for email, user_info in user_ids.items():
        if user_info["has_youtube"]:
            user_id = user_info["uid"]
            
            # Create a mock YouTube connection
            # Note: These are mock connections without real OAuth tokens
            # For real connections, users need to go through OAuth flow
            try:
                connection_id = firestore_service.create_youtube_connection(
                    user_id=user_id,
                    youtube_channel_id=f"UC_mock_channel_{user_id[:8]}",
                    youtube_channel_name=f"Mock Channel for {email}",
                    access_token="mock_access_token",
                    refresh_token="mock_refresh_token",
                    is_primary=True
                )
                print(f"✅ Created YouTube connection for {email}: {connection_id}")
                connections_created += 1
            except Exception as e:
                print(f"❌ Failed to create YouTube connection for {email}: {str(e)}")
    
    if connections_created == 0:
        print("ℹ️  No YouTube connections created (user1 is a new user)")
    print()


def create_mock_processing_jobs(user_ids: dict):
    """Create mock processing jobs (only for users with YouTube connections)."""
    print("⚙️  Creating mock processing jobs...\n")
    
    jobs_created = 0
    
    for email, user_info in user_ids.items():
        if user_info["has_youtube"]:
            user_id = user_info["uid"]
            
            # Create a mock processing job
            try:
                job_id = firestore_service.create_processing_job(
                    source_video_id="dQw4w9WgXcQ",
                    source_channel_id=f"UC_mock_channel_{user_id[:8]}",
                    user_id=user_id,
                    target_languages=["es", "fr"]
                )
                
                # Update job status
                firestore_service.update_processing_job(
                    job_id,
                    status="completed",
                    progress=100,
                    completed_at=datetime.utcnow()
                )
                
                print(f"✅ Created processing job for {email}: {job_id}")
                jobs_created += 1
            except Exception as e:
                print(f"❌ Failed to create job for {email}: {str(e)}")
    
    if jobs_created == 0:
        print("ℹ️  No processing jobs created (user1 is a new user)")
    print()


def main():
    """Main function to seed all mock data."""
    print("🌱 Seeding mock data to Firebase Auth and Firestore...\n")
    print("=" * 60)
    
    try:
        # Create mock users in Firebase Auth
        user_ids = create_mock_users()
        
        # Create YouTube connections (only for users who have YouTube)
        create_mock_youtube_connections(user_ids)
        
        # Create processing jobs (only for users with YouTube)
        create_mock_processing_jobs(user_ids)
        
        print("=" * 60)
        print("✅ Mock data seeding completed!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"   - Users created: {len(user_ids)}")
        
        print(f"\n👤 User Credentials:")
        for email, user_info in user_ids.items():
            # Get password from users list
            password = next((u["password"] for u in [
                {"email": "user1@gmail.com", "password": "123456"}
            ] if u["email"] == email), "N/A")
            print(f"   - Email: {email}")
            print(f"     Password: {password}")
            print(f"     UID: {user_info['uid']}")
            print(f"     YouTube Connected: {'Yes' if user_info['has_youtube'] else 'No (New User)'}")
            print()
        
        print(f"\n🧪 Test Login:")
        print(f"   POST http://localhost:8000/auth/login")
        print(f"   Body: {{")
        print(f"     \"email\": \"user1@gmail.com\",")
        print(f"     \"password\": \"123456\"")
        print(f"   }}")
        print()
        print(f"   After login, user1 will need to connect YouTube channel via:")
        print(f"   GET http://localhost:8000/youtube/connect")
        
    except Exception as e:
        print(f"\n❌ Error seeding mock data: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
