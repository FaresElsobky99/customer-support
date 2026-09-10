# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Overview

A customer-support system with a shared Python business core exposed two ways:

- an **MCP stdio server** (`backend/app/mcp/`) for AI clients;
- a **FastAPI REST API** (`backend/app/api/`) for the Angular dashboard (`frontend/`).

Both transports call the same **service layer** (`backend/app/services/`), which calls
**repositories** (`backend/app/database/repositories/`, raw psycopg3), which talk to
PostgreSQL (Supabase). Protected actions are written to `audit_logs`.

There is also a runtime **product agent** (`backend/app/agent/`, exposed at
`POST /agent/chat`) — a customer-facing self-service assistant — and `chatbot.py`, a CLI
Gemini chatbot that drives the MCP server. See `docs/agentic-ai.md` for how the AI pieces
fit together.

## Commands

```bash
uv sync --frozen                                            # install deps

uv run uvicorn backend.app.api_main:app --reload            # REST API on :8000 (/docs, /health)
uv run python -m backend.app.main                           # MCP server (stdio; waits silently)
uv run python client.py                                     # scripted MCP client
uv run python chatbot.py                                    # Gemini CLI chatbot

uv run pytest tests/ -m "not integration"                   # fast tests (CI gate)
uv run pytest tests/integration/ -m integration             # DB integration tests
uv run pytest tests/test_agent.py -v                        # hermetic agent tests

cd frontend && npm install && npm start                     # Angular dev server on :4200
cd frontend && npm run build                                # production bundle
```

## Architecture

```
MCP tools (backend/app/mcp/)  ─┐
REST routes (backend/app/api/) ─┼─> services ─> repositories ─> PostgreSQL / Supabase
agent (backend/app/agent/)     ─┘      │
                                       └─> audit_logs
```

- **Transports translate, services decide.** MCP tools and REST routes are thin: parse
  input, check auth, call a service, format the result. Business rules live in the service.
- `backend/app/agent/` is a **third consumer** of the service layer. It calls services
  directly (not over MCP) — see `docs/agentic-ai.md` §8.
- The agent's tool set, system prompt, and knowledge base are role-aware:
  `ServiceToolExecutor.tool_defs` and `assemble_system_prompt` branch on `auth.is_admin`
  (admins additionally get `update_ticket_status` / `list_all_customers`).
- `POST /agent/chat` is rate-limited per customer (`backend/app/agent/ratelimit.py`) and
  logs one JSON line per run (`backend/app/agent/observability.py`).
- The knowledge base is `knowledge/faq.md` — served as MCP `file://faq` and folded into
  the agent prompt. Edit it to change what the agent knows; no code change needed.

## Conventions

- **Repositories**: raw psycopg3 only — SQL + `%s` parameters, one connection per call via
  `with get_db_connection()` (`backend/app/database/connection.py`). No ORM.
- **Services** (`backend/app/services/*.py`): take `actor_customer_id` + `actor_role` for
  anything protected; return plain `dict`s; on failure return `{"error": "message"}` —
  **never raise**; call `audit_repository.log_action(actor_customer_id, actor_role, name)`
  as the first line of a protected action.
- **REST routes**: `user: dict = Depends(get_current_user)` for auth; map `{"error": ...}`
  to `HTTPException` (400 for validation, 403 for authz, 404 for missing).
- **MCP tools**: validate inputs via `backend/app/validation/schemas.py` (raises
  `ValidationError`, caught and returned as `{"error": ...}`); authorize via
  `backend/app/auth/authorization.py`; declare `token` and `customer_id` as explicit
  parameters.
- **Product agent**: never let the model supply identity. `ServiceToolExecutor` injects
  `actor_customer_id` / `actor_role` from the verified JWT. Admin-only tools are omitted
  from the tool list for non-admin callers.
- Absolute imports (`from backend.app...`), 4-space indent.

## Gotchas

- **The test suite is NOT hermetic.** Everything in `tests/` except `tests/test_agent.py`
  connects to the real `DATABASE_URL` from `.env` and expects these seed rows:
  | Email | Password | Role |
  |---|---|---|
  | `fares@example.com` | `1234` | `admin` (customer id 1) |
  | `ali@example.com` | `5678` | `customer` |
  Some tests (`test_create_ticket`, protected calls) **write rows**. Never run against a
  production database.
- `tests/test_agent.py` is hermetic (fake LLM + fake tool executor). New agent tests
  should follow that pattern.
- `backend/app/config.py` **raises `RuntimeError` at import** if `.env` lacks
  `DATABASE_URL` or `JWT_SECRET`. Anything importing `backend.app.*` needs `.env` present
  (CI provides it via secrets).
- **No DB migrations.** The schema reference is the table in `README.md` and the `db-schema`
  skill. Schema changes are made directly in Supabase, then documented.
- **Secrets**: `.env` is gitignored and contains real credentials. Never read it into
  context, never commit `DATABASE_URL` / `JWT_SECRET` / `GEMINI_API_KEY`. Use `.env.example`
  as the template.
- **Free LLM tiers return HTTP 429** under light load (Gemini, and OpenRouter free models).
  The provider client raises `LLMRateLimitError`; `AgentRunner` turns it into a friendly
  reply, not a 500. `LLM_PROVIDER` picks `gemini` or `openrouter` (`backend/app/agent/llm/`).
- The `mcp` package is **v2** — `MCPServer`, `Client(stdio_client(...))`, `tool.input_schema`.
  Not the older `FastMCP` API.
- The frontend has **no `.spec.ts` files**; `npm test` is not meaningful.
- Frontend API base URL is environment-split: `npm start` → `environment.development.ts`
  (`localhost:8000`), `npm run build` → `environment.ts` (Azure). Don't point the committed
  `environment.ts` at localhost.
- The `/chat` page (`components/chat/`) calls `POST /agent/chat`; it needs the target
  backend to have `GEMINI_API_KEY`.
- `pass.py` (bcrypt hasher) and `client.py` (manual walkthrough) are throwaway scripts, not
  part of the app or the tests.
- No formatter/linter is configured. If you add `ruff`, put it in a `dev` dependency group
  and consider a `PostToolUse` hook in `.claude/settings.json`.

## Skills and agents

- `.claude/skills/add-backend-capability` — full checklist for adding an operation
  (repository → service → MCP tool → REST route → validation → tests).
- `.claude/skills/run-backend` — running and curling the backend locally.
- `.claude/skills/db-schema` — the PostgreSQL schema (no migrations in the repo).
- `.claude/skills/deploy` — CI/CD pipeline, GHCR images, Azure Container Apps deploy.
- `.claude/agents/test-verifier` — runs the fast test suite and diagnoses failures.

`skills-lock.json` at the root is a separate mechanism (vendored Supabase agent-skills),
unrelated to `.claude/skills/`.
