#!/usr/bin/env python3
"""Test that the backend can import without Firebase errors."""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing imports...")

try:
    print("  ✓ Importing config...")
    from config import settings, DEMO_VIDEO_LIBRARY
    
    print("  ✓ Importing supabase_db...")
    from services.supabase_db import supabase_service
    
    print("  ✓ Importing job_queue...")
    from services.job_queue import enqueue_dubbing_job
    
    print("  ✓ Importing demo_simulator...")
    from services.demo_simulator import demo_simulator
    
    print("  ✓ Importing mock_pipeline...")
    from services.mock_pipeline import mock_pipeline
    
    print("  ✓ Importing routers...")
    from routers import jobs, auth, webhooks, settings as settings_router
    
    print("\n✅ All imports successful! Firebase has been removed.")
    print(f"\nDemo videos configured: {len(DEMO_VIDEO_LIBRARY)}")
    print(f"Environment: {settings.environment}")
    
except Exception as e:
    print(f"\n❌ Import failed: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
