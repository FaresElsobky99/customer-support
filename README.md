# MCP Customer Support

A customer-support backend that exposes the same PostgreSQL-backed business logic through:

- an MCP server for AI clients and agents;
- a FastAPI REST API;
- an interactive MCP client;
- a Gemini-powered support chatbot.

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
frontend/                          # Reserved for a future frontend
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
- uv for dependency and command execution
- A reachable PostgreSQL database, including Supabase PostgreSQL
- Docker and Docker Compose only if running the containerized REST API
- A Gemini API key only when using `chatbot.py` or `gemini_test.py`

## Environment configuration

Create `.env` in the project root:

```dotenv
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
JWT_SECRET=replace-with-a-long-random-secret
GEMINI_API_KEY=your-gemini-api-key
```

`DATABASE_URL` and `JWT_SECRET` are required when the backend is imported or started. `GEMINI_API_KEY` is optional unless a Gemini script is used.

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

The chatbot authenticates through MCP, reads the support-policy resource and support prompt, discovers the available tools, and lets Gemini select customer-support operations. Tokens and customer IDs are injected by the local chatbot rather than exposed to the model as user-entered arguments.

## Authentication and auditing

Successful login returns an HS256 JWT containing:

- `customer_id`;
- `role`;
- an expiry one hour after issuance.

Protected actions are written to `audit_logs`. Currently audited operations are:

- `get_customer`;
- `create_ticket`;
- `list_tickets`;
- `list_all_customers`.

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
