#!/usr/bin/env python3
"""
Show current Firebase authenticated users.
Helps identify which user_id to use for seeded data.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firebase_admin import auth

def list_users():
    """List all Firebase users."""
    print("\n" + "=" * 60)
    print("Firebase Users")
    print("=" * 60 + "\n")

    page = auth.list_users()
    users = []

    while page:
        for user in page.users:
            users.append(user)
        page = page.get_next_page()

    if not users:
        print("❌ No users found in Firebase Auth")
        return

    for i, user in enumerate(users, 1):
        print(f"\n👤 User #{i}")
        print(f"   UID: {user.uid}")
        print(f"   Email: {user.email or '(no email)'}")
        print(f"   Display Name: {user.display_name or '(no name)'}")
        print(f"   Created: {user.user_metadata.creation_timestamp}")

        # Check if provider
        providers = [p.provider_id for p in (user.provider_data or [])]
        if providers:
            print(f"   Providers: {', '.join(providers)}")

    print("\n" + "=" * 60)
    print(f"Total users: {len(users)}")
    print("=" * 60 + "\n")

    if len(users) == 1:
        print(f"💡 Use this user_id: {users[0].uid}")
    else:
        print("💡 Copy one of the UIDs above to use with update_user_id.py")

if __name__ == "__main__":
    list_users()
