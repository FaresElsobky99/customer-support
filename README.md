# MCP Customer Support

A customer-support backend that exposes the same PostgreSQL-backed business logic through:

- an MCP server for AI clients and agents;
- a FastAPI REST API;
- an interactive MCP client;
- a Gemini-powered support chatbot;
- a customer-facing self-service **agent** at `POST /agent/chat` (`backend/app/agent/`).

See [`docs/agentic-ai.md`](docs/agentic-ai.md) for how the AI pieces fit together and how
the runtime agent differs from Claude Code's `.claude/` dev tooling.

The application uses bcrypt password hashes, one-hour HS256 JWTs, role-based access control, and audit logging for protected customer and ticket actions.

## Architecture

```text
MCP tools ─┐
           ├─> services ─> repositories ─> PostgreSQL / Supabase
REST API ──┘       │
                   └─> audit_logs
```

- **API and MCP layers** translate transport-specific input and output.
- **Authentication and authorization** create and verify JWTs and enforce customer/admin access.
- **Services** contain authentication and customer/ticket business rules.
- **Repositories** contain psycopg database access and SQL only.
- **Validation** provides the MCP input validation helpers.

## Project structure

```text
backend/
└── app/
    ├── api_main.py                 # FastAPI application
    ├── main.py                     # MCP stdio entry point
    ├── config.py                   # Environment and project paths
    ├── api/
    │   ├── dependencies.py         # REST authentication dependency
    │   └── routes/
    │       ├── auth.py
    │       ├── customers.py
    │       └── tickets.py
    ├── auth/
    │   ├── jwt.py
    │   └── authorization.py
    ├── database/
    │   ├── connection.py
    │   └── repositories/
    │       ├── audit_repository.py
    │       ├── customer_repository.py
    │       └── ticket_repository.py
    ├── mcp/
    │   ├── server.py
    │   ├── resources.py
    │   ├── prompts.py
    │   └── tools/
    │       ├── auth_tools.py
    │       ├── customer_tools.py
    │       └── admin_tools.py
    ├── services/
    │   ├── customer_service.py
    │   └── ticket_service.py
    └── validation/
        └── schemas.py
tests/
├── integration/
│   └── test_database.py
├── test_auth.py
├── test_customer.py
├── test_health.py
└── test_tickets.py
frontend/                          # Angular customer-support frontend
.github/workflows/backend-ci.yml   # Test, build, and publish workflow
client.py                          # Interactive MCP client
chatbot.py                         # Gemini + MCP chatbot
support_policy.txt                 # MCP support-policy resource
Dockerfile
docker-compose.yml
pyproject.toml
uv.lock
```

The root `db.py` and `customers.db` files are legacy SQLite development artifacts. The backend does not use them; runtime database access uses PostgreSQL through `backend/app/database/connection.py`.

## Requirements

- Python 3.11 or newer
- Node.js 24.15 or newer and npm (for the Angular frontend)
- uv for dependency and command execution
- A reachable PostgreSQL database, including Supabase PostgreSQL
- Docker and Docker Compose only if running the containerized REST API
- A Gemini API key only when using `chatbot.py` or `gemini_test.py`

## Environment configuration

Create `.env` in the project root:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
JWT_SECRET=replace-with-a-long-random-secret

# Agent / chatbot (defaults shown)
LLM_PROVIDER=gemini            # or: openrouter
AGENT_MAX_STEPS=6

# gemini
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.6-flash

