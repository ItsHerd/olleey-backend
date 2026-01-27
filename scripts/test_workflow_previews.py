
import sys
import time
import requests
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://127.0.0.1:8000"
TEST_USER_ID = "5TEUt0AICGcrKAum7LJauZJcODq1"

def get_session():
    """Get requests session with mock auth."""
    session = requests.Session()
    # Mock auth headers - assuming the local middleware allows this or we use valid token
    # Since we are using mock DB/Auth usually in local test, we try with a mock token
    # that the mock auth middleware respects if configured.
    # Otherwise we might need to actually login.
    # Looking at middleware/auth.py in previous context might help.
    # We will assume a simple Bearer token works if verify_firebase_token is mocked in app (which it is for tests usually)
    # BUT, the running server might be real.
    # Let's try to set a header that identifies the user if possible or use a known test user token.
    session.headers.update({"Authorization": "Bearer mock-token-for-testing"})
    return session

def test_workflow_previews():
    print("🚀 Testing Workflow Previews (Dubbed Audio)")
    
    session = get_session()
    
    # 1. Create a simulated job
    print("\n1. Creating simulated job...")
    payload = {
        "source_video_id": "test_vid_123",
        "target_languages": ["es", "fr"],
        "is_simulation": True
    }
    # We need to simulate the user context. 
    # If the running server doesn't mock auth, this might fail 401. Acknowledged.
    # We'll try just passing user_id query param if the dev server allows it, or rely on existing auth.
    # Actually, the best way for local script against running server is to assume 
    # verify_firebase_token is NOT mocked in main.py unless env var set.
    # I'll rely on the server running with USE_MOCK_DB=true or similar.
    # If it fails, I'll know.
    
    # Wait, the previous script `scripts/test_activity_logs.py` used `TestClient` which mocks things internally.
    # `scripts/test_approval_workflow.py` used `requests` against localhost.
    # I should use `TestClient` pattern for reliability if I can import `app`.
    # BUT `app` is in `main.py` which imports everything.
    
    # Let's use `TestClient` to be safe and self-contained, mocking the auth dependency.
    from fastapi.testclient import TestClient
    try:
        from main import app
        from middleware.auth import verify_firebase_token
        from unittest.mock import MagicMock
        
        # Override auth
        async def mock_get_current_user():
             return {"user_id": TEST_USER_ID, "email": "test@example.com"}
        
        app.dependency_overrides[verify_firebase_token] = mock_get_current_user
        
        client = TestClient(app)
        
        response = client.post("/jobs", json=payload)
        if response.status_code != 200:
            print(f"❌ Creation failed: {response.text}")
            return
            
        data = response.json()
        job_id = data["job_id"]
        print(f"✅ Created Job ID: {job_id}")
        
        # 2. Wait for processing (Simulation is fast but has sleeps)
        print("Waiting for simulation to process...")
        max_retries = 10
        for i in range(max_retries):
            time.sleep(2)
            res = client.get(f"/jobs/{job_id}")
            status = res.json().get("status")
            print(f"   Status: {status}")
            if status == "waiting_approval":
                break
            if status == "failed":
                print("❌ Job failed during simulation")
                return
        else:
            print("❌ Timed out waiting for job")
            return
            
        # 3. Check videos for preview URLs
        print("\n3. Verifying Stage Previews...")
        res = client.get(f"/jobs/{job_id}/videos")
        videos = res.json()
        
        if not videos:
            print("❌ No videos found")
            return
            
        all_passed = True
        for vid in videos:
            lang = vid['language_code']
            audio_url = vid.get('dubbed_audio_url')
            storage_url = vid.get('storage_url')
            
            print(f"   Language: {lang}")
            print(f"     - Video URL: {storage_url}")
            print(f"     - Audio URL: {audio_url}")
            
            if not audio_url:
                print(f"❌ Missing dubbed_audio_url for {lang}")
                all_passed = False
            elif "mock_dub" not in audio_url and "storage/audios" not in audio_url: # basic validation matches simulation format
                print(f"⚠️ Unexpected format for audio_url: {audio_url}")
                
        if all_passed:
            print("\n✅ Verification Successful: Workflow previews are exposed!")
        else:
            print("\n❌ Verification Failed: Missing fields.")
            
    except ImportError:
        print("Could not import app. Run this from project root.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_workflow_previews()
