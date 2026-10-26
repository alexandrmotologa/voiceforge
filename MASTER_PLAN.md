# VoiceForge: Master Implementation Plan

Open-source production real-time voice agent server built in Python 3.12 (aiortc, onnxruntime, fastapi) and React 19.

VoiceForge provides a self-hosted alternative to the OpenAI Realtime API. It establishes full-duplex WebRTC audio connections with low latency, runs Silero VAD v5 locally on CPU for sub-80ms barge-in interruption handling, and supports both 100% offline local operation (Whisper, Kokoro, local LLMs) and cloud streaming pipelines (Deepgram, Claude, Cartesia) with target turnaround times under 450ms.

---

## 1. System Architecture

```
                                    VOICEFORGE
                                         |
         +-------------------------------+-------------------------------+
         |                                                               |
+--------v------------------------+             +------------------------v-------+
|   WebRTC Full-Duplex Gateway    |             |     Silero VAD & Barge-In      |
| * Opus audio streaming via UDP  |             | * ONNX Runtime (<2ms CPU)      |
| * aiortc peer connection engine |             | * 32ms frame sliding window    |
| * Data channels for telemetry   |             | * Sub-80ms playback interrupt  |
| * WebSocket streaming fallback  |             | * Abort signal dispatcher      |
+--------+------------------------+             +------------------------+-------+
         |                                                               |
         +-------------------------------+-------------------------------+
                                         |
                         +---------------v---------------+
                         |   Streaming Voice Pipeline    |
                         | * STT: Deepgram, Whisper      |
                         | * LLM: Claude, GPT-4o, Ollama |
                         | * TTS: Cartesia, Kokoro, OS   |
                         +---------------+---------------+
                                         |
                         +---------------v---------------+
                         |   Conversational Tool Runner  |
                         | * Mid-dialogue tool execution |
                         | * Natural vocal fillers       |
                         | * Context state persistence   |
                         +---------------+---------------+
                                         |
                         +---------------v---------------+
                         |  Interactive React 19 Studio  |
                         | * Real-time audio waveform    |
                         | * Turnaround latency waterfall|
                         | * Live transcript & barge-in  |
                         +-------------------------------+
```

---

## 2. Latency Budget & Turnaround Waterfall

Target end-to-end conversational turnaround: under 450ms in cloud mode, under 650ms in local mode.

| Stage | Mechanism | Cloud Target | Local Target |
| :--- | :--- | :--- | :--- |
| Audio Capture & Ingest | WebRTC Opus frame (20ms chunks) | 20ms | 20ms |
| Speech Detection (VAD) | Silero VAD v5 ONNX CPU inference | 3ms | 3ms |
| Speech Pause Confirmation | Trailing silence window (hysteresis) | 120ms | 150ms |
| Speech-to-Text (STT) | Streaming WebSocket / Local engine | 100ms | 180ms |
| LLM Time-to-First-Token | Streaming token generator | 120ms | 200ms |
| Sentence Chunking | First punctuation boundary delimiter | 20ms | 20ms |
| Text-to-Speech (TTS) | Streaming WebSocket / Native PCM | 80ms | 80ms |
| WebRTC Outbound Delivery | Paced Opus audio track to browser ear | 20ms | 20ms |
| **Total Turnaround Time** | **User speech end to first sound** | **~485ms (P50 <450ms)** | **~673ms** |

### Barge-In Interruption Budget

When user starts speaking while assistant is speaking:
- Silero VAD detection: 2 frames = 64ms.
- Model inference overhead: 2ms.
- Outbound audio queue clear: 1ms.
- Client audio abort signal: 5ms.
- Total interruption cutoff time: **under 75ms**.

---

## 3. Directory Layout

