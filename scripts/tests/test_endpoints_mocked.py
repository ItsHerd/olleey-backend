
import sys

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock dependencies BEFORE importing main
# We need to mock firebase_admin and services.firestore.firestore_service

# Mock Firebase Admin
mock_firebase_admin = MagicMock()
sys.modules["firebase_admin"] = mock_firebase_admin
sys.modules["firebase_admin.auth"] = MagicMock()
sys.modules["firebase_admin.credentials"] = MagicMock()
sys.modules["firebase_admin.firestore"] = MagicMock()

# Import main (which imports firestore_service)
# We need to patch the flrestore_service instance in services.firestore
with patch("services.firestore.firestore_service") as mock_firestore:
    from main import app
    from middleware.auth import verify_firebase_token
    
    # Create TestClient
    client = TestClient(app)

    # Mock User
    TEST_USER = {
        "user_id": "test_user_id",
        "email": "test@example.com",
        "name": "Test User",
        "email_verified": True,
        "firebase_claims": {}
    }

    # Override dependency
    async def override_get_current_user():
        return TEST_USER

    app.dependency_overrides[verify_firebase_token] = override_get_current_user

    def test_health():
        print("\nTesting /health")
        response = client.get("/health")
        assert response.status_code == 200
        print(response.json())

    def test_auth_me():
        print("\nTesting /auth/me")
        # Should succeed because we overrode the dependency
        response = client.get("/auth/me")
        assert response.status_code == 200
        print(response.json())

    def test_get_channels():
        print("\nTesting /channels")
        # Mock firestore response
        mock_firestore.get_language_channels.return_value = [
            {
                "id": "chan1",
                "channel_id": "UC123",
                "language_code": "es",
                "channel_name": "Test Channel ES",
                "created_at": 1234567890
            }
        ]
        
        response = client.get("/channels")
        print(response.json())
        assert response.status_code == 200
        data = response.json()
        assert len(data["channels"]) == 1
        assert data["channels"][0]["channel_id"] == "UC123"

    def test_get_jobs():
        print("\nTesting /jobs")
        # Mock firestore response
        mock_firestore.list_processing_jobs.return_value = ([
            {
                "id": "job1",
                "source_video_id": "vid1",
                "source_channel_id": "chan1",
                "status": "completed",
                "target_languages": ["es"],
                "created_at": 1234567890
            }
        ], 1)
        
        response = client.get("/jobs")
        print(response.json())
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 1
    
    def test_videos_list():
        print("\nTesting /videos/list")
        # Mock firestore response
        # videos/list logic depends on getting jobs and localized videos
        # It calls list_processing_jobs and then localized videos
        mock_firestore.list_processing_jobs.return_value = ([
            {
                "id": "job1",
                "source_video_id": "vid1",
                "source_channel_id": "chan1",
                "status": "completed",
                "target_languages": ["es"],
                "created_at": 1234567890
            }
        ], 1)
        mock_firestore.get_localized_videos_by_source_id.return_value = []
        
        response = client.get("/videos/list")
        print(response.json())
        assert response.status_code == 200


if __name__ == "__main__":
    print("Running mocked tests...")
    # Manually run tests since we are in a script
    try:
        test_health()
        test_auth_me()
        test_get_channels()
        test_get_jobs()
        test_videos_list()
        print("\n✅ All mocked tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
