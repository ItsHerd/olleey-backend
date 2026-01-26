"""
Script to verify project filtering for channels and graphs.
"""
import sys
import os
import uuid
from typing import Dict, List

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.firestore import firestore_service
from firebase_admin import firestore

USER_ID = "LlGV9wGDuvMcQMOXuVgA59RONxs2"

def setup_test_data():
    print(f"🚀 Setting up test data for user: {USER_ID}")
    
    # 1. Create two projects
    p1_id = str(uuid.uuid4())
    firestore_service.db.collection('projects').document(p1_id).set({
        'user_id': USER_ID,
        'name': 'Project A (Filtering Test)',
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    })
    
    p2_id = str(uuid.uuid4())
    firestore_service.db.collection('projects').document(p2_id).set({
        'user_id': USER_ID,
        'name': 'Project B (Filtering Test)',
        'created_at': firestore.SERVER_TIMESTAMP,
        'updated_at': firestore.SERVER_TIMESTAMP
    })
    
    # 2. Get/Create a master connection (needed for channel graph)
    connections = firestore_service.get_youtube_connections(USER_ID)
    master_conn = None
    for c in connections:
        if not c.get('master_connection_id'):
            master_conn = c
            break
            
    if not master_conn:
        print("❌ No master connection found. Please connect a YouTube channel first.")
        return None, None
        
    master_id = master_conn.get('connection_id') or master_conn.get('id')
    print(f"Using master connection: {master_id}")
    
    # 3. Create language channels for each project
    # Channel for Project A
    c1_id = firestore_service.create_language_channel(
        user_id=USER_ID,
        channel_id=f"UC_PROJ_A_{uuid.uuid4().hex[:6]}",
        language_code="es",
        language_codes=["es"],
        channel_name="Project A Channel",
        master_connection_id=master_id,
        project_id=p1_id
    )
    
    # Channel for Project B
    c2_id = firestore_service.create_language_channel(
        user_id=USER_ID,
        channel_id=f"UC_PROJ_B_{uuid.uuid4().hex[:6]}",
        language_code="de",
        language_codes=["de"],
        channel_name="Project B Channel",
        master_connection_id=master_id,
        project_id=p2_id
    )
    
    print(f"Created Project A ({p1_id}) with channel {c1_id}")
    print(f"Created Project B ({p2_id}) with channel {c2_id}")
    
    return p1_id, p2_id

def verify_filtering(p1_id, p2_id):
    import requests
    
    # This part requires the server to be running and a valid token.
    # Since we can't easily get a valid token in this script without complex auth,
    # we will verify using the service layer directly, which mirrors the endpoint logic.
    
    print("\n🔍 Verifying filtering logic via Service Layer...")
    
    # Test Project A
    channels_a = firestore_service.get_language_channels(USER_ID, project_id=p1_id)
    print(f"Project A Channels: {len(channels_a)}")
    is_valid_a = len(channels_a) == 1 and channels_a[0].get('project_id') == p1_id
    
    # Test Project B
    channels_b = firestore_service.get_language_channels(USER_ID, project_id=p2_id)
    print(f"Project B Channels: {len(channels_b)}")
    is_valid_b = len(channels_b) == 1 and channels_b[0].get('project_id') == p2_id
    
    if is_valid_a and is_valid_b:
        print("✅ Service layer filtering working correctly!")
    else:
        print("❌ Service layer filtering failed!")
        print(f"A: {channels_a}")
        print(f"B: {channels_b}")

if __name__ == "__main__":
    p1, p2 = setup_test_data()
    if p1 and p2:
        verify_filtering(p1, p2)
