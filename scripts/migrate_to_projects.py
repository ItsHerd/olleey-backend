
"""
Migration script to introduce Projects.
For each user, creates a 'Default Project' and assigns:
1. Primary YouTube Connection -> Project Master Account
2. Existing Jobs -> Project
3. Existing Language Channels -> Project
"""
import sys
import os
from pathlib import Path
from typing import Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure we use test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["USE_MOCK_DB"] = "false"

from services.firestore import firestore_service

def migrate_user(user_id: str):
    print(f"Migrating user: {user_id}")
    
    # Check if user already has projects
    projects = firestore_service.list_projects(user_id)
    if projects:
        print(f"User {user_id} already has {len(projects)} projects. Skipping creation.")
        default_project_id = projects[0]['id']
    else:
        # 1. Get Primary Connection
        primary_conn = firestore_service.get_primary_youtube_connection(user_id)
        master_conn_id = primary_conn['connection_id'] if primary_conn else None
        
        # 2. Create Default Project
        print(f"Creating 'Default Project' with Master Connection: {master_conn_id}")
        default_project_id = firestore_service.create_project(
            user_id=user_id,
            name="Default Project",
            master_connection_id=master_conn_id
        )
        print(f"Created Project ID: {default_project_id}")

    # 3. Migrate Jobs
    jobs, _ = firestore_service.list_processing_jobs(user_id, limit=1000)
    migrated_jobs = 0
    for job in jobs:
        if not job.get('project_id'):
            firestore_service.update_processing_job(job['id'], project_id=default_project_id)
            migrated_jobs += 1
    print(f"Migrated {migrated_jobs} jobs to project {default_project_id}")

    # 4. Migrate Language Channels
    channels = firestore_service.get_language_channels(user_id)
    migrated_channels = 0
    for channel in channels:
        if not channel.get('project_id'):
            firestore_service.update_language_channel(channel['id'], user_id, project_id=default_project_id)
            migrated_channels += 1
    print(f"Migrated {migrated_channels} language channels to project {default_project_id}")

def main():
    target_user_id = "L5gVvYWKdAMz7Fxdx6NmX39fzrX2"
    migrate_user(target_user_id)
    print("Migration complete!")

if __name__ == "__main__":
    main()
