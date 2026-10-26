"""Unit tests for the streaming voice pipeline components."""

import pytest
from src.pipeline.stt.fallback import FallbackSTT
from src.pipeline.llm.sentence_splitter import SentenceSplitter, stream_sentences
from src.pipeline.llm.fallback import FallbackLLM
from src.pipeline.tts.native_pcm import NativePCMTTS
from src.pipeline.manager import PipelineManager
from src.gateway.session import VoiceSession


@pytest.mark.asyncio
async def test_fallback_stt():
    stt = FallbackSTT()
    # Test silence (less than minimum bytes)
    empty = await stt.transcribe(b"")
    assert empty == ""

    # Test speech-like audio (512 samples * 5 frames of tone)
    import numpy as np
    t = np.linspace(0, 2560 / 16000, 2560, endpoint=False)
    tone = (np.sin(2 * np.pi * 350 * t) * 15000).astype(np.int16).tobytes()

    text = await stt.transcribe(tone)
    assert len(text) > 0


@pytest.mark.asyncio
async def test_sentence_splitter():
    splitter = SentenceSplitter(min_words=3)

    tokens = ["This ", "is ", "the ", "first ", "sentence. ", "Here ", "is ", "the ", "second! ", "And ", "residual"]
    results = []
    for t in tokens:
        sentences = splitter.process_token(t)
        results.extend(sentences)

    assert len(results) >= 2
    assert "This is the first sentence." in results[0]
    assert "Here is the second!" in results[1]

    flushed = splitter.flush()
    assert len(flushed) == 1
    assert "And residual" in flushed[0]


@pytest.mark.asyncio
async def test_fallback_llm_stream():
    llm = FallbackLLM()
    messages = [{"role": "user", "content": "What is the weather in Bucharest?"}]

    tokens = []
    async for token in llm.generate_stream(messages):
        tokens.append(token)

    full_text = "".join(tokens)
    assert len(full_text) > 0
    assert "Bucharest" in full_text


@pytest.mark.asyncio
async def test_native_pcm_tts():
    tts = NativePCMTTS()
    pcm = await tts.synthesize("Hello from VoiceForge real-time server.")
    assert isinstance(pcm, bytes)
    assert len(pcm) > 0
    # 16-bit PCM: length must be even number of bytes
    assert len(pcm) % 2 == 0


@pytest.mark.asyncio
async def test_pipeline_manager_turn():
    manager = PipelineManager()
    session = VoiceSession()

    events = []
    session.send_event = lambda payload: events.append(payload)

    # Generate synthetic speech audio (5 frames = 160ms)
    import numpy as np
    t = np.linspace(0, 2560 / 16000, 2560, endpoint=False)
    synthetic_audio = (np.sin(2 * np.pi * 400 * t) * 16000).astype(np.int16).tobytes()

    await manager.execute_turn(session, synthetic_audio)

    # Check metrics and transcript events were emitted
    metric_events = [e for e in events if e.get("type") == "metrics"]
    transcript_events = [e for e in events if e.get("type") == "transcript"]

    assert len(metric_events) >= 1
    assert "total_turnaround_ms" in metric_events[0]
    assert len(transcript_events) >= 2  # user + assistant
    assert session.outbound_track.has_pending_audio() or len(session.conversation_history) > 1
