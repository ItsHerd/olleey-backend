import os
from dotenv import load_dotenv

load_dotenv()

from services.supabase_db import supabase_service

try:
    user = supabase_service.client.auth.get_user("fake_token")
    print("Success:", user)
except Exception as e:
    import traceback
    traceback.print_exc()
