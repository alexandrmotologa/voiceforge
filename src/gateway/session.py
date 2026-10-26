"""Voice session lifecycle, state management, and cancellation tokens."""

import asyncio
import json
import logging
import time
import uuid
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
from aiortc import RTCDataChannel

from ..config import settings
from ..vad.silero import SileroVAD
from ..vad.detector import VADDetector
from ..vad.barge_in import BargeInController
from .audio_track import OutboundAudioTrack

logger = logging.getLogger(__name__)


class SessionState(str, Enum):
    IDLE = "idle"
    USER_SPEAKING = "user_speaking"
    AI_THINKING = "ai_thinking"
    AI_SPEAKING = "ai_speaking"
    INTERRUPTED = "interrupted"


class VoiceSession:
    """Manages the full lifecycle of an active WebRTC voice conversation."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        on_turn_ready: Optional[Callable[["VoiceSession", bytes], Any]] = None
    ):
        self.session_id = session_id or f"vf_sess_{uuid.uuid4().hex[:8]}"
        self.config = config or {}
        self.state = SessionState.IDLE
        self.abort_event = asyncio.Event()
        self.created_at = time.time()

        # Outbound audio track
        self.outbound_track = OutboundAudioTrack()

        # WebRTC Data channel
        self.data_channel: Optional[RTCDataChannel] = None
        self._ws_sender: Optional[Callable[[str], Any]] = None

        # VAD & Barge-in setup
        vad_model_path = self.config.get("vad_model_path", settings.vad_model_path)
        threshold = float(self.config.get("vad_threshold", settings.vad_threshold))
        self.vad = SileroVAD(vad_model_path)

        self.barge_in_controller = BargeInController(
            on_interrupt_action=self._on_barge_in_action,
            on_notify_client=self.send_event
        )

        self.on_turn_ready = on_turn_ready

        self.detector = VADDetector(
            vad=self.vad,
            threshold=threshold,
            speech_pad_frames=settings.vad_speech_pad_frames,
            silence_timeout_ms=settings.vad_silence_timeout_ms,
            on_speech_start=self._on_user_speech_start,
            on_speech_end=self._on_user_speech_end,
            on_barge_in=self._on_barge_in_detected
        )

        # Context & Dialogue memory
        self.conversation_history: List[Dict[str, str]] = []
        if settings.system_prompt:
            self.conversation_history.append({
                "role": "system",
                "content": self.config.get("system_prompt", settings.system_prompt)
            })

        # Telemetry for active turn
        self.current_turn_metrics: Dict[str, Any] = {}

    def set_data_channel(self, channel: RTCDataChannel) -> None:
        """Bind WebRTC data channel for bidirectional event messaging."""
        self.data_channel = channel

        @channel.on("message")
        def on_message(message):
            try:
                data = json.loads(message)
                logger.info("Received client data channel message: %s", data)
                self._handle_client_command(data)
            except Exception as e:
                logger.error("Failed to parse data channel message: %s", e)

    def set_ws_sender(self, sender: Callable[[str], Any]) -> None:
        """Bind WebSocket JSON sender for WebSocket fallback mode."""
        self._ws_sender = sender

    def send_event(self, payload: Dict[str, Any]) -> None:
        """Send JSON event message to client over WebRTC data channel or WebSocket."""
        msg = json.dumps(payload)
        if self.data_channel and self.data_channel.readyState == "open":
            try:
                self.data_channel.send(msg)
            except Exception as e:
                logger.debug("Failed to send via data channel: %s", e)
        elif self._ws_sender:
            try:
                if asyncio.iscoroutinefunction(self._ws_sender):
                    asyncio.create_task(self._ws_sender(msg))
                else:
                    self._ws_sender(msg)
            except Exception as e:
                logger.debug("Failed to send via ws sender: %s", e)

    def _handle_client_command(self, data: Dict[str, Any]) -> None:
        """Process incoming client instructions."""
        cmd = data.get("type")
        if cmd == "interrupt":
            self.barge_in_controller.trigger(speech_probability=1.0)
        elif cmd == "update_config":
            new_cfg = data.get("config", {})
            self.config.update(new_cfg)
            if "vad_threshold" in new_cfg:
                self.detector.threshold = float(new_cfg["vad_threshold"])

    def _on_user_speech_start(self) -> None:
        """Callback when user begins speaking."""
        self.state = SessionState.USER_SPEAKING
        self.send_event({
            "type": "state",
            "state": self.state.value,
            "timestamp": time.time()
        })

    def _on_user_speech_end(self, audio_bytes: bytes) -> None:
        """Callback when user finishes a complete speech phrase."""
        self.state = SessionState.AI_THINKING
        self.send_event({
            "type": "state",
            "state": self.state.value,
            "timestamp": time.time()
        })

        # Clear abort event for the new turn
        self.abort_event.clear()

        # Trigger turn execution in pipeline
        if self.on_turn_ready:
            asyncio.create_task(self._safe_execute_turn(audio_bytes))

    async def _safe_execute_turn(self, audio_bytes: bytes) -> None:
        """Safely invoke pipeline turn callback."""
        try:
            if self.on_turn_ready:
                res = self.on_turn_ready(self, audio_bytes)
                if asyncio.iscoroutine(res):
                    await res
        except Exception as e:
            logger.error("Error executing turn in session %s: %s", self.session_id, e, exc_info=True)

    def _on_barge_in_detected(self, prob: float) -> None:
        """Callback from VAD detector when user speech interrupts active assistant playback."""
        self.barge_in_controller.trigger(speech_probability=prob)

    def _on_barge_in_action(self) -> None:
        """Immediate action on barge-in: clear audio queue and trigger cancellation token."""
        self.state = SessionState.INTERRUPTED
        self.abort_event.set()
        discarded_bytes = self.outbound_track.clear_buffer()
        self.detector.set_agent_speaking(False)
        logger.info("Session %s interrupted: cleared %d bytes of audio buffer", self.session_id, discarded_bytes)

    def close(self) -> None:
        """Clean up session resources."""
        self.abort_event.set()
        self.outbound_track.clear_buffer()
        self.detector.reset()
