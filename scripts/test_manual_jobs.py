#!/usr/bin/env python3
"""
Test script for manual job creation endpoints.

This script demonstrates how to create dubbing jobs using:
1. YouTube URL
2. Video file upload
"""

import requests
import os

# Configuration
API_BASE_URL = "http://localhost:8000"
AUTH_TOKEN = "YOUR_AUTH_TOKEN_HERE"  # Replace with actual token

# Headers
headers = {
    "Authorization": f"Bearer {AUTH_TOKEN}"
}


def test_create_job_with_url():
    """Test creating a job with a YouTube URL."""
    print("\n=== Test 1: Create Job with YouTube URL ===")
    
    url = f"{API_BASE_URL}/jobs/manual"
    
    # Note: Replace these with actual channel document IDs from your Firestore
    data = {
        "source_channel_id": "UCxxxxxx",
        "target_channel_ids": "channel_doc_id_1,channel_doc_id_2",  # Comma-separated channel IDs
        "project_id": "proj_123",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    }
    
    response = requests.post(url, headers=headers, data=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json()



def test_create_job_with_file(video_file_path):
    """Test creating a job with a video file upload."""
    print("\n=== Test 2: Create Job with Video File Upload ===")
    
    if not os.path.exists(video_file_path):
        print(f"Error: Video file not found at {video_file_path}")
        return None
    
    url = f"{API_BASE_URL}/jobs/manual"
    
    # Note: Replace these with actual channel document IDs from your Firestore
    data = {
        "source_channel_id": "UCxxxxxx",
        "target_channel_ids": "channel_doc_id_1,channel_doc_id_2",  # Comma-separated channel IDs
        "project_id": "proj_456"
    }
    
    files = {
        "video_file": open(video_file_path, "rb")
    }
    
    response = requests.post(url, headers=headers, data=data, files=files)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json()


def test_create_job_json_with_url():
    """Test creating a job using JSON endpoint with URL."""
    print("\n=== Test 3: Create Job with JSON (URL) ===")
    
    url = f"{API_BASE_URL}/jobs"
    
    # Note: Replace these with actual channel document IDs from your Firestore
    json_data = {
        "source_video_url": "https://youtu.be/dQw4w9WgXcQ",
        "source_channel_id": "UCxxxxxx",
        "target_channel_ids": ["channel_doc_id_1", "channel_doc_id_2"],  # List of channel IDs
        "project_id": "proj_789"
    }
    
    headers_json = {
        **headers,
        "Content-Type": "application/json"
    }
    
    response = requests.post(url, headers=headers_json, json=json_data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json()


def test_get_job_status(job_id):
    """Test getting job status."""
    print(f"\n=== Test 4: Get Job Status for {job_id} ===")
    
    url = f"{API_BASE_URL}/jobs/{job_id}"
    
    response = requests.get(url, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    return response.json()


def test_list_jobs():
    """Test listing all jobs."""
    print("\n=== Test 5: List All Jobs ===")
    
    url = f"{API_BASE_URL}/jobs"
    
    params = {
        "limit": 10,
        "offset": 0
    }
    
    response = requests.get(url, headers=headers, params=params)
    
    print(f"Status Code: {response.status_code}")
    response_data = response.json()
    print(f"Total Jobs: {response_data.get('total', 0)}")
    print(f"Jobs Returned: {len(response_data.get('jobs', []))}")
    
    return response_data


def main():
    """Run all tests."""
    print("=" * 60)
    print("Manual Job Creation API Tests")
    print("=" * 60)
    
    # Test 1: Create job with URL
    try:
        job1 = test_create_job_with_url()
        if job1 and 'job_id' in job1:
            # Test getting job status
            test_get_job_status(job1['job_id'])
    except Exception as e:
        print(f"Error in Test 1: {e}")
    
    # Test 2: Create job with file upload (optional - requires video file)
    # Uncomment and provide a video file path to test
    # try:
    #     job2 = test_create_job_with_file("/path/to/your/video.mp4")
    # except Exception as e:
    #     print(f"Error in Test 2: {e}")
    
    # Test 3: Create job using JSON endpoint
    try:
        job3 = test_create_job_json_with_url()
    except Exception as e:
        print(f"Error in Test 3: {e}")
    
    # Test 4: List all jobs
    try:
        test_list_jobs()
    except Exception as e:
        print(f"Error in Test 4: {e}")
    
    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    # Check if AUTH_TOKEN is set
    if AUTH_TOKEN == "YOUR_AUTH_TOKEN_HERE":
        print("WARNING: Please set your AUTH_TOKEN in the script before running tests.")
        print("You can get a token by logging in through the /auth/login endpoint.")
        print("\nTo get a token:")
        print("1. Visit http://localhost:8000/auth/login")
        print("2. Complete OAuth flow")
        print("3. Extract the token from the response")
    else:
        main()
