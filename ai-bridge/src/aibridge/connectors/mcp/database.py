"""
数据库连接器

代理到成熟的数据库 MCP Server：
- PostgreSQL MCP
- SQLite MCP

提供统一的数据库操作接口。
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from ..base import (
    MCPConnector,
    ConnectorConfig,
    ConnectorStatus,
    ConnectorError,
    ToolInfo,
)
from aibridge.gateway.mcp_protocol import MCPProtocol

logger = logging.getLogger(__name__)


class DatabaseBackend(Enum):
    """数据库后端"""
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"
    AUTO = "auto"


@dataclass
class DatabaseConnectorConfig(ConnectorConfig):
    """数据库连接器配置"""
    backend: DatabaseBackend = DatabaseBackend.AUTO
    
    # PostgreSQL 配置
    pg_host: str = "localhost"
    pg_port: int = 5432
    pg_database: str = "postgres"
    pg_user: str = "postgres"
    pg_password: str = ""
    pg_connection_string: Optional[str] = None  # 优先使用连接字符串
    
    # SQLite 配置
    sqlite_path: str = ":memory:"  # 默认内存数据库
    
    # 通用配置
    read_only: bool = False  # 只读模式，更安全


# 后端启动配置
DATABASE_BACKEND_CONFIGS = {
    DatabaseBackend.POSTGRESQL: {
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-postgres"],
        "check_command": "npx",
        "check_args": ["--version"],
        "env_prefix": "POSTGRES_",
    },
    DatabaseBackend.SQLITE: {
        "command": "npx",
        "args": ["-y", "@anthropic-ai/mcp-server-sqlite"],
        "check_command": "npx",
        "check_args": ["--version"],
        "env_prefix": "SQLITE_",
    },
}


class DatabaseConnector(MCPConnector):
    """
    数据库连接器
    
    代理到成熟的数据库 MCP Server，提供统一的数据库操作接口。
    
    支持的后端：
    - PostgreSQL MCP: 企业级关系数据库
    - SQLite MCP: 轻量级嵌入式数据库
    
    使用示例：
    ```python
    # PostgreSQL
    config = DatabaseConnectorConfig(
        name="postgres",
        backend=DatabaseBackend.POSTGRESQL,
        pg_connection_string="postgresql://user:pass@localhost/mydb"
    )
    
    # SQLite
    config = DatabaseConnectorConfig(
        name="sqlite",
        backend=DatabaseBackend.SQLITE,
        sqlite_path="./data.db"
    )
    
    connector = DatabaseConnector(config)
    
    async with connector:
        # 执行查询
        result = await connector.query("SELECT * FROM users LIMIT 10")
        
        # 获取表结构
        schema = await connector.get_schema("users")
        
        # 列出所有表
        tables = await connector.list_tables()
    ```
    """
    
    def __init__(self, config: DatabaseConnectorConfig):
        super().__init__(config)
        self._db_config = config
        self._active_backend: Optional[DatabaseBackend] = None
        self._mcp: Optional[MCPProtocol] = None
    
    @property
    def active_backend(self) -> Optional[DatabaseBackend]:
        """当前使用的后端"""
        return self._active_backend
    
    @property
    def mcp_protocol(self) -> Optional[MCPProtocol]:
        """MCP 协议实例"""
        return self._mcp
    
    async def _detect_available_backend(self) -> Optional[DatabaseBackend]:
        """检测可用的后端"""
        backends_to_check = [
            DatabaseBackend.POSTGRESQL,
            DatabaseBackend.SQLITE,
        ]
        
        for backend in backends_to_check:
            if await self._is_backend_available(backend):
                logger.info(f"Detected available database backend: {backend.value}")
                return backend
        
        return None
    
    async def _is_backend_available(self, backend: DatabaseBackend) -> bool:
        """检查后端是否可用"""
        import shutil
        
        config = DATABASE_BACKEND_CONFIGS.get(backend)
        if not config:
            return False
        
        command = config["check_command"]
        if not shutil.which(command):
            return False
        
        try:
            proc = await asyncio.create_subprocess_exec(
                command,
                *config["check_args"],
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10.0)
            return proc.returncode == 0
        except Exception:
            return False
    
    async def _do_start(self) -> None:
        """启动数据库后端"""
        if self._db_config.backend == DatabaseBackend.AUTO:
            self._active_backend = await self._detect_available_backend()
            if not self._active_backend:
                raise ConnectorError(
                    "No available database backend found. "
                    "Please install: @modelcontextprotocol/server-postgres or @anthropic-ai/mcp-server-sqlite"
                )
        else:
            self._active_backend = self._db_config.backend
            if not await self._is_backend_available(self._active_backend):
                raise ConnectorError(f"Database backend {self._active_backend.value} is not available")
        
        await self._start_backend(self._active_backend)
    
    async def _start_backend(self, backend: DatabaseBackend) -> None:
        """启动指定后端并完成 MCP 协议握手"""
        import os
        
        config = DATABASE_BACKEND_CONFIGS[backend]
        logger.info(f"Starting database backend: {backend.value}")
        
        env = dict(os.environ)
        args = list(config["args"])
        
        # 配置连接参数
        if backend == DatabaseBackend.POSTGRESQL:
            if self._db_config.pg_connection_string:
                args.append(self._db_config.pg_connection_string)
            else:
                conn_str = (
                    f"postgresql://{self._db_config.pg_user}:{self._db_config.pg_password}"
                    f"@{self._db_config.pg_host}:{self._db_config.pg_port}"
                    f"/{self._db_config.pg_database}"
                )
                args.append(conn_str)
        
        elif backend == DatabaseBackend.SQLITE:
            args.append(self._db_config.sqlite_path)
        
        # 创建 MCP 协议实例
        self._mcp = MCPProtocol(timeout=self._config.timeout)
        
        await self._mcp.start(
            command=config["command"],
            args=args,
            env=env,
        )
        
        try:
            server_info = await self._mcp.initialize()
            logger.info(f"Database MCP Server initialized: {server_info.name} v{server_info.version}")
            
            mcp_tools = await self._mcp.list_tools()
            self._tools = [
                ToolInfo(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in mcp_tools
            ]
            logger.info(f"Got {len(self._tools)} tools from Database MCP Server")
            
        except Exception as e:
            logger.warning(f"MCP handshake failed, using standard tools: {e}")
            self._tools = self._get_standard_tools()
    
    async def _do_stop(self) -> None:
        """停止数据库后端"""
        if self._mcp:
            await self._mcp.shutdown()
            self._mcp = None
        self._active_backend = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 MCP 协议调用工具"""
        if not self._mcp:
            raise ConnectorError("MCP protocol not initialized")
        
        return await self._mcp.call_tool(name, params)
    
    def _get_standard_tools(self) -> List[ToolInfo]:
        """获取标准数据库工具列表"""
        return [
            ToolInfo(
                name="query",
                description="Execute a SQL query and return results",
                input_schema={
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL query to execute"
                        }
                    },
                    "required": ["sql"]
                }
            ),
            ToolInfo(
                name="list_tables",
                description="List all tables in the database",
                input_schema={
                    "type": "object",
                    "properties": {}
                }
            ),
            ToolInfo(
                name="describe_table",
                description="Get the schema/structure of a table",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table to describe"
                        }
                    },
                    "required": ["table_name"]
                }
            ),
            ToolInfo(
                name="insert",
                description="Insert data into a table",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string"},
                        "data": {"type": "object"}
                    },
                    "required": ["table", "data"]
                }
            ),
            ToolInfo(
                name="update",
                description="Update data in a table",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table": {"type": "string"},
                        "data": {"type": "object"},
                        "where": {"type": "string"}
                    },
                    "required": ["table", "data", "where"]
                }
            ),
        ]
    
    # 便捷方法
    async def query(self, sql: str) -> Any:
        """执行 SQL 查询"""
        return await self.call_tool("query", {"sql": sql})
    
    async def list_tables(self) -> Any:
        """列出所有表"""
        return await self.call_tool("list_tables", {})
    
    async def describe_table(self, table_name: str) -> Any:
        """获取表结构"""
        return await self.call_tool("describe_table", {"table_name": table_name})
    
    async def insert(self, table: str, data: Dict[str, Any]) -> Any:
        """插入数据"""
        if self._db_config.read_only:
            raise ConnectorError("Database is in read-only mode")
        return await self.call_tool("insert", {"table": table, "data": data})
    
    async def update(self, table: str, data: Dict[str, Any], where: str) -> Any:
        """更新数据"""
        if self._db_config.read_only:
            raise ConnectorError("Database is in read-only mode")
        return await self.call_tool("update", {"table": table, "data": data, "where": where})
