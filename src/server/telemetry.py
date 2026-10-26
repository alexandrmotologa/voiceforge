"""Telemetry broadcaster and metrics tracking for voice sessions."""

import asyncio
import json
import logging
import time
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class TelemetryBroadcaster:
    """Collects and broadcasts real-time latency and state telemetry via SSE or events."""

    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    def record_metrics(self, session_id: str, metrics: Dict[str, Any]) -> None:
        """Store metrics record in memory."""
        record = {
            "session_id": session_id,
            "timestamp": time.time(),
            **metrics
        }
        self._history.append(record)
        if len(self._history) > 500:
            self._history.pop(0)

    def get_recent_metrics(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return the most recent metrics records."""
        return self._history[-limit:]


telemetry_broadcaster = TelemetryBroadcaster()
