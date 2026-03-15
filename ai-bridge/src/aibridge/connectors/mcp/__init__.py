"""
MCP Server 连接器集合

提供各类 MCP Server 的连接器：
- browser: 浏览器自动化
- database: 数据库操作
- filesystem: 文件系统
- github: GitHub API
"""

from .browser import BrowserConnector, BrowserConnectorConfig

__all__ = [
    "BrowserConnector",
    "BrowserConnectorConfig",
]
