"""Configuration settings for the YouTube Dubbing Platform."""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase Configuration
    supabase_url: str = Field(..., env="SUPABASE_URL")
    supabase_anon_key: str = Field(..., env="SUPABASE_ANON_KEY")
    supabase_service_key: Optional[str] = Field(None, env="SUPABASE_SERVICE_KEY")
    supabase_jwt_secret: Optional[str] = Field(None, env="SUPABASE_JWT_SECRET")

    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str
    
    # YouTube API
    youtube_api_key: str
    
    # Database
    database_url: str = "sqlite:///./youtube_dubbing.db"
    
    # App Settings
    secret_key: str
    environment: str = "development"
    allow_dev_auth: bool = True
    dev_auth_user_id: Optional[str] = Field(
        "096c8549-ce41-4b94-b7f7-25e39eb7578b",
        env="DEV_AUTH_USER_ID"
    )
    
    # PubSubHubbub
    webhook_base_url: Optional[str] = None  # Base URL for webhook callbacks
    pubsubhubbub_hub_url: str = "https://pubsubhubbub.appspot.com/subscribe"
    enable_subscription_renewal_scheduler: bool = False
    subscription_renewal_interval_minutes: int = 1440  # default: daily
    subscription_renew_before_hours: int = 168  # default: 7 days
    
    # Frontend URL for OAuth redirects
    frontend_url: Optional[str] = None  # Frontend URL for OAuth callbacks (defaults to http://localhost:3000 in code)
    
    # Sync Labs API (for lip sync)
    sync_labs_api_key: Optional[str] = None
    sync_labs_base_url: str = "https://api.synclabs.so"

    # ElevenLabs
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"
        
    # OAuth Scopes
    use_mock_db: bool = False
    youtube_scopes: list[str] = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    storage_type: str = "local"  # Options: "local" or "s3"
    local_storage_dir: str = "./storage"  # Directory for storing processed videos locally
    
    # AWS S3 Configuration (used when storage_type="s3")
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_region: str = "us-west-1"
    aws_s3_bucket: Optional[str] = None
    s3_presigned_url_expiry: int = 3600  # Presigned URL expiry in seconds
    cloudfront_url: Optional[str] = None  # Optional CloudFront CDN URL
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"
    )

    @classmethod
    def parse_env_var(cls, field_name: str, raw_val: str):
        if field_name in ["google_client_id", "google_client_secret", "google_redirect_uri", "supabase_url", "supabase_anon_key", "supabase_jwt_secret"]:
            return raw_val.strip()
        return raw_val


settings = Settings()


# Demo Video Library - Multiple pre-configured videos for demo user
DEMO_VIDEO_LIBRARY = {
    "video_001_yceo": {
        "id": "demo_real_video_001",
        "title": "The Nature of Startups with YC CEO",
        "description": "In-depth discussion about the fundamental nature of startups",
        "original_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/en.mp4",
        "thumbnail": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "duration": 180,
        "languages": {
            "es": {
                "dubbed_video_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/es.mov",
                "dubbed_audio_url": "https://olleey-videos.s3.us-west-1.amazonaws.com/es.mp3",
                "transcript": "Welcome to this discussion about the nature of startups...",
                "translation": "Bienvenido a esta discusión sobre la naturaleza de las startups...",
            },
            # Add more languages as you create them (fr, de, etc.)
        }
    },
    # Add more videos here as you expand demo library
}

# Pipeline timing configuration (in seconds) for demo simulation
DEMO_PIPELINE_TIMING = {
    "transcription": 5,
    "translation": 3,
    "dubbing": 8,
    "lip_sync": 10,
}


def validate_demo_config():
    """Validate demo video URLs on startup."""
    if settings.environment == "development":
        for video_key, video_data in DEMO_VIDEO_LIBRARY.items():
            print(f"[CONFIG] Demo video: {video_data['id']} - {video_data['title']}")
            langs = list(video_data.get('languages', {}).keys())
            if langs:
                print(f"  Languages available: {', '.join(langs)}")
