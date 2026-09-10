"""Hermetic tests for the product agent.

Unlike the rest of ``tests/``, these hit no database and no LLM provider — the LLM and the
tool executor are fakes. This file is the template for future agent tests.
"""

import asyncio

from fastapi.testclient import TestClient

from backend.app.agent.auth import AuthContext
from backend.app.agent.deps import get_rate_limiter, get_runner
from backend.app.agent.llm.base import LLMRateLimitError
from backend.app.agent.llm.openrouter import (
    _parse_response,
    _to_openai_messages,
    _to_openai_tool,
)
from backend.app.agent.runner import AgentRunner
from backend.app.agent.tools.service_executor import ServiceToolExecutor
from backend.app.agent.types import LLMResponse, Message, ToolCall, ToolDef, ToolResult
from backend.app.api_main import app
from backend.app.auth.jwt import create_token


class FakeLLM:
    """Replays scripted responses; if it runs out, repeats the last one."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    async def generate(self, *, system, messages, tools):
        self.calls.append({"system": system, "messages": list(messages), "tools": list(tools)})
        if len(self._responses) > 1:
            return self._responses.pop(0)
        return self._responses[0]


class RaisingLLM:
    def __init__(self, error):
        self._error = error

    async def generate(self, *, system, messages, tools):
        raise self._error


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def tool_defs(self, auth):
        defs = [ToolDef("create_ticket", "open a ticket", {"type": "object", "properties": {}})]
        if auth.is_admin:
            defs.append(ToolDef("list_all_customers", "admin", {"type": "object", "properties": {}}))
        return defs

    async def execute(self, call, auth):
        self.calls.append((call.name, dict(call.arguments), auth))
        return ToolResult(call.id, call.name, '{"ticket_id": 1, "status": "open"}', is_error=False)


CUSTOMER = AuthContext(customer_id=7, role="customer")
ADMIN = AuthContext(customer_id=1, role="admin")


def test_returns_text_when_no_tool_calls():
    runner = AgentRunner(FakeLLM([LLMResponse(text="hello", tool_calls=())]), FakeExecutor())

    result = asyncio.run(runner.run(auth=CUSTOMER, history=[], user_message="hi"))

    assert result.reply == "hello"
    assert result.steps == 1
    assert result.stopped_reason == "final"
    assert result.tool_calls == []


def test_executes_tool_then_finalizes():
    llm = FakeLLM(
        [
            LLMResponse(text=None, tool_calls=(ToolCall("c0", "create_ticket", {"issue": "x"}),)),
            LLMResponse(text="done", tool_calls=()),
        ]
    )
    executor = FakeExecutor()
    runner = AgentRunner(llm, executor)

    result = asyncio.run(runner.run(auth=CUSTOMER, history=[], user_message="open a ticket"))

    assert result.reply == "done"
    assert result.tool_calls == ["create_ticket"]
    # identity came from AuthContext, never from the model
    name, args, auth = executor.calls[0]
    assert auth.customer_id == 7 and auth.role == "customer"
    assert "customer_id" not in args and "token" not in args


def test_stops_at_max_steps_without_running_tools_on_the_final_step():
    always_calls = LLMResponse(text=None, tool_calls=(ToolCall("c", "create_ticket", {"issue": "x"}),))
    executor = FakeExecutor()
    runner = AgentRunner(FakeLLM([always_calls]), executor, max_steps=3)

    result = asyncio.run(runner.run(auth=CUSTOMER, history=[], user_message="loop"))

    assert result.stopped_reason == "max_steps"
    assert result.steps == 3
    # 3 LLM calls, but the tool call on the final step is NOT executed (no phantom
    # side effects after telling the user we couldn't finish).
    assert len(executor.calls) == 2
    assert len(result.tool_calls) == 2


def test_rate_limit_is_a_friendly_reply():
    runner = AgentRunner(RaisingLLM(LLMRateLimitError("429")), FakeExecutor())

    result = asyncio.run(runner.run(auth=CUSTOMER, history=[], user_message="hi"))

    assert result.stopped_reason == "rate_limited"
    assert "try again" in result.reply.lower()


def test_generic_llm_error_is_a_friendly_reply_not_a_crash():
    from backend.app.agent.llm.base import LLMError

    runner = AgentRunner(RaisingLLM(LLMError("model retired: HTTP 404")), FakeExecutor())

    result = asyncio.run(runner.run(auth=CUSTOMER, history=[], user_message="hi"))

    assert result.stopped_reason == "error"
    assert "try again" in result.reply.lower()
    assert "404" not in result.reply  # no upstream detail leaked to the customer


def test_service_executor_hides_admin_tools_from_customers():
    executor = ServiceToolExecutor()

    customer_tools = {t.name for t in executor.tool_defs(CUSTOMER)}
    admin_tools = {t.name for t in executor.tool_defs(ADMIN)}

    assert {"list_all_customers", "update_ticket_status"}.isdisjoint(customer_tools)
    assert {"list_all_customers", "update_ticket_status"} <= admin_tools
    assert {"get_customer", "create_ticket", "list_tickets", "get_ticket"} <= customer_tools
    # no tool ever exposes identity arguments
    for tool in executor.tool_defs(ADMIN):
        assert "token" not in tool.parameters.get("properties", {})
        assert "customer_id" not in tool.parameters.get("properties", {})


def test_service_executor_rejects_admin_tool_call_from_a_customer():
    executor = ServiceToolExecutor()
    call = ToolCall("x", "update_ticket_status", {"ticket_id": 1, "status": "closed"})

    result = asyncio.run(executor.execute(call, CUSTOMER))

    assert result.is_error
    assert "Admin access required" in result.content


def test_rate_limiter_allows_burst_then_blocks():
    from backend.app.agent.ratelimit import RateLimiter

    limiter = RateLimiter(per_minute=60, burst=3)

    allowed = [limiter.check(customer_id=42)[0] for _ in range(5)]
    assert allowed == [True, True, True, False, False]
    # a different customer has their own bucket
    assert limiter.check(customer_id=99)[0] is True

    _, retry_after = limiter.check(customer_id=42)
    assert retry_after > 0


class _AllowAll:
    def check(self, customer_id):
        return True, 0.0


def _override(runner=None, limiter=None):
    if runner is not None:
        app.dependency_overrides[get_runner] = lambda: runner
    app.dependency_overrides[get_rate_limiter] = lambda: limiter or _AllowAll()


def _clear_overrides():
    app.dependency_overrides.pop(get_runner, None)
    app.dependency_overrides.pop(get_rate_limiter, None)


def test_chat_endpoint_with_faked_runner():
    llm = FakeLLM(
        [
            LLMResponse(text=None, tool_calls=(ToolCall("c0", "create_ticket", {"issue": "app crashes"}),)),
            LLMResponse(text="I've opened a ticket for you.", tool_calls=()),
        ]
    )
    _override(runner=AgentRunner(llm, FakeExecutor()))
    try:
        client = TestClient(app)
        token = create_token(7, "customer")

        first = client.post(
            "/agent/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "my app crashes on login"},
        )
        assert first.status_code == 200
        body = first.json()
        assert body["reply"] == "I've opened a ticket for you."
        assert body["tool_calls"] == ["create_ticket"]
        assert [t["role"] for t in body["history"]] == ["user", "assistant"]

        second = client.post(
            "/agent/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "thanks", "history": body["history"]},
        )
        assert second.status_code == 200
        assert len(second.json()["history"]) == 4
    finally:
        _clear_overrides()


def test_chat_endpoint_rate_limits_per_customer():
    from backend.app.agent.ratelimit import RateLimiter

    llm = FakeLLM([LLMResponse(text="ok", tool_calls=())])
    _override(runner=AgentRunner(llm, FakeExecutor()), limiter=RateLimiter(per_minute=60, burst=2))
    try:
        client = TestClient(app)
        token = create_token(7, "customer")
        codes = [
            client.post(
                "/agent/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"message": "hi"},
            ).status_code
            for _ in range(4)
        ]
        assert codes == [200, 200, 429, 429]
    finally:
        _clear_overrides()


def test_chat_endpoint_requires_auth():
    client = TestClient(app)
    response = client.post("/agent/chat", json={"message": "hi"})
    assert response.status_code in (401, 403)


def test_chat_endpoint_rejects_oversized_history():
    _override(runner=AgentRunner(FakeLLM([LLMResponse(text="x", tool_calls=())]), FakeExecutor()))
    try:
        client = TestClient(app)
        token = create_token(7, "customer")
        huge = [{"role": "user", "content": "x"} for _ in range(500)]
        response = client.post(
            "/agent/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"message": "hi", "history": huge},
        )
        assert response.status_code == 422
    finally:
        _clear_overrides()


def test_mcp_executor_is_error_only_on_error_key():
    from backend.app.agent.tools.mcp_executor import _is_error_payload

    # a real error payload
    assert _is_error_payload('{"error": "Not authorized"}') is True
    # a successful result whose text merely contains the word error
    assert _is_error_payload('{"tickets": [{"issue": "error", "status": "open"}]}') is False
    # non-JSON tool output
    assert _is_error_payload("Hello, how can I help?") is False


# --- OpenRouter translation (pure functions, no network) ---


def test_openrouter_tool_translation():
    tool = ToolDef("create_ticket", "open a ticket", {"type": "object", "properties": {}})
    result = _to_openai_tool(tool)
    assert result == {
        "type": "function",
        "function": {
            "name": "create_ticket",
            "description": "open a ticket",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def test_openrouter_message_translation_round_trips_tool_turns():
    messages = [
        Message(role="user", text="open a ticket"),
        Message(
            role="assistant",
            text=None,
            tool_calls=(ToolCall("call_1", "create_ticket", {"issue": "x"}),),
        ),
        Message(
            role="tool",
            tool_results=(ToolResult("call_1", "create_ticket", '{"ticket_id": 1}', False),),
        ),
    ]

    out = _to_openai_messages("SYSTEM", messages)

    assert out[0] == {"role": "system", "content": "SYSTEM"}
    assert out[1] == {"role": "user", "content": "open a ticket"}
    assert out[2]["role"] == "assistant"
    assert out[2]["tool_calls"][0]["id"] == "call_1"
    assert out[2]["tool_calls"][0]["function"]["name"] == "create_ticket"
    assert out[3] == {
        "role": "tool",
        "tool_call_id": "call_1",
        "content": '{"ticket_id": 1}',
    }


def test_openrouter_parses_tool_call_response():
    body = {
        "choices": [
            {
                "message": {
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc",
                            "function": {
                                "name": "list_tickets",
                                "arguments": '{"status": "open"}',
                            },
                        }
                    ],
                }
            }
        ]
    }
    response = _parse_response(body)
    assert response.text is None
    assert response.tool_calls[0].id == "call_abc"
    assert response.tool_calls[0].name == "list_tickets"
    assert response.tool_calls[0].arguments == {"status": "open"}


def test_openrouter_surfaces_rate_limit_in_200_body():
    body = {"error": {"code": 429, "message": "rate limited, retry later"}}
    try:
        _parse_response(body)
    except LLMRateLimitError:
        pass
    else:
        raise AssertionError("expected LLMRateLimitError")