# openrouter (free models available; bring your own key)
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_MODEL=openrouter/free
```

`DATABASE_URL` and `JWT_SECRET` are required when the backend is imported or started.
`LLM_PROVIDER` selects the agent's model backend (`backend/app/agent/llm/`): `gemini` needs
`GEMINI_API_KEY`, `openrouter` needs `OPENROUTER_API_KEY`. See [`.env.example`](.env.example).

### Using a free model via OpenRouter

[OpenRouter](https://openrouter.ai) fronts many models, several **free**. There is no shared
key — create your own (free) account:

1. Sign in at <https://openrouter.ai> (Google/GitHub).
2. **Keys → Create API Key**, copy the `sk-or-v1-...` value.
3. In `.env`: `OPENROUTER_API_KEY=sk-or-v1-...` and `LLM_PROVIDER=openrouter`.
4. Leave `OPENROUTER_MODEL=openrouter/free` (auto-routes to an available free tool-capable
   model), or pin one from <https://openrouter.ai/models?max_price=0> that supports "Tools".

Free models are still rate-limited per account (~20 req/min). The agent falls back to a
"briefly rate-limited" reply when that happens.

The `.env` file is ignored by Git. Do not commit database credentials or JWT secrets.

## Database requirements

The project does not currently include migrations or database initialization for PostgreSQL. The configured database must already contain these compatible tables:

| Table | Columns used by the application |
| --- | --- |
| `customers` | `id`, `name`, `email`, `status`, `password`, `role` |
| `tickets` | `id`, `customer_id`, `issue`, `status` |
| `audit_logs` | `id`, `customer_id`, `role`, `tool_name`, `created_at` |

Passwords in `customers.password` must be bcrypt hashes. Plain-text password comparison is not used.

Supported roles are:

- `customer`: may access only their own customer record and tickets;
- `admin`: may access any customer and list all customers.

Only customers whose `status` is `active` can create tickets.

## Installation

From the repository root:

```bash
uv sync --frozen
```

`pyproject.toml` and `uv.lock` are the dependency sources for this project. The empty, misspelled `requirments.txt` file is not used.

## Run the REST API

For local development:

```bash
uv run uvicorn backend.app.api_main:app --reload
```

The API is available at `http://127.0.0.1:8000`.

- Health check: `http://127.0.0.1:8000/health`
- OpenAPI documentation: `http://127.0.0.1:8000/docs`

### REST endpoints

| Method | Path | Authentication | Purpose |
| --- | --- | --- | --- |
| `GET` | `/health` | None | Application health check |
| `POST` | `/auth/login` | None | Authenticate and receive a JWT |
| `GET` | `/customers/me` | Bearer JWT | Return the authenticated customer |
| `GET` | `/customers` | Admin Bearer JWT | List every customer |
| `GET` | `/tickets` | Bearer JWT | List the authenticated customer's tickets |
| `POST` | `/tickets` | Bearer JWT | Create a ticket for the authenticated customer |
| `PATCH` | `/tickets/{ticket_id}/status` | Admin Bearer JWT | Open or close a ticket |
| `POST` | `/agent/chat` | Bearer JWT | Talk to the self-service support agent |

Login request:

```json
{
  "email": "customer@example.com",
  "password": "customer-password"
}
```

Authenticated requests use:

```http
Authorization: Bearer <token>
```

Create-ticket request:

```json
{
  "issue": "My account is locked"
}
```

Administrators receive all customers' tickets from `GET /tickets`. Regular
customers receive only their own tickets. Administrators can change a ticket's
status with:

```json
{
  "status": "open"
}
```

The other accepted status is `closed`.

## Run the Angular frontend

With the REST API running at `http://localhost:8000`, open another terminal:

```bash
cd frontend
npm install
npm start
```

Open `http://localhost:4200`. The backend allows this development origin through
its minimal CORS configuration.

The API base URL comes from `frontend/src/environments/`:

- `npm start` (`ng serve`, the `development` build) uses `environment.development.ts` →
  `http://localhost:8000`;
- `npm run build` (the `production` build) uses `environment.ts` → the Azure backend.

Pages: Dashboard, Profile, Tickets, **Assistant** (`/chat` — the self-service agent from
`POST /agent/chat`), and Customers (admin). The assistant page needs `GEMINI_API_KEY` set
on whichever backend the frontend points at.

Build the production bundle with:

```bash
cd frontend
npm run build
```

## Run the MCP server

The MCP server uses stdio transport:

```bash
uv run python -m backend.app.main
```

A stdio server normally waits silently for an MCP client. Use the included client to exercise it interactively:

```bash
uv run python client.py
```

### MCP capabilities

