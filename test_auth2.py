import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from services.supabase_db import supabase_service

print("Methods on auth:", dir(supabase_service.client.auth))
