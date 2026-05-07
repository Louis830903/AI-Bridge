"""
MCP Server 注册中心

功能：
- 注册/注销 MCP Server
- 管理 MCP Server 生命周期
- 提供统一的工具调用入口
- 支持本地进程和远程 HTTP 两种模式
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Union
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MCPTransport(Enum):
    """MCP Server 传输方式"""
    STDIO = "stdio"      # 本地进程 (stdin/stdout)
    HTTP = "http"        # HTTP/SSE
    WEBSOCKET = "ws"     # WebSocket


@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    name: str                              # Server 名称
    transport: MCPTransport                # 传输方式
    command: Optional[str] = None          # STDIO 模式：启动命令
    args: List[str] = field(default_factory=list)  # 命令参数
    env: Dict[str, str] = field(default_factory=dict)  # 环境变量
    url: Optional[str] = None              # HTTP/WS 模式：Server URL
    timeout: float = 30.0                  # 超时时间(秒)
    auto_start: bool = True                # 是否自动启动
    health_check_interval: float = 60.0    # 健康检查间隔(秒)
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据


@dataclass
class ToolSchema:
    """MCP Tool Schema"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    server_name: str  # 所属 Server


@dataclass
class MCPServerProxy:
    """MCP Server 代理"""
    config: MCPServerConfig
    tools: List[ToolSchema] = field(default_factory=list)
    is_connected: bool = False
    _process: Optional[asyncio.subprocess.Process] = None
    _client: Any = None  # MCP Client instance
    
    async def start(self) -> bool:
        """启动 MCP Server"""
        if self.is_connected:
            return True
            
        try:
            if self.config.transport == MCPTransport.STDIO:
                return await self._start_stdio()
            elif self.config.transport == MCPTransport.HTTP:
                return await self._start_http()
            else:
                logger.error(f"Unsupported transport: {self.config.transport}")
                return False
        except Exception as e:
            logger.error(f"Failed to start MCP Server {self.config.name}: {e}")
            return False
    
    async def _start_stdio(self) -> bool:
        """启动 STDIO 模式的 MCP Server"""
        if not self.config.command:
            raise ValueError("STDIO transport requires 'command' in config")
        
        try:
            # 构建完整命令
            cmd = self.config.command
            args = self.config.args
            
            logger.info(f"Starting MCP Server: {cmd} {' '.join(args)}")
            
            # 启动子进程
            self._process = await asyncio.create_subprocess_exec(
                cmd, *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**dict(__import__('os').environ), **self.config.env}
            )
            
            self.is_connected = True
            logger.info(f"MCP Server {self.config.name} started (PID: {self._process.pid})")
            return True
            
        except FileNotFoundError:
            logger.error(f"Command not found: {self.config.command}")
            return False
        except Exception as e:
            logger.error(f"Failed to start STDIO server: {e}")
            return False
    
    async def _start_http(self) -> bool:
        """启动 HTTP 模式的 MCP Server（连接到远程）"""
        if not self.config.url:
            raise ValueError("HTTP transport requires 'url' in config")
        
        # HTTP 模式下不需要启动进程，只需要验证连接
        # NOTE: HTTP 健康检查在 Phase II 意图引擎中实现
        self.is_connected = True
        logger.info(f"MCP Server {self.config.name} connected to {self.config.url}")
        return True
    
    async def stop(self) -> None:
        """停止 MCP Server"""
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
            self._process = None
        
        self.is_connected = False
        logger.info(f"MCP Server {self.config.name} stopped")
    
    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """调用工具"""
        if not self.is_connected:
            raise RuntimeError(f"MCP Server {self.config.name} is not connected")
        
        # NOTE: MCP 协议调用在 Phase II 意图引擎中实现
        # 根据传输方式实现具体的调用逻辑
        logger.info(f"Calling tool {tool_name} on {self.config.name} with params: {params}")
        
        raise NotImplementedError("MCP protocol call not implemented yet")
    
    async def list_tools(self) -> List[ToolSchema]:
        """获取工具列表"""
        if not self.is_connected:
            raise RuntimeError(f"MCP Server {self.config.name} is not connected")
        
        # NOTE: 工具列表获取在 Phase II 意图引擎中实现
        return self.tools


