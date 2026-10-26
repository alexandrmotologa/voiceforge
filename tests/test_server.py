"""Unit and integration tests for FastAPI server and WebRTC signaling endpoints."""

import pytest
from httpx import AsyncClient, ASGITransport
from aiortc import RTCPeerConnection
from src.server.app import app


@pytest.mark.asyncio
async def test_health_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "VoiceForge"


@pytest.mark.asyncio
async def test_api_config_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "audio_sample_rate" in data
        assert "available_stt" in data
        assert "available_tts" in data


@pytest.mark.asyncio
async def test_webrtc_signaling_offer_and_answer():
    transport = ASGITransport(app=app)

    # Create a real client-side RTCPeerConnection to generate a valid SDP offer
    client_pc = RTCPeerConnection()
    try:
        # Add audio transceiver (recvonly / sendrecv)
        client_pc.addTransceiver("audio", direction="sendrecv")
        client_offer = await client_pc.createOffer()
        await client_pc.setLocalDescription(client_offer)

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "sdp": client_offer.sdp,
                "type": "offer",
                "config": {
                    "stt_provider": "fallback",
                    "llm_provider": "fallback",
                    "tts_provider": "native"
                }
            }
            response = await client.post("/session/offer", json=payload)
            assert response.status_code == 200
            data = response.json()

            assert data["type"] == "answer"
            assert "session_id" in data
            assert "v=0" in data["sdp"]
            assert "m=audio" in data["sdp"]
    finally:
        await client_pc.close()
