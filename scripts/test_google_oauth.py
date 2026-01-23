"""
Test script for Google OAuth authentication endpoint.

This script demonstrates how to test the Google OAuth endpoint.
Note: You'll need a valid Google ID token to test this properly.
"""

import httpx
import asyncio


async def test_google_oauth():
    """Test the Google OAuth endpoint."""
    
    # NOTE: Replace this with a real Google ID token from your frontend
    # You can get one by implementing Google Sign-In on the frontend
    test_id_token = "YOUR_GOOGLE_ID_TOKEN_HERE"
    
    base_url = "http://localhost:8000"
    
    print("Testing Google OAuth endpoint...")
    print("-" * 50)
    
    try:
        async with httpx.AsyncClient() as client:
            # Test Google OAuth sign-in
            response = await client.post(
                f"{base_url}/auth/google",
                json={"id_token": test_id_token},
                timeout=10.0
            )
            
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                data = response.json()
                print("\n✅ Google OAuth successful!")
                print(f"Access Token: {data['access_token'][:50]}...")
                print(f"Refresh Token: {data['refresh_token'][:50]}...")
                print(f"Expires In: {data['expires_in']} seconds")
                
                # Test getting user info with the token
                print("\n" + "-" * 50)
                print("Testing /auth/me endpoint with Google OAuth token...")
                
                me_response = await client.get(
                    f"{base_url}/auth/me",
                    headers={"Authorization": f"Bearer {data['access_token']}"}
                )
                
                print(f"Status Code: {me_response.status_code}")
                print(f"User Info: {me_response.json()}")
                
                if me_response.status_code == 200:
                    user_info = me_response.json()
                    print(f"\n✅ User authenticated!")
                    print(f"User ID: {user_info['user_id']}")
                    print(f"Email: {user_info['email']}")
                    print(f"Name: {user_info['name']}")
                    print(f"Auth Provider: {user_info['auth_provider']}")
            else:
                print(f"\n❌ Google OAuth failed: {response.json()}")
                
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")


async def test_endpoint_availability():
    """Test if the Google OAuth endpoint is available."""
    
    base_url = "http://localhost:8000"
    
    print("Checking if server is running...")
    print("-" * 50)
    
    try:
        async with httpx.AsyncClient() as client:
            # Check health endpoint
            response = await client.get(f"{base_url}/health", timeout=5.0)
            
            if response.status_code == 200:
                print("✅ Server is running!")
                print(f"Response: {response.json()}")
                
                # Check API docs
                print("\n📚 API Documentation available at:")
                print(f"   {base_url}/docs")
                print(f"   {base_url}/redoc")
                
                return True
            else:
                print("❌ Server responded with error")
                return False
                
    except httpx.ConnectError:
        print("❌ Cannot connect to server. Is it running?")
        print("   Start the server with: python main.py")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


async def main():
    """Main test function."""
    
    print("=" * 50)
    print("Google OAuth Endpoint Test")
    print("=" * 50)
    print()
    
    # First check if server is available
    server_available = await test_endpoint_availability()
    
    if not server_available:
        return
    
    print("\n" + "=" * 50)
    print("Testing Google OAuth Flow")
    print("=" * 50)
    print()
    print("⚠️  To test this properly, you need to:")
    print("1. Implement Google Sign-In on your frontend")
    print("2. Get a valid Google ID token")
    print("3. Replace 'YOUR_GOOGLE_ID_TOKEN_HERE' in this script")
    print()
    print("For now, this will demonstrate the expected error:")
    print()
    
    await test_google_oauth()
    
    print("\n" + "=" * 50)
    print("Next Steps:")
    print("=" * 50)
    print("1. Enable Google Sign-In in Firebase Console")
    print("2. Add FIREBASE_WEB_API_KEY to your .env file")
    print("3. Implement Google Sign-In on your frontend")
    print("4. See GOOGLE_OAUTH_SETUP.md for detailed instructions")
    print()


if __name__ == "__main__":
    asyncio.run(main())