class MCPRegistry:
    """
    MCP Server 注册中心
    
    功能：
    - 注册/注销 MCP Server
    - 管理 Server 生命周期
    - 提供统一的工具调用入口
    - 服务发现和健康检查
    
    使用示例：
    ```python
    registry = MCPRegistry()
    
    # 注册 Browser Use MCP
    await registry.register(MCPServerConfig(
        name="browser-use",
        transport=MCPTransport.STDIO,
        command="npx",
        args=["@anthropic/browser-use-mcp"],
    ))
    
    # 列出所有工具
    tools = await registry.list_all_tools()
    
    # 调用工具
    result = await registry.call_tool("browser-use", "navigate", {"url": "https://example.com"})
    ```
    """
    
    def __init__(self):
        self._servers: Dict[str, MCPServerProxy] = {}
        self._lock = asyncio.Lock()
        self._started = False
    
    async def register(self, config: MCPServerConfig) -> MCPServerProxy:
        """
        注册 MCP Server
        
        Args:
            config: MCP Server 配置
            
        Returns:
            MCPServerProxy: Server 代理对象
        """
        async with self._lock:
            if config.name in self._servers:
                logger.warning(f"MCP Server {config.name} already registered, updating config")
                await self._servers[config.name].stop()
            
            proxy = MCPServerProxy(config=config)
            self._servers[config.name] = proxy
            
            if config.auto_start and self._started:
                await proxy.start()
            
            logger.info(f"Registered MCP Server: {config.name}")
            return proxy
    
    async def unregister(self, name: str) -> None:
        """
        注销 MCP Server
        
        Args:
            name: Server 名称
        """
        async with self._lock:
            if name not in self._servers:
                logger.warning(f"MCP Server {name} not found")
                return
            
            await self._servers[name].stop()
            del self._servers[name]
            logger.info(f"Unregistered MCP Server: {name}")
    
    async def get(self, name: str) -> Optional[MCPServerProxy]:
        """
        获取 MCP Server 代理
        
        Args:
            name: Server 名称
            
        Returns:
            MCPServerProxy or None
        """
        return self._servers.get(name)
    
    async def start_all(self) -> None:
        """启动所有已注册的 MCP Server"""
        self._started = True
        for name, proxy in self._servers.items():
            if proxy.config.auto_start and not proxy.is_connected:
                try:
                    await proxy.start()
                except Exception as e:
                    logger.error(f"Failed to start {name}: {e}")
    
    async def stop_all(self) -> None:
        """停止所有 MCP Server"""
        self._started = False
        for proxy in self._servers.values():
            try:
                await proxy.stop()
            except Exception as e:
                logger.error(f"Failed to stop {proxy.config.name}: {e}")
    
    async def list_servers(self) -> List[str]:
        """列出所有已注册的 Server 名称"""
        return list(self._servers.keys())
    
    async def list_all_tools(self) -> List[ToolSchema]:
        """
        列出所有可用工具
        
        Returns:
            所有已注册 Server 的工具列表
        """
        all_tools = []
        for proxy in self._servers.values():
            if proxy.is_connected:
                try:
                    tools = await proxy.list_tools()
                    all_tools.extend(tools)
                except Exception as e:
                    logger.error(f"Failed to list tools from {proxy.config.name}: {e}")
        return all_tools
    
    async def call_tool(
        self, 
        server_name: str, 
        tool_name: str, 
        params: Dict[str, Any]
    ) -> Any:
        """
        调用指定 Server 的工具
        
        Args:
            server_name: Server 名称
            tool_name: 工具名称
            params: 调用参数
            
        Returns:
            工具执行结果
        """
        proxy = self._servers.get(server_name)
        if not proxy:
            raise ValueError(f"MCP Server {server_name} not found")
        
        return await proxy.call_tool(tool_name, params)
    
    async def call_tool_by_name(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        按工具名调用（自动查找所属 Server）
        
        Args:
            tool_name: 工具名称
            params: 调用参数
            
        Returns:
            工具执行结果
        """
        # 在所有 Server 中查找工具
        for proxy in self._servers.values():
            if proxy.is_connected:
                for tool in proxy.tools:
                    if tool.name == tool_name:
                        return await proxy.call_tool(tool_name, params)
        
        raise ValueError(f"Tool {tool_name} not found in any registered server")
    
    def get_server_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Server 状态"""
        return {
            name: {
                "connected": proxy.is_connected,
                "transport": proxy.config.transport.value,
                "tools_count": len(proxy.tools),
            }
            for name, proxy in self._servers.items()
        }
    
    async def __aenter__(self):
        await self.start_all()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop_all()
