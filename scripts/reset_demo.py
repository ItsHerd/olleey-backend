#!/usr/bin/env python3
"""
Manual script to reset demo user data.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    from services.demo_simulator import demo_simulator
    from firebase_admin import auth
    
    # Find demo user
    try:
        user = auth.get_user_by_email("demo@olleey.com")
        user_id = user.uid
        print(f"Found demo user: {user_id}")
        
        # Reset demo data
        print("Resetting demo data...")
        await demo_simulator.reset_demo_data(user_id)
        print("Demo data reset complete!")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
