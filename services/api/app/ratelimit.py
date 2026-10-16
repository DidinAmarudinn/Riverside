"""In-memory sliding-window rate limits for the endpoints that cost a Gemini call (or create state).

Three layers, all per API instance (Cloud Run may run several, so the real ceiling is limit x instances):
  - per sandbox: one visitor cannot hammer the agents,
  - per client IP: rotating sandbox ids from one machine does not help,
  - per instance: a circuit breaker on spend when both of the above are spoofed (X-Forwarded-For is
    client-controllable at its first hop). It also means a determined attacker can lock honest visitors out,
    which is the better failure than an unbounded Gemini bill.
Limits come from env (RATE_LIMIT_*), 0 disables a layer.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Callable

WINDOW_S = 60.0


class SlidingWindow:
    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._calls = 0

    def retry_after(self, key: str, limit: int, window: float = WINDOW_S) -> int:
        """0 when the call is allowed (and recorded), else the seconds until the oldest hit expires."""
        if limit <= 0:
            return 0
        now = self._clock()
        hits = self._hits[key]
        while hits and now - hits[0] >= window:
            hits.popleft()
        if len(hits) >= limit:
            return max(1, int(window - (now - hits[0])) + 1)
        hits.append(now)
        self._calls += 1
        if self._calls % 500 == 0:
            self._sweep(now, window)
        return 0

    def _sweep(self, now: float, window: float) -> None:
        for key in [k for k, h in self._hits.items() if not h or now - h[-1] >= window]:
            del self._hits[key]

    def reset(self) -> None:
        self._hits.clear()


limiter = SlidingWindow()
