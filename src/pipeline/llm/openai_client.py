"""OpenAI GPT-4o streaming client for conversational voice."""

import json
import logging
from typing import AsyncIterator, List, Dict, Any, Optional
import httpx
from .base import BaseLLM
from .fallback import FallbackLLM
from ...config import settings

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    """Streams tokens from OpenAI chat completion models via SSE."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o-mini"):
        self.api_key = api_key or settings.openai_api_key
        self.model = model
        self._fallback = FallbackLLM()

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]:
        """Stream response tokens from OpenAI."""
        if not self.api_key:
            logger.info("OpenAI API key not configured, using fallback LLM")
            async for token in self._fallback.generate_stream(messages, tools):
                yield token
            return

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": 300
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
                                chunk = json.loads(raw_data)
                                choices = chunk.get("choices", [])
                                if choices:
                                    delta = choices[0].get("delta", {})
                                    content = delta.get("content")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.error("OpenAI streaming failed: %s, using fallback", e)
            async for token in self._fallback.generate_stream(messages, tools):
                yield token
