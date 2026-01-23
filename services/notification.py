
"""Notification service for real-time updates via SSE."""
import asyncio
import json
from typing import AsyncGenerator, Dict, List, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    """
    Manages Server-Sent Events (SSE) connections and broadcasts messages.
    """
    def __init__(self):
        # Maps user_id to a list of active queues
        self.active_connections: Dict[str, List[asyncio.Queue]] = defaultdict(list)
    
    async def connect(self, user_id: str) -> AsyncGenerator[str, None]:
        """
        Create a new connection for a user.
        Yields JSON-formatted strings for SSE.
        """
        queue = asyncio.Queue()
        self.active_connections[user_id].append(queue)
        
        try:
            # Send initial connection message
            yield json.dumps({"type": "connected", "message": "Connected to real-time updates"})
            
            while True:
                # Wait for messages
                message = await queue.get()
                yield message
        except asyncio.CancelledError:
            # Cleanup on disconnect
            self.disconnect(user_id, queue)
            raise
        finally:
            self.disconnect(user_id, queue)
    
    def disconnect(self, user_id: str, queue: asyncio.Queue):
        """Remove a connection."""
        if user_id in self.active_connections:
            if queue in self.active_connections[user_id]:
                self.active_connections[user_id].remove(queue)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
    
    async def broadcast_job_update(self, user_id: str, job_id: str, status: str, data: Optional[dict] = None):
        """
        Broadcast a job update to all connected clients for a user.
        """
        if user_id not in self.active_connections:
            return
            
        message = {
            "type": "job_update",
            "job_id": job_id,
            "status": status,
            "timestamp": data.get('updated_at') if data else None,
            "data": data or {}
        }
        
        json_msg = json.dumps(message, default=str)
        
        # Send to all user's active connections
        for queue in self.active_connections[user_id]:
            await queue.put(json_msg)
            
    async def broadcast_system_message(self, user_id: str, message: str, level: str = "info"):
        """Broadcast a system notification."""
        if user_id not in self.active_connections:
            return
            
        payload = {
            "type": "notification",
            "level": level,
            "message": message
        }
        
        json_msg = json.dumps(payload)
        
        for queue in self.active_connections[user_id]:
            await queue.put(json_msg)


# Global notification service
notification_service = NotificationService()
