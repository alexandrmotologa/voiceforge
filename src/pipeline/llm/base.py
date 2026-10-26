"""Abstract base class for Large Language Model (LLM) streaming engines."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, List, Dict, Any, Optional


class BaseLLM(ABC):
    """Abstract interface for streaming conversational LLM backends."""

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> AsyncIterator[str]:
        """Stream conversational response tokens.

        Args:
            messages: Conversation history list of {'role': str, 'content': str}.
            tools: Optional list of tool schema definitions for function calling.

        Yields:
            Token text chunks as they arrive from the language model.
        """
        pass
