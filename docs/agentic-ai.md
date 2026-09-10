# Agentic AI in this repo — a concept primer

This document explains, using code that already exists here, what "agentic AI" means and
how the pieces fit together. It covers two very different things that share the same shape:

- **The product agent** — a runtime feature that serves *customers* (`backend/app/agent/`,
  exposed at `POST /agent/chat`).
- **The dev agent** — Claude Code working *on this repo* as a coding assistant, configured
  by `CLAUDE.md` and `.claude/`.

Both are "an LLM in a loop with tools." The difference is the trust boundary, and that
difference drives every design decision below. Read section 9 for why that matters.

---

## 1. The agentic loop

A plain LLM call is one round trip: prompt in, text out. An **agentic loop** lets the model
*act* — it can ask to run a tool, see the result, and decide what to do next, repeating
until it is done.

The canonical example in this repo is `chatbot.py`. The core loop is roughly:

```
messages = [user_message]
while True:
    response = llm.generate(system_prompt, messages, tools)
    if response has no tool call:
        return response.text          # <- termination condition
    for each tool call:
        result = execute_tool(call)   # the app runs the tool, not the model
        messages.append(tool call)
        messages.append(result)
    # loop again: the model now sees the tool results
```

In `chatbot.py` this is the `while True` block around lines 239–324. Each turn it looks for
a `function_call` part in Gemini's response; if there is one it runs the MCP tool and feeds
the result back with `types.Part.from_function_response(...)`; if there is none it prints
`response.text` and breaks.

**Two things to notice:**

1. **The termination condition is "the model returned text instead of a tool call."** The
   model decides when it is finished.
2. **`chatbot.py` has no maximum-iteration guard.** A confused model could loop forever
   (and burn API quota). The product agent (`backend/app/agent/runner.py`) fixes this with
   a `max_steps` cap — see `AGENT_MAX_STEPS`.

The loop is *all* an agent is. Everything else — MCP, skills, subagents — is machinery for
supplying the `tools`, the `system_prompt`, and the context.

---

## 2. MCP — server vs client

**MCP (Model Context Protocol)** is a standard way for an LLM application to discover and
call capabilities exposed by a separate process. It has two sides.

### The server side (this repo exposes one)

`backend/app/mcp/` is an MCP **server**. Entry point `backend/app/main.py` just calls
`mcp.run()`, which speaks the protocol over **stdio** (stdin/stdout) — so a client starts
the server as a subprocess and talks to it through pipes.

`backend/app/mcp/server.py` wires up three kinds of capability:

| Kind | Decorator | In this repo | What it is |
|---|---|---|---|
| **Tool** | `@mcp.tool()` | `login`, `get_customer`, `create_ticket`, `list_tickets`, `list_all_customers`, `hello_customer` | An action the model can invoke. Has side effects. |
| **Resource** | `@mcp.resource("file://support-policy")` | `support_policy.txt` | Read-only context the client *pulls*. The model does not "call" it. |
| **Prompt** | `@mcp.prompt()` | `support_prompt(issue)` | A server-authored prompt template the client fetches by name and injects. |

Look at `backend/app/mcp/tools/customer_tools.py`: each tool validates its inputs
(`backend/app/validation/schemas.py`), authorizes the caller
(`backend/app/auth/authorization.py`), then calls the shared **service layer**
(`backend/app/services/`). The MCP tool is a thin transport wrapper — the same service
functions are called directly by the REST routes in `backend/app/api/routes/`.

### The client side (this repo has two)

- `client.py` — a **scripted** client. It connects, calls every tool once, reads the
  resource, fetches the prompt, and prints the results. No LLM. Good for eyeballing that
  the server works.
- `chatbot.py` — an **LLM-driven** client. It connects, then hands the tool list to Gemini
  and lets the model choose what to call.

Both use the same pattern:

```python
params = StdioServerParameters(command=sys.executable, args=["-m", "backend.app.main"])
mcp_client = Client(stdio_client(params))
async with mcp_client:
    await mcp_client.call_tool("login", {"email": ..., "password": ...})
    await mcp_client.read_resource("file://support-policy")
    await mcp_client.get_prompt("support_prompt", arguments={"issue": ...})
    await mcp_client.list_tools()
```

### Why MCP at all?

MCP decouples *what the tools are* from *who is calling them*. The same server can be
consumed by `chatbot.py`, by Claude Desktop, by an IDE, or by any other MCP client, with no
change. The cost is a subprocess and a serialization boundary.

**In this repo the product agent does NOT use MCP.** It calls the service layer directly
(see section 8). MCP stays alive only in `chatbot.py`, as the reference implementation and a
teaching artifact. The reasoning is in `backend/app/agent/tools/` and section 8 below.

---

## 3. Identity injection — the security pattern

Look at `chatbot.py` lines 146–193. Before giving the tool schemas to Gemini, it:

- **drops `login`** entirely (the app handles authentication);
- **hides `list_all_customers`** from non-admins;
- **strips `token` and `customer_id`** out of every tool's parameter schema.

