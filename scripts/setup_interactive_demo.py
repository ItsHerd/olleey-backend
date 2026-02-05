#!/usr/bin/env python3
"""
Quick script to reset and initialize the interactive demo with real videos.
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.demo_simulator import demo_simulator, DEMO_EMAIL
from firebase_admin import auth

def main():
    print("=" * 70)
    print("  Interactive Demo Setup - With Real Videos")
    print("=" * 70)
    print()
    
    # Get demo user ID
    try:
        user = auth.get_user_by_email(DEMO_EMAIL)
        user_id = user.uid
        print(f"✅ Found demo user: {DEMO_EMAIL}")
        print(f"   User ID: {user_id}")
    except Exception as e:
        print(f"❌ Demo user not found. Please run: python scripts/seed_demo_flow.py")
        return 1
    
    print()
    print("🔄 Resetting demo data...")
    
    # Reset demo data (this will recreate everything with the real video)
    import asyncio
    asyncio.run(demo_simulator.reset_demo_data(user_id))
    
    print()
    print("=" * 70)
    print("  Setup Complete!")
    print("=" * 70)
    print()
    print("Login credentials:")
    print(f"  Email: {DEMO_EMAIL}")
    print(f"  Password: password")
    print()
    print("Features:")
    print("  ✅ Real EN video with ES dubbed version")
    print("  ✅ Interactive state controls on video cards")
    print("  ✅ Context-aware actions (processing → draft → live)")
    print("  ✅ State persists in localStorage")
    print()
    print("Usage:")
    print("  1. Login at http://localhost:3000")
    print("  2. Navigate to All Media page")
    print("  3. Find your real video with Spanish localization")
    print("  4. Use the demo controls to change states:")
    print("     - Processing → Click '→ Draft'")
    print("     - Draft → Click '✓ Approve' to publish")
    print("     - Live → Click '← Unpublish' to return to draft")
    print()
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
