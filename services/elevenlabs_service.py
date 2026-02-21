import httpx
import asyncio
import os
import io
from typing import Optional, Dict, Any
from config import settings
from elevenlabs.client import ElevenLabs

class ElevenLabsService:
    def __init__(self):
        self.api_key = settings.elevenlabs_api_key
        if self.api_key:
            self.client = ElevenLabs(api_key=self.api_key)
        else:
            self.client = None

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
        if not self.client:
            raise ValueError("ElevenLabs API key is not configured")

        # Download the source URL first so we can pass it as a file object
        # As per the documentation, we need to pass a file-like object
        print(f"[ELEVENLABS] Downloading source file for dubbing: {source_url}")
        async with httpx.AsyncClient() as http_client:
            response = await http_client.get(source_url, timeout=120.0)
            if response.status_code != 200:
                raise Exception(f"Failed to download source file: {response.text}")
            
            file_data = io.BytesIO(response.content)
            
            # Determine extension based on URL or default to mp4
            ext = "mp4"
            if "." in source_url.split("/")[-1]:
                ext = source_url.split("/")[-1].split(".")[1].split("?")[0]
            
            file_data.name = f"source.{ext}"

        print(f"[ELEVENLABS] Creating dubbing task. Target: {target_lang}")
        
        # Use a thread pool to run the synchronous SDK call asynchronously
        loop = asyncio.get_event_loop()
        dubbed = await loop.run_in_executor(
            None,
            lambda: self.client.dubbing.create(
                file=file_data,
                target_lang=target_lang,
                source_lang=source_lang if source_lang != "auto" else None
            )
        )
        
        print(f"[ELEVENLABS] Dubbing task created. ID: {dubbed.dubbing_id}")
        return dubbed.dubbing_id

    async def get_dubbing_status(self, dubbing_id: str) -> str:
        """
        Check the status of a dubbing task.
        Returns: 'dubbing', 'dubbed', 'failed'
        """
        if not self.client:
            raise ValueError("ElevenLabs API key is not configured")
            
        loop = asyncio.get_event_loop()
        metadata = await loop.run_in_executor(
            None,
            lambda: self.client.dubbing.get(dubbing_id)
        )
        return metadata.status

    async def get_dubbing_metadata(self, dubbing_id: str) -> Dict[str, Any]:
        """
        Get full dubbing metadata including transcript, translations, and audio URLs.

        Args:
            dubbing_id: The dubbing project ID

        Returns:
            Dict containing:
                - status: Current status
                - source_language: Detected source language
                - target_language: Target language code
                - transcript: Original transcript text
                - translation: Translated text
                - dubbed_file_url: URL to dubbed audio file
                - metadata: Additional metadata from ElevenLabs
        """
        if not self.client:
            raise ValueError("ElevenLabs API key is not configured")

        loop = asyncio.get_event_loop()
        metadata = await loop.run_in_executor(
            None,
            lambda: self.client.dubbing.get(dubbing_id)
        )

        return {
            'status': metadata.status,
            'dubbing_id': dubbing_id,
            'target_language': metadata.target_lang,
            'dubbed_file_url': None, # SDK doesn't return this directly anymore, we download it instead.
            'metadata': metadata.dict() if hasattr(metadata, 'dict') else {},
            # Since the API doesn't return character cost here anymore in the SDK, we set it to 0. 
            # We would need to either use with_raw_response() or track it another way.
            'character_cost': 0
        }

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
        if not self.client:
            raise ValueError("ElevenLabs API key is not configured")
            
        print(f"[ELEVENLABS] Downloading dubbed audio for {dubbing_id} to {output_path}")
        
        loop = asyncio.get_event_loop()
        # SDK returns a generator of bytes
        audio_stream = await loop.run_in_executor(
            None,
            lambda: self.client.dubbing.get_audio(dubbing_id, language_code)
        )
        
        with open(output_path, "wb") as f:
            for chunk in audio_stream:
                if chunk:
                    f.write(chunk)
                    
        return output_path
    
    async def delete_dubbing_project(self, dubbing_id: str):
        """Clean up the project from ElevenLabs dashboard"""
        if not self.client:
            raise ValueError("ElevenLabs API key is not configured")
            
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self.client.dubbing.delete(dubbing_id)
        )

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

    async def mock_get_dubbing_metadata(self, dubbing_id: str) -> Dict[str, Any]:
        print(f"[MOCK] ElevenLabs get_dubbing_metadata called for {dubbing_id}")
        # Extract target language from dubbing_id (format: mock_dubbing_id_{lang})
        target_lang = dubbing_id.split('_')[-1] if '_' in dubbing_id else 'es'
        return {
            'status': 'dubbed',
            'dubbing_id': dubbing_id,
            'source_language': 'en',
            'target_language': target_lang,
            'transcript': 'This is a mock transcript of the source video content.',
            'translation': f'This is a mock translation in {target_lang}.',
            'dubbed_file_url': f'https://mock.elevenlabs.io/audio/{dubbing_id}.mp3',
            'metadata': {'mock': True}
        }

    ElevenLabsService.create_dubbing_task = mock_create_dubbing_task
    ElevenLabsService.get_dubbing_status = mock_get_dubbing_status
    ElevenLabsService.wait_for_completion = mock_wait_for_completion
    ElevenLabsService.download_dubbed_audio = mock_download_dubbed_audio
    ElevenLabsService.delete_dubbing_project = mock_delete_dubbing_project
    ElevenLabsService.get_dubbing_metadata = mock_get_dubbing_metadata
