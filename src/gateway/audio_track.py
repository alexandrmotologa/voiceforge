"""Audio track implementations for WebRTC Opus streaming and PCM transcoding."""

import asyncio
import logging
import time
from typing import Optional, Callable
import av
import numpy as np
from aiortc import MediaStreamTrack

logger = logging.getLogger(__name__)


class InboundAudioProcessor:
    """Consumes audio frames from a remote WebRTC track and transcodes to 16kHz PCM."""

    TARGET_SAMPLE_RATE = 16000

    def __init__(
        self,
        track: MediaStreamTrack,
        on_pcm_chunk: Optional[Callable[[bytes], None]] = None
    ):
        self.track = track
        self.on_pcm_chunk = on_pcm_chunk
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self) -> None:
        """Start background frame consumer."""
        self._running = True
        self._task = asyncio.create_task(self._run())

    def stop(self) -> None:
        """Stop frame consumer."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()

    async def _run(self) -> None:
        """Continuously pull audio frames, resample to 16kHz mono, and dispatch PCM bytes."""
        try:
            while self._running:
                frame = await self.track.recv()
                # Transcode PyAV AudioFrame to 16kHz mono linear PCM
                pcm_bytes = self._transcode_frame_to_pcm16(frame)
                if pcm_bytes and self.on_pcm_chunk:
                    self.on_pcm_chunk(pcm_bytes)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Inbound track reader ended: %s", e)

    def _transcode_frame_to_pcm16(self, frame: av.AudioFrame) -> bytes:
        """Convert av.AudioFrame (typically 48kHz stereo/mono) to 16kHz mono 16-bit PCM bytes."""
        # Extract raw numpy ndarray from audio frame
        raw_array = frame.to_ndarray()

        # Handle stereo -> mono
        if len(raw_array.shape) > 1 and raw_array.shape[0] > 1:
            raw_array = np.mean(raw_array, axis=0).astype(raw_array.dtype)
        elif len(raw_array.shape) > 1:
            raw_array = raw_array[0]

        # Resample to 16kHz if frame sample rate differs
        if frame.sample_rate != self.TARGET_SAMPLE_RATE:
            # Simple downsampling / interpolation
            num_target_samples = int(len(raw_array) * self.TARGET_SAMPLE_RATE / frame.sample_rate)
            indices = np.linspace(0, len(raw_array) - 1, num_target_samples)
            raw_array = np.interp(indices, np.arange(len(raw_array)), raw_array).astype(np.int16)
        else:
            raw_array = raw_array.astype(np.int16)

        return raw_array.tobytes()


class OutboundAudioTrack(MediaStreamTrack):
    """Custom WebRTC audio track that streams paced 20ms Opus frames to the client."""

    kind = "audio"
    SAMPLE_RATE = 48000
    CHANNELS = 1
    FRAME_DURATION_SEC = 0.02  # 20ms
    SAMPLES_PER_FRAME = int(SAMPLE_RATE * FRAME_DURATION_SEC)  # 960 samples

    def __init__(self):
        super().__init__()
        self._queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._pcm_buffer = bytearray()
        self._pts: int = 0
        self._time_base = 1 / self.SAMPLE_RATE
        self._last_frame_time: float = time.perf_counter()
        self._is_active = True

    def put_audio(self, pcm_bytes: bytes, source_sample_rate: int = 16000) -> None:
        """Queue raw 16-bit linear PCM audio for transmission to client ear."""
        if not self._is_active or not pcm_bytes:
            return

        # Upsample from source sample rate to 48kHz if required
        if source_sample_rate != self.SAMPLE_RATE:
            src_samples = np.frombuffer(pcm_bytes, dtype=np.int16)
            target_length = int(len(src_samples) * (self.SAMPLE_RATE / source_sample_rate))
            indices = np.linspace(0, len(src_samples) - 1, target_length)
            upsampled = np.interp(indices, np.arange(len(src_samples)), src_samples).astype(np.int16)
            self._pcm_buffer.extend(upsampled.tobytes())
        else:
            self._pcm_buffer.extend(pcm_bytes)

    def clear_buffer(self) -> int:
        """Instantly clear all queued outbound audio. Used for sub-80ms barge-in."""
        discarded_bytes = len(self._pcm_buffer)
        self._pcm_buffer.clear()
        # Also drain any pending queue items
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except (asyncio.QueueEmpty, ValueError):
                break
        logger.debug("Outbound audio buffer cleared (%d bytes discarded)", discarded_bytes)
        return discarded_bytes

    def has_pending_audio(self) -> bool:
        """Return True if there is currently queued audio waiting to be delivered."""
        return len(self._pcm_buffer) >= (self.SAMPLES_PER_FRAME * 2)

    async def recv(self) -> av.AudioFrame:
        """Paced audio frame generator called by aiortc WebRTC engine at 50fps."""
        # Calculate time pacing to prevent queue starvation or drift
        now = time.perf_counter()
        elapsed = now - self._last_frame_time
        sleep_time = self.FRAME_DURATION_SEC - elapsed
        if sleep_time > 0:
            await asyncio.sleep(sleep_time)
        self._last_frame_time = time.perf_counter()

        bytes_needed = self.SAMPLES_PER_FRAME * 2  # 2 bytes per sample for 16-bit PCM

        if len(self._pcm_buffer) >= bytes_needed:
            chunk = bytes(self._pcm_buffer[:bytes_needed])
            del self._pcm_buffer[:bytes_needed]
            samples = np.frombuffer(chunk, dtype=np.int16)
        else:
            # Generate silence frame (960 zeroes) to keep WebRTC RTP connection alive
            samples = np.zeros(self.SAMPLES_PER_FRAME, dtype=np.int16)

        # Wrap in PyAV AudioFrame
        samples_2d = np.expand_dims(samples, axis=0)  # Shape: (1, 960)
        frame = av.AudioFrame.from_ndarray(samples_2d, format="s16", layout="mono")
        frame.sample_rate = self.SAMPLE_RATE
        frame.pts = self._pts
        self._pts += self.SAMPLES_PER_FRAME

        return frame
