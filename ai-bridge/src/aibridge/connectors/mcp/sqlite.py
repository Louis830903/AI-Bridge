"""
SQLite 连接器

轻量级嵌入式数据库连接器，代理到 SQLite MCP Server。
这是 DatabaseConnector 的便捷封装，专注于 SQLite 使用场景。

使用示例：
```python
from aibridge.connectors.mcp import SQLiteConnector, SQLiteConnectorConfig

config = SQLiteConnectorConfig(
    name="mydb",
    db_path="./data.db"
)

async with SQLiteConnector(config) as db:
    # 执行查询
    result = await db.query("SELECT * FROM users")
    
    # 列出所有表
    tables = await db.list_tables()
```
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..base import (
    MCPConnector,
    ConnectorConfig,
    ConnectorStatus,
    ConnectorError,
    ToolInfo,
)
from aibridge.gateway.mcp_protocol import MCPProtocol

logger = logging.getLogger(__name__)


@dataclass
class SQLiteConnectorConfig(ConnectorConfig):
    """SQLite 连接器配置"""
    db_path: str = ":memory:"  # 默认内存数据库
    read_only: bool = False  # 只读模式


# MCP Server 配置
SQLITE_MCP_CONFIG = {
    "command": "npx",
    "args": ["-y", "@anthropic-ai/mcp-server-sqlite"],
    "check_command": "npx",
    "check_args": ["--version"],
}


class SQLiteConnector(MCPConnector):
    """
    SQLite 连接器
    
    轻量级嵌入式数据库连接器，适用于：
    - 本地数据存储
    - 快速原型开发
    - 单用户应用
    - 测试环境
    
    特点：
    - 零配置，开箱即用
    - 支持内存数据库
    - 支持只读模式
    """
    
    def __init__(self, config: SQLiteConnectorConfig):
        super().__init__(config)
        self._sqlite_config = config
        self._mcp: Optional[MCPProtocol] = None
    
    @property
    def db_path(self) -> str:
        """数据库路径"""
        return self._sqlite_config.db_path
    
    @property
    def is_memory_db(self) -> bool:
        """是否为内存数据库"""
        return self._sqlite_config.db_path == ":memory:"
    
    async def _check_backend_available(self) -> bool:
        """检查 SQLite MCP Server 是否可用"""
        import shutil
        import asyncio
        
        command = SQLITE_MCP_CONFIG["check_command"]
        if not shutil.which(command):
            return False
        
        try:
            proc = await asyncio.create_subprocess_exec(
                command,
                *SQLITE_MCP_CONFIG["check_args"],
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10.0)
            return proc.returncode == 0
        except Exception:
            return False
    
    async def _do_start(self) -> None:
        """启动 SQLite MCP Server"""
        import os
        
        if not await self._check_backend_available():
            raise ConnectorError(
                "SQLite MCP Server not available. "
                "Please install: npm install -g @anthropic-ai/mcp-server-sqlite"
            )
        
        logger.info(f"Starting SQLite connector: {self._sqlite_config.db_path}")
        
        args = list(SQLITE_MCP_CONFIG["args"])
        args.append(self._sqlite_config.db_path)
        
        if self._sqlite_config.read_only:
            args.append("--read-only")
        
        # 创建 MCP 协议实例
        self._mcp = MCPProtocol(timeout=self._config.timeout)
        
        await self._mcp.start(
            command=SQLITE_MCP_CONFIG["command"],
            args=args,
            env=dict(os.environ),
        )
        
        try:
            server_info = await self._mcp.initialize()
            logger.info(f"SQLite MCP Server initialized: {server_info.name} v{server_info.version}")
            
            mcp_tools = await self._mcp.list_tools()
            self._tools = [
                ToolInfo(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in mcp_tools
            ]
            logger.info(f"Got {len(self._tools)} tools from SQLite MCP Server")
            
        except Exception as e:
            logger.warning(f"MCP handshake failed, using standard tools: {e}")
            self._tools = self._get_standard_tools()
    
    async def _do_stop(self) -> None:
        """停止 SQLite MCP Server"""
        if self._mcp:
            await self._mcp.shutdown()
            self._mcp = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 MCP 协议调用工具"""
        if not self._mcp:
            raise ConnectorError("MCP protocol not initialized")
        
        return await self._mcp.call_tool(name, params)
    
    def _get_standard_tools(self) -> List[ToolInfo]:
        """获取标准 SQLite 工具列表"""
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
                input_schema={"type": "object", "properties": {}}
            ),
            ToolInfo(
                name="describe_table",
                description="Get the schema of a table",
                input_schema={
                    "type": "object",
                    "properties": {
                        "table_name": {
                            "type": "string",
                            "description": "Name of the table"
                        }
                    },
                    "required": ["table_name"]
                }
            ),
            ToolInfo(
                name="execute",
                description="Execute a SQL statement (INSERT/UPDATE/DELETE)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL statement to execute"
                        }
                    },
                    "required": ["sql"]
                }
            ),
        ]
    
    # 便捷方法
    async def query(self, sql: str) -> Any:
        """执行 SQL 查询"""
        return await self.call_tool("query", {"sql": sql})
    
    async def execute(self, sql: str) -> Any:
        """执行 SQL 语句 (INSERT/UPDATE/DELETE)"""
        if self._sqlite_config.read_only:
            raise ConnectorError("Database is in read-only mode")
        return await self.call_tool("execute", {"sql": sql})
    
    async def list_tables(self) -> Any:
        """列出所有表"""
        return await self.call_tool("list_tables", {})
    
    async def describe_table(self, table_name: str) -> Any:
        """获取表结构"""
        return await self.call_tool("describe_table", {"table_name": table_name})
    
    async def create_table(self, table_name: str, columns: Dict[str, str]) -> Any:
        """创建表"""
        if self._sqlite_config.read_only:
            raise ConnectorError("Database is in read-only mode")
        
        cols = ", ".join(f"{name} {dtype}" for name, dtype in columns.items())
        sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({cols})"
        return await self.execute(sql)
    
    async def insert(self, table: str, data: Dict[str, Any]) -> Any:
        """插入数据"""
        if self._sqlite_config.read_only:
            raise ConnectorError("Database is in read-only mode")
        
        columns = ", ".join(data.keys())
        placeholders = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in data.values())
        sql = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        return await self.execute(sql)
