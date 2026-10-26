"""Natural conversational vocal filler generation."""

import random
from typing import Optional

# Curated natural filler phrases that prevent conversational dead air
FILLERS = {
    "weather": [
        "Checking current conditions for you right now.",
        "Looking up the latest weather report.",
        "Let me pull up the forecast for that area."
    ],
    "time": [
        "Checking the clock right now.",
        "Looking up the current time."
    ],
    "calculate": [
        "Running that calculation for you.",
        "Let me compute that right now.",
        "Calculating the result."
    ],
    "system": [
        "Querying the internal system diagnostics.",
        "Checking the server status and audio tracks."
    ],
    "default": [
        "Looking into that for you right now.",
        "One second while I check that.",
        "Let me pull up that information."
    ]
}


def get_vocal_filler(tool_name: str, custom_filler: Optional[str] = None) -> str:
    """Return a natural vocal filler sentence appropriate for the given tool."""
    if custom_filler:
        return custom_filler

    lower_name = tool_name.lower()
    for key, options in FILLERS.items():
        if key in lower_name:
            return random.choice(options)

    return random.choice(FILLERS["default"])
