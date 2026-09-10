---
name: db-schema
description: >-
  Reference for the PostgreSQL schema (customers, tickets, audit_logs). Use when writing a
  query, adding a column, or reasoning about the data model. The repo has no migrations or
  schema files — this and the README table are the only source of truth.
---

# Database schema

There are **no migrations** in this repo. The database (Supabase PostgreSQL) is managed
directly. The tables below are reconstructed from
`backend/app/database/repositories/*.py`. If you change the schema, apply it in Supabase,
then update this file, the `README.md` table, and the affected repository.

## `customers`

```sql
CREATE TABLE customers (
    id       SERIAL PRIMARY KEY,
    name     TEXT NOT NULL,
    email    TEXT NOT NULL UNIQUE,
    status   TEXT NOT NULL,          -- 'active' gates ticket creation; other values = inactive
    password TEXT NOT NULL,          -- bcrypt hash (never plain text)
    role     TEXT NOT NULL           -- 'customer' | 'admin'  (enforced by convention, not a CHECK)
);
```

- `role`: `customer` sees only its own record and tickets; `admin` sees everything.
- `status`: only `active` customers may create tickets
  (`customer_service.create_ticket` / `ticket_service.create_ticket`).
- Columns read: `id, name, email, status` (customer view); `+ role` (admin list);
  `id, password, role` (login).

## `tickets`

```sql
CREATE TABLE tickets (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    issue       TEXT NOT NULL,       -- validated 5..1000 chars at the MCP layer
    status      TEXT NOT NULL        -- created as 'open'; normalized .lower() to {open, closed} on read
);
```

- New tickets are inserted with `status = 'open'` (`ticket_repository.create`).
- `ticket_service.list_tickets` / `update_ticket_status` call `.lower()` on `status`, so
  mixed-case values in the DB are tolerated but `{open, closed}` is the intended set.
- Only `admin` may change status (`update_ticket_status`).

## `audit_logs`

```sql
CREATE TABLE audit_logs (
    id          SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL,    -- the ACTOR (actor_customer_id), not necessarily the subject
    role        TEXT NOT NULL,       -- the actor's role at the time
    tool_name   TEXT NOT NULL,       -- e.g. 'create_ticket', 'list_tickets', 'list_all_customers'
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Written by `audit_repository.log_action(actor_customer_id, actor_role, tool_name)`, called
as the first line of every protected service action. The product agent's tool calls flow
through the same services, so agent-driven actions are audited too.

## Seed rows the test suite needs

| id | email | password | role | status |
|---|---|---|---|---|
| 1 | `fares@example.com` | `1234` (bcrypt) | `admin` | `active` |
| — | `ali@example.com` | `5678` (bcrypt) | `customer` | `active` |

Generate a bcrypt hash with `pass.py` (edit the plaintext first) or `bcrypt` directly.

## Access pattern

Every call opens a fresh connection (`get_db_connection()` → `psycopg.connect(DATABASE_URL)`),
uses it in a `with` block, and closes it. No pooling. Keep queries parameterized (`%s`),
never string-format values into SQL.

For broader PostgreSQL guidance, the repo also vendors the
`supabase-postgres-best-practices` skill via `skills-lock.json`.
