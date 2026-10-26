"""Sub-80ms barge-in interruption coordinator for cutting AI playback upon user speech."""

import time
import logging
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)


class BargeInController:
    """Coordinates instant audio playback cutoff and downstream task cancellation."""

    def __init__(
        self,
        on_interrupt_action: Optional[Callable[[], Any]] = None,
        on_notify_client: Optional[Callable[[dict], Any]] = None
    ):
        self.on_interrupt_action = on_interrupt_action
        self.on_notify_client = on_notify_client
        self.last_interrupt_time: float = 0.0
        self.last_latency_ms: float = 0.0

    def trigger(self, speech_probability: float, onset_time: Optional[float] = None) -> float:
        """Execute the barge-in cancellation protocol.

        Args:
            speech_probability: Probability that triggered the interruption.
            onset_time: Optional timestamp when the first speech frame was detected.

        Returns:
            Measured latency in milliseconds from detection to completion.
        """
        t0 = onset_time if onset_time else time.perf_counter()
        logger.info("Executing barge-in cutoff (speech_prob=%.3f)", speech_probability)

        # 1. Execute immediate queue flush and cancellation
        if self.on_interrupt_action:
            try:
                self.on_interrupt_action()
            except Exception as e:
                logger.error("Error executing interrupt action: %s", e)

        # 2. Calculate latency
        t_now = time.perf_counter()
        latency_ms = (t_now - t0) * 1000.0
        self.last_interrupt_time = time.time()
        self.last_latency_ms = latency_ms

        # 3. Notify connected client via data channel
        payload = {
            "type": "barge_in",
            "timestamp": self.last_interrupt_time,
            "latency_ms": round(latency_ms, 2),
            "speech_prob": round(speech_probability, 3)
        }

        if self.on_notify_client:
            try:
                self.on_notify_client(payload)
            except Exception as e:
                logger.error("Error notifying client of barge-in: %s", e)

        logger.info("Barge-in completed in %.2f ms", latency_ms)
        return latency_ms
