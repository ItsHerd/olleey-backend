from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
import google.generativeai as genai
from config import settings
from middleware.auth import get_current_user
from services.supabase_db import supabase_service
import json

router = APIRouter(
    prefix="/agent",
    tags=["agent"]
)

# Configure Gemini
if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    prompt: str
    history: Optional[List[Message]] = []

@router.post("/chat")
async def chat_endpoint(req: ChatRequest, current_user = Depends(get_current_user)):
    user_id = current_user.get('user_id')
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    if not settings.gemini_api_key:
        raise HTTPException(status_code=500, detail="Gemini API Key not configured.")

    # Define tools
    def get_active_jobs() -> str:
        """Returns a list of the user's current processing or queued localization jobs."""
        try:
            response = supabase_service.client.table('processing_jobs').select('*').eq('user_id', user_id).execute()
            jobs = response.data or []
            active = [j for j in jobs if j.get('status') in ['pending', 'downloading', 'processing', 'uploading', 'queued']]
            return json.dumps([{"job_id": j['job_id'], "status": j['status'], "target_languages": j['target_languages']} for j in active])
        except Exception as e:
            return f"Error fetching active jobs: {str(e)}"

    def get_job_status(job_id: str) -> str:
        """Gets detailed status for a specific job ID including progress and current stage."""
        try:
            response = supabase_service.client.table('processing_jobs').select('*').eq('user_id', user_id).eq('job_id', job_id).execute()
            if not response.data:
                return f"Job {job_id} not found."
            j = response.data[0]
            return json.dumps({
                "job_id": j.get('job_id'),
                "status": j.get('status'),
                "progress": j.get('progress'),
                "current_stage": j.get('current_stage'),
                "target_languages": j.get('target_languages')
            })
        except Exception as e:
            return f"Error fetching job status: {str(e)}"

    def list_videos() -> str:
        """Returns the user's connected YouTube videos available for dubbing."""
        try:
            response = supabase_service.client.table('videos').select('video_id, title, status, duration').eq('user_id', user_id).execute()
            return json.dumps(response.data or [])
        except Exception as e:
            return f"Error listing videos: {str(e)}"

    def list_channels() -> str:
        """Returns all language channels configured by the user."""
        try:
            channels = supabase_service.get_youtube_connections(user_id)
            return json.dumps([{"channel_name": c.get("youtube_channel_name"), "language_code": c.get("language_code")} for c in channels])
        except Exception as e:
            return f"Error listing channels: {str(e)}"

    def get_pending_reviews() -> str:
        """Returns a list of videos/jobs that are waiting for manual user review or approval."""
        try:
            response = supabase_service.client.table('processing_jobs').select('*').eq('user_id', user_id).eq('status', 'waiting_approval').execute()
            jobs = response.data or []
            return json.dumps([{"job_id": j['job_id'], "source_video_id": j['source_video_id'], "target_languages": j['target_languages']} for j in jobs])
        except Exception as e:
            return f"Error fetching pending reviews: {str(e)}"

    tools = [get_active_jobs, get_job_status, list_videos, list_channels, get_pending_reviews]
    
    # Format history for Gemini
    formatted_history = []
    for msg in (req.history or []):
        role = 'model' if msg.role == 'assistant' else 'user'
        formatted_history.append({'role': role, 'parts': [msg.content]})

    system_instruction = (
        "You are Olleey, a helpful and concise localization assistant. "
        "You help users translate their videos, check dubbing status, view pending reviews, and manage language channels using the provided tools. "
        "Refuse any generic requests like writing poems or code. Only use the tools provided to answer questions about the user's data. "
        "Do not invent data; always rely on the tool outputs. Keep your answers brief and directly address the user's needs."
    )

    model = genai.GenerativeModel(
        model_name='gemini-2.5-flash',
        tools=tools,
        system_instruction=system_instruction
    )
    
    chat = model.start_chat(history=formatted_history, enable_automatic_function_calling=True)
    
    try:
        response = chat.send_message(req.prompt)
        return {"response": response.text}
    except Exception as e:
        return {"response": f"I encountered an error processing your request: {str(e)}"}
