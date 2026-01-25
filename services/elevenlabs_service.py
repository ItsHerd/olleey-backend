import httpx
import asyncio
import os
from typing import Optional, Dict, Any
from config import settings

class ElevenLabsService:
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        self.base_url = settings.elevenlabs_base_url
        self.headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    async def create_dubbing_task(self, source_url: str, target_lang: str, source_lang: str = "auto") -> str:
        """
        Create a dubbing task from a URL.
        
        Args:
            source_url: Public URL of the video/audio
            target_lang: ISO 639-1 language code (e.g. 'es', 'de')
            source_lang: Source language code or 'auto'
            
        Returns:
            dubbing_id: The ID of the created dubbing project
        """
        if not self.api_key:
            raise ValueError("ElevenLabs API key is not configured")

        url = f"{self.base_url}/dubbing"
        
        payload = {
            "mode": "automatic",
            "source_url": source_url,
            "source_lang": source_lang,
            "target_lang": target_lang,
            "num_speakers": 0,
            "watermark": False
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, headers=self.headers, timeout=30.0)
            
            if response.status_code not in (200, 201):
                raise Exception(f"Failed to create dubbing task: {response.text}")
                
            data = response.json()
            return data["dubbing_id"]

    async def get_dubbing_status(self, dubbing_id: str) -> str:
        """
        Check the status of a dubbing task.
        Returns: 'dubbing', 'dubbed', 'failed'
        """
        url = f"{self.base_url}/dubbing/{dubbing_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=self.headers, timeout=10.0)
            
            if response.status_code != 200:
                raise Exception(f"Failed to get dubbing status: {response.text}")
                
            data = response.json()
            return data["status"]

    async def wait_for_completion(self, dubbing_id: str, check_interval: int = 10, timeout: int = 1200) -> bool:
        """
        Wait for a dubbing task to complete.
        """
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            status = await self.get_dubbing_status(dubbing_id)
            
            if status == "dubbed":
                return True
            elif status == "failed":
                raise Exception("Dubbing task failed")
                
            await asyncio.sleep(check_interval)
            
        raise TimeoutError("Dubbing task timed out")

    async def download_dubbed_audio(self, dubbing_id: str, language_code: str, output_path: str) -> str:
        """
        Download the dubbed audio for a specific language.
        """
        url = f"{self.base_url}/dubbing/{dubbing_id}/audio/{language_code}"
        
        async with httpx.AsyncClient() as client:
            # Increase timeout for file download
            response = await client.get(url, headers=self.headers, timeout=60.0)
            
            if response.status_code != 200:
                raise Exception(f"Failed to download audio: {response.text}")
                
            with open(output_path, "wb") as f:
                for chunk in response.iter_bytes():
                    f.write(chunk)
                    
        return output_path
    
    async def delete_dubbing_project(self, dubbing_id: str):
        """Clean up the project from ElevenLabs dashboard"""
        url = f"{self.base_url}/dubbing/{dubbing_id}"
        async with httpx.AsyncClient() as client:
            await client.delete(url, headers=self.headers)

# Singleton instance
elevenlabs_service = ElevenLabsService()

# Monkey patch for testing/mocking if needed
if settings.environment == "test" or settings.use_mock_db:
    async def mock_create_dubbing_task(self, source_url: str, target_lang: str, source_lang: str = "auto") -> str:
        print("[MOCK] ElevenLabs create_dubbing_task called")
        return f"mock_dubbing_id_{target_lang}"

    async def mock_get_dubbing_status(self, dubbing_id: str) -> str:
        print(f"[MOCK] ElevenLabs get_dubbing_status called for {dubbing_id}")
        return "dubbed"
        
    async def mock_wait_for_completion(self, dubbing_id: str, check_interval: int = 10, timeout: int = 1200) -> bool:
        print(f"[MOCK] ElevenLabs wait_for_completion called for {dubbing_id}")
        return True

    async def mock_download_dubbed_audio(self, dubbing_id: str, language_code: str, output_path: str) -> str:
        print(f"[MOCK] ElevenLabs download_dubbed_audio called for {dubbing_id}")
        # Create a dummy audio file
        with open(output_path, "wb") as f:
            f.write(b"mock_audio_content")
        return output_path
        
    async def mock_delete_dubbing_project(self, dubbing_id: str):
        print(f"[MOCK] ElevenLabs delete_dubbing_project called for {dubbing_id}")
        pass

    ElevenLabsService.create_dubbing_task = mock_create_dubbing_task
    ElevenLabsService.get_dubbing_status = mock_get_dubbing_status
    ElevenLabsService.wait_for_completion = mock_wait_for_completion
    ElevenLabsService.download_dubbed_audio = mock_download_dubbed_audio
    ElevenLabsService.delete_dubbing_project = mock_delete_dubbing_project
