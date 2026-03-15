"""
MCP Tool Registration for AI-Bridge

Provides decorators and utilities to expose adapter actions as MCP Tools.

Usage:
    from aibridge.server.mcp_tools import mcp_tool, MCPToolRegistry
    
    @mcp_tool(
        name="gimp_open_image",
        description="Open an image file in GIMP",
        parameters={
            "file_path": {"type": "string", "description": "Path to image file"}
        }
    )
    async def gimp_open_image(file_path: str) -> dict:
        adapter = GIMPAdapter()
        await adapter.initialize()
        result = await adapter.execute(Action(
            name="open_image",
            params={"file_path": file_path}
        ))
        return result.to_dict()
"""

import asyncio
import inspect as inspect_module
import json
import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, Union, get_type_hints

from aibridge.core.protocol import Response
from aibridge.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


@dataclass
class MCPToolParameter:
    """Definition of an MCP Tool parameter."""
    name: str
    type: str  # string, number, boolean, array, object
    description: str
    required: bool = True
    default: Any = None
    enum: Optional[List[Any]] = None
    
    def to_schema(self) -> dict:
        """Convert to JSON Schema property."""
        schema = {
            "type": self.type,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        return schema


@dataclass
class MCPTool:
    """Definition of an MCP Tool."""
    name: str
    description: str
    parameters: List[MCPToolParameter]
    handler: Callable
    adapter_class: Optional[Type[BaseAdapter]] = None
    adapter_instance: Optional[BaseAdapter] = None
    
    def to_schema(self) -> dict:
        """Convert to MCP Tool schema."""
        required = [p.name for p in self.parameters if p.required]
        properties = {p.name: p.to_schema() for p in self.parameters}
        
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            }
        }
    
    async def execute(self, params: dict) -> dict:
        """Execute the tool with given parameters."""
        adapter_created = False
        try:
            # Initialize adapter if needed
            if self.adapter_class and not self.adapter_instance:
                self.adapter_instance = self.adapter_class()
                await self.adapter_instance.initialize()
                adapter_created = True
            
            # Call handler
            if inspect_module.iscoroutinefunction(self.handler):
                result = await self.handler(**params)
            else:
                result = self.handler(**params)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2, default=str)
                    }
                ],
                "isError": False
            }
        except Exception as e:
            logger.exception(f"Error executing MCP tool {self.name}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {str(e)}"
                    }
                ],
                "isError": True
            }
        finally:
            # Cleanup adapter if we created it (not persistent)
            if adapter_created and self.adapter_instance and hasattr(self.adapter_instance, 'cleanup'):
                try:
                    await self.adapter_instance.cleanup()
                except Exception:
                    pass  # Best effort cleanup


