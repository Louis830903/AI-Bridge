"""
Notion 连接器

团队协作连接器，代理到 Notion MCP Server。
支持页面、数据库、块的读写操作。

使用示例：
```python
import os
from aibridge.connectors.mcp import NotionConnector, NotionConnectorConfig

# WARNING: 生产环境请使用环境变量，不要硬编码凭证
config = NotionConnectorConfig(
    name="notion",
    api_key=os.environ.get("NOTION_API_KEY")  # 从环境变量读取
)

async with NotionConnector(config) as notion:
    # 搜索页面
    pages = await notion.search("Meeting Notes")
    
    # 读取页面内容
    content = await notion.get_page("page_id")
    
    # 创建页面
    page = await notion.create_page(parent_id="xxx", title="New Page")
    
    # 查询数据库
    rows = await notion.query_database("db_id", filter={...})
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
class NotionConnectorConfig(ConnectorConfig):
    """Notion 连接器配置"""
    api_key: Optional[str] = None  # Notion Integration Token
    
    # 默认设置
    default_page_icon: str = "📄"
    default_database_icon: str = "📊"


# MCP Server 配置
NOTION_MCP_CONFIG = {
    "command": "npx",
    "args": ["-y", "@anthropic-ai/mcp-server-notion"],
    "check_command": "npx",
    "check_args": ["--version"],
}


class NotionConnector(MCPConnector):
    """
    Notion 连接器
    
    团队协作连接器，支持：
    - 页面管理 (创建、读取、更新、删除)
    - 数据库操作 (查询、插入、更新)
    - 块操作 (添加、修改、删除内容块)
    - 搜索功能
    
    需要 Notion Integration Token，创建地址：https://www.notion.so/my-integrations
    """
    
    def __init__(self, config: NotionConnectorConfig):
        super().__init__(config)
        self._notion_config = config
        self._mcp: Optional[MCPProtocol] = None
    
    @property
    def api_key(self) -> Optional[str]:
        """API Key"""
        return self._notion_config.api_key or os.environ.get("NOTION_API_KEY")
    
    async def _check_backend_available(self) -> bool:
        """检查 Notion MCP Server 是否可用"""
        import shutil
        import asyncio
        
        command = NOTION_MCP_CONFIG["check_command"]
        if not shutil.which(command):
            return False
        
        try:
            proc = await asyncio.create_subprocess_exec(
                command,
                *NOTION_MCP_CONFIG["check_args"],
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10.0)
            return proc.returncode == 0
        except Exception:
            return False
    
    async def _do_start(self) -> None:
        """启动 Notion MCP Server"""
        if not await self._check_backend_available():
            raise ConnectorError(
                "Notion MCP Server not available. "
                "Please install: npm install -g @anthropic-ai/mcp-server-notion"
            )
        
        if not self.api_key:
            raise ConnectorError(
                "Notion API Key required. "
                "Set NOTION_API_KEY environment variable or provide api_key in config."
            )
        
        logger.info("Starting Notion connector")
        
        env = dict(os.environ)
        env["NOTION_API_KEY"] = self.api_key
        
        # 创建 MCP 协议实例
        self._mcp = MCPProtocol(timeout=self._config.timeout)
        
        await self._mcp.start(
            command=NOTION_MCP_CONFIG["command"],
            args=NOTION_MCP_CONFIG["args"],
            env=env,
        )
        
        try:
            server_info = await self._mcp.initialize()
            logger.info(f"Notion MCP Server initialized: {server_info.name} v{server_info.version}")
            
            mcp_tools = await self._mcp.list_tools()
            self._tools = [
                ToolInfo(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in mcp_tools
            ]
            logger.info(f"Got {len(self._tools)} tools from Notion MCP Server")
            
        except Exception as e:
            logger.warning(f"MCP handshake failed, using standard tools: {e}")
            self._tools = self._get_standard_tools()
    
    async def _do_stop(self) -> None:
        """停止 Notion MCP Server"""
        if self._mcp:
            await self._mcp.shutdown()
            self._mcp = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 MCP 协议调用工具"""
        if not self._mcp:
            raise ConnectorError("MCP protocol not initialized")
        
        return await self._mcp.call_tool(name, params)
    
    def _get_standard_tools(self) -> List[ToolInfo]:
        """获取标准 Notion 工具列表"""
        return [
            ToolInfo(
                name="search",
                description="Search for pages and databases in Notion",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "filter": {
                            "type": "object",
                            "description": "Filter by object type (page or database)"
                        }
                    },
                    "required": ["query"]
                }
            ),
            ToolInfo(
                name="get_page",
                description="Get a page's content",
                input_schema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page ID"
                        }
                    },
                    "required": ["page_id"]
                }
            ),
            ToolInfo(
                name="create_page",
                description="Create a new page",
                input_schema={
                    "type": "object",
                    "properties": {
                        "parent_id": {
                            "type": "string",
                            "description": "Parent page or database ID"
                        },
                        "title": {
                            "type": "string",
                            "description": "Page title"
                        },
                        "content": {
                            "type": "string",
                            "description": "Page content (markdown)"
                        }
                    },
                    "required": ["parent_id", "title"]
                }
            ),
            ToolInfo(
                name="update_page",
                description="Update a page's properties",
                input_schema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page ID"
                        },
                        "properties": {
                            "type": "object",
                            "description": "Properties to update"
                        }
                    },
                    "required": ["page_id", "properties"]
                }
            ),
            ToolInfo(
                name="query_database",
                description="Query a database",
                input_schema={
                    "type": "object",
                    "properties": {
                        "database_id": {
                            "type": "string",
                            "description": "Database ID"
                        },
                        "filter": {
                            "type": "object",
                            "description": "Filter conditions"
                        },
                        "sorts": {
                            "type": "array",
                            "description": "Sort conditions"
                        }
                    },
                    "required": ["database_id"]
                }
            ),
            ToolInfo(
                name="append_blocks",
                description="Append blocks to a page",
                input_schema={
                    "type": "object",
                    "properties": {
                        "page_id": {
                            "type": "string",
                            "description": "Page ID"
                        },
                        "blocks": {
                            "type": "array",
                            "description": "Blocks to append"
                        }
                    },
                    "required": ["page_id", "blocks"]
                }
            ),
        ]
    
    # 便捷方法
    async def search(self, query: str, filter_type: str = None) -> Any:
        """搜索页面和数据库"""
        params = {"query": query}
        if filter_type:
            params["filter"] = {"property": "object", "value": filter_type}
        return await self.call_tool("search", params)
    
    async def get_page(self, page_id: str) -> Any:
        """获取页面内容"""
        return await self.call_tool("get_page", {"page_id": page_id})
    
    async def create_page(
        self,
        parent_id: str,
        title: str,
        content: str = None,
        icon: str = None,
    ) -> Any:
        """创建页面"""
        params = {
            "parent_id": parent_id,
            "title": title,
        }
        if content:
            params["content"] = content
        if icon:
            params["icon"] = icon
        return await self.call_tool("create_page", params)
    
    async def update_page(self, page_id: str, properties: Dict[str, Any]) -> Any:
        """更新页面属性"""
        return await self.call_tool("update_page", {"page_id": page_id, "properties": properties})
    
    async def query_database(
        self,
        database_id: str,
        filter: Dict[str, Any] = None,
        sorts: List[Dict[str, Any]] = None,
    ) -> Any:
        """查询数据库"""
        params = {"database_id": database_id}
        if filter:
            params["filter"] = filter
        if sorts:
            params["sorts"] = sorts
        return await self.call_tool("query_database", params)
    
    async def append_blocks(self, page_id: str, blocks: List[Dict[str, Any]]) -> Any:
        """向页面追加内容块"""
        return await self.call_tool("append_blocks", {"page_id": page_id, "blocks": blocks})
    
    async def append_text(self, page_id: str, text: str) -> Any:
        """向页面追加文本"""
        blocks = [
            {
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": text}}]
                }
            }
        ]
        return await self.append_blocks(page_id, blocks)