```
voiceforge/
├── src/
│   ├── __init__.py
│   ├── config.py                 # Application settings and environment variables
│   ├── cli.py                    # Typer command-line interface
│   ├── gateway/
│   │   ├── __init__.py
│   │   ├── webrtc.py             # aiortc PeerConnection and session manager
│   │   ├── audio_track.py        # Custom MediaStreamTrack for Opus and PCM
│   │   ├── session.py            # Active session state, queues, and cancellation
│   │   └── ws_fallback.py        # WebSocket fallback for restricted networks
│   ├── vad/
│   │   ├── __init__.py
│   │   ├── silero.py             # Silero VAD v5 ONNX wrapper (CPU execution)
│   │   ├── detector.py           # Frame buffer, smoothing, and state tracking
│   │   ├── barge_in.py           # Sub-80ms interruption event coordinator
│   │   └── models/
│   │       └── silero_vad.onnx   # Bundled ONNX model file
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── manager.py            # Orchestrator connecting STT -> LLM -> TTS
│   │   ├── stt/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Abstract STT interface
│   │   │   ├── deepgram.py       # Deepgram streaming WebSocket client
│   │   │   ├── whisper_local.py  # Local faster-whisper / ONNX provider
│   │   │   └── fallback.py       # Built-in zero-key speech recognizer
│   │   ├── llm/
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # Abstract LLM interface
│   │   │   ├── anthropic.py      # Claude 3.5 streaming client
│   │   │   ├── openai_client.py  # OpenAI GPT-4o streaming client
│   │   │   ├── ollama.py         # Ollama / vLLM local streaming client
│   │   │   ├── sentence_splitter.py # Punctuation-based sentence buffer
│   │   │   └── fallback.py       # Built-in conversational dialogue engine
│   │   └── tts/
│   │       ├── __init__.py
│   │       ├── base.py           # Abstract TTS interface
│   │       ├── cartesia.py       # Cartesia Sonic WebSocket streaming client
│   │       ├── elevenlabs.py     # ElevenLabs streaming client
│   │       └── native_pcm.py     # Fast local PCM audio synthesizer (pyttsx3)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── registry.py           # Tool decorator and schema definitions
│   │   ├── runner.py             # Asynchronous tool executor
│   │   ├── fillers.py            # Conversational filler phrase generator
│   │   └── builtin.py            # Clock, weather, knowledge, and system tools
│   └── server/
│       ├── __init__.py
│       ├── app.py                # FastAPI HTTP routes and WebRTC signaling
│       ├── signaling.py          # SDP offer and answer handling
│       └── telemetry.py          # Real-time metrics and SSE broadcasting
├── web/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   ├── components/
│   │   │   ├── Header.tsx
│   │   │   ├── Visualizer.tsx    # Audio waveform and frequency visualizer
│   │   │   ├── LatencyWaterfall.tsx # Real-time latency waterfall chart
│   │   │   ├── TranscriptView.tsx# Live transcript with barge-in markers
│   │   │   ├── ToolMonitor.tsx   # Active tool execution inspector
│   │   │   └── SettingsModal.tsx # Engine, voice, and threshold settings
│   │   ├── hooks/
│   │   │   ├── useWebRTCVoice.ts # WebRTC connection and audio capture hook
│   │   │   └── useAudioVisualizer.ts
│   │   └── types.ts
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── tests/
│   ├── test_vad.py               # VAD inference and latency unit tests
│   ├── test_barge_in.py          # Interruption timing and cancellation tests
│   ├── test_pipeline.py          # STT, LLM, sentence splitter, and TTS tests
│   ├── test_tools.py             # Tool registration and execution tests
│   └── test_server.py            # WebRTC signaling and API endpoint tests
├── docs/
│   ├── ARCHITECTURE.md
│   ├── WEBRTC_SPEC.md
│   ├── BENCHMARKS.md
│   └── images/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── README.md
```

---

## 4. Phase-by-Phase Implementation Roadmap

### Phase 1: Core Configuration and Foundation
- Implement `src/config.py` using `pydantic-settings` to manage API keys, audio sample rates, thresholds, and server ports.
- Verify Silero VAD v5 model presence in `src/vad/models/silero_vad.onnx`.

### Phase 2: Silero VAD and Sub-80ms Barge-In Controller
- Implement `src/vad/silero.py` wrapping ONNX Runtime:
  - Input: float32 tensor of shape `[1, 512]` at 16,000 Hz (32ms).
  - Recurrent state tensor: shape `[2, 1, 128]`.
  - Output: speech probability float in `[0.0, 1.0]`.
- Implement `src/vad/detector.py`:
  - Circular frame buffer for raw PCM chunks.
  - Hysteresis filter: 2 frames of speech to trigger speaking state, 150ms of silence to trigger turn completion.
- Implement `src/vad/barge_in.py`:
  - When speech begins while assistant is outputting audio, trigger cancellation:
    1. Clear outbound audio track queue.
    2. Signal `asyncio.Event` abort token to halt LLM and TTS tasks.
    3. Send interruption event to client data channel.

