"""
AI-Bridge Connectors - 外部服务连接器

连接器用于接入外部 MCP Server 和其他服务，
实现"协议网关"的核心能力。

模块：
- base: 连接器基类
- mcp/: MCP Server 连接器
  - browser: 浏览器自动化 (Browser Use, Chrome DevTools, Playwright)
  - database: 数据库 (PostgreSQL, SQLite)
  - filesystem: 文件系统
  - github: GitHub API
"""

from .base import (
    MCPConnector,
    ConnectorConfig,
    ConnectorStatus,
    ConnectorError,
)

__all__ = [
    "MCPConnector",
    "ConnectorConfig",
    "ConnectorStatus",
    "ConnectorError",
]