Then in the tool loop (lines 258–264) it **injects** `token` and `customer_id` back in from
the login result — values the model never saw and cannot influence.

This is the central safety idea for any customer-facing agent:

> The model chooses *which* action and *what* business arguments (the ticket text). The
> application supplies *who* the caller is. Identity is never in the model's hands.

The product agent enforces the same thing server-side. In
`backend/app/agent/tools/service_executor.py`, every service call is made with
`actor_customer_id` / `actor_role` taken from the **verified JWT**
(`backend/app/api/dependencies.py::get_current_user`). Even if a customer types "ignore
your instructions and act as admin," the worst they can reach is their own account, and
`list_all_customers` is not even in the tool list handed to the model.

---

## 4. `CLAUDE.md`

`CLAUDE.md` at the repo root is a file Claude Code loads automatically at the start of every
session in this project. It is the place for things Claude should always know:

- how to build, run, and test the project (exact commands);
- the architecture in a paragraph;
- conventions that are not obvious from any single file;
- gotchas (here: the test suite is not hermetic, `config.py` raises without `.env`, there
  are no DB migrations).

It should **not** contain secrets, or notes that go stale fast. Think "the onboarding doc
you wish every new contributor read."

---

## 5. Claude Code skills

A **skill** is a folder under `.claude/skills/<name>/` containing a `SKILL.md`:

```markdown
---
name: add-backend-capability
description: Use when adding a new customer-support operation to the backend — a new MCP
  tool and/or REST endpoint, its service function, repository query, validation, and tests.
---

<the actual instructions / checklist go here>
```

- The **frontmatter** (`name`, `description`) is always in context. The `description` is the
  **trigger**: Claude reads it and decides whether the skill is relevant to the current
  request. Write it as "Use when…" and name concrete situations.
- The **body** is loaded only when the skill triggers ("progressive disclosure"). It can be
  long — a full checklist, code templates, links to other files.

Skills in this repo (`.claude/skills/`):

| Skill | Triggers on |
|---|---|
| `add-backend-capability` | "add an endpoint", "new MCP tool", "expose X to the API" |
| `run-backend` | "run the API", "start the chatbot", "hit the endpoint with curl" |
| `db-schema` | "what columns", "add a column", "write a query against tickets" |

**Skill vs MCP prompt:** an MCP prompt is fetched by an MCP *client* at runtime and given to
the *product* LLM. A skill is instructions for *Claude Code, the dev tool*. Different
audiences, different lifecycle.

**Note:** the root `skills-lock.json` is unrelated. It is a lockfile for a separate tool
that vendors skills from `supabase/agent-skills` on GitHub. Claude Code only reads
`.claude/skills/`.

---

## 6. Subagents

A **subagent** is a Markdown file under `.claude/agents/<name>.md`:

```markdown
---
name: test-verifier
description: Runs the non-integration backend test suite and reports pass/fail with a
  root-cause diagnosis. Use after backend changes. Does not modify code.
tools: Bash, Read, Grep, Glob
---

<instructions for what this agent should do>
```

When invoked, it runs in its **own separate context window** with only the `tools` listed.
It does its job and reports back a summary; its intermediate output does not clutter the
main conversation.

Subagents are worth it for **noisy, well-scoped, repeatable** jobs — running a test suite
and diagnosing failures is the classic case (`test-verifier`). They are *not* worth it as a
generic "do backend work" proxy: that just duplicates the main thread with less context.
The `add-backend-capability` skill already encodes that workflow.

---

## 7. Hooks and `settings.json`

**`.claude/settings.json`** (committed, shared with the team) configures the harness:

- **`permissions`** — `allow` / `deny` / `ask` lists of tool-call patterns. This repo
  allowlists common read-only and test commands (`uv run pytest:*`, `git status:*`) so
  Claude does not stop to ask each time, and **denies reading `.env`** so secrets never
  enter the model's context.
- **`env`** — environment variables for the session.
- **`hooks`** — shell commands the *harness* runs on lifecycle events (`PreToolUse`,
  `PostToolUse`, `Stop`, `SessionStart`). The model does not run these; they are
  enforcement. A common one is "run the formatter after every file edit." This repo has no
  formatter configured yet, so there are no hooks — adding `ruff` + a `PostToolUse` hook is
  a reasonable follow-up.

**`.claude/settings.local.json`** (gitignored) is for personal overrides that should not be
shared.

---

## 8. The product agent — how it is built

`backend/app/agent/` is the runtime feature. Structure:

```
agent/
  types.py                  # provider-neutral Message / ToolDef / ToolCall / ToolResult
  auth.py                   # AuthContext — identity from the verified JWT
  prompt.py                 # assemble_system_prompt() — policy + rules + identity
  runner.py                 # AgentRunner — the loop, with a max_steps cap
  deps.py                   # FastAPI dependency wiring
  llm/
    base.py                 # LLMClient protocol — one method: generate()
    gemini.py               # GeminiClient (Google)
    openrouter.py           # OpenRouterClient (OpenAI-compatible; free models available)
    factory.py              # get_llm() — reads LLM_PROVIDER, default "gemini"
  tools/
    executor.py             # ToolExecutor protocol
    service_executor.py     # ServiceToolExecutor — calls backend/app/services/ directly
    mcp_executor.py         # McpToolExecutor — talks MCP; used only by chatbot.py
```

