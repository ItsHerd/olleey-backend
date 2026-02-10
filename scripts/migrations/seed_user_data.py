#!/usr/bin/env python3
"""
Seed script to populate Firestore with sample data for a specific user.
Includes channels, videos, and the Garry Tan demo.
"""

import sys
import os
from datetime import datetime, timezone
import uuid

# Add parent directory to path to import from routers
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.firestore import firestore_service, FirestoreService

def seed_user_data(user_id: str):
    """Seed data for a specific user."""

    print(f"Starting data seeding for user: {user_id}")

    # Create a default project
    project_id = str(uuid.uuid4())
    project_data = {
        'id': project_id,
        'user_id': user_id,
        'name': 'Demo Project',
        'description': 'Sample project with demo content',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'settings': {}
    }

    try:
        firestore_service.db.collection('projects').document(project_id).set(project_data)
        print(f"✓ Created project: {project_id}")
    except Exception as e:
        print(f"✗ Error creating project: {e}")
        return

    # Create master channel (English)
    master_channel_id = f"UC_{uuid.uuid4().hex[:16]}"
    master_channel_data = {
        'channel_id': master_channel_id,
        'user_id': user_id,
        'project_id': project_id,
        'channel_name': 'Tech Insights',
        'language_code': 'en',
        'language_name': 'English',
        'is_master': True,
        'description': 'Original English tech content',
        'thumbnail_url': 'https://via.placeholder.com/800x800/4F46E5/FFFFFF?text=Tech+Insights',
        'subscriber_count': 125000,
        'video_count': 1,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }

    try:
        firestore_service.db.collection('channels').document(master_channel_id).set(master_channel_data)
        print(f"✓ Created master channel: {master_channel_id}")
    except Exception as e:
        print(f"✗ Error creating master channel: {e}")
        return

    # Create Spanish localization channel
    spanish_channel_id = f"UC_{uuid.uuid4().hex[:16]}"
    spanish_channel_data = {
        'channel_id': spanish_channel_id,
        'user_id': user_id,
        'project_id': project_id,
        'channel_name': 'Tech Insights ES',
        'language_code': 'es',
        'language_name': 'Spanish',
        'is_master': False,
        'master_channel_id': master_channel_id,
        'description': 'Contenido técnico en español',
        'thumbnail_url': 'https://via.placeholder.com/800x800/EC4899/FFFFFF?text=Tech+ES',
        'subscriber_count': 45000,
        'video_count': 1,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }

    try:
        firestore_service.db.collection('channels').document(spanish_channel_id).set(spanish_channel_data)
        print(f"✓ Created Spanish channel: {spanish_channel_id}")
    except Exception as e:
        print(f"✗ Error creating Spanish channel: {e}")
        return

    # Create the Garry Tan demo video
    video_id = "garry_tan_yc_demo"
    video_data = {
        'video_id': video_id,
        'user_id': user_id,
        'project_id': project_id,
        'channel_id': master_channel_id,
        'channel_name': 'Tech Insights',
        'title': 'Garry Tan - President & CEO of Y Combinator',
        'description': 'Garry Tan discusses the future of startups, innovation at Y Combinator, and advice for founders building the next generation of transformative companies.',
        'thumbnail_url': 'https://tii.imgix.net/production/articles/7643/03e02ef7-f12e-4faf-8551-37d5c5785586-UQ6LXV.jpg',
        'storage_url': 'https://olleey-videos.s3.us-west-1.amazonaws.com/en.mov',
        'video_url': 'https://olleey-videos.s3.us-west-1.amazonaws.com/en.mov',
        'duration': 180,
        'view_count': 285000,
        'like_count': 12400,
        'comment_count': 856,
        'published_at': datetime.now(timezone.utc),
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'status': 'published',
        'language_code': 'en',
        'localizations': []
    }

    try:
        firestore_service.db.collection('videos').document(video_id).set(video_data)
        print(f"✓ Created Garry Tan demo video: {video_id}")
    except Exception as e:
        print(f"✗ Error creating video: {e}")
        return

    # Create a processing job for the video
    job_id = str(uuid.uuid4())
    job_data = {
        'id': job_id,
        'job_id': job_id,
        'user_id': user_id,
        'project_id': project_id,
        'source_video_id': video_id,
        'source_channel_id': master_channel_id,
        'target_languages': ['es'],
        'status': 'completed',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc),
        'workflow_state': {
            'metadata_extraction': {'status': 'completed'},
            'translations': {'es': {'status': 'completed'}},
            'video_dubbing': {'es': {'status': 'completed'}},
            'thumbnails': {'es': {'status': 'completed'}},
            'approval_status': {
                'requires_review': False,
                'approved_languages': ['es'],
                'rejected_languages': []
            }
        }
    }

    try:
        firestore_service.db.collection('processing_jobs').document(job_id).set(job_data)
        print(f"✓ Created processing job: {job_id}")
    except Exception as e:
        print(f"✗ Error creating job: {e}")
        return

    # Create Spanish localized video
    localized_video_id = str(uuid.uuid4())
    localized_video_data = {
        'id': localized_video_id,
        'job_id': job_id,
        'source_video_id': video_id,
        'user_id': user_id,
        'project_id': project_id,
        'channel_id': spanish_channel_id,
        'language_code': 'es',
        'status': 'waiting_approval',
        'title': 'Garry Tan - Presidente y CEO de Y Combinator',
        'description': 'Garry Tan analiza el futuro de las startups, la innovación en Y Combinator y consejos para fundadores que construyen la próxima generación de empresas transformadoras.',
        'thumbnail_url': 'https://tii.imgix.net/production/articles/7643/03e02ef7-f12e-4faf-8551-37d5c5785586-UQ6LXV.jpg',
        'storage_url': 'https://olleey-videos.s3.us-west-1.amazonaws.com/es.mov',
        'video_url': 'https://olleey-videos.s3.us-west-1.amazonaws.com/es.mov',
        'duration': 180,
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }

    try:
        firestore_service.db.collection('localized_videos').document(localized_video_id).set(localized_video_data)
        print(f"✓ Created Spanish localized video: {localized_video_id}")
    except Exception as e:
        print(f"✗ Error creating localized video: {e}")
        return

    print("\n" + "="*50)
    print("✓ Data seeding completed successfully!")
    print("="*50)
    print(f"\nUser ID: {user_id}")
    print(f"Project ID: {project_id}")
    print(f"Master Channel: {master_channel_id}")
    print(f"Spanish Channel: {spanish_channel_id}")
    print(f"Video ID: {video_id}")
    print(f"Job ID: {job_id}")
    print(f"Localized Video ID: {localized_video_id}")
    print("\nThe user can now:")
    print("1. View the Garry Tan demo video in All Media")
    print("2. Review the Spanish localization in the Review Hub")
    print("3. See the video in both English and Spanish channels")


if __name__ == "__main__":
    user_id = "hMMfeokJJYVd9BcYxEKxU54qjkr2"
    seed_user_data(user_id)
