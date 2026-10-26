"""FastAPI signaling router for WebRTC session negotiation, recording, and tool registration."""

import logging
from typing import Dict, Any, Optional
import httpx
from fastapi import APIRouter, HTTPException, Response, Query
from pydantic import BaseModel, Field

from ..config import settings
from ..gateway.webrtc import WebRTCManager
from ..pipeline.manager import PipelineManager
from ..tools.registry import TOOL_REGISTRY

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


class RegisterToolRequest(BaseModel):
    name: str = Field(description="Unique tool identifier")
    description: str = Field(description="Semantic tool purpose for LLM function calling")
    webhook_url: str = Field(description="Target HTTP webhook URL")
    method: str = Field(default="POST", description="HTTP method (GET or POST)")
    filler: Optional[str] = Field(default=None, description="Custom spoken vocal filler phrase")


class SimulatedPromptRequest(BaseModel):
    prompt: str = Field(description="Simulated user speech transcript to trigger turn")


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


@router.get("/session/{session_id}/recording")
async def download_session_recording(session_id: str):
    """Export the synchronized stereo call audio as standard 16kHz WAV."""
    session = webrtc_manager.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    wav_bytes = session.recorder.export_stereo_wav()
    return Response(
        content=wav_bytes,
        media_type="audio/wav",
        headers={
            "Content-Disposition": f'attachment; filename="voiceforge_{session_id}.wav"',
            "Content-Length": str(len(wav_bytes))
        }
    )


@router.get("/session/{session_id}/report")
async def get_session_report(
    session_id: str,
    format_type: str = Query("json", alias="format", pattern="^(json|markdown)$")
):
    """Retrieve complete session dialogue and latency waterfall report."""
    session = webrtc_manager.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    content = session.generate_report(format_type=format_type)
    media_type = "text/markdown" if format_type == "markdown" else "application/json"
    return Response(content=content, media_type=media_type)


@router.post("/session/{session_id}/inject-prompt")
async def inject_simulated_prompt(session_id: str, req: SimulatedPromptRequest):
    """Simulate user spoken utterance into pipeline for automated testing."""
    session = webrtc_manager.sessions.get(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Broadcast simulated user transcript
    session.send_event({
        "type": "transcript",
        "speaker": "user",
        "text": req.prompt,
        "is_final": True
    })
    session.conversation_history.append({"role": "user", "content": req.prompt})

    # Synthesize small mock audio buffer to trigger turn
    dummy_audio = bytes(3200)  # 100ms
    import asyncio
    asyncio.create_task(pipeline_manager.execute_turn(session, dummy_audio))

    return {"status": "injected", "prompt": req.prompt}


@router.post("/api/tools/register")
async def register_custom_webhook_tool(tool_req: RegisterToolRequest):
    """Dynamically register an external HTTP webhook as a conversational tool."""
    tool_name = tool_req.name
    webhook_url = tool_req.webhook_url
    method = tool_req.method.upper()
    filler = tool_req.filler or f"Querying {tool_name} right now."

    async def custom_webhook_handler(**kwargs):
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                if method == "POST":
                    resp = await client.post(webhook_url, json=kwargs)
                else:
                    resp = await client.get(webhook_url, params=kwargs)
                resp.raise_for_status()
                return resp.json()
        except Exception as err:
            logger.error("Custom webhook tool error: %s", err)
            return {"error": str(err), "status": "failed"}

    schema = {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": tool_req.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }

    TOOL_REGISTRY[tool_name] = {
        "name": tool_name,
        "description": tool_req.description,
        "filler": filler,
        "handler": custom_webhook_handler,
        "schema": schema
    }

    logger.info("Dynamically registered custom tool '%s' -> %s", tool_name, webhook_url)
    return {"status": "registered", "tool_name": tool_name}
