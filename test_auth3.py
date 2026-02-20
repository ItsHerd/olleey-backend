from supabase_auth.types import User

print("Methods on User:", dir(User))
if hasattr(User, 'dict'):
    print("Has dict")
if hasattr(User, 'model_dump'):
    print("Has model_dump")
