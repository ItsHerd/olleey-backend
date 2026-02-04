"""Configuration settings for the YouTube Dubbing Platform."""
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
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
    
    # PubSubHubbub
    webhook_base_url: Optional[str] = None  # Base URL for webhook callbacks
    pubsubhubbub_hub_url: str = "https://pubsubhubbub.appspot.com/subscribe"
    
    # Frontend URL for OAuth redirects
    frontend_url: Optional[str] = None  # Frontend URL for OAuth callbacks (defaults to http://localhost:3000 in code)
    
    # Sync Labs API (for lip sync)
    sync_labs_api_key: Optional[str] = None
    sync_labs_base_url: str = "https://api.synclabs.so"

    # ElevenLabs
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_base_url: str = "https://api.elevenlabs.io/v1"
        
    # Firebase/Firestore
    # Production Credentials
    firebase_project_id_prod: str = "vox-translate-b8c94"
    firebase_credentials_path_prod: str = "./vox-translate-b8c94-firebase-adminsdk-fbsvc-7749166547.json"
    firebase_web_api_key_prod: Optional[str] = None
    firebase_web_api_key_generic: Optional[str] = Field(None, alias="firebase_web_api_key")

    # Test Credentials
    firebase_project_id_test: str = "olleey-test"
    firebase_credentials_path_test: str = "./olleey-test-firebase-adminsdk-fbsvc-c807baae03.json"
    firebase_web_api_key_test: Optional[str] = "AIzaSyBEi-QjTm_3uc5Zf2qaHfG2FkD1DhYGteE"

    @property
    def firebase_project_id(self) -> str:
        """Get active project ID based on environment."""
        if self.use_mock_db: # Fallback if flag is still true, though we removed implementation
             return "mock-project"
        if self.environment.lower() in ["test", "testing"]:
            return self.firebase_project_id_test
        return self.firebase_project_id_prod

    @property
    def firebase_credentials_path(self) -> str:
        """Get active credentials path based on environment."""
        if self.environment.lower() in ["test", "testing"]:
            return self.firebase_credentials_path_test
        return self.firebase_credentials_path_prod

    @property
    def firebase_web_api_key(self) -> Optional[str]:
        """Get active Web API Key based on environment."""
        # Prioritize the generic key from .env if it was explicitly set
        if self.firebase_web_api_key_generic:
            return self.firebase_web_api_key_generic
            
        if self.environment.lower() in ["test", "testing"]:
            return self.firebase_web_api_key_test
        return self.firebase_web_api_key_prod
    
    # Local Storage
    local_storage_dir: str = "./storage"  # Directory for storing processed videos locally
    
    # OAuth Scopes
    use_mock_db: bool = False
    youtube_scopes: list[str] = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile"
    ]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name in ["google_client_id", "google_client_secret", "google_redirect_uri", "firebase_web_api_key"]:
                return raw_val.strip()
            return raw_val


settings = Settings()
