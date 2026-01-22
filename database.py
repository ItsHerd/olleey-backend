"""Database configuration and session management."""
from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import Generator
import uuid
from config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    """User model for storing OAuth tokens."""
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Subscription(Base):
    """PubSubHubbub subscription model."""
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, index=True)
    channel_id = Column(String, nullable=False, index=True)
    callback_url = Column(String, nullable=False)
    topic = Column(String, nullable=False)  # Feed URL
    lease_seconds = Column(Integer, nullable=False, default=2592000)  # 30 days default
    expires_at = Column(DateTime, nullable=True)
    secret = Column(String, nullable=True)  # Optional HMAC secret
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ProcessingJob(Base):
    """Processing job model for dubbing pipeline."""
    __tablename__ = "processing_jobs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_video_id = Column(String, nullable=False, index=True)
    source_channel_id = Column(String, nullable=False, index=True)
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, index=True)
    status = Column(String, nullable=False, default='pending')  # pending, downloading, processing, uploading, completed, failed
    target_languages = Column(JSON, nullable=False)  # Array of language codes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    progress = Column(Integer, nullable=True)  # 0-100


class LanguageChannel(Base):
    """Language-specific channel model."""
    __tablename__ = "language_channels"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey('users.user_id'), nullable=False, index=True)
    channel_id = Column(String, nullable=False, index=True)
    language_code = Column(String, nullable=False, index=True)  # ISO 639-1
    channel_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class LocalizedVideo(Base):
    """Localized video model."""
    __tablename__ = "localized_videos"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String, ForeignKey('processing_jobs.id'), nullable=False, index=True)
    source_video_id = Column(String, nullable=False, index=True)
    localized_video_id = Column(String, nullable=True, index=True)
    language_code = Column(String, nullable=False, index=True)
    channel_id = Column(String, nullable=False)
    status = Column(String, nullable=False, default='pending')  # pending, uploaded, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
