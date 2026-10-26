"""Silero VAD v5 ONNX Runtime implementation for sub-2ms CPU voice activity detection."""

import logging
from pathlib import Path
from typing import Optional, Union
import numpy as np
import onnxruntime as ort

logger = logging.getLogger(__name__)


class SileroVAD:
    """Wrapper around the official Silero VAD v5 ONNX neural network.

    Processes 512-sample (32ms at 16,000 Hz) audio chunks and produces
    speech probability estimates between 0.0 and 1.0 while maintaining
    recurrent hidden states across audio frames.
    """

    SAMPLE_RATE = 16000
    WINDOW_SIZE_SAMPLES = 512  # 32ms at 16kHz
    STATE_SHAPE = (2, 1, 128)

    def __init__(self, model_path: Union[str, Path]):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"Silero VAD ONNX model not found at: {self.model_path}")

        # Optimize ONNX Runtime for single-core CPU execution
        session_options = ort.SessionOptions()
        session_options.inter_op_num_threads = 1
        session_options.intra_op_num_threads = 1
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=session_options,
            providers=["CPUExecutionProvider"]
        )

        self._sr_tensor = np.array(self.SAMPLE_RATE, dtype=np.int64)
        self.state = np.zeros(self.STATE_SHAPE, dtype=np.float32)

    def reset(self) -> None:
        """Reset the recurrent neural network hidden states."""
        self.state = np.zeros(self.STATE_SHAPE, dtype=np.float32)

    def process_chunk(self, audio_chunk: Union[np.ndarray, bytes]) -> float:
        """Process a single 512-sample audio chunk and return speech probability.

        Args:
            audio_chunk: 512 samples of 16kHz mono audio as float32 array in [-1.0, 1.0],
                         or 1024 bytes of 16-bit signed PCM audio.

        Returns:
            Speech probability between 0.0 (silence/noise) and 1.0 (confident speech).
        """
        if isinstance(audio_chunk, bytes):
            audio_data = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            audio_data = audio_chunk.astype(np.float32)
            if audio_data.dtype == np.int16:
                audio_data = audio_data / 32768.0

        if len(audio_data.shape) == 1:
            audio_data = np.expand_dims(audio_data, axis=0)

        if audio_data.shape[1] != self.WINDOW_SIZE_SAMPLES:
            raise ValueError(
                f"Audio chunk must have exactly {self.WINDOW_SIZE_SAMPLES} samples, got {audio_data.shape[1]}"
            )

        ort_inputs = {
            "input": audio_data,
            "state": self.state,
            "sr": self._sr_tensor
        }

        ort_outputs = self.session.run(None, ort_inputs)
        speech_prob = float(ort_outputs[0][0, 0])
        self.state = ort_outputs[1]

        return speech_prob
