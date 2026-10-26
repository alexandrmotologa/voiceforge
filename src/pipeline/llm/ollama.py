"""Local Ollama and vLLM OpenAI-compatible streaming LLM client."""

import json
import logging
from typing import AsyncIterator, List, Dict, Any, Optional
import httpx
from .base import BaseLLM
from .fallback import FallbackLLM
from ...config import settings

logger = logging.getLogger(__name__)


class OllamaLLM(BaseLLM):
    """Streams tokens from local Ollama or vLLM instances."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self._fallback = FallbackLLM()

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]:
        """Stream tokens from local Ollama endpoint."""
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "max_tokens": 300
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                async with client.stream("POST", endpoint, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            raw = line[6:].strip()
                            if raw == "[DONE]":
                                break
                            try:
                                chunk = json.loads(raw)
                                choices = chunk.get("choices", [])
                                if choices:
                                    content = choices[0].get("delta", {}).get("content")
                                    if content:
                                        yield content
                            except json.JSONDecodeError:
                                continue
        except Exception as e:
            logger.info("Ollama connection unreachable at %s: %s, using fallback", endpoint, e)
            async for token in self._fallback.generate_stream(messages, tools):
                yield token