### Phase 3: WebRTC Audio Gateway and Session Management
- Implement `src/gateway/audio_track.py`:
  - Inbound audio track: decodes Opus audio to 16kHz linear PCM, pushes to VAD and STT buffers.
  - Outbound audio track: generates 20ms Opus frames (960 samples at 48kHz). Reads from priority audio queue; outputs silence frames when idle to keep WebRTC connection active.
  - `clear_buffer()` method for instantaneous playback abort.
- Implement `src/gateway/session.py`:
  - Manages call state machine (`IDLE`, `LISTENING`, `THINKING`, `SPEAKING`).
  - Coordinates inbound VAD events and outbound audio queue.
- Implement `src/gateway/webrtc.py`:
  - WebRTC PeerConnection manager with SDP offer/answer negotiation and ICE state tracking.
  - Data channel handler for bidirectional JSON messaging (transcripts, latency metrics, tool events).

### Phase 4: Streaming Voice Pipeline (STT -> LLM -> TTS)
- Implement `src/pipeline/stt/`:
  - Abstract `BaseSTT`.
  - `DeepgramSTT`: Real-time streaming WebSocket client.
  - `WhisperLocalSTT`: Local transcription provider.
  - `FallbackSTT`: Zero-key audio pattern and keyword matcher for immediate local testing.
- Implement `src/pipeline/llm/`:
  - Abstract `BaseLLM`.
  - `SentenceSplitter`: Buffers streamed tokens, yields complete sentences at punctuation boundaries (`.`, `!`, `?`, `\n`) to enable immediate TTS synthesis.
  - `AnthropicLLM`, `OpenAILLM`, `OllamaLLM`.
  - `FallbackLLM`: Rule-based local conversational agent with context memory and tool calling.
- Implement `src/pipeline/tts/`:
  - Abstract `BaseTTS`.
  - `CartesiaTTS`: WebSocket client streaming 16kHz PCM audio chunks.
  - `NativePCMTTS`: Local pyttsx3 synthesizer producing raw PCM audio in 50ms without external API keys.
- Implement `src/pipeline/manager.py`:
  - Glues STT, LLM, and TTS with latency tracking at each hop.

### Phase 5: Conversational Tool Calling and Natural Fillers
- Implement `src/tools/registry.py`:
  - Decorator `@register_tool` with JSON schema generation.
- Implement `src/tools/builtin.py`:
  - Current time tool, weather lookup, calculator, system diagnostics tool.
- Implement `src/tools/fillers.py`:
  - Natural conversational fillers injected when a tool call starts ("Let me check that for you right now...").
- Implement `src/tools/runner.py`:
  - Executes tool functions asynchronously, returns output to LLM context.

### Phase 6: FastAPI Server and Telemetry Signaling
- Implement `src/server/signaling.py`:
  - Endpoints: `POST /session/offer`, `POST /session/ice`, `GET /session/{id}/metrics`.
- Implement `src/server/telemetry.py`:
  - Latency breakdown recorder emitting structured JSON metrics.
- Implement `src/server/app.py`:
  - Mounts API routes, WebSocket fallback, and static frontend assets.

### Phase 7: Interactive React 19 Web Studio
- Create Vite React 19 project in `web/` with TypeScript and Tailwind CSS.
- Build components:
  - `Visualizer.tsx`: Dual-channel frequency oscilloscope (User vs Assistant).
  - `LatencyWaterfall.tsx`: Gantt chart breakdown of turnaround stages.
  - `TranscriptView.tsx`: Real-time message dialogue with barge-in interruption tags.
  - `ToolMonitor.tsx`: Live display of tool calls, inputs, and results.
  - `SettingsModal.tsx`: Control panel for models, voices, and VAD sensitivity.
- Build `useWebRTCVoice.ts`: Manages browser microphone, WebRTC connection, data channel listeners, and fallback audio.

### Phase 8: CLI, Testing Suite, and Verification
- Implement `src/cli.py` with Typer:
  - `serve`: Starts FastAPI server and WebRTC gateway.
  - `benchmark`: Measures VAD inference speed, STT latency, and TTS generation time.
  - `test-vad`: Evaluates VAD on a WAV audio file.
- Write unit and integration tests in `tests/`:
  - Test VAD inference, state maintenance, and speech probability.
  - Test barge-in interruption latency and queue clearing.
  - Test sentence splitter on streaming tokens.
  - Test tool execution and filler selection.
  - Test WebRTC signaling endpoints.
- Build production Dockerfile and documentation.
