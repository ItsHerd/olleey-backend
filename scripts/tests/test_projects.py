
"""
Test script for verifying Multi-Project Architecture.
"""
import sys
import os
from pathlib import Path
import asyncio

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure we use test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["USE_MOCK_DB"] = "false"

from services.firestore import firestore_service

async def test_multi_project_flow():
    user_id = "L5gVvYWKdAMz7Fxdx6NmX39fzrX2"
    print(f"Testing for user: {user_id}")
    
    # 1. List Projects
    projects = firestore_service.list_projects(user_id)
    print(f"User has {len(projects)} projects.")
    
    # 2. Create Second Project
    print("Creating 'Second Project'...")
    project2_id = firestore_service.create_project(
        user_id=user_id,
        name="Second Project"
    )
    print(f"Created Project 2: {project2_id}")
    
    # 3. Create Job in Project 2
    print("Creating Job in Project 2...")
    job2_id = firestore_service.create_processing_job(
        source_video_id="proj2_vid",
        source_channel_id="proj2_chan",
        user_id=user_id,
        target_languages=["es"],
        project_id=project2_id
    )
    
    # 4. Verify Isolation
    print("Verifying List Isolation...")
    # List all jobs (should include both if no filter)
    all_jobs, _ = firestore_service.list_processing_jobs(user_id, limit=100)
    print(f"Total Jobs (all projects): {len(all_jobs)}")
    
    # List Project 1 jobs
    proj1_id = projects[0]['id']
    proj1_jobs, _ = firestore_service.list_processing_jobs(user_id, project_id=proj1_id)
    print(f"Project 1 Jobs: {len(proj1_jobs)}")
    
    # List Project 2 jobs
    proj2_jobs, _ = firestore_service.list_processing_jobs(user_id, project_id=project2_id)
    print(f"Project 2 Jobs: {len(proj2_jobs)}")
    
    assert job2_id in [j['id'] for j in proj2_jobs], "Job 2 not found in Project 2 list"
    assert job2_id not in [j['id'] for j in proj1_jobs], "Job 2 found in Project 1 list (Isolation Fail)"
    
    print("✅ Project Isolation Verified!")
    
    # Cleanup (Optional, but good for repetitive testing)
    # firestore_service.delete_project(project2_id)

if __name__ == "__main__":
    asyncio.run(test_multi_project_flow())
