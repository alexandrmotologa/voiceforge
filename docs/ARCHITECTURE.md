# VoiceForge Architecture Specification

## Overview

VoiceForge is a self-hostable real-time voice orchestration engine designed as an open-source alternative to proprietary solutions like the OpenAI Realtime API. It bridges browser and telephony clients over UDP via WebRTC, detects human speech with sub-millisecond precision, and streams bidirectional conversational audio with an end-to-end turnaround target under 450 milliseconds.

---

## 1. Threading and Asyncio Model

VoiceForge runs on Python 3.12 using asyncio as its primary concurrency runtime. Real-time media processing requires careful separation between I/O bound network loops and CPU bound audio processing.

```
+-----------------------------------------------------------------------------+
|                           FastAPI / Uvicorn Process                         |
|                                                                             |
|  +-------------------------+            +--------------------------------+  |
|  |   asyncio Event Loop    |            |       ThreadPoolExecutor       |  |
|  |                         |            |                                |  |
|  | * WebRTC Signaling      |            | * ONNX Silero VAD inference    |  |
|  | * MediaStreamTrack loop |            | * Opus audio transcoding       |  |
|  | * WebSocket streaming   |            | * Local pyttsx3 PCM synthesis  |  |
|  | * Tool async tasks      |            | * File I/O and disk logging    |  |
|  +------------+------------+            +---------------+----------------+  |
|               |                                         |                   |
|               +--------------------+--------------------+                   |
|                                    |                                        |
|                          +---------v---------+                              |
|                          |   In-Memory State |                              |
|                          | * Active Sessions |                              |
|                          | * Audio RingBuffer|                              |
|                          | * Abort Events    |                              |
|                          +-------------------+                              |
+-----------------------------------------------------------------------------+
```

### Event Loop Safety
1. WebRTC frame generation (`AudioStreamTrack.recv`) runs inside the asyncio loop. Calls cannot block for more than 10 milliseconds without causing audio stutter.
2. CPU heavy operations (such as ONNX Runtime inference or pyttsx3 audio rendering) are dispatched to an internal `ThreadPoolExecutor` when required, or executed directly if sub-2ms benchmarks are guaranteed on modern cores.
3. Audio queues use `asyncio.Queue` with bounded sizes to prevent unbounded memory growth during network degradation.

---

## 2. Audio Pipeline and Data Flow

Audio flows through the system in discrete phases:

```
[Browser Mic]
     | (WebRTC Opus, 48kHz UDP)
     v
[InboundAudioTrack]
     | (Decode to 16kHz linear PCM, 16-bit mono)
     v
[Silero VAD Buffer] ---> (Speech detected? P > 0.5)
     |                               |
     | (Raw PCM chunks)              +---> [Barge-In Controller]
     v                                       (If Agent is speaking:
[Streaming STT Provider]                      flush outbound queue,
     | (Transcribed text tokens)              trigger abort event,
     v                                        notify client UI)
[Streaming LLM Engine]
     | (Streamed token stream)
     v
[Sentence Boundary Splitter]
     | (Complete sentences: ".", "!", "?", "\n")
     v
[Streaming TTS Provider]
     | (Raw PCM audio bytes)
     v
[OutboundAudioTrack Queue]
     | (Paced into 20ms Opus frames)
     v
[Browser Speaker]
```

### Audio Resampling and Format Standards
- **Network Format**: Opus 48,000 Hz, 1 or 2 channels, 20ms frame duration (960 samples per frame).
- **Internal Pipeline Format**: Linear PCM, 16,000 Hz, 16-bit signed integer, mono.
- **Conversion**:
  - Inbound 48kHz frames are downsampled to 16kHz by linear decimation (taking every 3rd sample) or using `scipy.signal.resample_poly` for higher fidelity.
  - Outbound 16kHz or 24kHz TTS audio is upsampled to 48kHz for Opus encoding.

---

## 3. Silero VAD v5 and Barge-In Controller

### Silero VAD v5 Mechanics
Silero VAD v5 is a compact neural network trained on multilingual speech.
- **Input Chunk Size**: 512 samples at 16,000 Hz (exact 32ms duration).
- **Recurrent State Tensor**: Shape `[2, 1, 128]` float32. This recurrent state persists across frames for a given session, maintaining temporal memory of speech cadence.
- **Execution Overhead**: Between 0.8ms and 2.5ms on a single modern CPU core via ONNX Runtime `CPUExecutionProvider`.

### State Machine
The session transitions between five discrete states:

```
+--------+       Speech Detected       +---------------+
|  IDLE  | --------------------------> | USER_SPEAKING |
+--------+                             +-------+-------+
    ^                                          |
    |                                          | Silence > 150ms
    |                                          v
+---+-----------+                      +-------+-------+
|  INTERRUPTED  |                      |  AI_THINKING  |
+---------------+                      +-------+-------+
    ^                                          |
    | User Speech During AI Playback           | First TTS Chunk
    |                                          v
    +--------------------------------- +---------------+
                                       |  AI_SPEAKING  |
                                       +---------------+
```

### Barge-In Protocol
When the session is in `AI_SPEAKING` and Silero VAD detects 2 consecutive speech frames ($2 \times 32\text{ms} = 64\text{ms}$ with $P > 0.5$):
1. **Queue Flush**: `OutboundAudioTrack.clear_buffer()` drains all remaining synthesized audio packets immediately.
2. **Cancellation Signal**: `session.abort_event.set()` cancels the current LLM token consumer and TTS generation coroutine.
3. **Data Channel Event**: Emits a lightweight JSON payload:
   ```json
   {
     "type": "barge_in",
     "timestamp": 1729976400.123,
     "latency_ms": 68
   }
   ```
4. **Client Action**: The browser client clears its internal Web Audio buffer source so remaining in-flight audio is not played in the user's headphones.

---

## 4. Latency Waterfall Architecture

Turnaround time is measured and reported across five discrete timestamps:

1. **$T_0$ (Turn End)**: User finishes speaking (VAD silence threshold reached).
2. **$T_1$ (STT Completion)**: Final text transcript emitted by speech-to-text.
3. **$T_2$ (LLM First Token)**: Time-to-First-Token (TTFT) from language model.
4. **$T_3$ (Sentence Ready)**: Sentence splitter emits first syntactically complete sentence.
5. **$T_4$ (TTS First Chunk)**: First synthesized audio buffer received from TTS.
6. **$T_5$ (Ear Delivery)**: Outbound WebRTC track encodes and transmits first audio packet.

Total Turnaround Time:
$$\Delta T = T_5 - T_0$$

The server broadcasts these metrics over the WebRTC data channel and SSE stream after every conversational turn.

---

## 5. Extensibility and Provider Swapping

VoiceForge enforces modular interfaces for STT, LLM, and TTS:

- `BaseSTT`: Supports both chunked streaming (`transcribe_stream`) and complete buffer decoding (`transcribe_buffer`).
- `BaseLLM`: Supports streaming token generation (`generate_stream`) with structured tool call parsing.
- `BaseTTS`: Supports streaming text-to-speech synthesis (`synthesize_stream`), yielding raw PCM bytes.

Each provider can be selected per session or configured globally via environment variables without modifying core orchestration logic.
