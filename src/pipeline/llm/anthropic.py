"""Anthropic Claude streaming client for low-latency conversational voice."""

import json
import logging
from typing import AsyncIterator, List, Dict, Any, Optional
import httpx
from .base import BaseLLM
from .fallback import FallbackLLM
from ...config import settings

logger = logging.getLogger(__name__)


class AnthropicLLM(BaseLLM):
    """Streams tokens from Anthropic Claude models via SSE."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-5-sonnet-20241022"):
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model
        self._fallback = FallbackLLM()

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]:
        """Stream response tokens from Claude."""
        if not self.api_key:
            logger.info("Anthropic API key not configured, using fallback LLM")
            async for token in self._fallback.generate_stream(messages, tools):
                yield token
            return

        # Prepare messages in Anthropic format (extract system message)
        system_content = settings.system_prompt
        chat_messages = []
        for m in messages:
            if m.get("role") == "system":
                system_content = m.get("content", system_content)
            else:
                chat_messages.append({"role": m["role"], "content": m["content"]})

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }

        payload = {
            "model": self.model,
            "max_tokens": 300,
            "system": system_content,
            "messages": chat_messages,
            "stream": True
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                async with client.stream("POST", self.API_URL, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            raw_data = line[6:].strip()
                            if raw_data == "[DONE]":
                                break
                            try:
                                event = json.loads(raw_data)
                                if event.get("type") == "content_block_delta":
                                    delta = event.get("delta", {})
                                    if delta.get("type") == "text_delta":
                                        yield delta.get("text", "")
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error("Anthropic streaming failed: %s, using fallback", e)
            async for token in self._fallback.generate_stream(messages, tools):
                yield token
