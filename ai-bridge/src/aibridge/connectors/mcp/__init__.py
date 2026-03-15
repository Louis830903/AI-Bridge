"""
MCP Server 连接器集合

提供各类 MCP Server 的连接器：
- browser: 浏览器自动化 (Browser Use, Chrome DevTools, Playwright)
- database: 数据库操作 (PostgreSQL, SQLite)
- filesystem: 文件系统操作
- github: GitHub API
- sqlite: SQLite 轻量数据库
- firecrawl: 网页抓取
- notion: 团队协作
- slack: 通讯集成
"""

from .browser import BrowserConnector, BrowserConnectorConfig
from .database import DatabaseConnector, DatabaseConnectorConfig, DatabaseBackend
from .filesystem import FilesystemConnector, FilesystemConnectorConfig
from .github import GitHubConnector, GitHubConnectorConfig
from .sqlite import SQLiteConnector, SQLiteConnectorConfig
from .firecrawl import FirecrawlConnector, FirecrawlConnectorConfig
from .notion import NotionConnector, NotionConnectorConfig
from .slack import SlackConnector, SlackConnectorConfig

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
    # SQLite
    "SQLiteConnector",
    "SQLiteConnectorConfig",
    # Firecrawl
    "FirecrawlConnector",
    "FirecrawlConnectorConfig",
    # Notion
    "NotionConnector",
    "NotionConnectorConfig",
    # Slack
    "SlackConnector",
    "SlackConnectorConfig",
]
