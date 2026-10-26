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
                    "tts_provider": "native",
                    "speech_rate": 1.1
                }
            }
            response = await client.post("/session/offer", json=payload)
            assert response.status_code == 200
            data = response.json()

            assert data["type"] == "answer"
            assert "session_id" in data
            session_id = data["session_id"]
            assert "v=0" in data["sdp"]
            assert "m=audio" in data["sdp"]

            # Test simulated prompt injection
            inj_resp = await client.post(
                f"/session/{session_id}/inject-prompt",
                json={"prompt": "What is the system status?"}
            )
            assert inj_resp.status_code == 200
            assert inj_resp.json()["status"] == "injected"

            # Test session report (json & markdown)
            rep_json = await client.get(f"/session/{session_id}/report?format=json")
            assert rep_json.status_code == 200
            assert "session_id" in rep_json.json()

            rep_md = await client.get(f"/session/{session_id}/report?format=markdown")
            assert rep_md.status_code == 200
            assert "# VoiceForge Session Report" in rep_md.text

            # Test call audio recording download
            rec_resp = await client.get(f"/session/{session_id}/recording")
            assert rec_resp.status_code == 200
            assert rec_resp.headers["content-type"] == "audio/wav"
            assert len(rec_resp.content) > 44
    finally:
        await client_pc.close()


@pytest.mark.asyncio
async def test_register_custom_tool():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "name": "lookup_user_account",
            "description": "Fetch account status for customer",
            "webhook_url": "https://httpbin.org/post",
            "method": "POST",
            "filler": "Querying customer account database right now."
        }
        response = await client.post("/api/tools/register", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "registered"
        assert data["tool_name"] == "lookup_user_account"
