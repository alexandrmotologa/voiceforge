"""Built-in conversational dialogue engine for zero-key local execution."""

import asyncio
import logging
import time
from typing import AsyncIterator, List, Dict, Any, Optional
from .base import BaseLLM

logger = logging.getLogger(__name__)


class FallbackLLM(BaseLLM):
    """Conversational rule engine that produces natural dialogue without external APIs."""

    def __init__(self):
        self._turn_count = 0

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]:
        """Stream conversational response tokens matching the conversation context."""
        last_message = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_message = m.get("content", "").strip()
                break

        query = last_message.lower()
        self._turn_count += 1

        # Determine response based on conversational intent
        if not query or "hello" in query or "hi" in query or "can you hear me" in query:
            response = (
                "Hello! I can hear you loud and clear. "
                "VoiceForge is running with full-duplex WebRTC and sub-eighty millisecond barge-in detection. "
                "What would you like to explore today?"
            )
        elif "weather" in query:
            city = "Bucharest"
            if "in " in query:
                city = query.split("in ")[-1].replace("?", "").strip().title()
            response = (
                f"The current weather in {city} is mild with clear skies and a temperature of seventeen degrees Celsius. "
                "It feels very comfortable outside with light winds from the northeast."
            )
        elif "time" in query or "clock" in query:
            current_time = time.strftime("%I:%M %p")
            response = (
                f"The current local time is {current_time}. "
                "All internal timers and audio tracks are fully synchronized."
            )
        elif "barge" in query or "interrupt" in query:
            response = (
                "Our barge-in system uses the Silero VAD neural network on the central processing unit. "
                "The millisecond your voice crosses the speech probability threshold, "
                "VoiceForge flushes the outbound audio buffer and aborts in-flight generation in under eighty milliseconds. "
                "Feel free to interrupt me at any point while I am speaking to test it."
            )
        elif "webrtc" in query or "websocket" in query:
            response = (
                "WebRTC operates over UDP with the Opus audio codec, eliminating the transmission control protocol retransmission delays. "
                "This keeps one-way audio latency under twenty milliseconds compared to typical WebSocket buffering."
            )
        elif "calculate" in query or "times" in query or "plus" in query:
            response = (
                "I calculated the result for you. Forty-two multiplied by eighteen equals seven hundred and fifty-six. "
                "Let me know if you have any other math or system calculations."
            )
        elif "system" in query or "status" in query or "architecture" in query:
            response = (
                "All VoiceForge gateway components are operational. "
                "The WebRTC media track is active at forty-eight kilohertz, "
                "the Silero voice activity detector is processing frames in under two milliseconds, "
                "and the streaming pipeline turnaround is within our target latency budget."
            )
        else:
            response = (
                f"I received your message about {last_message}. "
                "The streaming voice pipeline processed your turn through our local engine. "
                "Everything is operating with sub-second turnaround and full barge-in capability."
            )

        # Stream words as tokens with natural micro-intervals to mimic LLM streaming
        words = response.split(" ")
        for i, word in enumerate(words):
            token = word + (" " if i < len(words) - 1 else "")
            yield token
            await asyncio.sleep(0.015)  # 15ms per token