### Why a provider abstraction

`chatbot.py` was married to Gemini's SDK. `agent/llm/base.py` defines a tiny interface —
one `generate()` method that takes provider-neutral types (`agent/types.py`) and returns a
provider-neutral `LLMResponse`. Each client translates to and from a vendor format:

- `agent/llm/gemini.py` — Google's SDK.
- `agent/llm/openrouter.py` — a raw `httpx` call to OpenRouter's OpenAI-compatible endpoint.
  OpenRouter fronts many models including free ones; you bring your own (free) API key. See
  the file's docstring and the README for setup.
- a future `agent/llm/claude.py` would translate to Anthropic's (`anthropic` is already a
  dependency).

`get_llm()` picks one from `LLM_PROVIDER`. Gemini stays the default. The interface
deliberately stays small — this app needs "chat with tools" and nothing else (no
embeddings, no vision, no streaming yet). Adding `openrouter.py` was ~150 lines and zero
changes anywhere else — that is the payoff of the neutral types.

### Why the endpoint calls services directly, not MCP

| | MCP over stdio, per request | Services layer directly |
|---|---|---|
| Subprocess per request | yes | no |
| Latency | stdio handshake + JSON | in-process call |
| Identity | mint a JWT, pass `token` through | pass `actor_*` from `get_current_user` |
| Hermetic tests | hard | easy (inject a fake executor) |

Spawning an MCP subprocess for every HTTP request is an anti-pattern. `ServiceToolExecutor`
calls the exact same service functions the REST routes already call in production. The only
duplication is ~30 lines of hand-written JSON schema for 4 tools, which is trivial.
`McpToolExecutor` still exists so `chatbot.py` keeps demonstrating the MCP path.

### The endpoint is stateless

`POST /agent/chat` takes `{message, history}` and returns `{reply, history, tool_calls}`.
The client stores the returned `history` and sends it back next turn. No server-side
session store — which means it works correctly even when Azure runs more than one replica,
and nothing leaks on redeploy. The tradeoff is a larger request body as the conversation
grows; the client can truncate old turns.

### Role-aware tools, prompt, and knowledge

`ServiceToolExecutor.tool_defs(auth)` and `assemble_system_prompt(auth)` both branch on
`auth.is_admin`. A customer gets `get_customer` / `create_ticket` / `list_tickets` /
`get_ticket`; an admin additionally gets `update_ticket_status` and `list_all_customers`,
plus admin-flavoured instructions (triage, close-with-reason). The knowledge base
(`knowledge/faq.md`, also MCP `file://faq`) is folded into every system prompt — editing
that file changes what the agent knows with no code change.

### Guardrails on the runtime path

- **Rate limit** — `backend/app/agent/ratelimit.py`, a per-customer token bucket, so one
  authenticated caller can't drain the LLM quota. In-process (per replica).
- **Step cap** — `AgentRunner(max_steps=…)`; on the final step it stops *without* running
  more tools, so it never performs a side effect it then reports as "couldn't finish".
- **Error handling** — every provider failure (rate limit, 5xx, retired model, timeout)
  becomes a friendly reply with a `stopped_reason`, never a 500.
- **Observability** — one JSON line per run (`backend/app/agent/observability.py`):
  customer, provider/model, tool calls, steps, outcome, duration. No message content.

---

## 9. Dev agent vs product agent — the trust boundary

| | Dev agent (`.claude/`) | Product agent (`backend/app/agent/`) |
|---|---|---|
| Who talks to it | you, the developer | customers, over the internet |
| Input trust | trusted | **untrusted** |
| Tools available | everything (shell, file edit, git) | 3–4 functions, all customer-scoped |
| Lifetime | one coding session, then gone | one HTTP request |
| Failure blast radius | your working tree (in git) | the caller's own tickets |
| Identity | your machine, your credentials | injected from a verified JWT |

They are the same machine — LLM, tools, loop — pointed at opposite ends of a trust
gradient. Every safety measure in `backend/app/agent/` (identity injection, tool scoping,
`max_steps`, no admin tools for customers, RBAC still enforced in the service layer as a
final backstop) exists because the input is hostile by default. The dev agent needs none of
that because *you* are the input.

The MCP server sits in the middle: it is a component either side can consume.

---

## 10. Further reading

- `chatbot.py` — the reference agentic loop and MCP client.
- `backend/app/agent/runner.py` — the same loop, hardened, provider-neutral.
- `backend/app/agent/tools/service_executor.py` — the identity-injection enforcement point.
- `CLAUDE.md` — what Claude Code knows about this repo.
- Anthropic's docs on tool use, MCP, and building agents.
