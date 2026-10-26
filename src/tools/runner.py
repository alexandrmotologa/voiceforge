"""Asynchronous tool execution coordinator with conversational filler injection."""

import asyncio
import inspect
import logging
import time
from typing import Dict, Any, Optional, Tuple, Callable
from .registry import TOOL_REGISTRY
from .fillers import get_vocal_filler

logger = logging.getLogger(__name__)


class ToolRunner:
    """Dispatches tool execution, handles vocal filler cues, and records duration."""

    def __init__(self, on_event: Optional[Callable[[Dict[str, Any]], None]] = None):
        self.on_event = on_event

    async def execute_tool(
        self,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Optional[str]]:
        """Execute a registered tool by name with arguments.

        Returns:
            A tuple of (tool_result_dict, filler_spoken_text)
        """
        tool_entry = TOOL_REGISTRY.get(tool_name)
        if not tool_entry:
            error_msg = f"Tool '{tool_name}' not found in registry"
            logger.error(error_msg)
            return {"error": error_msg, "status": "failed"}, None

        handler = tool_entry["handler"]
        filler = get_vocal_filler(tool_name, tool_entry.get("filler"))

        t0 = time.perf_counter()

        # Emit tool start event to client UI
        if self.on_event:
            self.on_event({
                "type": "tool_call",
                "status": "executing",
                "tool_name": tool_name,
                "arguments": arguments,
                "filler_spoken": filler
            })

        try:
            # Call handler (supporting both async coroutines and standard sync functions)
            if inspect.iscoroutinefunction(handler):
                result = await asyncio.wait_for(handler(**arguments), timeout=8.0)
            else:
                result = await asyncio.to_thread(handler, **arguments)
        except asyncio.TimeoutError:
            result = {"error": f"Tool '{tool_name}' timed out after 8 seconds", "status": "timeout"}
        except Exception as e:
            logger.error("Error executing tool %s: %s", tool_name, e)
            result = {"error": str(e), "status": "failed"}

        duration_ms = (time.perf_counter() - t0) * 1000.0

        # Emit tool completed event to client UI
        if self.on_event:
            self.on_event({
                "type": "tool_call",
                "status": "completed",
                "tool_name": tool_name,
                "result": result,
                "duration_ms": round(duration_ms, 2)
            })

        return result, filler
