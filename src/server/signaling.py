"""FastAPI signaling router for WebRTC session negotiation and ICE exchange."""

import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from ..config import settings
from ..gateway.webrtc import WebRTCManager
from ..pipeline.manager import PipelineManager

logger = logging.getLogger(__name__)

router = APIRouter()

# Global pipeline and WebRTC managers
pipeline_manager = PipelineManager()
webrtc_manager = WebRTCManager(on_turn_ready=pipeline_manager.execute_turn)


class OfferRequest(BaseModel):
    sdp: str = Field(description="Client SDP offer string")
    type: str = Field(default="offer", description="SDP message type")
    session_id: Optional[str] = Field(default=None, description="Optional existing session ID")
    config: Optional[Dict[str, Any]] = Field(default=None, description="Session runtime configuration")


class OfferResponse(BaseModel):
    sdp: str
    type: str = "answer"
    session_id: str


class ICERequest(BaseModel):
    session_id: str
    candidate: str
    sdpMid: Optional[str] = None
    sdpMLineIndex: Optional[int] = None


@router.post("/session/offer", response_model=OfferResponse)
async def create_session_offer(offer: OfferRequest):
    """Receive browser SDP offer, initialize WebRTC PeerConnection, and return SDP answer."""
    try:
        answer_sdp, session = await webrtc_manager.handle_offer(
            sdp_offer=offer.sdp,
            offer_type=offer.type,
            session_id=offer.session_id,
            config=offer.config
        )
        return OfferResponse(
            sdp=answer_sdp,
            type="answer",
            session_id=session.session_id
        )
    except Exception as e:
        logger.error("Failed to negotiate WebRTC offer: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"WebRTC negotiation failed: {str(e)}")


@router.post("/session/ice")
async def handle_ice_candidate(ice_req: ICERequest):
    """Receive and attach trickle ICE candidates from client."""
    try:
        await webrtc_manager.handle_ice_candidate(
            session_id=ice_req.session_id,
            candidate_data=ice_req.model_dump()
        )
        return {"status": "ok"}
    except Exception as e:
        logger.error("Failed to process ICE candidate: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/config")
async def get_server_config():
    """Retrieve active server parameters and supported providers."""
    return {
        "audio_sample_rate": settings.audio_sample_rate,
        "webrtc_sample_rate": settings.webrtc_sample_rate,
        "vad_threshold": settings.vad_threshold,
        "default_stt": settings.default_stt_provider,
        "default_llm": settings.default_llm_provider,
        "default_tts": settings.default_tts_provider,
        "available_stt": ["deepgram", "whisper_local", "fallback"],
        "available_llm": ["anthropic", "openai", "ollama", "fallback"],
        "available_tts": ["cartesia", "elevenlabs", "native"]
    }


@router.post("/session/{session_id}/interrupt")
async def trigger_manual_interrupt(session_id: str):
    """Manually trigger barge-in interruption for an active session."""
    session = webrtc_manager.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    latency_ms = session.barge_in_controller.trigger(speech_probability=1.0)
    return {"status": "interrupted", "latency_ms": latency_ms}
