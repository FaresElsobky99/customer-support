from mcp.server import MCPServer

from backend.app.mcp.prompts import register_prompts
from backend.app.mcp.resources import register_resources
from backend.app.mcp.tools.admin_tools import register_admin_tools
from backend.app.mcp.tools.auth_tools import register_auth_tools
from backend.app.mcp.tools.customer_tools import register_customer_tools


mcp = MCPServer("Customer Support")

register_auth_tools(mcp)
register_customer_tools(mcp)
register_admin_tools(mcp)
register_resources(mcp)
register_prompts(mcp)
