"""WebRTC PeerConnection and signaling coordinator using aiortc."""

import asyncio
import logging
from typing import Dict, Optional, Tuple, Any, Callable
from aiortc import (
    RTCPeerConnection,
    RTCSessionDescription,
    RTCIceCandidate,
    RTCConfiguration,
    RTCIceServer
)
from .session import VoiceSession
from .audio_track import InboundAudioProcessor

logger = logging.getLogger(__name__)


class WebRTCManager:
    """Manages WebRTC PeerConnections, media tracks, and session lifecycle."""

    def __init__(self, on_turn_ready: Optional[Callable[[VoiceSession, bytes], Any]] = None):
        self.sessions: Dict[str, VoiceSession] = {}
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.inbound_processors: Dict[str, InboundAudioProcessor] = {}
        self.on_turn_ready = on_turn_ready

    async def handle_offer(
        self,
        sdp_offer: str,
        offer_type: str = "offer",
        session_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, VoiceSession]:
        """Process browser SDP offer, establish tracks and data channel, and return SDP answer."""
        config = config or {}
        session = VoiceSession(
            session_id=session_id,
            config=config,
            on_turn_ready=self.on_turn_ready
        )
        sid = session.session_id

        # Configure public STUN servers for NAT traversal
        ice_servers = [RTCIceServer(urls=["stun:stun.l.google.com:19302", "stun:stun1.l.google.com:19302"])]
        rtc_config = RTCConfiguration(iceServers=ice_servers)
        pc = RTCPeerConnection(configuration=rtc_config)

        self.sessions[sid] = session
        self.peer_connections[sid] = pc

        # 1. Attach outbound Opus audio track to peer connection
        pc.addTrack(session.outbound_track)

        # 2. Create server-side data channel for event broadcasting
        channel = pc.createDataChannel("voiceforge-events")
        session.set_data_channel(channel)

        # 3. Handle incoming client-created data channels
        @pc.on("datachannel")
        def on_datachannel(remote_channel):
            logger.info("Remote data channel opened: %s", remote_channel.label)
            session.set_data_channel(remote_channel)

        # 4. Handle incoming remote audio track from client microphone
        @pc.on("track")
        def on_track(track):
            logger.info("Received incoming WebRTC track: %s (kind=%s)", track.id, track.kind)
            if track.kind == "audio":
                processor = InboundAudioProcessor(
                    track=track,
                    on_pcm_chunk=session.feed_inbound_pcm
                )
                self.inbound_processors[sid] = processor
                processor.start()

        # 5. Monitor connection state
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info("Connection state changed for session %s: %s", sid, pc.connectionState)
            if pc.connectionState in ["failed", "closed"]:
                await self.close_session(sid)

        # 6. Set remote description and generate SDP answer
        offer_desc = RTCSessionDescription(sdp=sdp_offer, type=offer_type)
        await pc.setRemoteDescription(offer_desc)

        answer_desc = await pc.createAnswer()
        await pc.setLocalDescription(answer_desc)

        return pc.localDescription.sdp, session

    async def handle_ice_candidate(self, session_id: str, candidate_data: Dict[str, Any]) -> None:
        """Add remote ICE candidate to peer connection."""
        pc = self.peer_connections.get(session_id)
        if not pc:
            logger.warning("Received ICE candidate for non-existent session %s", session_id)
            return

        candidate_str = candidate_data.get("candidate", "")
        if not candidate_str:
            return

        sdp_mid = candidate_data.get("sdpMid")
        sdp_mline_index = candidate_data.get("sdpMLineIndex")

        # Parse candidate string into RTCIceCandidate attributes
        parts = candidate_str.strip().split()
        if len(parts) >= 8 and parts[0].startswith("candidate:"):
            candidate = RTCIceCandidate(
                component=int(parts[1]),
                foundation=parts[0].split(":")[1],
                ip=parts[4],
                port=int(parts[5]),
                priority=int(parts[3]),
                protocol=parts[2].lower(),
                type=parts[7],
                sdpMid=sdp_mid,
                sdpMLineIndex=sdp_mline_index
            )
            await pc.addIceCandidate(candidate)

    async def close_session(self, session_id: str) -> None:
        """Gracefully terminate a WebRTC session."""
        session = self.sessions.pop(session_id, None)
        if session:
            session.close()

        processor = self.inbound_processors.pop(session_id, None)
        if processor:
            processor.stop()

        pc = self.peer_connections.pop(session_id, None)
        if pc:
            await pc.close()
            logger.info("Closed WebRTC PeerConnection for session %s", session_id)
