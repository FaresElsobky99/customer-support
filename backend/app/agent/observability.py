"""One structured log line per agent run, for debugging and cost tracking.

Emitted at INFO on the ``customer_support.agent`` logger, which uvicorn surfaces at its
default log level. No message content is logged — only shape and outcome.
"""

from __future__ import annotations

import json
import logging
import os

from backend.app.agent.runner import AgentResult

logger = logging.getLogger("customer_support.agent")


def log_agent_run(
    *,
    customer_id: int,
    role: str,
    result: AgentResult,
    duration_ms: int,
    message_chars: int,
) -> None:
    provider = (os.getenv("LLM_PROVIDER") or "gemini").lower()
    model = os.getenv("OPENROUTER_MODEL" if provider == "openrouter" else "GEMINI_MODEL")

    logger.info(
        json.dumps(
            {
                "event": "agent_run",
                "customer_id": customer_id,
                "role": role,
                "provider": provider,
                "model": model,
                "steps": result.steps,
                "stopped_reason": result.stopped_reason,
                "tool_calls": result.tool_calls,
                "duration_ms": duration_ms,
                "message_chars": message_chars,
            }
        )
    )
