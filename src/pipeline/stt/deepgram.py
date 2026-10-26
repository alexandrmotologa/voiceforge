"""Deepgram Nova-2 streaming speech-to-text client."""

import logging
import httpx
from typing import Optional
from .base import BaseSTT
from .fallback import FallbackSTT
from ...config import settings

logger = logging.getLogger(__name__)


class DeepgramSTT(BaseSTT):
    """Deepgram Nova-2 speech recognition client with low-latency REST and streaming support."""

    API_URL = "https://api.deepgram.com/v1/listen"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.deepgram_api_key
        self._fallback = FallbackSTT()

    async def transcribe(self, pcm_bytes: bytes) -> str:
        """Send raw 16kHz linear PCM bytes to Deepgram Nova-2."""
        if not self.api_key:
            logger.info("Deepgram API key not provided, using fallback STT")
            return await self._fallback.transcribe(pcm_bytes)

        if not pcm_bytes:
            return ""

        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/raw;encoding=linear16;sample_rate=16000;channels=1"
        }
        params = {
            "model": "nova-2",
            "smart_format": "true",
            "punctuate": "true"
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.API_URL,
                    params=params,
                    headers=headers,
                    content=pcm_bytes
                )
                response.raise_for_status()
                data = response.json()

                # Extract top transcript
                channels = data.get("results", {}).get("channels", [])
                if channels and channels[0].get("alternatives"):
                    transcript = channels[0]["alternatives"][0].get("transcript", "").strip()
                    logger.info("Deepgram transcribed: '%s'", transcript)
                    return transcript
        except Exception as e:
            logger.error("Deepgram transcription failed: %s, using fallback", e)
            return await self._fallback.transcribe(pcm_bytes)

        return ""
