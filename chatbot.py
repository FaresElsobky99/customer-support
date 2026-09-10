"""Gemini + MCP customer-support chatbot (CLI).

Thin shell around the shared agent core:

- MCP wiring lives here (spawn the server over stdio, log in, discover tools) so the
  protocol stays visible — see docs/agentic-ai.md §2.
- The loop, the system prompt, provider handling, and rate-limit handling live in
  ``backend/app/agent/`` and are shared with ``POST /agent/chat``.
"""

import asyncio
import json
import sys

from mcp import Client, StdioServerParameters
from mcp.client.stdio import stdio_client

from backend.app.agent.auth import AuthContext
from backend.app.agent.llm.factory import get_llm
from backend.app.agent.runner import AgentRunner
from backend.app.agent.tools.mcp_executor import McpToolExecutor
from backend.app.agent.types import Message


async def main() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "backend.app.main"],
    )
    mcp_client = Client(stdio_client(params))

    async with mcp_client:
        # --- Login (handled by the app, never by the model) ---
        print("=== Login ===")
        email = input("Email: ")
        password = input("Password: ")

        login_result = await mcp_client.call_tool(
            "login", {"email": email, "password": password}
        )
        if not login_result.content:
            print("Login failed: empty response")
            return

        login_data = json.loads(login_result.content[0].text)
        if "error" in login_data:
            print(f"Login failed: {login_data['error']}")
            return

        auth = AuthContext(
            customer_id=login_data["customer_id"],
            role=login_data["role"],
            token=login_data["token"],
        )
        print(f"\nLogged in as customer {auth.customer_id} ({auth.role}).")

        # --- Discover MCP tools and build the agent ---
        tools_response = await mcp_client.list_tools()
        executor = McpToolExecutor(mcp_client, tools_response.tools)
        runner = AgentRunner(get_llm(), executor)

        print("\nCustomer Support Agent. Type 'exit' to stop.")
        history: list[Message] = []

        while True:
            user_query = input("\nYou: ")
            if user_query.lower() in {"exit", "quit"}:
                print("Assistant: Goodbye!")
                break

            result = await runner.run(
                auth=auth, history=history, user_message=user_query
            )
            history = result.history

            if result.tool_calls:
                print(f"[tools: {', '.join(result.tool_calls)}]")
            print(f"\nAssistant: {result.reply}")


if __name__ == "__main__":
    asyncio.run(main())
