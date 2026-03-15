"""
Firecrawl 连接器

网页抓取连接器，代理到 Firecrawl MCP Server。
支持网页内容提取、爬虫、结构化数据抓取。

使用示例：
```python
import os
from aibridge.connectors.mcp import FirecrawlConnector, FirecrawlConnectorConfig

# WARNING: 生产环境请使用环境变量，不要硬编码凭证
config = FirecrawlConnectorConfig(
    name="crawler",
    api_key=os.environ.get("FIRECRAWL_API_KEY")  # 从环境变量读取
)

async with FirecrawlConnector(config) as crawler:
    # 抓取单个页面
    content = await crawler.scrape("https://example.com")
    
    # 爬取整个网站
    pages = await crawler.crawl("https://example.com", max_pages=10)
    
    # 搜索网页
    results = await crawler.search("AI agents")
```
"""

import logging
import os
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
class FirecrawlConnectorConfig(ConnectorConfig):
    """Firecrawl 连接器配置"""
    api_key: Optional[str] = None  # Firecrawl API Key
    api_url: str = "https://api.firecrawl.dev"  # API 地址
    
    # 爬取配置
    max_pages: int = 100  # 最大爬取页数
    wait_until: str = "networkidle"  # 等待条件: load, domcontentloaded, networkidle
    include_markdown: bool = True  # 是否返回 Markdown 格式
    include_html: bool = False  # 是否返回原始 HTML


# MCP Server 配置
FIRECRAWL_MCP_CONFIG = {
    "command": "npx",
    "args": ["-y", "@anthropic-ai/mcp-server-firecrawl"],
    "check_command": "npx",
    "check_args": ["--version"],
}


class FirecrawlConnector(MCPConnector):
    """
    Firecrawl 连接器
    
    网页抓取连接器，支持：
    - 单页面抓取 (scrape)
    - 网站爬取 (crawl)
    - 网页搜索 (search)
    - 结构化数据提取
    
    需要 Firecrawl API Key，获取地址：https://firecrawl.dev
    """
    
    def __init__(self, config: FirecrawlConnectorConfig):
        super().__init__(config)
        self._fc_config = config
        self._mcp: Optional[MCPProtocol] = None
    
    @property
    def api_key(self) -> Optional[str]:
        """API Key"""
        return self._fc_config.api_key or os.environ.get("FIRECRAWL_API_KEY")
    
    async def _check_backend_available(self) -> bool:
        """检查 Firecrawl MCP Server 是否可用"""
        import shutil
        import asyncio
        
        command = FIRECRAWL_MCP_CONFIG["check_command"]
        if not shutil.which(command):
            return False
        
        try:
            proc = await asyncio.create_subprocess_exec(
                command,
                *FIRECRAWL_MCP_CONFIG["check_args"],
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10.0)
            return proc.returncode == 0
        except Exception:
            return False
    
    async def _do_start(self) -> None:
        """启动 Firecrawl MCP Server"""
        if not await self._check_backend_available():
            raise ConnectorError(
                "Firecrawl MCP Server not available. "
                "Please install: npm install -g @anthropic-ai/mcp-server-firecrawl"
            )
        
        if not self.api_key:
            raise ConnectorError(
                "Firecrawl API Key required. "
                "Set FIRECRAWL_API_KEY environment variable or provide api_key in config."
            )
        
        logger.info("Starting Firecrawl connector")
        
        env = dict(os.environ)
        env["FIRECRAWL_API_KEY"] = self.api_key
        env["FIRECRAWL_API_URL"] = self._fc_config.api_url
        
        # 创建 MCP 协议实例
        self._mcp = MCPProtocol(timeout=self._config.timeout)
        
        await self._mcp.start(
            command=FIRECRAWL_MCP_CONFIG["command"],
            args=FIRECRAWL_MCP_CONFIG["args"],
            env=env,
        )
        
        try:
            server_info = await self._mcp.initialize()
            logger.info(f"Firecrawl MCP Server initialized: {server_info.name} v{server_info.version}")
            
            mcp_tools = await self._mcp.list_tools()
            self._tools = [
                ToolInfo(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in mcp_tools
            ]
            logger.info(f"Got {len(self._tools)} tools from Firecrawl MCP Server")
            
        except Exception as e:
            logger.warning(f"MCP handshake failed, using standard tools: {e}")
            self._tools = self._get_standard_tools()
    
    async def _do_stop(self) -> None:
        """停止 Firecrawl MCP Server"""
        if self._mcp:
            await self._mcp.shutdown()
            self._mcp = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 MCP 协议调用工具"""
        if not self._mcp:
            raise ConnectorError("MCP protocol not initialized")
        
        return await self._mcp.call_tool(name, params)
    
    def _get_standard_tools(self) -> List[ToolInfo]:
        """获取标准 Firecrawl 工具列表"""
        return [
            ToolInfo(
                name="scrape",
                description="Scrape a single URL and extract content",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to scrape"
                        },
                        "formats": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Output formats: markdown, html, text"
                        }
                    },
                    "required": ["url"]
                }
            ),
            ToolInfo(
                name="crawl",
                description="Crawl a website and extract content from multiple pages",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "Starting URL to crawl"
                        },
                        "max_pages": {
                            "type": "integer",
                            "description": "Maximum number of pages to crawl"
                        },
                        "include_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URL patterns to include"
                        },
                        "exclude_patterns": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "URL patterns to exclude"
                        }
                    },
                    "required": ["url"]
                }
            ),
            ToolInfo(
                name="search",
                description="Search the web and return relevant results",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of results"
                        }
                    },
                    "required": ["query"]
                }
            ),
            ToolInfo(
                name="extract",
                description="Extract structured data from a URL",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL to extract data from"
                        },
                        "schema": {
                            "type": "object",
                            "description": "JSON schema for extracted data"
                        }
                    },
                    "required": ["url"]
                }
            ),
        ]
    
    # 便捷方法
    async def scrape(self, url: str, formats: List[str] = None) -> Any:
        """抓取单个页面"""
        params = {"url": url}
        if formats:
            params["formats"] = formats
        elif self._fc_config.include_markdown:
            params["formats"] = ["markdown"]
        return await self.call_tool("scrape", params)
    
    async def crawl(
        self,
        url: str,
        max_pages: int = None,
        include_patterns: List[str] = None,
        exclude_patterns: List[str] = None,
    ) -> Any:
        """爬取网站"""
        params = {"url": url}
        params["max_pages"] = max_pages or self._fc_config.max_pages
        if include_patterns:
            params["include_patterns"] = include_patterns
        if exclude_patterns:
            params["exclude_patterns"] = exclude_patterns
        return await self.call_tool("crawl", params)
    
    async def search(self, query: str, limit: int = 10) -> Any:
        """搜索网页"""
        return await self.call_tool("search", {"query": query, "limit": limit})
    
    async def extract(self, url: str, schema: Dict[str, Any] = None) -> Any:
        """提取结构化数据"""
        params = {"url": url}
        if schema:
            params["schema"] = schema
        return await self.call_tool("extract", params)
