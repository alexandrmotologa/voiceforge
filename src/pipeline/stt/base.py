"""Abstract base class for Speech-to-Text (STT) providers."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional


class BaseSTT(ABC):
    """Abstract interface for Speech-to-Text engines."""

    @abstractmethod
    async def transcribe(self, pcm_bytes: bytes) -> str:
        """Transcribe a complete buffer of 16-bit 16kHz mono linear PCM audio.

        Args:
            pcm_bytes: Raw 16-bit signed PCM audio bytes.

        Returns:
            The transcribed text string.
        """
        pass

    async def transcribe_stream(self, pcm_generator: AsyncIterator[bytes]) -> AsyncIterator[str]:
        """Transcribe an asynchronous stream of PCM audio chunks in real-time.

        Default implementation accumulates chunks and calls transcribe().
        Streaming providers (e.g. Deepgram) override this with live WebSockets.
        """
        accumulated = bytearray()
        async for chunk in pcm_generator:
            accumulated.extend(chunk)

        result = await self.transcribe(bytes(accumulated))
        if result:
            yield result
