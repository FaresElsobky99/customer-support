"""POST /agent/chat — the customer-facing self-service agent.

Stateless: the client sends the running transcript in ``history`` and stores the
``history`` returned in the response for the next turn. No server-side session store, so
this is correct across multiple replicas and survives redeploys.
"""

from __future__ import annotations

import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from backend.app.agent.auth import AuthContext
from backend.app.agent.deps import get_rate_limiter, get_runner
from backend.app.agent.observability import log_agent_run
from backend.app.agent.ratelimit import RateLimiter
from backend.app.agent.runner import AgentRunner
from backend.app.agent.types import Message
from backend.app.api.dependencies import get_current_user

router = APIRouter(prefix="/agent", tags=["agent"])

_MAX_HISTORY_TURNS = 40
_MAX_TURN_CHARS = 8000


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(max_length=_MAX_TURN_CHARS)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=200)


class ChatResponse(BaseModel):
    reply: str
    history: list[ChatTurn]
    tool_calls: list[str]
    stopped_reason: str


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    response: Response,
    user: dict = Depends(get_current_user),
    runner: AgentRunner = Depends(get_runner),
    rate_limiter: RateLimiter = Depends(get_rate_limiter),
) -> ChatResponse:
    allowed, retry_after = rate_limiter.check(user["customer_id"])
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please slow down.",
            headers={"Retry-After": str(int(retry_after) + 1)},
        )

    auth = AuthContext(customer_id=user["customer_id"], role=user["role"])

    prior = request.history[-_MAX_HISTORY_TURNS:]
    history = [Message(role=turn.role, text=turn.content) for turn in prior]

    started = time.monotonic()
    result = await runner.run(auth=auth, history=history, user_message=request.message)
    duration_ms = int((time.monotonic() - started) * 1000)

    log_agent_run(
        customer_id=user["customer_id"],
        role=user["role"],
        result=result,
        duration_ms=duration_ms,
        message_chars=len(request.message),
    )

    turns = list(prior)
    turns.append(ChatTurn(role="user", content=request.message))
    turns.append(ChatTurn(role="assistant", content=result.reply))

    response.headers["X-Agent-Stopped-Reason"] = result.stopped_reason
    return ChatResponse(
        reply=result.reply,
        history=turns,
        tool_calls=result.tool_calls,
        stopped_reason=result.stopped_reason,
    )
