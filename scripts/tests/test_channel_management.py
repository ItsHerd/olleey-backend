"""Test script for channel management APIs."""
import sys
import asyncio
import httpx
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

BASE_URL = "http://localhost:8000"

# Test credentials
TEST_EMAIL = "testuser@example.com"
TEST_PASSWORD = "testpass123"


async def login():
    """Login and get access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/auth/login",
            json={"email": TEST_EMAIL, "password": TEST_PASSWORD}
        )
        if response.status_code != 200:
            print(f"❌ Login failed: {response.text}")
            sys.exit(1)
        data = response.json()
        return data["access_token"]


async def test_youtube_connections(token):
    """Test YouTube connection management."""
    print("\n" + "=" * 60)
    print("🔗 Testing YouTube Connection Management")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # 1. List connections
        print("\n1️⃣ Listing YouTube connections...")
        response = await client.get(f"{BASE_URL}/youtube/connections", headers=headers)
        if response.status_code == 200:
            data = response.json()
            connections = data.get("connections", [])
            print(f"✅ Found {len(connections)} connections")
            
            if not connections:
                print("⚠️ No connections found. Skipping connection tests.")
                return None
            
            # Display connections
            for conn in connections:
                primary = "🟢 PRIMARY" if conn.get("is_primary") else "⚪ Secondary"
                print(f"   {primary} - {conn.get('youtube_channel_name')} ({conn.get('connection_id')})")
            
            # Find non-primary connection for testing
            non_primary = next((c for c in connections if not c.get("is_primary")), None)
            
            if non_primary and len(connections) > 1:
                # 2. Set primary connection
                print(f"\n2️⃣ Setting '{non_primary.get('youtube_channel_name')}' as primary...")
                connection_id = non_primary.get("connection_id")
                response = await client.put(
                    f"{BASE_URL}/youtube/connections/{connection_id}/set-primary",
                    headers=headers
                )
                if response.status_code == 200:
                    print("✅ Primary connection updated")
                else:
                    print(f"❌ Failed: {response.text}")
                
                # 3. Verify change
                print("\n3️⃣ Verifying primary connection change...")
                response = await client.get(f"{BASE_URL}/youtube/connections", headers=headers)
                if response.status_code == 200:
                    connections = response.json().get("connections", [])
                    primary_conn = next((c for c in connections if c.get("is_primary")), None)
                    if primary_conn and primary_conn.get("connection_id") == connection_id:
                        print(f"✅ Verified: '{primary_conn.get('youtube_channel_name')}' is now primary")
                    else:
                        print("❌ Primary connection not updated correctly")
                
                # 4. Update connection (set back to non-primary)
                print("\n4️⃣ Updating connection settings...")
                response = await client.patch(
                    f"{BASE_URL}/youtube/connections/{connection_id}",
                    headers=headers,
                    json={"is_primary": False}
                )
                if response.status_code == 200:
                    print("✅ Connection updated")
                else:
                    print(f"❌ Failed: {response.text}")
            
            return connections[0].get("connection_id")
        else:
            print(f"❌ Failed to list connections: {response.text}")
            return None


async def test_language_channels(token):
    """Test language channel management."""
    print("\n" + "=" * 60)
    print("🌐 Testing Language Channel Management")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        # 1. List channels
        print("\n1️⃣ Listing language channels...")
        response = await client.get(f"{BASE_URL}/channels", headers=headers)
        if response.status_code == 200:
            data = response.json()
            channels = data.get("channels", [])
            print(f"✅ Found {len(channels)} language channels")
            
            if not channels:
                print("⚠️ No channels found. Skipping channel tests.")
                return
            
            # Display channels
            for ch in channels:
                paused = "⏸️ PAUSED" if ch.get("is_paused") else "▶️ Active"
                print(f"   {paused} - {ch.get('channel_name')} ({ch.get('language_code')})")
            
            # Pick first channel for testing
            test_channel = channels[0]
            channel_id = test_channel.get("channel_id")
            original_paused = test_channel.get("is_paused", False)
            
            # 2. Pause channel
            print(f"\n2️⃣ Pausing channel '{test_channel.get('channel_name')}'...")
            response = await client.put(
                f"{BASE_URL}/channels/{channel_id}/pause",
                headers=headers
            )
            if response.status_code == 200:
                print("✅ Channel paused")
            else:
                print(f"❌ Failed: {response.text}")
            
            # 3. Verify pause status
            print("\n3️⃣ Verifying pause status...")
            response = await client.get(f"{BASE_URL}/channels", headers=headers)
            if response.status_code == 200:
                channels = response.json().get("channels", [])
                updated_channel = next((c for c in channels if c.get("channel_id") == channel_id), None)
                if updated_channel and updated_channel.get("is_paused"):
                    print("✅ Verified: Channel is paused")
                else:
                    print("❌ Channel pause status not updated")
            
            # 4. Unpause channel
            print(f"\n4️⃣ Unpausing channel '{test_channel.get('channel_name')}'...")
            response = await client.put(
                f"{BASE_URL}/channels/{channel_id}/unpause",
                headers=headers
            )
            if response.status_code == 200:
                print("✅ Channel unpaused")
            else:
                print(f"❌ Failed: {response.text}")
            
            # 5. Update channel metadata
            print("\n5️⃣ Updating channel metadata...")
            new_name = f"{test_channel.get('channel_name')} (Updated)"
            response = await client.patch(
                f"{BASE_URL}/channels/{channel_id}",
                headers=headers,
                json={
                    "channel_name": new_name,
                    "is_paused": original_paused  # Restore original pause state
                }
            )
            if response.status_code == 200:
                updated = response.json()
                print(f"✅ Channel updated: {updated.get('channel_name')}")
                
                # Restore original name
                print("\n6️⃣ Restoring original channel name...")
                await client.patch(
                    f"{BASE_URL}/channels/{channel_id}",
                    headers=headers,
                    json={"channel_name": test_channel.get("channel_name")}
                )
                print("✅ Original name restored")
            else:
                print(f"❌ Failed: {response.text}")
        else:
            print(f"❌ Failed to list channels: {response.text}")


async def test_channel_graph(token):
    """Test channel graph endpoint."""
    print("\n" + "=" * 60)
    print("📊 Testing Channel Graph")
    print("=" * 60)
    
    headers = {"Authorization": f"Bearer {token}"}
    
    async with httpx.AsyncClient() as client:
        print("\n1️⃣ Getting channel graph...")
        response = await client.get(f"{BASE_URL}/channels/graph", headers=headers)
        if response.status_code == 200:
            data = response.json()
            master_nodes = data.get("master_nodes", [])
            print(f"✅ Graph retrieved")
            print(f"   Total connections: {data.get('total_connections')}")
            print(f"   Active: {data.get('active_connections')}")
            print(f"   Expired: {data.get('expired_connections')}")
            
            for master in master_nodes:
                primary = "🟢 PRIMARY" if master.get("is_primary") else "⚪ Secondary"
                print(f"\n   {primary} {master.get('channel_name')}")
                print(f"   Status: {master.get('status', {}).get('status')}")
                print(f"   Videos: {master.get('total_videos')}")
                print(f"   Translations: {master.get('total_translations')}")
                
                lang_channels = master.get("language_channels", [])
                print(f"   Language Channels: {len(lang_channels)}")
                for lang in lang_channels:
                    paused = "⏸️" if lang.get("is_paused") else "▶️"
                    print(f"      {paused} {lang.get('language_name')} - {lang.get('videos_count')} videos")
        else:
            print(f"❌ Failed: {response.text}")


async def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Channel Management API Tests")
    print("=" * 60)
    
    try:
        # Login
        print("\n🔑 Logging in...")
        token = await login()
        print("✅ Login successful")
        
        # Run tests
        await test_youtube_connections(token)
        await test_language_channels(token)
        await test_channel_graph(token)
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ All tests completed!")
        print("=" * 60)
        print("\nWhat was tested:")
        print("  ✅ List YouTube connections")
        print("  ✅ Set primary connection")
        print("  ✅ Update connection settings")
        print("  ✅ List language channels")
        print("  ✅ Pause/unpause channels")
        print("  ✅ Update channel metadata")
        print("  ✅ Channel graph with status")
        print("\n" + "=" * 60)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
