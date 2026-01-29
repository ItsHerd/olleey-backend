"""Main FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import os

from config import settings
from routers import auth, videos, localization, webhooks, channels, jobs, youtube_connect, dashboard, settings, events, projects


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    # Initialize Firestore (will be done automatically on first use)
    # Initialize local storage directory
    storage_dir = getattr(settings, 'local_storage_dir', './storage')
    os.makedirs(storage_dir, exist_ok=True)
    os.makedirs(os.path.join(storage_dir, 'videos'), exist_ok=True)
    yield


app = FastAPI(
    title="YouTube Dubbing Platform API",
    description="Backend service for managing YouTube content for dubbing/localization",
    version="1.0.0",
    lifespan=lifespan
)

# Trust proxy headers for Render deployment
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(dashboard.router)
app.include_router(youtube_connect.router)
app.include_router(videos.router)
app.include_router(localization.router)
app.include_router(webhooks.router)
app.include_router(channels.router)
app.include_router(jobs.router)
app.include_router(projects.router)
app.include_router(settings.router)
app.include_router(events.router)

# Mount storage directory for serving processed videos
storage_dir = getattr(settings, 'local_storage_dir', './storage')
os.makedirs(storage_dir, exist_ok=True)
os.makedirs(os.path.join(storage_dir, 'videos'), exist_ok=True)
app.mount("/storage", StaticFiles(directory=storage_dir), name="storage")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "YouTube Dubbing Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    # Run with hot reload enabled for development
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,  # Enable hot reload
        reload_dirs=["./"]  # Watch all files in project directory
    )
