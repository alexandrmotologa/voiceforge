"""Decorator and schema registry for conversational tool calling."""

import inspect
from typing import Callable, Dict, Any, Optional

# Global tool registry mapping tool name to tool metadata and handler
TOOL_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    filler: Optional[str] = None
):
    """Decorator to register a python function as a callable conversational tool."""
    def decorator(func: Callable):
        tool_name = name or func.__name__
        tool_desc = description or (func.__doc__ or "").strip()

        # Generate JSON schema from function signature
        sig = inspect.signature(func)
        properties = {}
        required = []

        for param_name, param in sig.parameters.items():
            if param_name in ["self", "cls"]:
                continue

            param_type = "string"
            if param.annotation == int:
                param_type = "integer"
            elif param.annotation == float:
                param_type = "number"
            elif param.annotation == bool:
                param_type = "boolean"
            elif param.annotation == list:
                param_type = "array"
            elif param.annotation == dict:
                param_type = "object"

            properties[param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}"
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)

        schema = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool_desc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

        TOOL_REGISTRY[tool_name] = {
            "name": tool_name,
            "description": tool_desc,
            "filler": filler,
            "handler": func,
            "schema": schema
        }

        return func

    return decorator


def get_all_tool_schemas() -> list:
    """Return a list of all registered tool schemas formatted for LLMs."""
    return [t["schema"] for t in TOOL_REGISTRY.values()]
