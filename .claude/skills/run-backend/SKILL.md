---
name: run-backend
description: >-
  Use to run or one-shot-exercise the backend locally — the REST API, the MCP server, the
  scripted MCP client, or the Gemini chatbot — and to hit endpoints with curl (get a JWT,
  call a protected route, test POST /agent/chat).
---

# Running the backend

## Prerequisites

`.env` in the repo root with at least:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
JWT_SECRET=some-long-random-string
GEMINI_API_KEY=...        # only for chatbot.py and POST /agent/chat
```

`backend/app/config.py` raises `RuntimeError` at import if `DATABASE_URL` or `JWT_SECRET`
is missing. Then:

```bash
uv sync --frozen
```

## Run targets

| Command | What it does |
|---|---|
| `uv run uvicorn backend.app.api_main:app --reload` | REST API on `:8000` — `/docs`, `/health` |
| `uv run python -m backend.app.main` | MCP server over stdio (waits silently for a client) |
| `uv run python client.py` | scripted MCP client — calls every tool once, prints results |
| `uv run python chatbot.py` | Gemini CLI chatbot (asks for email/password, then a REPL) |

## curl recipes

Get a token and call a protected route:

```bash
TOK=$(curl -s localhost:8000/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"ali@example.com","password":"5678"}' | jq -r .token)

curl -s localhost:8000/tickets -H "Authorization: Bearer $TOK" | jq
curl -s localhost:8000/tickets -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' -d '{"issue":"My account is locked"}' | jq
```

Talk to the product agent (stateless — resend the returned `history`):

```bash
curl -s localhost:8000/agent/chat -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' \
  -d '{"message":"my app crashes on login, please open a ticket"}' | jq

curl -s localhost:8000/agent/chat -H "Authorization: Bearer $TOK" \
  -H 'Content-Type: application/json' \
  -d '{"message":"what tickets do I have?","history":[{"role":"user","content":"..."},{"role":"assistant","content":"..."}]}' | jq
```

## Common failures

| Symptom | Cause |
|---|---|
| `RuntimeError: DATABASE_URL is missing` at startup | no `.env`, or missing key |
| `401 Invalid or expired token` | JWT older than 1 hour — log in again |
| `429` / "assistant is busy" in the chatbot or `/agent/chat` | Gemini free-tier rate limit — wait and retry |
| MCP server prints nothing | expected — it is waiting for a client on stdio; use `client.py` |

## Seed accounts (shared test DB)

| Email | Password | Role |
|---|---|---|
| `fares@example.com` | `1234` | admin (customer id 1) |
| `ali@example.com` | `5678` | customer |
