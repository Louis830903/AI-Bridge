"""
AI-Bridge MCP Server Package

Provides MCP (Model Context Protocol) server implementations
for exposing CLI adapters as MCP Tools.

Usage:
    # Use pre-configured CLI MCP server
    from aibridge.server.cli_mcp_server import create_cli_mcp_server
    server = create_cli_mcp_server()
    await server.run_stdio()

    # Or use auto-discovery
    from aibridge.server.adapter_discovery import auto_discover_and_register
    registered = await auto_discover_and_register(server)

    # Or create custom MCP tools
    from aibridge.server.mcp_tools import mcp_tool, MCPToolRegistry

    @mcp_tool(name="my_tool", description="My custom tool")
    async def my_tool(input: str) -> dict:
        return {"result": f"Processed: {input}"}
"""

from .mcp_server import AIBridgeMCPServer, SimpleMCPServer
from .mcp_tools import MCPToolRegistry, MCPToolsGenerator, mcp_tool, register_adapter_actions

__all__ = [
    "AIBridgeMCPServer",
    "SimpleMCPServer",
    "MCPToolRegistry",
    "MCPToolsGenerator",
    "mcp_tool",
    "register_adapter_actions",
]

# Optional imports
try:
    from .cli_mcp_server import create_cli_mcp_server
    __all__.append("create_cli_mcp_server")
except ImportError:
    pass

try:
    from .adapter_discovery import AdapterDiscovery, auto_discover_and_register
    __all__.extend(["AdapterDiscovery", "auto_discover_and_register"])
except ImportError:
    pass
