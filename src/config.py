"""Configuration management for VoiceForge using pydantic-settings."""

from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Server Settings
    host: str = Field(default="0.0.0.0", description="Host address to bind the server")
    port: int = Field(default=8765, description="Port to listen for HTTP and WebRTC signaling")
    debug: bool = Field(default=False, description="Enable debug logging and verbose tracing")

    # Audio Standards
    audio_sample_rate: int = Field(default=16000, description="Internal linear PCM sample rate in Hz")
    webrtc_sample_rate: int = Field(default=48000, description="WebRTC Opus audio sample rate in Hz")
    webrtc_frame_duration_ms: int = Field(default=20, description="WebRTC Opus packet duration in milliseconds")

    # Silero VAD Settings
    vad_model_path: Path = Field(
        default=ROOT_DIR / "src" / "vad" / "models" / "silero_vad.onnx",
        description="Path to the Silero VAD v5 ONNX model file"
    )
    vad_threshold: float = Field(default=0.5, description="Speech probability threshold (0.0 to 1.0)")
    vad_speech_pad_frames: int = Field(default=2, description="Consecutive speech frames required to confirm speech")
    vad_silence_timeout_ms: int = Field(default=150, description="Silence duration in ms to trigger turn completion")

    # Default Providers
    default_stt_provider: Literal["deepgram", "whisper_local", "fallback"] = Field(
        default="fallback", description="Default Speech-to-Text provider"
    )
    default_llm_provider: Literal["anthropic", "openai", "ollama", "fallback"] = Field(
        default="fallback", description="Default Large Language Model provider"
    )
    default_tts_provider: Literal["cartesia", "elevenlabs", "native"] = Field(
        default="native", description="Default Text-to-Speech provider"
    )

    # API Keys for Cloud Providers
    deepgram_api_key: str = Field(default="", description="Deepgram API key for streaming Nova-2 STT")
    anthropic_api_key: str = Field(default="", description="Anthropic API key for streaming Claude 3.5")
    openai_api_key: str = Field(default="", description="OpenAI API key for GPT-4o streaming")
    cartesia_api_key: str = Field(default="", description="Cartesia API key for Sonic streaming TTS")
    elevenlabs_api_key: str = Field(default="", description="ElevenLabs API key for streaming TTS")

    # Local LLM (Ollama / vLLM)
    ollama_base_url: str = Field(default="http://localhost:11434/v1", description="OpenAI-compatible local endpoint")
    ollama_model: str = Field(default="llama3.1:8b", description="Model name for local LLM inference")

    # Voice Personality
    system_prompt: str = Field(
        default=(
            "You are VoiceForge, an ultra-fast, conversational AI voice assistant. "
            "Speak naturally in clear, concise sentences. Avoid markdown formatting, "
            "bullet points, or citations since your response will be synthesized directly into speech. "
            "Keep each sentence conversational and punchy."
        ),
        description="Default conversational voice system prompt"
    )


settings = Settings()
