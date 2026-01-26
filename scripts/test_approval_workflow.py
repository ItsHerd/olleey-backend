"""Script to test approval workflow endpoints."""
import requests
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://127.0.0.1:8000"
TEST_USER_ID = "5TEUt0AICGcrKAum7LJauZJcODq1"

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

def test_approval_workflow():
    """Test approval workflow endpoints."""
    print("\n🚀 Testing Approval Workflow Endpoints")
    print("="*60)
    
    session = get_session()
    
    # 1. Get List of Jobs
    print("\n1. Listing jobs to find a candidate...")
    response = session.get(f"{BASE_URL}/jobs", params={"user_id": TEST_USER_ID})
    
    if response.status_code != 200:
        print(f"Failed to list jobs: {response.text}")
        return
        
    data = response.json()
    jobs = data.get("jobs", [])
    
    if not jobs:
        print("No jobs found. Creating a manual job...")
        # Create a manual job
        create_data = {
            "source_channel_id": "UC_TEST_SOURCE_CHANNEL",
            "target_channel_ids": "UC_TEST_TARGET_CHANNEL",
            "target_languages": "es",
            "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ" 
        }
        res = session.post(f"{BASE_URL}/jobs/manual", data=create_data)
        if res.status_code != 200:
            print(f"Failed to create manual job: {res.text}")
            return
            
        print("Manual job created.")
        job_id = res.json().get("job_id")
    else:
        # 2. Pick a job (first one)
        job_id = jobs[0].get("job_id")
        
    print(f"\n2. Testing with Job ID: {job_id}")
    
    # 3. Test GET /jobs/{job_id}/videos (NEW ENDPOINT)
    print(f"\n3. Testing GET /jobs/{job_id}/videos")
    response = session.get(f"{BASE_URL}/jobs/{job_id}/videos", params={"user_id": TEST_USER_ID})
    print_response("GET", f"/jobs/{job_id}/videos", response)
    
    if response.status_code == 200:
        videos = response.json()
        print(f"✅ Successfully retrieved {len(videos)} localized videos for job {job_id}")
        if len(videos) > 0:
            print("Sample video data:")
            print(json.dumps(videos[0], indent=2))
            
            # Verify schema fields
            required_fields = ["id", "job_id", "source_video_id", "language_code", "status"]
            video = videos[0]
            missing = [f for f in required_fields if f not in video]
            if missing:
                print(f"❌ Missing required fields in response: {missing}")
            else:
                print("✅ Schema verification passed")
    else:
        print("❌ Failed to retrieve videos")

if __name__ == "__main__":
    test_approval_workflow()
