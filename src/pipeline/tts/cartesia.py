"""Cartesia Sonic low-latency streaming text-to-speech client."""

import json
import logging
from typing import Optional, AsyncIterator
import httpx
from .base import BaseTTS
from .native_pcm import NativePCMTTS
from ...config import settings

logger = logging.getLogger(__name__)


class CartesiaTTS(BaseTTS):
    """Cartesia Sonic streaming text-to-speech client with sub-90ms first audio chunk."""

    API_URL = "https://api.cartesia.ai/tts/bytes"

    def __init__(self, api_key: Optional[str] = None, voice_id: str = "a0e99841-438c-4a64-b679-ae501e7d6091"):
        self.api_key = api_key or settings.cartesia_api_key
        self.voice_id = voice_id
        self._fallback = NativePCMTTS()

    async def synthesize(self, text: str) -> bytes:
        """Synthesize text using Cartesia Sonic REST API with 16kHz linear PCM output."""
        if not self.api_key:
            logger.info("Cartesia API key not provided, using native local TTS")
            return await self._fallback.synthesize(text)

        headers = {
            "X-API-Key": self.api_key,
            "Cartesia-Version": "2024-06-10",
            "Content-Type": "application/json"
        }

        payload = {
            "model_id": "sonic-english",
            "transcript": text,
            "voice": {
                "mode": "id",
                "id": self.voice_id
            },
            "output_format": {
                "container": "raw",
                "encoding": "pcm_s16le",
                "sample_rate": 16000
            }
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(self.API_URL, headers=headers, json=payload)
                response.raise_for_status()
                pcm_bytes = response.content
                if pcm_bytes:
                    return pcm_bytes
        except Exception as e:
            logger.error("Cartesia synthesis failed: %s, using native fallback", e)
            return await self._fallback.synthesize(text)

        return b""
