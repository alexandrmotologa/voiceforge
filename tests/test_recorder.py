"""Unit tests for dual-track call audio recorder and WAV generator."""

import io
import wave
import numpy as np
import pytest
from src.gateway.recorder import AudioCallRecorder


def test_audio_call_recorder_empty():
    recorder = AudioCallRecorder()
    wav_bytes = recorder.export_stereo_wav()

    assert isinstance(wav_bytes, bytes)
    assert len(wav_bytes) > 44  # Valid WAV header

    # Parse WAV bytes
    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 2
        assert wf.getsampwidth() == 2
        assert wf.getframerate() == 16000


def test_audio_call_recorder_dual_channels():
    recorder = AudioCallRecorder()

    # Inbound: 16000 samples (1 sec) of 300Hz tone
    t = np.linspace(0, 1.0, 16000, endpoint=False)
    inbound_pcm = (np.sin(2 * np.pi * 300 * t) * 12000).astype(np.int16).tobytes()

    # Outbound: 8000 samples (0.5 sec) of 600Hz tone
    t_out = np.linspace(0, 0.5, 8000, endpoint=False)
    outbound_pcm = (np.sin(2 * np.pi * 600 * t_out) * 14000).astype(np.int16).tobytes()

    recorder.record_inbound(inbound_pcm)
    recorder.record_outbound(outbound_pcm)

    wav_bytes = recorder.export_stereo_wav()
    assert len(wav_bytes) > 64000  # 1 second stereo at 16kHz = 64,000 bytes + header

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        assert wf.getnchannels() == 2
        assert wf.getframerate() == 16000
        assert wf.getnframes() == 16000
