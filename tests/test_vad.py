"""Unit tests for Silero VAD v5 and VADDetector."""

import time
import numpy as np
import pytest
from src.config import settings
from src.vad.silero import SileroVAD
from src.vad.detector import VADDetector
from src.vad.barge_in import BargeInController


def test_silero_vad_init_and_reset():
    vad = SileroVAD(settings.vad_model_path)
    assert vad.session is not None
    assert vad.state.shape == (2, 1, 128)
    assert np.all(vad.state == 0)

    vad.reset()
    assert np.all(vad.state == 0)


def test_silero_vad_silence_probability():
    vad = SileroVAD(settings.vad_model_path)
    silence = np.zeros((1, 512), dtype=np.float32)

    t0 = time.perf_counter()
    prob = vad.process_chunk(silence)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert 0.0 <= prob <= 0.1
    # Check that CPU inference is fast (under 15ms even in unoptimized pytest environment)
    assert elapsed_ms < 15.0


def test_silero_vad_speech_chunk_bytes():
    vad = SileroVAD(settings.vad_model_path)
    # Generate 512 samples of 400Hz tone in int16 PCM format
    t = np.linspace(0, 512 / 16000, 512, endpoint=False)
    samples = (np.sin(2 * np.pi * 400 * t) * 16000).astype(np.int16)
    raw_bytes = samples.tobytes()

    prob = vad.process_chunk(raw_bytes)
    assert 0.0 <= prob <= 1.0


def test_vad_detector_transitions():
    vad = SileroVAD(settings.vad_model_path)
    events = []

    detector = VADDetector(
        vad=vad,
        threshold=0.3,
        speech_pad_frames=2,
        silence_timeout_ms=100,
        on_speech_start=lambda: events.append("start"),
        on_speech_end=lambda data: events.append(f"end_{len(data)}")
    )

    # Feed silence frames (1024 bytes each = 512 samples)
    silence_frame = bytes(1024)
    for _ in range(5):
        detector.process_pcm_bytes(silence_frame)

    assert "start" not in events

    # Feed high amplitude speech simulation (speech tone)
    t = np.linspace(0, 512 / 16000, 512, endpoint=False)
    speech_frame = (np.sin(2 * np.pi * 300 * t) * 20000).astype(np.int16).tobytes()

    # Manually mock high speech probability for testing detector state machine
    original_process = vad.process_chunk
    try:
        vad.process_chunk = lambda chunk: 0.95
        # Feed 3 speech frames
        for _ in range(3):
            detector.process_pcm_bytes(speech_frame)

        assert "start" in events

        # Now simulate silence to trigger speech end
        vad.process_chunk = lambda chunk: 0.01
        for _ in range(6):
            detector.process_pcm_bytes(silence_frame)

        assert any(e.startswith("end_") for e in events)
    finally:
        vad.process_chunk = original_process


def test_barge_in_controller():
    interrupted = False
    notified_data = {}

    def on_interrupt():
        nonlocal interrupted
        interrupted = True

    def on_notify(payload):
        nonlocal notified_data
        notified_data = payload

    controller = BargeInController(
        on_interrupt_action=on_interrupt,
        on_notify_client=on_notify
    )

    latency_ms = controller.trigger(speech_probability=0.88)

    assert interrupted is True
    assert notified_data.get("type") == "barge_in"
    assert notified_data.get("speech_prob") == 0.88
    assert latency_ms < 50.0  # Should execute in less than 50ms
