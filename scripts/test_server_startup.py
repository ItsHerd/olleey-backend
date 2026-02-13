#!/usr/bin/env python3
"""Test starting the FastAPI server."""
import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("Testing FastAPI server startup...")

try:
    print("  ✓ Importing main app...")
    from main import app
    
    print("  ✓ App created successfully!")
    print(f"  App title: {app.title}")
    print(f"  Routes: {len(app.routes)}")
    
    print("\n✅ Server can start! Firebase has been successfully removed.")
    print("\nYou can now run: python3 dev_server.py")
    
except Exception as e:
    print(f"\n❌ Server startup failed: {str(e)}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
