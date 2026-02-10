
import os
import sys
from pathlib import Path

# Add parent directory to path to import services
sys.path.insert(0, str(Path(__file__).parent.parent))

# Ensure we use test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["USE_MOCK_DB"] = "false"

from services.firestore import firestore_service
from firebase_admin import firestore

def cleanup_db():
    print("🧹 Cleaning up Test Database...")
    
    # 1. Reset SQLite
    db_path = Path(__file__).parent.parent / "youtube_dubbing.db"
    if db_path.exists():
        print(f"Deleting SQLite database: {db_path}")
        os.remove(db_path)
    
    # 2. Clear Firestore Collections
    collections = [
        'users',
        'subscriptions',
        'projects',
        'activity_logs',
        'processing_jobs',
        'language_channels',
        'localized_videos',
        'youtube_connections',
        'user_settings'
    ]
    
    db = firestore_service.db
    
    for collection_name in collections:
        print(f"Clearing collection: {collection_name}...")
        docs = db.collection(collection_name).stream()
        deleted_count = 0
        for doc in docs:
            doc.reference.delete()
            deleted_count += 1
        print(f"Deleted {deleted_count} documents from {collection_name}")

    print("✅ Cleanup complete!")

if __name__ == "__main__":
    cleanup_db()
