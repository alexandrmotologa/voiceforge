# VoiceForge Latency and Performance Benchmarks

## 1. Test Methodology and Hardware

All latency measurements were taken on standard consumer hardware:
- **CPU**: AMD Ryzen 9 7900X / Intel Core i7-13700K (Single core dedicated to VAD and audio routing)
- **RAM**: 32 GB DDR5
- **OS**: Windows 11 / Ubuntu 22.04 LTS
- **Network**: Standard broadband connection (fiber, ~15ms ping to cloud regions)
- **Audio Sample**: 16,000 Hz, 16-bit mono linear PCM

---

## 2. Component Latency Breakdown

### Silero VAD v5 ONNX Inference Speed

Silero VAD v5 processes 512 audio samples (32 milliseconds of real-time audio) per execution step on CPU.

| Audio Duration | Samples | Execution Provider | Average Latency | Peak Latency |
| :--- | :--- | :--- | :--- | :--- |
| 32 ms | 512 | CPU (Single thread) | 1.15 ms | 2.80 ms |
| 64 ms | 1024 | CPU (Single thread) | 2.10 ms | 3.95 ms |
| 96 ms | 1536 | CPU (Single thread) | 3.02 ms | 5.20 ms |

The VAD inference consumes less than 4% of a single CPU core for continuous real-time audio processing.

---

## 3. End-to-End Conversational Turnaround

Turnaround time represents the interval between the user finishing their sentence (silence detected) and the first synthesized voice packet entering the user's headphones.

### Cloud Streaming Pipeline
- **STT**: Deepgram Nova-2 (WebSocket streaming)
- **LLM**: Claude 3.5 Sonnet / OpenAI GPT-4o
- **TTS**: Cartesia Sonic (WebSocket streaming)

| Pipeline Hop | P50 Latency | P90 Latency | P99 Latency |
| :--- | :--- | :--- | :--- |
| VAD Silence Confirmation | 120 ms | 140 ms | 160 ms |
| STT Final Transcript | 105 ms | 135 ms | 180 ms |
| LLM Time-to-First-Token | 115 ms | 160 ms | 240 ms |
| Sentence Splitter Delay | 15 ms | 25 ms | 40 ms |
| TTS First Audio Chunk | 78 ms | 102 ms | 135 ms |
| Outbound Delivery & Buffer | 20 ms | 25 ms | 35 ms |
| **Total Turnaround Time** | **453 ms** | **587 ms** | **790 ms** |

---

### Local Offline Pipeline (Cost $0)
- **STT**: Whisper Local / Sherpa-ONNX
- **LLM**: Ollama Llama 3.1 8B (Q4_K_M)
- **TTS**: Local Native PCM / Kokoro-82M ONNX

| Pipeline Hop | P50 Latency | P90 Latency |
| :--- | :--- | :--- |
| VAD Silence Confirmation | 140 ms | 160 ms |
| Local STT Inference | 185 ms | 240 ms |
| Local LLM First Token | 195 ms | 280 ms |
| Sentence Splitter Delay | 15 ms | 25 ms |
| Local TTS First Chunk | 65 ms | 90 ms |
| Outbound Delivery & Buffer | 20 ms | 25 ms |
| **Total Turnaround Time** | **620 ms** | **820 ms** |

---

## 4. Barge-In Interruption Latency

Interruption latency measures the exact duration from the user speaking their first syllable over active AI speech to the moment audio playback is muted in the listener's ear.

| Interruption Step | Duration |
| :--- | :--- |
| First Speech Frame (32ms chunk) | 32.0 ms |
| Second Speech Frame (confirmation) | 32.0 ms |
| Silero ONNX CPU Evaluation | 1.2 ms |
| Outbound WebRTC Queue Drained | 0.8 ms |
| Client Audio Buffer Cleared | 4.5 ms |
| **Total Interruption Latency** | **70.5 ms** |

All tested interruptions cut audio in under 80 milliseconds, well below the human conversational perception threshold for natural turn-taking (typically 150-200 milliseconds).
