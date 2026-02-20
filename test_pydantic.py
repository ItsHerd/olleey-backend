from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str

    class Config:
        env_file = ".env"

print(Settings().model_dump())
