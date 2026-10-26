"""Local Whisper speech-to-text engine using faster-whisper or local ONNX."""

import logging
from typing import Optional
import numpy as np
from .base import BaseSTT
from .fallback import FallbackSTT

logger = logging.getLogger(__name__)


class WhisperLocalSTT(BaseSTT):
    """Local offline speech recognition using faster-whisper or fallback."""

    def __init__(self, model_size: str = "base.en", device: str = "cpu"):
        self.model_size = model_size
        self.device = device
        self._model = None
        self._fallback = FallbackSTT()

        try:
            from faster_whisper import WhisperModel
            self._model = WhisperModel(model_size, device=device, compute_type="int8")
            logger.info("Loaded local faster-whisper model (%s on %s)", model_size, device)
        except ImportError:
            logger.info("faster-whisper not installed; WhisperLocalSTT will use acoustic fallback")
        except Exception as e:
            logger.warning("Could not initialize local WhisperModel: %s", e)

    async def transcribe(self, pcm_bytes: bytes) -> str:
        """Transcribe PCM audio buffer locally."""
        if self._model is None or not pcm_bytes:
            return await self._fallback.transcribe(pcm_bytes)

        try:
            samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.float32) / 32768.0
            segments, _ = self._model.transcribe(samples, beam_size=1)
            text = " ".join([segment.text.strip() for segment in segments])
            return text
        except Exception as e:
            logger.error("Local Whisper transcription failed: %s", e)
            return await self._fallback.transcribe(pcm_bytes)
