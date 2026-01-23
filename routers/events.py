
"""Real-time events router."""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from middleware.auth import get_current_user
from services.notification import notification_service
import asyncio

router = APIRouter(prefix="/events", tags=["events"])

@router.get("/stream")
async def event_stream(
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Server-Sent Events (SSE) endpoint for real-time updates.
    
    Processing jobs will push status updates here, removing the need for
    frontend polling.
    """
    user_id = current_user["user_id"]
    
    async def event_generator():
        try:
            async for message in notification_service.connect(user_id):
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                yield f"data: {message}\n\n"
        except asyncio.CancelledError:
            pass

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
