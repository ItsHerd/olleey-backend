import os
from dotenv import load_dotenv

load_dotenv()

from services.supabase_db import supabase_service

print("get_user method varnames:", supabase_service.client.auth.get_user.__code__.co_varnames)
