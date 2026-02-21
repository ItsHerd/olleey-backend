"""Main FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import asyncio
import os

from config import settings
from routers import auth, videos, localization, webhooks, channels, jobs, youtube_connect, dashboard, settings as settings_router, events, projects, costs, agent
from services.subscription_renewal import renewal_scheduler_loop, stop_scheduler_task


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    renewal_task = None

    # Initialize local storage directory
    storage_dir = getattr(settings, 'local_storage_dir', './storage')
    os.makedirs(storage_dir, exist_ok=True)
    os.makedirs(os.path.join(storage_dir, 'videos'), exist_ok=True)
    
    # Validate demo configuration
    from config import validate_demo_config
    validate_demo_config()

    # Optional background scheduler for subscription lease renewal.
    if settings.enable_subscription_renewal_scheduler:
        renewal_task = asyncio.create_task(
            renewal_scheduler_loop(
                interval_minutes=settings.subscription_renewal_interval_minutes,
                renew_before_hours=settings.subscription_renew_before_hours,
            )
        )
        print(
            "[SUB_RENEWAL] scheduler started "
            f"(interval={settings.subscription_renewal_interval_minutes}m, "
            f"renew_before={settings.subscription_renew_before_hours}h)"
        )
    
    yield

    await stop_scheduler_task(renewal_task)


app = FastAPI(
    title="YouTube Dubbing Platform API",
    description="Backend service for managing YouTube content for dubbing/localization",
    version="1.0.0",
    lifespan=lifespan
)

# Trust proxy headers for Render deployment
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

@app.middleware("http")
async def force_https_middleware(request, call_next):
    """Force https scheme for production requests behind a proxy."""
    if settings.environment.lower() == "production" or request.headers.get("x-forwarded-proto") == "https":
        request.scope["scheme"] = "https"
    return await call_next(request)

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
app.include_router(settings_router.router)
app.include_router(events.router)
app.include_router(costs.router)
app.include_router(agent.router)

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
