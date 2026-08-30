Yes. A good hands-on project is a **Customer Support MCP Server** because it lets you practice everything you learned:

```text
User / Agent
   ↓
MCP Server
├── Tool      → search_customer()
├── Tool      → create_support_ticket()
├── Resource  → support_policy.md
├── Prompt    → investigate_customer_issue
├── Database  → customers + tickets
└── Auth      → protect access
```

We’ll build it step by step:

1. Create a basic MCP server
2. Add one simple tool
3. Connect it to an online database
4. Add database query tools
5. Add an MCP resource
6. Add an MCP prompt
7. Add authentication/authorization
8. Connect an MCP client/agent
9. Let the LLM choose tools automatically
10. Add error handling + security
11. Test it like a real AI engineer
12. Put it on GitHub as a portfolio project

### Step 1 — Basic MCP Server

Create:

```text
mcp-customer-support/
├── server.py
└── requirements.txt
```

Install:

```bash
pip install mcp
```

Start with:

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Customer Support")

@mcp.tool()
def hello_customer(name: str) -> str:
    """Return a greeting for a customer."""
    return f"Hello {name}"

if __name__ == "__main__":
    mcp.run()
```

Here:

```text
FastMCP(...)
    ↓
creates MCP server

@mcp.tool()
    ↓
exposes function to agents

hello_customer()
    ↓
your actual business logic
```

For example, an agent could discover:

```text
Tool:
hello_customer

Input:
name: string
```

and call:

```text
hello_customer("Fares")
```

returning:

```text
Hello Fares
```

Do **only this first**. Once this works, the next step is replacing the fake `hello_customer()` tool with our first real **database-backed tool**.
