"""Pipeline manager coordinating STT, LLM, SentenceSplitter, and TTS with latency telemetry."""

import asyncio
import logging
import time
from typing import Dict, Any, Optional

from ..config import settings
from ..gateway.session import VoiceSession, SessionState
from .stt.base import BaseSTT
from .stt.deepgram import DeepgramSTT
from .stt.whisper_local import WhisperLocalSTT
from .stt.fallback import FallbackSTT
from .llm.base import BaseLLM
from .llm.anthropic import AnthropicLLM
from .llm.openai_client import OpenAILLM
from .llm.ollama import OllamaLLM
from .llm.fallback import FallbackLLM
from .llm.sentence_splitter import SentenceSplitter
from .tts.base import BaseTTS
from .tts.native_pcm import NativePCMTTS
from .tts.cartesia import CartesiaTTS
from .tts.elevenlabs import ElevenLabsTTS
from ..tools.registry import get_all_tool_schemas
from ..tools.runner import ToolRunner

logger = logging.getLogger(__name__)


class PipelineManager:
    """Coordinates end-to-end conversational turns and measures latency waterfall."""

    def __init__(self):
        # Default engine instances
        self._stt_providers: Dict[str, BaseSTT] = {
            "deepgram": DeepgramSTT(),
            "whisper_local": WhisperLocalSTT(),
            "fallback": FallbackSTT()
        }
        self._llm_providers: Dict[str, BaseLLM] = {
            "anthropic": AnthropicLLM(),
            "openai": OpenAILLM(),
            "ollama": OllamaLLM(),
            "fallback": FallbackLLM()
        }
        self._tts_providers: Dict[str, BaseTTS] = {
            "cartesia": CartesiaTTS(),
            "elevenlabs": ElevenLabsTTS(),
            "native": NativePCMTTS()
        }

    def get_stt(self, name: Optional[str] = None) -> BaseSTT:
        key = name or settings.default_stt_provider
        return self._stt_providers.get(key, self._stt_providers["fallback"])

    def get_llm(self, name: Optional[str] = None) -> BaseLLM:
        key = name or settings.default_llm_provider
        return self._llm_providers.get(key, self._llm_providers["fallback"])

    def get_tts(self, name: Optional[str] = None) -> BaseTTS:
        key = name or settings.default_tts_provider
        return self._tts_providers.get(key, self._tts_providers["native"])

    async def execute_turn(self, session: VoiceSession, user_audio_bytes: bytes) -> None:
        """Process complete conversational turn from audio input to outbound synthesis."""
        t0 = time.perf_counter()
        session_id = session.session_id

        stt_name = session.config.get("stt_provider", settings.default_stt_provider)
        llm_name = session.config.get("llm_provider", settings.default_llm_provider)
        tts_name = session.config.get("tts_provider", settings.default_tts_provider)

        stt = self.get_stt(stt_name)
        llm = self.get_llm(llm_name)
        tts = self.get_tts(tts_name)

        logger.info(
            "Turn start for session %s (STT=%s, LLM=%s, TTS=%s)",
            session_id, stt_name, llm_name, tts_name
        )

        # 1. Speech-to-Text Transcription
        t_stt_start = time.perf_counter()
        transcript = await stt.transcribe(user_audio_bytes)
        t_stt_end = time.perf_counter()
        stt_duration_ms = (t_stt_end - t_stt_start) * 1000.0

        if not transcript.strip():
            logger.debug("Empty transcript, returning to idle state")
            session.state = SessionState.IDLE
            return

        # Check if turn was aborted during STT
        if session.abort_event.is_set():
            logger.info("Turn aborted during STT for session %s", session_id)
            return

        # Broadcast user transcript to client UI
        session.send_event({
            "type": "transcript",
            "speaker": "user",
            "text": transcript,
            "is_final": True,
            "timestamp": time.time()
        })

        session.conversation_history.append({"role": "user", "content": transcript})

        # 2. LLM Streaming & Sentence Chunking
        session.state = SessionState.AI_THINKING
        session.send_event({"type": "state", "state": session.state.value})

        t_llm_start = time.perf_counter()
        t_first_token: Optional[float] = None
        t_first_sentence: Optional[float] = None
        t_first_audio_chunk: Optional[float] = None

        tool_schemas = get_all_tool_schemas()
        splitter = SentenceSplitter(min_words=3)

        full_assistant_response = []
        is_first_sentence = True

        try:
            token_stream = llm.generate_stream(
                session.conversation_history,
                tools=tool_schemas
            )

            async for token in token_stream:
                if session.abort_event.is_set():
                    logger.info("Turn aborted during LLM generation for session %s", session_id)
                    break

                if t_first_token is None:
                    t_first_token = time.perf_counter()

                full_assistant_response.append(token)
                ready_sentences = splitter.process_token(token)

                for sentence in ready_sentences:
                    if session.abort_event.is_set():
                        break

                    if t_first_sentence is None:
                        t_first_sentence = time.perf_counter()

                    # Synthesize and enqueue sentence
                    t_tts_start = time.perf_counter()
                    pcm_audio = await tts.synthesize(sentence)

                    if t_first_audio_chunk is None and pcm_audio:
                        t_first_audio_chunk = time.perf_counter()

                    if pcm_audio and not session.abort_event.is_set():
                        # Inform VAD detector that assistant is speaking (enables barge-in)
                        session.state = SessionState.AI_SPEAKING
                        session.detector.set_agent_speaking(True)
                        session.outbound_track.put_audio(pcm_audio, source_sample_rate=16000)

                        if is_first_sentence:
                            # Record and emit latency waterfall
                            t_delivery = time.perf_counter()
                            llm_ttft_ms = (t_first_token - t_llm_start) * 1000.0 if t_first_token else 0.0
                            sentence_ms = (t_first_sentence - t_first_token) * 1000.0 if (t_first_sentence and t_first_token) else 0.0
                            tts_chunk_ms = (t_first_audio_chunk - t_tts_start) * 1000.0 if t_first_audio_chunk else 0.0
                            total_turnaround_ms = (t_delivery - t0) * 1000.0

                            metrics = {
                                "type": "metrics",
                                "turn_id": f"turn_{int(t0)}",
                                "stt_latency_ms": round(stt_duration_ms, 1),
                                "llm_ttft_ms": round(llm_ttft_ms, 1),
                                "sentence_split_ms": round(sentence_ms, 1),
                                "tts_first_chunk_ms": round(tts_chunk_ms, 1),
                                "total_turnaround_ms": round(total_turnaround_ms, 1)
                            }
                            session.current_turn_metrics = metrics
                            session.send_event(metrics)
                            logger.info(
                                "Turn turnaround completed: %0.1f ms (STT=%0.1fms, TTFT=%0.1fms, TTS=%0.1fms)",
                                total_turnaround_ms, stt_duration_ms, llm_ttft_ms, tts_chunk_ms
                            )
                            is_first_sentence = False

            # Flush remaining tokens as final sentence
            if not session.abort_event.is_set():
                remaining_sentences = splitter.flush()
                for sentence in remaining_sentences:
                    if session.abort_event.is_set():
                        break
                    pcm_audio = await tts.synthesize(sentence)
                    if pcm_audio and not session.abort_event.is_set():
                        session.outbound_track.put_audio(pcm_audio, source_sample_rate=16000)

            # Record assistant response in conversation history
            complete_text = "".join(full_assistant_response).strip()
            if complete_text:
                session.conversation_history.append({"role": "assistant", "content": complete_text})
                session.send_event({
                    "type": "transcript",
                    "speaker": "assistant",
                    "text": complete_text,
                    "is_final": True,
                    "timestamp": time.time()
                })

        except Exception as e:
            logger.error("Error in turn execution for session %s: %s", session_id, e, exc_info=True)
        finally:
            if not session.outbound_track.has_pending_audio():
                session.detector.set_agent_speaking(False)
                session.state = SessionState.IDLE
                session.send_event({"type": "state", "state": session.state.value})
