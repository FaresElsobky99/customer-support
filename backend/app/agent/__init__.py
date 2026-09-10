"""Customer-facing product agent: an LLM in a tool loop over the support service layer.

See docs/agentic-ai.md for the full picture. Entry points:

- ``AgentRunner`` (runner.py) — the loop.
- ``get_llm`` (llm/factory.py) — provider selection.
- ``ServiceToolExecutor`` (tools/service_executor.py) — the tools, scoped to the caller.
"""
