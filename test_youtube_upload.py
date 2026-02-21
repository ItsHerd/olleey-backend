import asyncio
from services.supabase_db import supabase_service
from routers.youtube_auth import get_youtube_service
import json
import traceback

async def main():
    try:
        # 1. Fetch all youtube connections to find a real one
        print("Fetching youtube connections...")
        # Since we don't have a specific user_id, let's query the table directly if possible
        # Or we can get all users and iterate. 
        # Actually, let's just use the supabase client directly to get all rows
        response = supabase_service.client.table('youtube_connections').select('*').execute()
        connections = response.data
        print(f"Total connections found: {len(connections)}")
        
        real_connections = [c for c in connections if not c.get('access_token', '').startswith('mock_')]
        print(f"Real connections: {len(real_connections)}")
        
        for conn in real_connections:
            user_id = conn['user_id']
            connection_id = conn['connection_id']
            print(f"\n--- Testing with user_id: {user_id}, connection_id: {connection_id}, channel: {conn.get('youtube_channel_name')} ---")
            
            try:
                # 2. Try to get the YouTube service
                youtube = get_youtube_service(user_id=user_id, connection_id=connection_id)
                if not youtube:
                    print("Failed to get YouTube service")
                    continue
                    
                print("Successfully authenticated with YouTube.")
                
                # 3. Test API call (e.g., getting channel details)
                channels_response = youtube.channels().list(mine=True, part='snippet').execute()
                print("Channel list response snippet (title): ", channels_response['items'][0]['snippet']['title'])
                
                print("\n\nTesting actual upload by creating a dummy video file...")
                
                # Create a tiny dummy text file and rename it to .mp4 (YouTube will reject it eventually as processing fails, but the API upload will succeed)
                dummy_file = "dummy_video_upload_test.mp4"
                with open(dummy_file, "w") as f:
                    f.write("This is a dummy video file for testing YouTube API uploads via Olleey pipeline.")
                
                try:
                    from googleapiclient.http import MediaFileUpload
                    
                    body = {
                        'snippet': {
                            'title': '[Test] Olleey Pipeline Upload Dummy',
                            'description': 'This is a test video uploaded via the Olleey API to verify OAuth scopes and Quotas. Feel free to delete.',
                            'tags': ['test', 'olleey'],
                            'categoryId': '22'
                        },
                        'status': {
                            'privacyStatus': 'private',
                            'selfDeclaredMadeForKids': False
                        }
                    }
                    
                    media = MediaFileUpload(
                        dummy_file,
                        chunksize=-1,
                        resumable=True
                    )
                    
                    print("Uploading to YouTube...")
                    insert_request = youtube.videos().insert(
                        part=','.join(body.keys()),
                        body=body,
                        media_body=media
                    )
                    
                    response = insert_request.execute()
                    print(f"\n✅ Upload Successful! Video ID: {response['id']}")
                    print(f"Watch Link: https://www.youtube.com/watch?v={response['id']}")
                    
                finally:
                    import os
                    if os.path.exists(dummy_file):
                        os.remove(dummy_file)
                        
                break # Stop after finding a working connection
            except Exception as e:
                print(f"Error for this connection: {e}")
                
    except Exception as e:
        print(f"Global Error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
