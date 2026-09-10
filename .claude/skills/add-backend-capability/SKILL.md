---
name: add-backend-capability
description: >-
  Use when adding a new customer-support operation to the backend — a new MCP tool and/or
  REST endpoint, its service function, repository query, input validation, and tests.
  Covers the full path: repository -> service -> MCP tool -> REST route -> validation ->
  tests, and (if the product agent should use it) the agent tool registry.
---

# Adding a backend capability

The business core is shared: an operation is written once in a **service** and exposed
through the **MCP tool** layer, the **REST route** layer, or both. Follow the layers in
order.

## 1. Repository — `backend/app/database/repositories/<entity>_repository.py`

Raw psycopg3 only. SQL string + `%s` parameters, one connection per call.

```python
from backend.app.database.connection import get_db_connection

def find_open_by_customer_id(customer_id: int) -> list[tuple]:
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, customer_id, issue, status FROM tickets "
                "WHERE customer_id = %s AND status = 'open'",
                (customer_id,),
            )
            return cur.fetchall()
```

Return raw tuples; the service maps them to dicts. See `db-schema` skill for columns.

## 2. Service — `backend/app/services/<entity>_service.py`

```python
def close_all_tickets(customer_id: int, actor_customer_id: int, actor_role: str) -> dict:
    audit_repository.log_action(actor_customer_id, actor_role, "close_all_tickets")
    if actor_role != "admin" and actor_customer_id != customer_id:
        return {"error": "Not authorized"}
    count = ticket_repository.close_all_for_customer(customer_id)
    return {"closed": count}
```

Rules:
- Signature ends with `actor_customer_id: int, actor_role: str` for anything protected.
- First line of a protected action: `audit_repository.log_action(actor_customer_id, actor_role, "<name>")`.
- Return a `dict`. On failure return `{"error": "message"}` — **never raise**.

## 3. Validation (only if a new input type) — `backend/app/validation/schemas.py`

Add a `validate_*` function that raises `ValidationError` (a `ValueError` subclass).
Mirror the existing ones (`validate_ticket_issue`, `validate_customer_id`).

## 4. MCP tool — `backend/app/mcp/tools/<group>_tools.py`

Register inside the existing `register_*_tools(mcp)` function.

```python
@mcp.tool()
def close_all_tickets(token: str, customer_id: int) -> dict:
    """Close every open ticket for a customer."""
    try:
        customer_id = validate_customer_id(customer_id)
    except ValidationError as error:
        return {"error": str(error)}
    user, auth_error = authorize_customer(token, customer_id)
    if auth_error:
        return auth_error
    return ticket_service.close_all_tickets(customer_id, user["customer_id"], user["role"])
```

- Declare `token` and `customer_id` as explicit parameters (the MCP client strips and
  re-injects them — see `docs/agentic-ai.md` §3).
- Validate, then `authorize_customer` / `authorize_admin`
  (`backend/app/auth/authorization.py`), then call the service.
- New tool groups must be wired in `backend/app/mcp/server.py`.

## 5. REST route — `backend/app/api/routes/<group>.py`

```python
class CloseAllRequest(BaseModel):
    confirm: bool

@router.post("/close-all")
def close_all(request: CloseAllRequest, user: dict = Depends(get_current_user)):
    result = close_all_tickets(
        customer_id=user["customer_id"],
        actor_customer_id=user["customer_id"],
        actor_role=user["role"],
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
```

- Auth via `user: dict = Depends(get_current_user)` (`backend/app/api/dependencies.py`).
- Map `{"error": ...}` → `HTTPException` (400 validation, 403 authz, 404 missing).
- A **new** router file must be registered in `backend/app/api_main.py`
  (`from backend.app.api.routes import ..., <group>` + `app.include_router(<group>.router)`).

## 6. Tests — `tests/test_<group>.py`

Use `TestClient(app)` and the login helpers (copy `get_token()` /
`get_customer_session()` from `tests/test_tickets.py`). Cover: success, the `{"error"}`
path, and RBAC (customer vs admin, 403 for the wrong role). Remember the suite is **not
hermetic** — it hits the live DB and needs the seed accounts.

## 7. Product agent (only if the customer-facing agent should call it)

Add the tool to `backend/app/agent/tools/service_executor.py`:
- a `ToolDef` in `tool_defs()` (role-gated if admin-only) exposing only the real business
  arguments — never `token` or `customer_id`;
- a dispatch branch in `execute()` that calls the service with
  `actor_customer_id=auth.customer_id`, `actor_role=auth.role`.

Also update `chatbot.py`'s `PROTECTED_TOOLS` / `CUSTOMER_SCOPED_TOOLS` / `ADMIN_TOOLS`
sets if the new tool needs identity injection there.

Add a hermetic case to `tests/test_agent.py`.

## Verify

```bash
uv run pytest tests/ -m "not integration" -q
uv run python client.py            # exercises every MCP tool
```
