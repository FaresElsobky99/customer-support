"""FastAPI wiring for the product agent.

``get_runner`` / ``get_rate_limiter`` are dependencies so tests can override them
(``app.dependency_overrides[...] = ...``).
"""

from __future__ import annotations

from functools import lru_cache

from backend.app.agent.llm.factory import get_llm
from backend.app.agent.ratelimit import RateLimiter, build_rate_limiter
from backend.app.agent.runner import AgentRunner
from backend.app.agent.tools.service_executor import ServiceToolExecutor


@lru_cache(maxsize=1)
def build_default_runner() -> AgentRunner:
    return AgentRunner(get_llm(), ServiceToolExecutor())


@lru_cache(maxsize=1)
def _default_rate_limiter() -> RateLimiter:
    return build_rate_limiter()


def get_runner() -> AgentRunner:
    return build_default_runner()


def get_rate_limiter() -> RateLimiter:
    return _default_rate_limiter()