| Type | Name or URI | Purpose |
| --- | --- | --- |
| Tool | `hello_customer` | Return a customer greeting |
| Tool | `login` | Authenticate and return a JWT |
| Tool | `get_customer` | Read an authorized customer record |
| Tool | `create_ticket` | Create a ticket for an active customer |
| Tool | `list_tickets` | List an authorized customer's tickets |
| Tool | `list_all_customers` | List customers as an admin |
| Resource | `file://support-policy` | Return `support_policy.txt` |
| Prompt | `support_prompt` | Build a support workflow prompt for an issue |

MCP validation checks email format, password presence, positive customer IDs, non-empty names, and trimmed ticket issues between 5 and 1000 characters.

## Run the Gemini chatbot

Set `GEMINI_API_KEY` in `.env`, then run:

```bash
uv run python chatbot.py
```

The chatbot authenticates through MCP, discovers the available tools, and lets Gemini
select customer-support operations. Tokens and customer IDs are injected locally, never
exposed to the model. The loop, prompt, and provider handling are shared with the HTTP
agent below (`backend/app/agent/`).

## Agentic AI

Two separate things, explained in full in [`docs/agentic-ai.md`](docs/agentic-ai.md):

- **The product agent** — `POST /agent/chat`, a customer-facing self-service assistant
  (`backend/app/agent/`). It runs an LLM tool-loop over the service layer, scoped to the
  authenticated caller: identity comes from the verified JWT, admin tools are not offered
  to customers, and a `max_steps` cap bounds each turn. The endpoint is stateless — the
  client sends the transcript back in `history` each turn.

  ```bash
  TOK=$(curl -s localhost:8000/auth/login -H 'Content-Type: application/json' \
    -d '{"email":"ali@example.com","password":"5678"}' | jq -r .token)

  curl -s localhost:8000/agent/chat -H "Authorization: Bearer $TOK" \
    -H 'Content-Type: application/json' \
    -d '{"message":"my password reset email never arrives, please open a ticket"}' | jq
  ```

  The LLM backend is pluggable via `LLM_PROVIDER` (`backend/app/agent/llm/`): `gemini` or
  `openrouter` (free models — see below), with Claude/others as a one-file addition.

- **The dev tooling** — `CLAUDE.md` and `.claude/` (skills, a `test-verifier` subagent,
  permission settings) configure Claude Code as a coding assistant *on this repo*. This is
  unrelated to `skills-lock.json`, which vendors external Supabase agent-skills through a
  different tool.

## Authentication and auditing

Successful login returns an HS256 JWT containing:

- `customer_id`;
- `role`;
- an expiry one hour after issuance.

Protected actions are written to `audit_logs`. Currently audited operations are:

- `get_customer`;
- `create_ticket`;
- `list_tickets`;
- `list_all_customers`;
- `update_ticket_status`.

## Tests

Run all tests:

```bash
uv run pytest tests/
```

Run the API test group while excluding explicitly marked integration tests:

```bash
uv run pytest tests/ -m "not integration"
```

Run only PostgreSQL integration tests:

```bash
uv run pytest tests/integration/ -m integration
```

The database integration test verifies that the configured server is PostgreSQL. The current API tests also call the configured database and expect these test records:

| Email | Password | Expected properties |
| --- | --- | --- |
| `fares@example.com` | `1234` | Customer ID `1`, role `admin`, active account |
| `ali@example.com` | `5678` | Non-admin customer |

These credentials are test fixtures only. Do not use them in a production database. `test_create_ticket` inserts a ticket and audit records are created by protected service calls, so run the suite against a test database rather than production.

## Docker

Build and run the REST API with Docker Compose:

```bash
docker compose up --build
```

The compose service reads `.env`, exposes port `8000`, and checks `/health` every 30 seconds.

Stop it with:

```bash
docker compose down
```

## Continuous integration

The GitHub Actions workflow runs on pushes and pull requests to `main`:

1. install Python 3.11 and dependencies with uv;
2. run tests excluding the explicit integration marker;
3. run the PostgreSQL integration test;
4. build the Docker image;
5. on pushes to `main`, publish `ghcr.io/fareselsobky99/customer-support-api:latest`.

The workflow requires repository secrets named `DATABASE_URL` and `JWT_SECRET`.
