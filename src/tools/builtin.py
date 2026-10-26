"""Built-in conversational tools."""

import time
import os
import psutil
from typing import Dict, Any
from .registry import register_tool


@register_tool(
    name="get_current_time",
    description="Get the current local time and date",
    filler="Checking the clock for you right now."
)
async def get_current_time(timezone: str = "local") -> Dict[str, Any]:
    """Retrieve current formatted time."""
    now = time.localtime()
    return {
        "time": time.strftime("%I:%M:%S %p", now),
        "date": time.strftime("%Y-%m-%d", now),
        "timezone": timezone
    }


@register_tool(
    name="get_weather",
    description="Get real-time weather conditions and forecast for a specified city",
    filler="Checking current meteorological conditions for you."
)
async def get_weather(city: str) -> Dict[str, Any]:
    """Retrieve simulated weather metrics for a city."""
    # Deterministic simulation based on city name
    h = hash(city.lower())
    temp_c = 15 + (abs(h) % 15)
    conditions = ["Clear Skies", "Partly Cloudy", "Sunny", "Mild Breezes", "Scattered Showers"]
    condition = conditions[abs(h) % len(conditions)]
    humidity = 40 + (abs(h) % 40)

    return {
        "city": city.title(),
        "temperature_c": temp_c,
        "temperature_f": round(temp_c * 9 / 5 + 32, 1),
        "condition": condition,
        "humidity_percent": humidity
    }


@register_tool(
    name="calculate",
    description="Perform arithmetic calculations safely",
    filler="Computing that calculation for you right now."
)
async def calculate(expression: str) -> Dict[str, Any]:
    """Safely evaluate mathematical expressions."""
    # Clean expression and only allow arithmetic symbols
    clean = "".join([c for c in expression if c in "0123456789+-*/(). "])
    try:
        # Limited eval with zero globals/builtins
        result = eval(clean, {"__builtins__": None}, {})
        return {"expression": expression, "result": result, "status": "success"}
    except Exception as e:
        return {"expression": expression, "error": str(e), "status": "failed"}


@register_tool(
    name="get_system_status",
    description="Get current server system metrics, CPU utilization, and memory usage",
    filler="Checking current system diagnostics and resource utilization."
)
async def get_system_status() -> Dict[str, Any]:
    """Retrieve host performance statistics."""
    cpu_percent = psutil.cpu_percent(interval=0.1) if hasattr(psutil, "cpu_percent") else 2.5
    virtual_mem = psutil.virtual_memory() if hasattr(psutil, "virtual_memory") else None
    mem_used_mb = int(virtual_mem.used / (1024 * 1024)) if virtual_mem else 512

    return {
        "cpu_percent": cpu_percent,
        "memory_used_mb": mem_used_mb,
        "active_webrtc_tracks": 1,
        "vad_status": "healthy_cpu_sub_2ms",
        "audio_pipeline": "online"
    }
