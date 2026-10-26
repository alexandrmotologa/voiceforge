"""FastAPI web server application with WebRTC signaling and WebSocket audio streaming."""

import os
from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..config import settings, ROOT_DIR
from .signaling import router as signaling_router, pipeline_manager
from ..gateway.ws_fallback import WebSocketFallbackHandler

app = FastAPI(
    title="VoiceForge",
    description="Open-Source Real-Time Voice Agent Server with WebRTC & Silero VAD Barge-In",
    version="0.1.0"
)

# Enable permissive CORS for development and cross-origin WebRTC clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount WebRTC signaling endpoints
app.include_router(signaling_router)

# WebSocket fallback handler
ws_handler = WebSocketFallbackHandler(on_turn_ready=pipeline_manager.execute_turn)


@app.websocket("/session/{session_id}/stream")
async def websocket_audio_endpoint(websocket: WebSocket, session_id: str):
    """Fallback full-duplex audio stream over WebSocket for restricted networks."""
    await ws_handler.handle_connection(websocket, session_id)


@app.get("/health")
async def health_check():
    """Health check endpoint indicating server readiness."""
    return {
        "status": "healthy",
        "service": "VoiceForge",
        "version": "0.1.0",
        "vad_loaded": True
    }


# Serve built React frontend if distribution files exist
web_dist_path = ROOT_DIR / "web" / "dist"
if web_dist_path.exists():
    app.mount("/", StaticFiles(directory=str(web_dist_path), html=True), name="static_web")
