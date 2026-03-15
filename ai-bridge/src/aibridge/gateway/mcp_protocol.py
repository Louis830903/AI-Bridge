"""
MCP 协议通信层

实现 Model Context Protocol (MCP) 的 JSON-RPC over STDIO 通信。

MCP 协议规范：
- 传输层：STDIO (stdin/stdout) 或 HTTP/SSE
- 消息格式：JSON-RPC 2.0
- 主要消息类型：
  - initialize: 初始化握手
  - tools/list: 获取工具列表
  - tools/call: 调用工具
  - resources/list: 获取资源列表
  - prompts/list: 获取提示列表

参考：https://modelcontextprotocol.io/docs
"""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union
from enum import Enum

logger = logging.getLogger(__name__)


class MCPMethod(str, Enum):
    """MCP 方法名"""
    # 生命周期
    INITIALIZE = "initialize"
    INITIALIZED = "notifications/initialized"
    SHUTDOWN = "shutdown"
    
    # 工具
    TOOLS_LIST = "tools/list"
    TOOLS_CALL = "tools/call"
    
    # 资源
    RESOURCES_LIST = "resources/list"
    RESOURCES_READ = "resources/read"
    
    # 提示
    PROMPTS_LIST = "prompts/list"
    PROMPTS_GET = "prompts/get"
    
    # 日志
    LOG = "notifications/message"


@dataclass
class JSONRPCRequest:
    """JSON-RPC 2.0 请求"""
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Union[str, int]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            "jsonrpc": "2.0",
            "method": self.method,
        }
        if self.params is not None:
            d["params"] = self.params
        if self.id is not None:
            d["id"] = self.id
        return d
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())


@dataclass
class JSONRPCResponse:
    """JSON-RPC 2.0 响应"""
    id: Optional[Union[str, int]]
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JSONRPCResponse":
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error"),
        )
    
    @property
    def is_error(self) -> bool:
        return self.error is not None


