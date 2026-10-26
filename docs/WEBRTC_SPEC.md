# VoiceForge WebRTC Specification

## 1. Protocol Overview

VoiceForge uses standard WebRTC (RFC 8829 / RFC 8831) for real-time bidirectional media and metadata transport between client and server.

- **Audio Track**: Opus codec encapsulated in SRTP / UDP.
- **Data Channel**: Bidirectional SCTP data channel for real-time signaling, telemetry, transcripts, and barge-in events.
- **Signaling Transport**: HTTP REST for SDP Offer and Answer negotiation, with optional WebSocket fallback for restrictive network environments.

---

## 2. Signaling Lifecycle

### Step 1: Client SDP Offer
The client captures user microphone audio using `navigator.mediaDevices.getUserMedia({ audio: true })`, attaches the track to an `RTCPeerConnection`, creates an SDP offer, and sends it via HTTP POST:

```http
POST /session/offer HTTP/1.1
Host: localhost:8765
Content-Type: application/json

{
  "sdp": "v=0\r\no=- 4200 2 IN IP4 127.0.0.1...",
  "type": "offer",
  "config": {
    "stt_provider": "deepgram",
    "llm_provider": "claude",
    "tts_provider": "cartesia",
    "vad_threshold": 0.5,
    "voice_id": "sonic-english"
  }
}
```

### Step 2: Server SDP Answer
The server instantiates an `RTCPeerConnection`, binds an inbound audio receiver, creates a custom `OutboundAudioTrack`, binds a data channel, and responds with its SDP answer:

```http
HTTP/1.1 200 OK
Content-Type: application/json

{
  "session_id": "vf_sess_8f93e2b1",
  "sdp": "v=0\r\no=- 4201 2 IN IP4 127.0.0.1...",
  "type": "answer"
}
```

### Step 3: ICE Candidate Exchange
ICE candidates discovered by the browser can be trickle-exchanged via:

```http
POST /session/ice HTTP/1.1
Content-Type: application/json

{
  "session_id": "vf_sess_8f93e2b1",
  "candidate": "candidate:1 1 UDP 2130706431 192.168.1.100 54321 typ host...",
  "sdpMid": "0",
  "sdpMLineIndex": 0
}
```

---

## 3. Data Channel Messaging Schema

The WebRTC data channel label is `voiceforge-events`. All messages are serialized as UTF-8 JSON.

### Message Types

#### 1. Transcript Event
Emitted whenever user or agent speech is transcribed or generated.

```json
{
  "type": "transcript",
  "speaker": "user",
  "text": "What is the weather in Bucharest right now?",
  "is_final": true,
  "timestamp": 1729976402.450
}
```

```json
{
  "type": "transcript",
  "speaker": "assistant",
  "text": "The current temperature in Bucharest is 14 degrees Celsius with clear skies.",
  "is_final": true,
  "timestamp": 1729976404.100
}
```

#### 2. Barge-In Interruption Event
Dispatched the exact millisecond user speech interrupts active assistant playback.

```json
{
  "type": "barge_in",
  "timestamp": 1729976405.320,
  "latency_ms": 64,
  "interrupted_text": "The current temperature in..."
}
```

#### 3. Latency Waterfall Metrics
Emitted after every conversational turn with millisecond timing breakdowns.

```json
{
  "type": "metrics",
  "turn_id": "turn_01",
  "vad_silence_ms": 130,
  "stt_latency_ms": 112,
  "llm_ttft_ms": 128,
  "tts_first_chunk_ms": 78,
  "audio_delivery_ms": 15,
  "total_turnaround_ms": 463
}
```

#### 4. Tool Execution Event
Emitted when a conversational function is invoked.

```json
{
  "type": "tool_call",
  "status": "executing",
  "tool_name": "get_weather",
  "arguments": { "city": "Bucharest" },
  "filler_spoken": "Checking the weather conditions now..."
}
```

```json
{
  "type": "tool_call",
  "status": "completed",
  "tool_name": "get_weather",
  "result": { "temp_c": 14, "condition": "Clear" },
  "duration_ms": 320
}
```

---

## 4. WebSocket Fallback Protocol

In networks where UDP or WebRTC STUN/TURN traffic is filtered, clients can connect to `/session/{id}/stream` over standard WebSocket.

- **Audio Upstream**: Client streams raw 16-bit 16kHz linear PCM frames in binary WebSocket packets (640 bytes = 20ms).
- **Audio Downstream**: Server streams 16-bit 16kHz linear PCM audio packets to client over binary frames.
- **Control & Events**: Text WebSocket frames carry the identical JSON message schema documented above.
