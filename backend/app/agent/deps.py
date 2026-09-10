"""FastAPI wiring for the product agent.

``get_runner`` is a dependency so tests can override it
(``app.dependency_overrides[get_runner] = ...``) with a runner built on a fake LLM.
"""

from __future__ import annotations

from functools import lru_cache

from backend.app.agent.llm.factory import get_llm
from backend.app.agent.runner import AgentRunner
from backend.app.agent.tools.service_executor import ServiceToolExecutor


@lru_cache(maxsize=1)
def build_default_runner() -> AgentRunner:
    return AgentRunner(get_llm(), ServiceToolExecutor())


def get_runner() -> AgentRunner:
    return build_default_runner()
