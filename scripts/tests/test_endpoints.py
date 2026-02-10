"""Script to test API endpoints with mock data."""
import requests
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://127.0.0.1:8000"
TEST_USER_ID = "12345678901234567890"


def print_response(method: str, endpoint: str, response: requests.Response):
    """Pretty print API response."""
    print(f"\n{'='*60}")
    print(f"{method} {endpoint}")
    print(f"Status: {response.status_code}")
    print(f"{'='*60}")
    
    try:
        data = response.json()
        print(json.dumps(data, indent=2, default=str))
    except:
        print(response.text)
    print()


def get_session():
    """Get requests session with mock auth."""
    session = requests.Session()
    session.headers.update({"Authorization": "Bearer mock-token"})
    return session



def test_auth_endpoints():
    """Test authentication endpoints."""
    print("\n🔐 Testing Authentication Endpoints")
    print("="*60)
    
    session = get_session()
    # Test /auth/me
    response = session.get(f"{BASE_URL}/auth/me", params={"user_id": TEST_USER_ID})
    print_response("GET", "/auth/me", response)


def test_channel_endpoints():
    """Test channel endpoints."""
    print("\n📺 Testing Channel Endpoints")
    print("="*60)
    
    session = get_session()
    # Test GET /channels
    response = session.get(f"{BASE_URL}/channels", params={"user_id": TEST_USER_ID})
    print_response("GET", "/channels", response)


def test_job_endpoints():
    """Test job endpoints."""
    print("\n⚙️  Testing Job Endpoints")
    print("="*60)
    
    session = get_session()
    # Test GET /jobs (list all jobs)
    response = session.get(f"{BASE_URL}/jobs", params={"user_id": TEST_USER_ID})
    print_response("GET", "/jobs", response)
    
    # Get first job ID if available
    if response.status_code == 200:
        data = response.json()
        jobs = data.get("jobs", [])
        if jobs:
            first_job_id = jobs[0].get("job_id")
            
            # Test GET /jobs/{job_id}
            response = session.get(
                f"{BASE_URL}/jobs/{first_job_id}",
                params={"user_id": TEST_USER_ID}
            )
            print_response("GET", f"/jobs/{first_job_id}", response)
            
            # Test filtering by status
            response = session.get(
                f"{BASE_URL}/jobs",
                params={"user_id": TEST_USER_ID, "status": "completed"}
            )
            print_response("GET", "/jobs?status=completed", response)


def test_video_endpoints():
    """Test video endpoints."""
    print("\n🎥 Testing Video Endpoints")
    print("="*60)
    
    session = get_session()
    # Test GET /videos/list
    response = session.get(
        f"{BASE_URL}/videos/list",
        params={"user_id": TEST_USER_ID, "limit": 5}
    )
    print_response("GET", "/videos/list", response)


def test_root_endpoints():
    """Test root/health endpoints."""
    print("\n🏠 Testing Root Endpoints")
    print("="*60)
    
    # Test GET /
    response = requests.get(f"{BASE_URL}/")
    print_response("GET", "/", response)
    
    # Test GET /health
    response = requests.get(f"{BASE_URL}/health")
    print_response("GET", "/health", response)


def main():
    """Run all endpoint tests."""
    print("🧪 Testing YouTube Dubbing Platform API Endpoints")
    print("="*60)
    print(f"Base URL: {BASE_URL}")
    print(f"Test User ID: {TEST_USER_ID}")
    
    try:
        # Test if server is running
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code != 200:
            print(f"\n❌ Server is not responding correctly. Status: {response.status_code}")
            sys.exit(1)
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Cannot connect to server at {BASE_URL}")
        print("   Make sure the server is running: uvicorn main:app --reload")
        sys.exit(1)
    
    # Run tests
    test_root_endpoints()
    test_auth_endpoints()
    test_channel_endpoints()
    test_job_endpoints()
    test_video_endpoints()
    
    print("\n" + "="*60)
    print("✅ All endpoint tests completed!")
    print("="*60)


if __name__ == "__main__":
    main()
