"""Abstract base class for Text-to-Speech (TTS) synthesis engines."""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseTTS(ABC):
    """Abstract interface for streaming Text-to-Speech synthesis."""

    SAMPLE_RATE = 16000

    @abstractmethod
    async def synthesize(self, text: str, speech_rate: float = 1.0) -> bytes:
        """Synthesize a complete sentence into 16-bit 16kHz mono linear PCM bytes.

        Args:
            text: Sentence or phrase to synthesize.
            speech_rate: Speaking speed multiplier between 0.75 and 1.5 (default: 1.0).
        """
        pass

    async def synthesize_stream(
        self,
        text_stream: AsyncIterator[str],
        speech_rate: float = 1.0
    ) -> AsyncIterator[bytes]:
        """Synthesize a stream of text chunks/sentences into raw audio PCM bytes."""
        async for sentence in text_stream:
            clean_text = sentence.strip()
            if clean_text:
                audio_bytes = await self.synthesize(clean_text, speech_rate=speech_rate)
                if audio_bytes:
                    yield audio_bytes
