"""ElevenLabs streaming text-to-speech client."""

import logging
from typing import Optional
import httpx
from .base import BaseTTS
from .native_pcm import NativePCMTTS
from ...config import settings

logger = logging.getLogger(__name__)


class ElevenLabsTTS(BaseTTS):
    """ElevenLabs Turbo v2.5 streaming text-to-speech client."""

    API_URL = "https://api.elevenlabs.io/v1/text-to-speech"

    def __init__(self, api_key: Optional[str] = None, voice_id: str = "21m00Tcm4TlvDq8ikWAM"):
        self.api_key = api_key or settings.elevenlabs_api_key
        self.voice_id = voice_id
        self._fallback = NativePCMTTS()

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text via ElevenLabs API."""
        if not self.api_key:
            logger.info("ElevenLabs API key not provided, using native local TTS")
            return await self._fallback.synthesize(text)

        url = f"{self.API_URL}/{self.voice_id}?output_format=pcm_16000"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        payload = {
            "text": text,
            "model_id": "eleven_turbo_v2_5",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                pcm_bytes = response.content
                if pcm_bytes:
                    return pcm_bytes
        except Exception as e:
            logger.error("ElevenLabs synthesis failed: %s, using fallback", e)
            return await self._fallback.synthesize(text)

        return b""
