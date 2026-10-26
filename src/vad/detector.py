"""Sliding window frame buffer, adaptive noise gate, and speech state detector."""

import time
import logging
from collections import deque
from typing import Callable, Optional, Deque
import numpy as np
from .silero import SileroVAD

logger = logging.getLogger(__name__)


class VADDetector:
    """Buffers raw audio streams, tracks ambient noise floor, and emits state transitions."""

    SAMPLE_RATE = 16000
    BYTES_PER_SAMPLE = 2  # 16-bit PCM
    CHUNK_SAMPLES = 512
    CHUNK_BYTES = CHUNK_SAMPLES * BYTES_PER_SAMPLE  # 1024 bytes per 32ms frame

    def __init__(
        self,
        vad: SileroVAD,
        threshold: float = 0.5,
        speech_pad_frames: int = 2,
        silence_timeout_ms: int = 150,
        enable_noise_gate: bool = True,
        enable_echo_guard: bool = True,
        on_speech_start: Optional[Callable[[], None]] = None,
        on_speech_chunk: Optional[Callable[[bytes], None]] = None,
        on_speech_end: Optional[Callable[[bytes], None]] = None,
        on_barge_in: Optional[Callable[[float], None]] = None,
    ):
        self.vad = vad
        self.threshold = threshold
        self.speech_pad_frames = speech_pad_frames
        self.silence_timeout_frames = max(1, int((silence_timeout_ms / 1000.0) * (self.SAMPLE_RATE / self.CHUNK_SAMPLES)))
        self.enable_noise_gate = enable_noise_gate
        self.enable_echo_guard = enable_echo_guard

        self.on_speech_start = on_speech_start
        self.on_speech_chunk = on_speech_chunk
        self.on_speech_end = on_speech_end
        self.on_barge_in = on_barge_in

        # Internal state
        self._raw_buffer = bytearray()
        self._is_speaking = False
        self._agent_speaking = False
        self._consecutive_speech_frames = 0
        self._consecutive_silence_frames = 0
        self._speech_bytes_buffer = bytearray()

        # Adaptive noise floor tracking
        self.noise_floor_rms: float = 80.0
        self.current_chunk_rms: float = 0.0
        self._rms_history: Deque[float] = deque(maxlen=60)  # ~2 seconds history

        # Pre-speech ring buffer (to preserve onset phonemes)
        self._pre_speech_buffer: Deque[bytes] = deque(maxlen=self.speech_pad_frames + 2)

    def set_agent_speaking(self, speaking: bool) -> None:
        """Inform the detector whether the assistant is currently speaking audio."""
        self._agent_speaking = speaking

    def reset(self) -> None:
        """Reset internal buffers, states, and the VAD neural network."""
        self._raw_buffer.clear()
        self._speech_bytes_buffer.clear()
        self._pre_speech_buffer.clear()
        self._rms_history.clear()
        self._is_speaking = False
        self._consecutive_speech_frames = 0
        self._consecutive_silence_frames = 0
        self.noise_floor_rms = 80.0
        self.vad.reset()

    def process_pcm_bytes(self, pcm_bytes: bytes) -> Optional[float]:
        """Accept arbitrary byte chunks of 16kHz 16-bit linear PCM and process all full 512-sample frames.

        Returns:
            The most recent speech probability, or None if no full frame was processed.
        """
        self._raw_buffer.extend(pcm_bytes)
        latest_prob = None

        while len(self._raw_buffer) >= self.CHUNK_BYTES:
            frame_bytes = bytes(self._raw_buffer[:self.CHUNK_BYTES])
            del self._raw_buffer[:self.CHUNK_BYTES]

            # 1. Calculate chunk energy and update adaptive noise floor
            samples = np.frombuffer(frame_bytes, dtype=np.int16).astype(np.float32)
            chunk_rms = float(np.sqrt(np.mean(samples ** 2)))
            self.current_chunk_rms = chunk_rms

            if not self._is_speaking and not self._agent_speaking:
                self._rms_history.append(chunk_rms)
                if len(self._rms_history) >= 10:
                    # Rolling 15th percentile as noise floor estimate
                    self.noise_floor_rms = float(np.percentile(list(self._rms_history), 15))

            # 2. Check noise gate: if energy is lower than ambient noise floor, attenuate probability
            prob = self.vad.process_chunk(frame_bytes)

            if self.enable_noise_gate and chunk_rms < (self.noise_floor_rms * 1.4 + 40.0):
                # Suppress background hum/fan noise
                prob = prob * 0.4

            latest_prob = prob
            self._handle_frame(frame_bytes, prob, chunk_rms)

        return latest_prob

    def _handle_frame(self, frame_bytes: bytes, prob: float, chunk_rms: float) -> None:
        """Evaluate a single 32ms frame against threshold and hysteresis counters."""
        # Acoustic Self-Echo Guard: When agent is speaking over room speakers,
        # elevate the required threshold and frame count to prevent false self-interruption
        effective_threshold = self.threshold
        required_speech_frames = self.speech_pad_frames

        if self._agent_speaking and self.enable_echo_guard:
            # Require higher certainty and an extra frame when audio is radiating from speakers
            effective_threshold = min(0.85, self.threshold * 1.35)
            required_speech_frames = self.speech_pad_frames + 1

        is_speech = prob >= effective_threshold

        if is_speech:
            self._consecutive_speech_frames += 1
            self._consecutive_silence_frames = 0
        else:
            self._consecutive_silence_frames += 1
            self._consecutive_speech_frames = 0

        # Check for barge-in trigger (user speaks while agent is active)
        if self._agent_speaking and is_speech and self._consecutive_speech_frames >= required_speech_frames:
            logger.info(
                "Barge-in triggered: user speech detected during playback (prob=%.2f, rms=%.1f, threshold=%.2f)",
                prob, chunk_rms, effective_threshold
            )
            if self.on_barge_in:
                self.on_barge_in(prob)
            self._agent_speaking = False

        if not self._is_speaking:
            self._pre_speech_buffer.append(frame_bytes)
            # Confirm user speech onset
            if self._consecutive_speech_frames >= self.speech_pad_frames:
                self._is_speaking = True
                self._speech_bytes_buffer.clear()

                # Flush pre-speech padding to capture beginning of word
                for pad_frame in self._pre_speech_buffer:
                    self._speech_bytes_buffer.extend(pad_frame)
                    if self.on_speech_chunk:
                        self.on_speech_chunk(pad_frame)
                self._pre_speech_buffer.clear()

                if self.on_speech_start:
                    self.on_speech_start()
        else:
            # User is actively speaking
            self._speech_bytes_buffer.extend(frame_bytes)
            if self.on_speech_chunk:
                self.on_speech_chunk(frame_bytes)

            # Confirm user finished speaking
            if self._consecutive_silence_frames >= self.silence_timeout_frames:
                self._is_speaking = False
                completed_speech = bytes(self._speech_bytes_buffer)
                self._speech_bytes_buffer.clear()
                self._consecutive_speech_frames = 0
                self._consecutive_silence_frames = 0

                if self.on_speech_end:
                    self.on_speech_end(completed_speech)
