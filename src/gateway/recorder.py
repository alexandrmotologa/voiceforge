"""Dual-channel stereo audio recorder for voice session archiving and replay."""

import io
import time
import wave
import logging
from typing import List, Tuple
import numpy as np

logger = logging.getLogger(__name__)


class AudioCallRecorder:
    """Records synchronized dual-channel audio (Left: User Mic, Right: Assistant Voice)."""

    SAMPLE_RATE = 16000
    CHANNELS = 2
    BYTES_PER_SAMPLE = 2

    def __init__(self):
        self._start_time = time.time()
        self._inbound_chunks: List[bytes] = []
        self._outbound_chunks: List[bytes] = []

    def record_inbound(self, pcm_bytes: bytes) -> None:
        """Record raw 16kHz 16-bit mono PCM from user microphone."""
        if pcm_bytes:
            self._inbound_chunks.append(pcm_bytes)

    def record_outbound(self, pcm_bytes: bytes) -> None:
        """Record raw 16kHz 16-bit mono PCM from assistant voice."""
        if pcm_bytes:
            self._outbound_chunks.append(pcm_bytes)

    def export_stereo_wav(self) -> bytes:
        """Combine inbound and outbound tracks into a standard 16kHz 16-bit stereo WAV."""
        inbound_bytes = b"".join(self._inbound_chunks)
        outbound_bytes = b"".join(self._outbound_chunks)

        inbound_samples = np.frombuffer(inbound_bytes, dtype=np.int16) if inbound_bytes else np.zeros(0, dtype=np.int16)
        outbound_samples = np.frombuffer(outbound_bytes, dtype=np.int16) if outbound_bytes else np.zeros(0, dtype=np.int16)

        max_len = max(len(inbound_samples), len(outbound_samples))
        if max_len == 0:
            # Generate a 1-second silence frame if empty
            max_len = self.SAMPLE_RATE

        # Pad shorter stream with silence to align both tracks
        left = np.pad(inbound_samples, (0, max(0, max_len - len(inbound_samples))), mode="constant")
        right = np.pad(outbound_samples, (0, max(0, max_len - len(outbound_samples))), mode="constant")

        # Interleave into stereo array [L0, R0, L1, R1, ...]
        stereo = np.empty((max_len * 2,), dtype=np.int16)
        stereo[0::2] = left
        stereo[1::2] = right

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.BYTES_PER_SAMPLE)
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(stereo.tobytes())

        return buf.getvalue()
