"""
MCP Server - Model Context Protocol server implementation
完全兼容 MCP 协议，支持 Tools, Resources, Prompts
"""

import json
import asyncio
import inspect
import sys
from typing import Any, Dict, List, Optional
from aibridge.core.manager import AdapterManager
from aibridge.core.protocol import Request, Response
from aibridge.core.resources import ResourceManager, AdapterResourceProvider, ConfigResourceProvider
from aibridge.core.prompts import PromptManager


# MCP 协议版本
MCP_PROTOCOL_VERSION = "2024-11-05"


class AIBridgeServer:
    """
    MCP Server implementation for AI-Bridge.
    
    This server exposes AI-Bridge capabilities as MCP tools,
    allowing AI assistants to interact with GUI applications.
    
    Supports:
    - Tools: Application interaction
    - Resources: Adapter info, configs
    - Prompts: Pre-defined templates
    """
    
    def __init__(
        self,
        manager: Optional[AdapterManager] = None,
        config: Optional[Any] = None
    ):
        """
        Initialize the MCP server.
        
        Args:
            manager: AdapterManager instance, creates new one if None
            config: Configuration object
        """
        self.manager = manager or AdapterManager()
        self.config = config
        self._running = False
        
        # 初始化资源管理器
        self.resource_manager = ResourceManager()
        self.resource_manager.register_provider(AdapterResourceProvider(self.manager))
        if config:
            self.resource_manager.register_provider(ConfigResourceProvider(config))
        
        # 初始化提示词管理器
        self.prompt_manager = PromptManager()
    
    def get_server_info(self) -> Dict[str, Any]:
        """Get server information."""
        return {
            "name": "aibridge",
            "version": "0.1.0",
            "description": "AI-Bridge: Bridge AI Assistants to GUI Applications"
        }
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """
        Get MCP tools definition.
        
        Returns:
            List of tool definitions in MCP format
        """
        available_apps = self.manager.list_adapter_ids()
        
        return [
            {
                "name": "aibridge_interact",
                "description": f"Interact with GUI applications. Available apps: {', '.join(available_apps) or 'none registered'}",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "Target application ID",
                            "enum": available_apps if available_apps else None
                        },
                        "action": {
                            "type": "string",
                            "description": "Action to perform (click, type, read, screenshot, etc.)"
                        },
                        "target": {
                            "type": "object",
                            "description": "Element locator",
                            "properties": {
                                "name": {"type": "string", "description": "Element name/text"},
                                "role": {"type": "string", "description": "Element role"},
                                "xpath": {"type": "string", "description": "XPath (browser)"},
                                "css": {"type": "string", "description": "CSS selector (browser)"},
                                "automation_id": {"type": "string", "description": "Automation ID (desktop)"},
                            }
                        },
                        "value": {
                            "type": "string",
                            "description": "Value for the operation"
                        },
                        "options": {
                            "type": "object",
                            "description": "Additional options",
                            "properties": {
                                "timeout": {"type": "integer", "description": "Timeout in ms"},
                                "wait_after": {"type": "integer", "description": "Wait after operation in ms"},
                            }
                        }
                    },
                    "required": ["app", "action"]
                }
            },
            {
                "name": "aibridge_list_apps",
                "description": "List all available applications and their capabilities",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "aibridge_app_status",
                "description": "Get the status of a specific application",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "app": {
                            "type": "string",
                            "description": "Application ID to check"
                        }
                    },
                    "required": ["app"]
                }
            },
            {
                "name": "aibridge_health",
                "description": "Check health status of all adapters",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            }
        ]
    
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle an MCP tool call.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            
        Returns:
            Tool result dictionary
        """
        if name == "aibridge_list_apps":
            return {
                "apps": self.manager.list_adapters()
            }
        
        elif name == "aibridge_app_status":
            app_id = arguments.get("app")
            adapter = self.manager.get_any_adapter(app_id)
            if not adapter:
                return {"error": f"Unknown application: {app_id}"}
            
            if hasattr(adapter, 'health_check'):
                if inspect.iscoroutinefunction(adapter.health_check):
                    return await adapter.health_check()
                else:
                    return adapter.health_check()
            return {"error": "Health check not available"}
        
        elif name == "aibridge_health":
            return await self.manager.health_check_all()
        
        elif name == "aibridge_interact":
            return await self.manager.execute(
                app=arguments.get("app", ""),
                action=arguments.get("action", ""),
                target=arguments.get("target"),
                value=arguments.get("value"),
                options=arguments.get("options")
            )
        
        return {"error": f"Unknown tool: {name}"}
    
    async def run_stdio(self):
        """
        Run the MCP server in stdio mode.
        
        This is the main entry point for MCP communication.
        """
        self._running = True
        
        while self._running:
            try:
                # Read line from stdin
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                # Parse JSON-RPC request
                try:
                    request = json.loads(line)
                except json.JSONDecodeError as e:
                    self._send_error(None, -32700, f"Parse error: {e}")
                    continue
                
                # Handle request
                await self._handle_request(request)
                
            except Exception as e:
                self._send_error(None, -32603, f"Internal error: {e}")
    
    async def _handle_request(self, request: Dict[str, Any]):
        """Handle a JSON-RPC request."""
        request_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params", {})
        
        # Initialize
        if method == "initialize":
            self._send_response(request_id, {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "serverInfo": self.get_server_info(),
                "capabilities": {
                    "tools": {},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                }
            })
        
        # Initialized notification
        elif method == "notifications/initialized":
            pass  # No response needed for notifications
        
        # Ping
        elif method == "ping":
            self._send_response(request_id, {})
        
        # List tools
        elif method == "tools/list":
            self._send_response(request_id, {
                "tools": self.get_tools()
            })
        
        # Call tool
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            
            result = await self.handle_tool_call(tool_name, arguments)
            
            self._send_response(request_id, {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, ensure_ascii=False, indent=2)
                    }
                ]
            })
        
        # List resources
        elif method == "resources/list":
            try:
                resources = await self.resource_manager.list_resources()
                self._send_response(request_id, {"resources": resources})
            except Exception as e:
                self._send_error(request_id, -32603, f"Failed to list resources: {e}")
        
        # Read resource
        elif method == "resources/read":
            uri = params.get("uri", "")
            try:
                content = await self.resource_manager.read_resource(uri)
                self._send_response(request_id, {"contents": [content]})
            except ValueError as e:
                self._send_error(request_id, -32602, str(e))
            except Exception as e:
                self._send_error(request_id, -32603, f"Failed to read resource: {e}")
        
        # List resource templates
        elif method == "resources/templates/list":
            templates = self.resource_manager.list_templates()
            self._send_response(request_id, {"resourceTemplates": templates})
        
        # List prompts
        elif method == "prompts/list":
            prompts = self.prompt_manager.list_prompts()
            self._send_response(request_id, {"prompts": prompts})
        
        # Get prompt
        elif method == "prompts/get":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                result = self.prompt_manager.get_prompt(name, arguments)
                self._send_response(request_id, result)
            except ValueError as e:
                self._send_error(request_id, -32602, str(e))
            except Exception as e:
                self._send_error(request_id, -32603, f"Failed to get prompt: {e}")
        
        # Unknown method
        else:
            if request_id:  # Only respond if it's a request (has id)
                self._send_error(request_id, -32601, f"Method not found: {method}")
    
    def _send_response(self, request_id: Any, result: Any):
        """Send a JSON-RPC response."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }
        print(json.dumps(response), flush=True)
    
    def _send_error(self, request_id: Any, code: int, message: str):
        """Send a JSON-RPC error response."""
        response = {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }
        print(json.dumps(response), flush=True)
    
    def stop(self):
        """Stop the server."""
        self._running = False
