"""
MCP Server 连接器集合

提供各类 MCP Server 的连接器：
- browser: 浏览器自动化 (Browser Use, Chrome DevTools, Playwright)
- database: 数据库操作 (PostgreSQL, SQLite)
- filesystem: 文件系统操作
- github: GitHub API
"""

from .browser import BrowserConnector, BrowserConnectorConfig
from .database import DatabaseConnector, DatabaseConnectorConfig, DatabaseBackend
from .filesystem import FilesystemConnector, FilesystemConnectorConfig
from .github import GitHubConnector, GitHubConnectorConfig

__all__ = [
    # Browser
    "BrowserConnector",
    "BrowserConnectorConfig",
    # Database
    "DatabaseConnector",
    "DatabaseConnectorConfig",
    "DatabaseBackend",
    # Filesystem
    "FilesystemConnector",
    "FilesystemConnectorConfig",
    # GitHub
    "GitHubConnector",
    "GitHubConnectorConfig",
]
