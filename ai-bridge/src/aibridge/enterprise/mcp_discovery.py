"""
MCP Server 动态发现

提供 MCP Server 的自动发现和管理：
- 多源配置发现（文件、环境变量、注册中心）
- 配置热更新
- 服务健康监控
- 连接池管理
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Awaitable, Any, Set
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
import asyncio
import json
import logging
import os

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc)


class ServerStatus(str, Enum):
    """Server 状态"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    CONNECTING = "connecting"
    DISCONNECTED = "disconnected"


class TransportType(str, Enum):
    """传输类型"""
    STDIO = "stdio"
    SSE = "sse"
    WEBSOCKET = "websocket"
    HTTP = "http"


@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    # 基础信息
    name: str
    command: Optional[str] = None  # STDIO 命令
    args: List[str] = field(default_factory=list)
    url: Optional[str] = None  # HTTP/SSE/WebSocket URL
    
    # 传输配置
    transport: TransportType = TransportType.STDIO
    
    # 环境变量
    env: Dict[str, str] = field(default_factory=dict)
    
    # 连接配置
    timeout_seconds: float = 30.0
    retry_count: int = 3
    retry_delay_seconds: float = 1.0
    
    # 健康检查
    health_check_interval: float = 60.0
    health_check_enabled: bool = True
    
    # 元数据
    description: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # 状态（运行时）
    status: ServerStatus = ServerStatus.UNKNOWN
    last_health_check: Optional[datetime] = None
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "command": self.command,
            "args": self.args,
            "url": self.url,
            "transport": self.transport.value,
            "env": self.env,
            "timeout_seconds": self.timeout_seconds,
            "retry_count": self.retry_count,
            "retry_delay_seconds": self.retry_delay_seconds,
            "health_check_interval": self.health_check_interval,
            "health_check_enabled": self.health_check_enabled,
            "description": self.description,
            "tags": self.tags,
            "metadata": self.metadata,
            "status": self.status.value,
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
            "error_message": self.error_message,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPServerConfig":
        """从字典创建"""
        return cls(
            name=data["name"],
            command=data.get("command"),
            args=data.get("args", []),
            url=data.get("url"),
            transport=TransportType(data.get("transport", "stdio")),
            env=data.get("env", {}),
            timeout_seconds=data.get("timeout_seconds", 30.0),
            retry_count=data.get("retry_count", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 1.0),
            health_check_interval=data.get("health_check_interval", 60.0),
            health_check_enabled=data.get("health_check_enabled", True),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class DiscoverySource:
    """发现源"""
    name: str
    source_type: str  # file, env, registry, manual
    priority: int = 0  # 优先级，数字越大优先级越高
    last_update: Optional[datetime] = None


class ConfigFileWatcher:
    """配置文件监视器"""
    
    def __init__(
        self,
        file_path: str,
        on_change: Callable[[], Awaitable[None]],
        poll_interval: float = 5.0,
    ):
        self._file_path = Path(file_path)
        self._on_change = on_change
        self._poll_interval = poll_interval
        self._last_mtime: Optional[float] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动监视"""
        if self._running:
            return
        
        self._running = True
        if self._file_path.exists():
            self._last_mtime = self._file_path.stat().st_mtime
        self._task = asyncio.create_task(self._watch_loop())
    
    async def stop(self) -> None:
        """停止监视"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _watch_loop(self) -> None:
        """监视循环"""
        while self._running:
            await asyncio.sleep(self._poll_interval)
            
            if not self._file_path.exists():
                continue
            
            current_mtime = self._file_path.stat().st_mtime
            if self._last_mtime is None or current_mtime > self._last_mtime:
                self._last_mtime = current_mtime
                logger.info(f"Config file changed: {self._file_path}")
                try:
                    await self._on_change()
                except Exception as e:
                    logger.error(f"Error handling config change: {e}")


class MCPServerDiscovery:
    """MCP Server 动态发现服务
    
    支持多种发现源：
    - 配置文件（Claude Desktop 格式）
    - 环境变量
    - Registry 注册中心
    - 手动注册
    """
    
    def __init__(self):
        self._servers: Dict[str, MCPServerConfig] = {}
        self._sources: Dict[str, DiscoverySource] = {}
        self._file_watchers: List[ConfigFileWatcher] = []
        self._lock = asyncio.Lock()
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        
        # 回调
        self._on_server_added: List[Callable[[MCPServerConfig], Awaitable[None]]] = []
        self._on_server_removed: List[Callable[[str], Awaitable[None]]] = []
        self._on_server_updated: List[Callable[[MCPServerConfig], Awaitable[None]]] = []
        self._on_health_changed: List[Callable[[str, ServerStatus, ServerStatus], Awaitable[None]]] = []
    
    # ========== 生命周期 ==========
    
    async def start(self) -> None:
        """启动发现服务"""
        if self._running:
            return
        
        self._running = True
        
        # 启动文件监视器
        for watcher in self._file_watchers:
            await watcher.start()
        
        # 启动健康检查
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        
        logger.info("MCPServerDiscovery started")
    
    async def stop(self) -> None:
        """停止发现服务"""
        self._running = False
        
        # 停止文件监视器
        for watcher in self._file_watchers:
            await watcher.stop()
        
        # 停止健康检查
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        logger.info("MCPServerDiscovery stopped")
    
    # ========== 发现源配置 ==========
    
    async def add_config_file(
        self,
        file_path: str,
        source_name: str = None,
        priority: int = 0,
        watch: bool = True,
    ) -> None:
        """添加配置文件源
        
        支持 Claude Desktop 格式的配置文件
        """
        path = Path(file_path)
        source_name = source_name or f"file:{path.name}"
        
        self._sources[source_name] = DiscoverySource(
            name=source_name,
            source_type="file",
            priority=priority,
        )
        
        # 加载配置
        await self._load_from_file(path, source_name)
        
        # 设置文件监视
        if watch:
            watcher = ConfigFileWatcher(
                file_path,
                lambda: self._load_from_file(path, source_name),
            )
            self._file_watchers.append(watcher)
            if self._running:
                await watcher.start()
    
    async def add_env_source(
        self,
        prefix: str = "MCP_SERVER_",
        source_name: str = "env",
        priority: int = 10,
    ) -> None:
        """从环境变量添加
        
        格式: MCP_SERVER_<NAME>=command:args:url
        """
        self._sources[source_name] = DiscoverySource(
            name=source_name,
            source_type="env",
            priority=priority,
        )
        
        await self._load_from_env(prefix, source_name)
    
    async def register(
        self,
        config: MCPServerConfig,
        source_name: str = "manual",
    ) -> None:
        """手动注册 Server"""
        if source_name not in self._sources:
            self._sources[source_name] = DiscoverySource(
                name=source_name,
                source_type="manual",
                priority=100,  # 手动注册优先级最高
            )
        
        async with self._lock:
            is_new = config.name not in self._servers
            self._servers[config.name] = config
        
        if is_new:
            await self._notify_server_added(config)
        else:
            await self._notify_server_updated(config)
    
    async def unregister(self, name: str) -> bool:
        """注销 Server"""
        async with self._lock:
            if name not in self._servers:
                return False
            del self._servers[name]
        
        await self._notify_server_removed(name)
        return True
    
    # ========== 查询接口 ==========
    
    async def get(self, name: str) -> Optional[MCPServerConfig]:
        """获取 Server 配置"""
        return self._servers.get(name)
    
    async def list_servers(
        self,
        status: Optional[ServerStatus] = None,
        tags: Optional[List[str]] = None,
        transport: Optional[TransportType] = None,
    ) -> List[MCPServerConfig]:
        """列出 Servers"""
        servers = list(self._servers.values())
        
        if status:
            servers = [s for s in servers if s.status == status]
        
        if tags:
            def has_tag(server: MCPServerConfig) -> bool:
                return any(t in server.tags for t in tags)
            servers = [s for s in servers if has_tag(s)]
        
        if transport:
            servers = [s for s in servers if s.transport == transport]
        
        return servers
    
    async def get_healthy_servers(self) -> List[MCPServerConfig]:
        """获取健康的 Servers"""
        return await self.list_servers(status=ServerStatus.HEALTHY)
    
    async def count(self, status: Optional[ServerStatus] = None) -> int:
        """统计数量"""
        servers = await self.list_servers(status=status)
        return len(servers)
    
    # ========== 回调注册 ==========
    
    def on_server_added(self, callback: Callable[[MCPServerConfig], Awaitable[None]]) -> None:
        """注册回调：Server 添加时"""
        self._on_server_added.append(callback)
    
    def on_server_removed(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """注册回调：Server 移除时"""
        self._on_server_removed.append(callback)
    
    def on_server_updated(self, callback: Callable[[MCPServerConfig], Awaitable[None]]) -> None:
        """注册回调：Server 更新时"""
        self._on_server_updated.append(callback)
    
    def on_health_changed(
        self,
        callback: Callable[[str, ServerStatus, ServerStatus], Awaitable[None]]
    ) -> None:
        """注册回调：健康状态变化时"""
        self._on_health_changed.append(callback)
    
    # ========== 内部方法 ==========
    
    async def _load_from_file(self, path: Path, source_name: str) -> None:
        """从文件加载配置"""
        if not path.exists():
            logger.warning(f"Config file not found: {path}")
            return
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # 支持 Claude Desktop 格式
            mcp_servers = data.get("mcpServers", {})
            
            loaded_names: Set[str] = set()
            for name, server_data in mcp_servers.items():
                config = self._parse_claude_desktop_config(name, server_data)
                async with self._lock:
                    is_new = name not in self._servers
                    self._servers[name] = config
                    loaded_names.add(name)
                
                if is_new:
                    await self._notify_server_added(config)
                else:
                    await self._notify_server_updated(config)
            
            # 更新源的时间戳
            self._sources[source_name].last_update = _utcnow()
            
            logger.info(f"Loaded {len(loaded_names)} servers from {path}")
            
        except Exception as e:
            logger.error(f"Failed to load config file {path}: {e}")
    
    def _parse_claude_desktop_config(
        self,
        name: str,
        data: Dict[str, Any]
    ) -> MCPServerConfig:
        """解析 Claude Desktop 格式的配置"""
        return MCPServerConfig(
            name=name,
            command=data.get("command"),
            args=data.get("args", []),
            url=data.get("url"),
            transport=TransportType(data.get("transport", "stdio")),
            env=data.get("env", {}),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )
    
    async def _load_from_env(self, prefix: str, source_name: str) -> None:
        """从环境变量加载"""
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue
            
            name = key[len(prefix):].lower()
            
            # 解析格式: command|args|url 或 JSON
            try:
                if value.startswith("{"):
                    # JSON 格式
                    data = json.loads(value)
                    config = MCPServerConfig.from_dict({**data, "name": name})
                else:
                    # 简单格式: command|arg1,arg2|url
                    parts = value.split("|")
                    config = MCPServerConfig(
                        name=name,
                        command=parts[0] if len(parts) > 0 else None,
                        args=parts[1].split(",") if len(parts) > 1 and parts[1] else [],
                        url=parts[2] if len(parts) > 2 else None,
                    )
                
                async with self._lock:
                    is_new = name not in self._servers
                    self._servers[name] = config
                
                if is_new:
                    await self._notify_server_added(config)
                    
            except Exception as e:
                logger.warning(f"Failed to parse env {key}: {e}")
        
        self._sources[source_name].last_update = _utcnow()
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self._running:
            await asyncio.sleep(30)  # 基础间隔
            
            for name, server in list(self._servers.items()):
                if not server.health_check_enabled:
                    continue
                
                # 检查是否需要健康检查
                if server.last_health_check:
                    elapsed = (_utcnow() - server.last_health_check).total_seconds()
                    if elapsed < server.health_check_interval:
                        continue
                
                old_status = server.status
                new_status = await self._check_server_health(server)
                
                async with self._lock:
                    if name in self._servers:
                        self._servers[name].status = new_status
                        self._servers[name].last_health_check = _utcnow()
                
                if old_status != new_status:
                    await self._notify_health_changed(name, old_status, new_status)
    
    async def _check_server_health(self, server: MCPServerConfig) -> ServerStatus:
        """检查 Server 健康状态"""
        if server.transport == TransportType.STDIO:
            return await self._check_stdio_health(server)
        elif server.transport in (TransportType.HTTP, TransportType.SSE):
            return await self._check_http_health(server)
        else:
            return ServerStatus.UNKNOWN
    
    async def _check_stdio_health(self, server: MCPServerConfig) -> ServerStatus:
        """检查 STDIO Server 健康"""
        if not server.command:
            return ServerStatus.UNHEALTHY
        
        # 检查命令是否存在
        import shutil
        if not shutil.which(server.command):
            server.error_message = f"Command not found: {server.command}"
            return ServerStatus.UNHEALTHY
        
        return ServerStatus.HEALTHY
    
    async def _check_http_health(self, server: MCPServerConfig) -> ServerStatus:
        """检查 HTTP Server 健康"""
        if not server.url:
            return ServerStatus.UNHEALTHY
        
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    server.url,
                    timeout=aiohttp.ClientTimeout(total=server.timeout_seconds)
                ) as resp:
                    if resp.status < 500:
                        return ServerStatus.HEALTHY
                    else:
                        server.error_message = f"HTTP {resp.status}"
                        return ServerStatus.UNHEALTHY
        except ImportError:
            return ServerStatus.UNKNOWN
        except Exception as e:
            server.error_message = str(e)
            return ServerStatus.UNHEALTHY
    
    async def _notify_server_added(self, config: MCPServerConfig) -> None:
        """通知 Server 添加"""
        logger.info(f"Server added: {config.name}")
        for callback in self._on_server_added:
            try:
                await callback(config)
            except Exception as e:
                logger.warning(f"Server added callback error: {e}")
    
    async def _notify_server_removed(self, name: str) -> None:
        """通知 Server 移除"""
        logger.info(f"Server removed: {name}")
        for callback in self._on_server_removed:
            try:
                await callback(name)
            except Exception as e:
                logger.warning(f"Server removed callback error: {e}")
    
    async def _notify_server_updated(self, config: MCPServerConfig) -> None:
        """通知 Server 更新"""
        logger.debug(f"Server updated: {config.name}")
        for callback in self._on_server_updated:
            try:
                await callback(config)
            except Exception as e:
                logger.warning(f"Server updated callback error: {e}")
    
    async def _notify_health_changed(
        self,
        name: str,
        old_status: ServerStatus,
        new_status: ServerStatus
    ) -> None:
        """通知健康状态变化"""
        logger.info(f"Server {name} health: {old_status.value} -> {new_status.value}")
        for callback in self._on_health_changed:
            try:
                await callback(name, old_status, new_status)
            except Exception as e:
                logger.warning(f"Health changed callback error: {e}")


class MCPConnectionPool:
    """MCP 连接池
    
    管理与 MCP Server 的连接
    """
    
    def __init__(
        self,
        discovery: MCPServerDiscovery,
        max_connections_per_server: int = 5,
    ):
        self._discovery = discovery
        self._max_connections = max_connections_per_server
        self._connections: Dict[str, List[Any]] = {}  # name -> connections
        self._lock = asyncio.Lock()
    
    async def get_connection(self, server_name: str) -> Optional[Any]:
        """获取连接
        
        注意：实际连接实现依赖具体的 MCP SDK
        这里提供连接池管理框架
        """
        async with self._lock:
            if server_name not in self._connections:
                self._connections[server_name] = []
            
            pool = self._connections[server_name]
            
            # 尝试复用现有连接
            while pool:
                conn = pool.pop(0)
                if await self._is_connection_valid(conn):
                    return conn
            
            # 创建新连接
            server = await self._discovery.get(server_name)
            if not server:
                return None
            
            return await self._create_connection(server)
    
    async def release_connection(self, server_name: str, conn: Any) -> None:
        """释放连接回池"""
        async with self._lock:
            if server_name not in self._connections:
                self._connections[server_name] = []
            
            pool = self._connections[server_name]
            if len(pool) < self._max_connections:
                pool.append(conn)
    
    async def close_all(self) -> None:
        """关闭所有连接"""
        async with self._lock:
            for pool in self._connections.values():
                for conn in pool:
                    await self._close_connection(conn)
            self._connections.clear()
    
    async def _is_connection_valid(self, conn: Any) -> bool:
        """检查连接是否有效"""
        # 由子类实现
        return True
    
    async def _create_connection(self, server: MCPServerConfig) -> Optional[Any]:
        """创建连接"""
        # 由子类实现具体的连接创建逻辑
        logger.debug(f"Creating connection to {server.name}")
        return None
    
    async def _close_connection(self, conn: Any) -> None:
        """关闭连接"""
        # 由子类实现
        pass


# ========== 便捷函数 ==========

async def discover_from_claude_desktop() -> MCPServerDiscovery:
    """从 Claude Desktop 配置发现 MCP Servers
    
    自动查找常见配置文件位置
    """
    discovery = MCPServerDiscovery()
    
    # Claude Desktop 配置文件位置
    possible_paths = [
        Path.home() / ".config" / "claude" / "claude_desktop_config.json",
        Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
        Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json",
    ]
    
    for path in possible_paths:
        if path.exists():
            await discovery.add_config_file(str(path))
            break
    
    return discovery


async def discover_from_env(prefix: str = "MCP_SERVER_") -> MCPServerDiscovery:
    """从环境变量发现 MCP Servers"""
    discovery = MCPServerDiscovery()
    await discovery.add_env_source(prefix)
    return discovery