class MCPToolRegistry:
    """
    Registry for MCP Tools.
    
    Manages tool registration, schema generation, and execution.
    Thread-safe singleton implementation.
    """
    _instance = None
    _lock = threading.Lock()
    _tools: Dict[str, MCPTool] = {}
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._tools = {}
        return cls._instance
    
    def register(self, tool: MCPTool) -> None:
        """Register an MCP Tool."""
        self._tools[tool.name] = tool
        logger.info(f"Registered MCP Tool: {tool.name}")
    
    def unregister(self, name: str) -> None:
        """Unregister an MCP Tool."""
        if name in self._tools:
            del self._tools[name]
            logger.info(f"Unregistered MCP Tool: {name}")
    
    def get(self, name: str) -> Optional[MCPTool]:
        """Get a registered tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[dict]:
        """List all registered tools as schemas."""
        return [tool.to_schema() for tool in self._tools.values()]
    
    async def execute(self, name: str, params: dict) -> dict:
        """Execute a tool by name."""
        tool = self.get(name)
        if not tool:
            return {
                "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
                "isError": True
            }
        return await tool.execute(params)
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()


def mcp_tool(
    name: Optional[str] = None,
    description: Optional[str] = None,
    parameters: Optional[Dict[str, dict]] = None,
    adapter_class: Optional[Type[BaseAdapter]] = None
):
    """
    Decorator to register a function as an MCP Tool.
    
    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        parameters: Parameter definitions {name: {type, description, required, default}}
        adapter_class: Associated adapter class for automatic initialization
        
    Example:
        @mcp_tool(
            name="search_files",
            description="Search for files matching a pattern",
            parameters={
                "pattern": {"type": "string", "description": "Search pattern"},
                "path": {"type": "string", "description": "Directory to search", "required": False}
            }
        )
        async def search_files(pattern: str, path: str = ".") -> list:
            return await do_search(pattern, path)
    """
    def decorator(func: Callable) -> Callable:
        tool_name = name or func.__name__
        tool_description = description or (func.__doc__ or "").strip()
        
        # Build parameter list
        tool_params = []
        type_hints = get_type_hints(func)
        sig = inspect_module.signature(func)
        
        params_dict = parameters or {}
        
        for param_name, param in sig.parameters.items():
            if param_name in params_dict:
                param_def = params_dict[param_name]
            else:
                # Auto-infer from type hints
                param_type = type_hints.get(param_name, str)
                type_map = {
                    str: "string",
                    int: "number",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object",
                }
                param_def = {
                    "type": type_map.get(param_type, "string"),
                    "description": f"Parameter: {param_name}"
                }
            
            tool_params.append(MCPToolParameter(
                name=param_name,
                type=param_def.get("type", "string"),
                description=param_def.get("description", ""),
                required=param_def.get("required", param.default == inspect_module.Parameter.empty),
                default=param.default if param.default != inspect_module.Parameter.empty else None,
                enum=param_def.get("enum")
            ))
        
        tool = MCPTool(
            name=tool_name,
            description=tool_description,
            parameters=tool_params,
            handler=func,
            adapter_class=adapter_class
        )
        
        # Register
        MCPToolRegistry().register(tool)
        
        return func
    
    return decorator


def register_adapter_actions(
    adapter_class: Type[BaseAdapter],
    action_handlers: Dict[str, dict],
    prefix: Optional[str] = None
):
    """
    Bulk register adapter actions as MCP Tools.
    
    Args:
        adapter_class: The adapter class to register
        action_handlers: Map of action names to their metadata
            {
                "open_image": {
                    "description": "Open an image",
                    "parameters": {"file_path": {"type": "string", "description": "Image path"}}
                }
            }
        prefix: Optional prefix for tool names (e.g., "gimp_")
    """
    registry = MCPToolRegistry()
    prefix = prefix or f"{adapter_class.__name__.lower().replace('adapter', '')}_"
    
    for action_name, metadata in action_handlers.items():
        tool_name = f"{prefix}{action_name}"
        
        # Create handler that wraps the adapter
        async def make_handler(action):
            async def handler(**params):
                adapter = adapter_class()
                await adapter.initialize()
                try:
                    # Import Action class here to avoid circular imports
                    from aibridge.core.protocol import ActionRequest
                    result = await adapter.execute(ActionRequest(
                        name=action,
                        params=params
                    ))
                    return {
                        "success": result.success,
                        "data": result.data,
                        "error": result.error
                    }
                finally:
                    await adapter.cleanup()
            return handler
        
        # Create an instance of the handler for this specific action
        handler = asyncio.get_event_loop().run_until_complete(make_handler(action_name)) if asyncio.get_event_loop().is_running() else None
        
        # Create a sync wrapper that will be called
        def create_handler(act_name):
            async def action_handler(**params):
                adapter = adapter_class()
                await adapter.initialize()
                try:
                    from aibridge.core.protocol import ActionRequest
                    result = await adapter.execute(ActionRequest(
                        name=act_name,
                        params=params
                    ))
                    return {
                        "success": result.success,
                        "data": result.data,
                        "error": result.error
                    }
                finally:
                    await adapter.cleanup()
            return action_handler
        
        handler = create_handler(action_name)
        handler.__name__ = tool_name
        
        tool = MCPTool(
            name=tool_name,
            description=metadata.get("description", f"Execute {action_name}"),
            parameters=[
                MCPToolParameter(
                    name=k,
                    type=v.get("type", "string"),
                    description=v.get("description", ""),
                    required=v.get("required", True),
                    enum=v.get("enum")
                )
                for k, v in metadata.get("parameters", {}).items()
            ],
            handler=handler,
            adapter_class=adapter_class
        )
        
        registry.register(tool)
        logger.info(f"Auto-registered MCP Tool: {tool_name}")


class MCPToolsGenerator:
    """
    从 AdapterManager 自动生成 MCP Tools。
    
    此类提供了一种便捷方式，将 AI-Bridge 适配器的能力自动暴露为 MCP Tool。
    
    用法示例:
        ```python
        from aibridge.core.manager import AdapterManager
        from aibridge.server.mcp_tools import MCPToolsGenerator
        
        manager = AdapterManager()
        generator = MCPToolsGenerator(manager)
        tools = generator.generate_all()
        
        # 或者生成特定适配器的工具
        chrome_tools = generator.generate_for_adapter("chrome")
        ```
    """
    
    def __init__(self, manager: "AdapterManager" = None):
        """
        初始化工具生成器。
        
        Args:
            manager: AdapterManager 实例，如果不提供则按需创建
        """
        self._manager = manager
        self._registry = MCPToolRegistry()
        self._generated_tools: Dict[str, List[MCPTool]] = {}
    
    @property
    def manager(self):
        """Lazy load manager."""
        if self._manager is None:
            from aibridge.core.manager import AdapterManager
            self._manager = AdapterManager()
        return self._manager
    
    def generate_for_adapter(
        self,
        adapter_id: str,
        prefix: Optional[str] = None,
        register: bool = True
    ) -> List[MCPTool]:
        """
        为特定适配器生成 MCP 工具。
        
        Args:
            adapter_id: 适配器 ID
            prefix: 工具名称前缀（默认使用适配器 ID）
            register: 是否自动注册到全局注册表
            
        Returns:
            生成的 MCP 工具列表
        """
        tools = []
        prefix = prefix or f"{adapter_id}_"
        
        # 获取适配器信息
        adapters = self.manager.list_adapters()
        adapter_info = None
        for a in adapters:
            if a.get("id") == adapter_id or a.get("name", "").lower() == adapter_id.lower():
                adapter_info = a
                break
        
        if not adapter_info:
            logger.warning(f"Adapter not found: {adapter_id}")
            return tools
        
        # 获取适配器支持的动作
        actions = adapter_info.get("actions", [])
        
        for action_name in actions:
            tool = MCPTool(
                name=f"{prefix}{action_name}",
                description=f"Execute {action_name} on {adapter_id}",
                parameters=[],  # 参数需要从适配器定义获取
                handler=self._create_action_handler(adapter_id, action_name)
            )
            tools.append(tool)
            
            if register:
                self._registry.register(tool)
        
        self._generated_tools[adapter_id] = tools
        return tools
    
    def generate_all(
        self,
        include_adapters: Optional[List[str]] = None,
        exclude_adapters: Optional[List[str]] = None,
        register: bool = True
    ) -> Dict[str, List[MCPTool]]:
        """
        为所有适配器生成 MCP 工具。
        
        Args:
            include_adapters: 要包含的适配器列表（不指定则包含所有）
            exclude_adapters: 要排除的适配器列表
            register: 是否自动注册到全局注册表
            
        Returns:
            每个适配器生成的工具字典
        """
        all_tools = {}
        exclude_set = set(exclude_adapters or [])
        
        for adapter in self.manager.list_adapters():
            adapter_id = adapter.get("id", "")
            
            # 检查包含/排除
            if include_adapters and adapter_id not in include_adapters:
                continue
            if adapter_id in exclude_set:
                continue
            
            tools = self.generate_for_adapter(adapter_id, register=register)
            if tools:
                all_tools[adapter_id] = tools
        
        return all_tools
    
    def list_generated_tools(self) -> List[dict]:
        """
        列出所有已生成的工具的 schema。
        
        Returns:
            工具 schema 列表
        """
        return self._registry.list_tools()
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """获取工具"""
        return self._registry.get(name)
    
    async def execute_tool(self, name: str, params: dict) -> dict:
        """执行工具"""
        return await self._registry.execute(name, params)
    
    def _create_action_handler(self, adapter_id: str, action_name: str):
        """创建动作处理器"""
        manager = self.manager
        
        async def handler(**params):
            # 获取适配器
            adapter = await manager.get_adapter(adapter_id)
            if not adapter:
                return {"success": False, "error": f"Adapter {adapter_id} not available"}
            
            try:
                # 执行动作
                result = await adapter.execute(
                    action=action_name,
                    target=params.get("target"),
                    value=params.get("value"),
                    options=params.get("options")
                )
                return {
                    "success": result.get("success", True) if isinstance(result, dict) else True,
                    "data": result.get("data") if isinstance(result, dict) else result,
                    "error": result.get("error") if isinstance(result, dict) else None
                }
            except Exception as e:
                logger.exception(f"Error executing {action_name} on {adapter_id}")
                return {"success": False, "error": str(e)}
        
        handler.__name__ = f"{adapter_id}_{action_name}"
        return handler
    
    @property
    def registry(self) -> MCPToolRegistry:
        """获取工具注册表"""
        return self._registry
