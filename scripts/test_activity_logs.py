
import sys
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Mock Firebase
sys.modules["firebase_admin"] = MagicMock()
sys.modules["firebase_admin.auth"] = MagicMock()
sys.modules["firebase_admin.credentials"] = MagicMock()
sys.modules["firebase_admin.firestore"] = MagicMock()

with patch("services.firestore.firestore_service") as mock_firestore:
    from main import app
    from middleware.auth import verify_firebase_token
    
    client = TestClient(app)
    TEST_USER = {"user_id": "test_user_id", "email": "test@example.com"}

    async def override_get_current_user():
        return TEST_USER
    app.dependency_overrides[verify_firebase_token] = override_get_current_user

    def test_log_creation_on_project_create():
        print("\nTesting Activity Log creation on /projects POST")
        mock_firestore.create_project.return_value = "new_project_id"
        mock_firestore.get_project.return_value = {"id": "new_project_id", "name": "New Project"}
        
        response = client.post("/projects", json={"name": "New Project"})
        assert response.status_code == 200
        
        # Verify log_activity was called
        mock_firestore.log_activity.assert_called_with(
            user_id="test_user_id",
            project_id="new_project_id",
            action="Created project",
            details="Project 'New Project' created."
        )
        print("✅ Activity logged successfully on project creation")

    def test_get_project_activity():
        print("\nTesting /projects/{id}/activity GET")
        mock_firestore.get_project.return_value = {"id": "proj123", "user_id": "test_user_id"}
        mock_firestore.list_activity_logs.return_value = [
            {
                "id": "log1",
                "project_id": "proj123",
                "action": "Test Action",
                "status": "info",
                "details": "Details here",
                "timestamp": datetime.utcnow()
            }
        ]
        
        response = client.get("/projects/proj123/activity")
        assert response.status_code == 200
        logs = response.json()
        assert len(logs) == 1
        assert logs[0]["action"] == "Test Action"
        print("✅ Activity logs retrieved successfully")

if __name__ == "__main__":
    test_log_creation_on_project_create()
    test_get_project_activity()
    print("\n✅ Activity log tests passed!")
