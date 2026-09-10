"""In-process token-bucket rate limiter, keyed by customer id.

Bounds how often one authenticated customer can call the agent (each call is one or more
LLM requests). In-process only: with multiple backend replicas the effective limit is
per-replica. For this app that is acceptable; a shared store (Redis) would make it exact.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass


@dataclass
class _Bucket:
    tokens: float
    updated: float


class RateLimiter:
    def __init__(self, per_minute: int, burst: int) -> None:
        self._refill_per_sec = per_minute / 60.0
        self._capacity = float(max(1, burst))
        self._buckets: dict[int, _Bucket] = {}

    def check(self, customer_id: int) -> tuple[bool, float]:
        """Return (allowed, retry_after_seconds)."""
        now = time.monotonic()
        bucket = self._buckets.get(customer_id)

        if bucket is None:
            self._buckets[customer_id] = _Bucket(tokens=self._capacity - 1.0, updated=now)
            return True, 0.0

        bucket.tokens = min(
            self._capacity,
            bucket.tokens + (now - bucket.updated) * self._refill_per_sec,
        )
        bucket.updated = now

        if bucket.tokens >= 1.0:
            bucket.tokens -= 1.0
            return True, 0.0

        retry_after = (1.0 - bucket.tokens) / self._refill_per_sec
        return False, retry_after


def _int_env(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def build_rate_limiter() -> RateLimiter:
    return RateLimiter(
        per_minute=_int_env("AGENT_RATE_PER_MIN", 10),
        burst=_int_env("AGENT_RATE_BURST", 5),
    )
