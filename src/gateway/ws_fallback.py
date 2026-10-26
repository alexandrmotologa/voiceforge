"""WebSocket streaming fallback for networks where WebRTC UDP is blocked."""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, Callable
from fastapi import WebSocket, WebSocketDisconnect
from .session import VoiceSession

logger = logging.getLogger(__name__)


class WebSocketFallbackHandler:
    """Manages full-duplex binary audio and JSON signaling over a single WebSocket."""

    def __init__(self, on_turn_ready: Optional[Callable[[VoiceSession, bytes], Any]] = None):
        self.sessions: Dict[str, VoiceSession] = {}
        self.on_turn_ready = on_turn_ready

    async def handle_connection(self, websocket: WebSocket, session_id: str) -> None:
        """Handle incoming WebSocket connection for real-time audio and events."""
        await websocket.accept()

        session = VoiceSession(
            session_id=session_id,
            on_turn_ready=self.on_turn_ready
        )
        self.sessions[session_id] = session

        # Bind WebSocket sender to session
        async def send_json_message(msg: str):
            try:
                await websocket.send_text(msg)
            except Exception as e:
                logger.debug("WebSocket send error: %s", e)

        session.set_ws_sender(send_json_message)

        # Background task: stream outbound audio packets to client as binary frames
        stream_task = asyncio.create_task(self._stream_outbound_audio(websocket, session))

        try:
            while True:
                message = await websocket.receive()
                if "bytes" in message and message["bytes"]:
                    # Inbound binary audio PCM chunk from client microphone
                    pcm_chunk = message["bytes"]
                    session.feed_inbound_pcm(pcm_chunk)
                elif "text" in message and message["text"]:
                    # Inbound JSON control command
                    try:
                        data = json.loads(message["text"])
                        session._handle_client_command(data)
                    except Exception as e:
                        logger.error("Error handling ws text command: %s", e)
        except WebSocketDisconnect:
            logger.info("WebSocket client disconnected for session %s", session_id)
        except Exception as e:
            logger.error("WebSocket error in session %s: %s", session_id, e)
        finally:
            stream_task.cancel()
            session.close()
            self.sessions.pop(session_id, None)

    async def _stream_outbound_audio(self, websocket: WebSocket, session: VoiceSession) -> None:
        """Paced sender yielding outbound synthesized PCM audio chunks over binary frames."""
        try:
            frame_duration = 0.02  # 20ms
            bytes_per_frame = int(16000 * frame_duration * 2)  # 640 bytes at 16kHz

            while True:
                await asyncio.sleep(frame_duration)

                # Check if outbound track has audio buffered
                if len(session.outbound_track._pcm_buffer) >= bytes_per_frame:
                    chunk = bytes(session.outbound_track._pcm_buffer[:bytes_per_frame])
                    del session.outbound_track._pcm_buffer[:bytes_per_frame]
                    await websocket.send_bytes(chunk)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.debug("Outbound audio streaming ended: %s", e)
