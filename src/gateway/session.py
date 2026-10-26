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
from .recorder import AudioCallRecorder

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

        # Audio Call Recorder (Dual-channel stereo)
        self.recorder = AudioCallRecorder()

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
            on_notify_client=self._on_barge_in_notify
        )

        self.on_turn_ready = on_turn_ready

        self.detector = VADDetector(
            vad=self.vad,
            threshold=threshold,
            speech_pad_frames=settings.vad_speech_pad_frames,
            silence_timeout_ms=settings.vad_silence_timeout_ms,
            enable_noise_gate=True,
            enable_echo_guard=True,
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

        # Telemetry for active turn & historical analytics
        self.current_turn_metrics: Dict[str, Any] = {}
        self.turn_metrics_history: List[Dict[str, Any]] = []
        self.barge_in_history: List[Dict[str, Any]] = []
        self.tool_calls_history: List[Dict[str, Any]] = []

    def feed_inbound_pcm(self, pcm_bytes: bytes) -> Optional[float]:
        """Ingest incoming microphone audio, record to dual-track, and evaluate VAD."""
        self.recorder.record_inbound(pcm_bytes)
        return self.detector.process_pcm_bytes(pcm_bytes)

    def queue_outbound_pcm(self, pcm_bytes: bytes, source_sample_rate: int = 16000) -> None:
        """Enqueue synthesized voice to WebRTC track and record to dual-track."""
        self.recorder.record_outbound(pcm_bytes)
        self.outbound_track.put_audio(pcm_bytes, source_sample_rate=source_sample_rate)

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
        # Record history of events for reporting
        ev_type = payload.get("type")
        if ev_type == "metrics":
            self.turn_metrics_history.append(payload)
        elif ev_type == "tool_call":
            self.tool_calls_history.append(payload)

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
            if "speech_rate" in new_cfg:
                self.config["speech_rate"] = float(new_cfg["speech_rate"])

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

    def _on_barge_in_notify(self, payload: Dict[str, Any]) -> None:
        """Store barge-in event in history and notify client."""
        self.barge_in_history.append(payload)
        self.send_event(payload)

    def _on_barge_in_action(self) -> None:
        """Immediate action on barge-in: clear audio queue and trigger cancellation token."""
        self.state = SessionState.INTERRUPTED
        self.abort_event.set()
        discarded_bytes = self.outbound_track.clear_buffer()
        self.detector.set_agent_speaking(False)
        logger.info("Session %s interrupted: cleared %d bytes of audio buffer", self.session_id, discarded_bytes)

    def generate_report(self, format_type: str = "json") -> str:
        """Export session dialogue, latency analytics, and barge-in events as JSON or Markdown."""
        duration_sec = round(time.time() - self.created_at, 1)
        turnarounds = [m.get("total_turnaround_ms", 0) for m in self.turn_metrics_history]
        avg_turnaround = round(sum(turnarounds) / len(turnarounds), 1) if turnarounds else 0.0

        report_data = {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "duration_seconds": duration_sec,
            "total_turns": len(self.turn_metrics_history),
            "average_turnaround_ms": avg_turnaround,
            "total_barge_in_interruptions": len(self.barge_in_history),
            "barge_in_events": self.barge_in_history,
            "turn_metrics": self.turn_metrics_history,
            "tool_calls": self.tool_calls_history,
            "conversation_history": [
                m for m in self.conversation_history if m.get("role") != "system"
            ]
        }

        if format_type.lower() == "markdown":
            lines = [
                f"# VoiceForge Session Report: `{self.session_id}`",
                "",
                f"- **Duration**: {duration_sec} seconds",
                f"- **Total Turns**: {len(self.turn_metrics_history)}",
                f"- **Average Turnaround**: {avg_turnaround} ms",
                f"- **Barge-In Interruptions**: {len(self.barge_in_history)}",
                "",
                "## Conversational Transcript",
                ""
            ]
            for m in report_data["conversation_history"]:
                role = m.get("role", "unknown").capitalize()
                content = m.get("content", "")
                lines.append(f"**{role}**: {content}\n")

            if self.turn_metrics_history:
                lines.extend([
                    "## Latency Waterfall Summary",
                    "",
                    "| Turn | STT (ms) | LLM TTFT (ms) | Sentence Split (ms) | TTS Chunk (ms) | Turnaround (ms) |",
                    "| :--- | :--- | :--- | :--- | :--- | :--- |"
                ])
                for i, tm in enumerate(self.turn_metrics_history, 1):
                    lines.append(
                        f"| #{i} | {tm.get('stt_latency_ms', 0)} | {tm.get('llm_ttft_ms', 0)} | "
                        f"{tm.get('sentence_split_ms', 0)} | {tm.get('tts_first_chunk_ms', 0)} | "
                        f"**{tm.get('total_turnaround_ms', 0)}** |"
                    )

            if self.barge_in_history:
                lines.extend([
                    "",
                    "## Barge-In Interruption Log",
                    "",
                    "| Event | Cutoff Latency (ms) | Speech Probability |",
                    "| :--- | :--- | :--- |"
                ])
                for j, b in enumerate(self.barge_in_history, 1):
                    lines.append(f"| #{j} | {b.get('latency_ms', 0)} ms | {b.get('speech_prob', 0)} |")

            return "\n".join(lines)

        return json.dumps(report_data, indent=2)

    def close(self) -> None:
        """Clean up session resources."""
        self.abort_event.set()
        self.outbound_track.clear_buffer()
        self.detector.reset()