@dataclass
class MCPTool:
    """MCP 工具定义"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPTool":
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            input_schema=data.get("inputSchema", {}),
        )


@dataclass
class MCPClientInfo:
    """MCP 客户端信息"""
    name: str = "AI-Bridge"
    version: str = "3.0.0"


@dataclass
class MCPServerInfo:
    """MCP 服务端信息"""
    name: str = ""
    version: str = ""
    protocol_version: str = ""


class MCPProtocol:
    """
    MCP 协议通信类
    
    实现 JSON-RPC over STDIO 的 MCP 通信。
    
    使用示例：
    ```python
    protocol = MCPProtocol()
    
    # 启动 MCP Server 进程
    await protocol.start("npx", ["@anthropic-ai/browser-use-mcp"])
    
    # 初始化握手
    server_info = await protocol.initialize()
    
    # 获取工具列表
    tools = await protocol.list_tools()
    
    # 调用工具
    result = await protocol.call_tool("navigate", {"url": "https://example.com"})
    
    # 关闭
    await protocol.shutdown()
    ```
    """
    
    def __init__(self, timeout: float = 30.0):
        self._timeout = timeout
        self._process: Optional[asyncio.subprocess.Process] = None
        self._server_info: Optional[MCPServerInfo] = None
        self._tools: List[MCPTool] = []
        self._request_id = 0
        self._pending_requests: Dict[Union[str, int], asyncio.Future] = {}
        self._read_task: Optional[asyncio.Task] = None
        self._initialized = False
    
    @property
    def is_running(self) -> bool:
        return self._process is not None and self._process.returncode is None
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def server_info(self) -> Optional[MCPServerInfo]:
        return self._server_info
    
    @property
    def tools(self) -> List[MCPTool]:
        return self._tools.copy()
    
    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id
    
    async def start(
        self,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        """
        启动 MCP Server 进程
        
        Args:
            command: 命令（如 "npx"）
            args: 命令参数
            env: 环境变量
        """
        import os
        
        args = args or []
        full_env = {**os.environ, **(env or {})}
        
        logger.info(f"Starting MCP Server: {command} {' '.join(args)}")
        
        self._process = await asyncio.create_subprocess_exec(
            command,
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=full_env,
        )
        
        # 启动读取任务
        self._read_task = asyncio.create_task(self._read_loop())
        
        logger.info(f"MCP Server started with PID: {self._process.pid}")
    
    async def _read_loop(self) -> None:
        """读取 stdout 并分发响应"""
        if not self._process or not self._process.stdout:
            return
        
        buffer = ""
        while self.is_running:
            try:
                # 读取一行
                line = await self._process.stdout.readline()
                if not line:
                    break
                
                text = line.decode("utf-8").strip()
                if not text:
                    continue
                
                # 尝试解析 JSON
                try:
                    data = json.loads(text)
                    await self._handle_message(data)
                except json.JSONDecodeError:
                    # 可能是日志输出，忽略
                    logger.debug(f"Non-JSON output: {text}")
                    
            except Exception as e:
                logger.error(f"Error reading from MCP Server: {e}")
                break
    
    async def _handle_message(self, data: Dict[str, Any]) -> None:
        """处理接收到的消息"""
        # 检查是否是响应
        if "id" in data and ("result" in data or "error" in data):
            response = JSONRPCResponse.from_dict(data)
            request_id = response.id
            
            if request_id in self._pending_requests:
                future = self._pending_requests.pop(request_id)
                if not future.done():
                    future.set_result(response)
        
        # 检查是否是通知
        elif "method" in data and "id" not in data:
            await self._handle_notification(data)
    
    async def _handle_notification(self, data: Dict[str, Any]) -> None:
        """处理通知消息"""
        method = data.get("method", "")
        params = data.get("params", {})
        
        if method == MCPMethod.LOG:
            level = params.get("level", "info")
            message = params.get("data", "")
            logger.log(
                getattr(logging, level.upper(), logging.INFO),
                f"[MCP Server] {message}"
            )
    
    async def _send_request(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> JSONRPCResponse:
        """
        发送请求并等待响应
        
        Args:
            method: 方法名
            params: 参数
            
        Returns:
            JSONRPCResponse
        """
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP Server not started")
        
        # 创建请求
        request_id = self._next_id()
        request = JSONRPCRequest(method=method, params=params, id=request_id)
        
        # 创建 Future 等待响应
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future
        
        try:
            # 发送请求
            message = request.to_json() + "\n"
            self._process.stdin.write(message.encode("utf-8"))
            await self._process.stdin.drain()
            
            logger.debug(f"Sent: {message.strip()}")
            
            # 等待响应
            response = await asyncio.wait_for(future, timeout=self._timeout)
            return response
            
        except asyncio.TimeoutError:
            self._pending_requests.pop(request_id, None)
            raise TimeoutError(f"Request {method} timed out after {self._timeout}s")
        except Exception as e:
            self._pending_requests.pop(request_id, None)
            raise
    
    async def _send_notification(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> None:
        """发送通知（无需响应）"""
        if not self._process or not self._process.stdin:
            raise RuntimeError("MCP Server not started")
        
        request = JSONRPCRequest(method=method, params=params, id=None)
        message = request.to_json() + "\n"
        self._process.stdin.write(message.encode("utf-8"))
        await self._process.stdin.drain()
        
        logger.debug(f"Sent notification: {message.strip()}")
    
    async def initialize(
        self,
        client_info: Optional[MCPClientInfo] = None,
    ) -> MCPServerInfo:
        """
        初始化 MCP 连接
        
        这是 MCP 协议的握手过程，必须在调用其他方法之前执行。
        
        Args:
            client_info: 客户端信息
            
        Returns:
            MCPServerInfo: 服务端信息
        """
        client_info = client_info or MCPClientInfo()
        
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
            },
            "clientInfo": {
                "name": client_info.name,
                "version": client_info.version,
            }
        }
        
        response = await self._send_request(MCPMethod.INITIALIZE, params)
        
        if response.is_error:
            raise RuntimeError(f"Initialize failed: {response.error}")
        
        result = response.result or {}
        
        self._server_info = MCPServerInfo(
            name=result.get("serverInfo", {}).get("name", ""),
            version=result.get("serverInfo", {}).get("version", ""),
            protocol_version=result.get("protocolVersion", ""),
        )
        
        # 发送 initialized 通知
        await self._send_notification(MCPMethod.INITIALIZED)
        
        self._initialized = True
        logger.info(f"MCP initialized: {self._server_info.name} v{self._server_info.version}")
        
        return self._server_info
    
    async def list_tools(self) -> List[MCPTool]:
        """
        获取工具列表
        
        Returns:
            工具列表
        """
        if not self._initialized:
            raise RuntimeError("MCP not initialized. Call initialize() first.")
        
        response = await self._send_request(MCPMethod.TOOLS_LIST)
        
        if response.is_error:
            raise RuntimeError(f"List tools failed: {response.error}")
        
        result = response.result or {}
        tools_data = result.get("tools", [])
        
        self._tools = [MCPTool.from_dict(t) for t in tools_data]
        
        logger.info(f"Got {len(self._tools)} tools from MCP Server")
        return self._tools.copy()
    
    async def call_tool(
        self,
        name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        调用工具
        
        Args:
            name: 工具名称
            arguments: 调用参数
            
        Returns:
            工具执行结果
        """
        if not self._initialized:
            raise RuntimeError("MCP not initialized. Call initialize() first.")
        
        params = {
            "name": name,
            "arguments": arguments or {},
        }
        
        response = await self._send_request(MCPMethod.TOOLS_CALL, params)
        
        if response.is_error:
            raise RuntimeError(f"Tool call failed: {response.error}")
        
        result = response.result or {}
        
        # MCP 工具调用结果格式
        content = result.get("content", [])
        if content:
            # 返回第一个内容项
            first = content[0]
            if first.get("type") == "text":
                return first.get("text")
            elif first.get("type") == "image":
                return first.get("data")
            else:
                return first
        
        return result
    
    async def shutdown(self) -> None:
        """关闭 MCP 连接"""
        if self._initialized:
            try:
                await self._send_request(MCPMethod.SHUTDOWN)
            except Exception as e:
                logger.warning(f"Shutdown request failed: {e}")
        
        self._initialized = False
        
        # 取消读取任务
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
            self._read_task = None
        
        # 终止进程
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            self._process = None
        
        # 清理待处理请求
        for future in self._pending_requests.values():
            if not future.done():
                future.set_exception(RuntimeError("MCP connection closed"))
        self._pending_requests.clear()
        
        logger.info("MCP connection closed")
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.shutdown()
