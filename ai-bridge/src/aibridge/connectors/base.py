"""
连接器基类

定义所有 MCP Server 连接器的统一接口。
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ConnectorStatus(Enum):
    """连接器状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class ConnectorError(Exception):
    """连接器错误"""
    pass


@dataclass
class ConnectorConfig:
    """连接器配置基类"""
    name: str                              # 连接器名称
    enabled: bool = True                   # 是否启用
    auto_connect: bool = True              # 是否自动连接
    timeout: float = 30.0                  # 操作超时时间(秒)
    retry_count: int = 3                   # 重试次数
    retry_delay: float = 1.0               # 重试延迟(秒)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolInfo:
    """工具信息"""
    name: str
    description: str
    input_schema: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema,
        }


class MCPConnector(ABC):
    """
    MCP Server 连接器基类
    
    所有连接器必须实现此接口，提供统一的：
    - 生命周期管理 (start/stop)
    - 工具列表获取 (list_tools)
    - 工具调用 (call_tool)
    
    使用示例：
    ```python
    class BrowserConnector(MCPConnector):
        async def start(self):
            # 启动 Browser Use MCP Server
            ...
        
        async def call_tool(self, name, params):
            # 调用浏览器工具
            ...
    
    connector = BrowserConnector(config)
    async with connector:
        tools = await connector.list_tools()
        result = await connector.call_tool("navigate", {"url": "https://example.com"})
    ```
    """
    
    def __init__(self, config: ConnectorConfig):
        self._config = config
        self._status = ConnectorStatus.DISCONNECTED
        self._tools: List[ToolInfo] = []
        self._lock = asyncio.Lock()
    
    @property
    def name(self) -> str:
        """连接器名称"""
        return self._config.name
    
    @property
    def status(self) -> ConnectorStatus:
        """当前状态"""
        return self._status
    
    @property
    def is_connected(self) -> bool:
        """是否已连接"""
        return self._status == ConnectorStatus.CONNECTED
    
    @property
    def config(self) -> ConnectorConfig:
        """获取配置"""
        return self._config
    
    @abstractmethod
    async def _do_start(self) -> None:
        """
        实际的启动逻辑（子类实现）
        
        子类应在此方法中：
        1. 启动 MCP Server 进程或建立连接
        2. 获取并缓存工具列表
        """
        pass
    
    @abstractmethod
    async def _do_stop(self) -> None:
        """
        实际的停止逻辑（子类实现）
        
        子类应在此方法中：
        1. 关闭连接
        2. 停止 MCP Server 进程
        3. 清理资源
        """
        pass
    
    @abstractmethod
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """
        实际的工具调用逻辑（子类实现）
        
        Args:
            name: 工具名称
            params: 调用参数
            
        Returns:
            工具执行结果
        """
        pass
    
    async def start(self) -> None:
        """
        启动连接器
        
        包含重试逻辑和状态管理
        """
        if self._status == ConnectorStatus.CONNECTED:
            logger.debug(f"Connector {self.name} already connected")
            return
        
        async with self._lock:
            self._status = ConnectorStatus.CONNECTING
            last_error = None
            
            for attempt in range(self._config.retry_count):
                try:
                    await asyncio.wait_for(
                        self._do_start(),
                        timeout=self._config.timeout
                    )
                    self._status = ConnectorStatus.CONNECTED
                    logger.info(f"Connector {self.name} started successfully")
                    return
                    
                except asyncio.TimeoutError:
                    last_error = f"Timeout after {self._config.timeout}s"
                    logger.warning(f"Connector {self.name} start timeout (attempt {attempt + 1})")
                    
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"Connector {self.name} start failed (attempt {attempt + 1}): {e}")
                
                if attempt < self._config.retry_count - 1:
                    await asyncio.sleep(self._config.retry_delay)
            
            self._status = ConnectorStatus.ERROR
            raise ConnectorError(f"Failed to start connector {self.name}: {last_error}")
    
    async def stop(self) -> None:
        """停止连接器"""
        if self._status == ConnectorStatus.DISCONNECTED:
            return
        
        async with self._lock:
            try:
                await self._do_stop()
            except Exception as e:
                logger.error(f"Error stopping connector {self.name}: {e}")
            finally:
                self._status = ConnectorStatus.DISCONNECTED
                self._tools.clear()
                logger.info(f"Connector {self.name} stopped")
    
    async def restart(self) -> None:
        """重启连接器"""
        await self.stop()
        await self.start()
    
    async def list_tools(self) -> List[ToolInfo]:
        """
        获取工具列表
        
        Returns:
            工具信息列表
        """
        if not self.is_connected:
            raise ConnectorError(f"Connector {self.name} is not connected")
        return self._tools.copy()
    
    async def call_tool(self, name: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        调用工具
        
        Args:
            name: 工具名称
            params: 调用参数（可选）
            
        Returns:
            工具执行结果
            
        Raises:
            ConnectorError: 连接器未连接或调用失败
        """
        if not self.is_connected:
            raise ConnectorError(f"Connector {self.name} is not connected")
        
        params = params or {}
        
        try:
            result = await asyncio.wait_for(
                self._do_call_tool(name, params),
                timeout=self._config.timeout
            )
            logger.debug(f"Tool {name} called successfully on {self.name}")
            return result
            
        except asyncio.TimeoutError:
            raise ConnectorError(f"Tool {name} call timeout after {self._config.timeout}s")
            
        except Exception as e:
            raise ConnectorError(f"Tool {name} call failed: {e}") from e
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            是否健康
        """
        try:
            if not self.is_connected:
                return False
            # 子类可以覆盖此方法实现更复杂的健康检查
            return True
        except Exception:
            return False
    
    def get_status_info(self) -> Dict[str, Any]:
        """获取状态信息"""
        return {
            "name": self.name,
            "status": self._status.value,
            "tools_count": len(self._tools),
            "config": {
                "enabled": self._config.enabled,
                "timeout": self._config.timeout,
            }
        }
    
    async def __aenter__(self):
        """异步上下文管理器入口"""
        if self._config.auto_connect:
            await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.stop()


class StdioMCPConnector(MCPConnector):
    """
    基于 STDIO 的 MCP 连接器
    
    通过启动子进程并使用 stdin/stdout 通信
    """
    
    def __init__(
        self, 
        config: ConnectorConfig,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ):
        super().__init__(config)
        self._command = command
        self._args = args or []
        self._env = env or {}
        self._process: Optional[asyncio.subprocess.Process] = None
    
    async def _do_start(self) -> None:
        """启动 MCP Server 子进程"""
        import os
        
        logger.info(f"Starting MCP Server: {self._command} {' '.join(self._args)}")
        
        # 合并环境变量
        env = {**os.environ, **self._env}
        
        self._process = await asyncio.create_subprocess_exec(
            self._command,
            *self._args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )
        
        logger.info(f"MCP Server started with PID: {self._process.pid}")
        
        # NOTE: MCP 协议握手在 Phase II 意图引擎中实现
    
    async def _do_stop(self) -> None:
        """停止子进程"""
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
                await self._process.wait()
            self._process = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 STDIO 调用工具"""
        if not self._process:
            raise ConnectorError("Process not started")
        
        # NOTE: MCP tool call 在 Phase II 意图引擎中实现
        raise NotImplementedError("STDIO MCP protocol not implemented yet")


class HttpMCPConnector(MCPConnector):
    """
    基于 HTTP/SSE 的 MCP 连接器
    
    连接到远程 MCP Server
    """
    
    def __init__(
        self, 
        config: ConnectorConfig,
        url: str,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(config)
        self._url = url
        self._headers = headers or {}
        self._session = None  # aiohttp session
    
    async def _do_start(self) -> None:
        """建立 HTTP 连接"""
        try:
            import aiohttp
            self._session = aiohttp.ClientSession(headers=self._headers)
            
            # 验证连接
            async with self._session.get(f"{self._url}/health") as resp:
                if resp.status != 200:
                    raise ConnectorError(f"Health check failed: {resp.status}")
            
            logger.info(f"Connected to MCP Server at {self._url}")
            
        except ImportError:
            raise ConnectorError("aiohttp is required for HTTP connector: pip install aiohttp")
    
    async def _do_stop(self) -> None:
        """关闭 HTTP 连接"""
        if self._session:
            await self._session.close()
            self._session = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 HTTP 调用工具"""
        if not self._session:
            raise ConnectorError("Session not established")
        
        # NOTE: MCP over HTTP 在 Phase II 意图引擎中实现
        raise NotImplementedError("HTTP MCP protocol not implemented yet")
