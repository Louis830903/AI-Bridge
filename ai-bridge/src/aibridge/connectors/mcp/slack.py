"""
Slack 连接器

通讯集成连接器，代理到 Slack MCP Server。
支持消息发送、频道管理、用户查询等功能。

使用示例：
```python
import os
from aibridge.connectors.mcp import SlackConnector, SlackConnectorConfig

# WARNING: 生产环境请使用环境变量，不要硬编码凭证
config = SlackConnectorConfig(
    name="slack",
    bot_token=os.environ.get("SLACK_BOT_TOKEN")  # 从环境变量读取
)

async with SlackConnector(config) as slack:
    # 发送消息
    await slack.send_message("#general", "Hello from AI-Bridge!")
    
    # 列出频道
    channels = await slack.list_channels()
    
    # 获取消息历史
    messages = await slack.get_messages("#general", limit=10)
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
class SlackConnectorConfig(ConnectorConfig):
    """Slack 连接器配置"""
    bot_token: Optional[str] = None  # Slack Bot Token (xoxb-xxx)
    
    # 默认频道
    default_channel: str = "#general"
    
    # 消息配置
    unfurl_links: bool = True  # 展开链接预览
    unfurl_media: bool = True  # 展开媒体预览


# MCP Server 配置
SLACK_MCP_CONFIG = {
    "command": "npx",
    "args": ["-y", "@anthropic-ai/mcp-server-slack"],
    "check_command": "npx",
    "check_args": ["--version"],
}


class SlackConnector(MCPConnector):
    """
    Slack 连接器
    
    通讯集成连接器，支持：
    - 消息发送 (文本、富文本、附件)
    - 频道管理 (列出、创建、归档)
    - 用户查询
    - 消息历史
    - 反应 (Emoji Reactions)
    
    需要 Slack Bot Token，创建地址：https://api.slack.com/apps
    
    所需权限 (Scopes):
    - channels:read, channels:history
    - chat:write
    - users:read
    """
    
    def __init__(self, config: SlackConnectorConfig):
        super().__init__(config)
        self._slack_config = config
        self._mcp: Optional[MCPProtocol] = None
    
    @property
    def bot_token(self) -> Optional[str]:
        """Bot Token"""
        return self._slack_config.bot_token or os.environ.get("SLACK_BOT_TOKEN")
    
    async def _check_backend_available(self) -> bool:
        """检查 Slack MCP Server 是否可用"""
        import shutil
        import asyncio
        
        command = SLACK_MCP_CONFIG["check_command"]
        if not shutil.which(command):
            return False
        
        try:
            proc = await asyncio.create_subprocess_exec(
                command,
                *SLACK_MCP_CONFIG["check_args"],
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10.0)
            return proc.returncode == 0
        except Exception:
            return False
    
    async def _do_start(self) -> None:
        """启动 Slack MCP Server"""
        if not await self._check_backend_available():
            raise ConnectorError(
                "Slack MCP Server not available. "
                "Please install: npm install -g @anthropic-ai/mcp-server-slack"
            )
        
        if not self.bot_token:
            raise ConnectorError(
                "Slack Bot Token required. "
                "Set SLACK_BOT_TOKEN environment variable or provide bot_token in config."
            )
        
        logger.info("Starting Slack connector")
        
        env = dict(os.environ)
        env["SLACK_BOT_TOKEN"] = self.bot_token
        
        # 创建 MCP 协议实例
        self._mcp = MCPProtocol(timeout=self._config.timeout)
        
        await self._mcp.start(
            command=SLACK_MCP_CONFIG["command"],
            args=SLACK_MCP_CONFIG["args"],
            env=env,
        )
        
        try:
            server_info = await self._mcp.initialize()
            logger.info(f"Slack MCP Server initialized: {server_info.name} v{server_info.version}")
            
            mcp_tools = await self._mcp.list_tools()
            self._tools = [
                ToolInfo(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in mcp_tools
            ]
            logger.info(f"Got {len(self._tools)} tools from Slack MCP Server")
            
        except Exception as e:
            logger.warning(f"MCP handshake failed, using standard tools: {e}")
            self._tools = self._get_standard_tools()
    
    async def _do_stop(self) -> None:
        """停止 Slack MCP Server"""
        if self._mcp:
            await self._mcp.shutdown()
            self._mcp = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 MCP 协议调用工具"""
        if not self._mcp:
            raise ConnectorError("MCP protocol not initialized")
        
        return await self._mcp.call_tool(name, params)
    
    def _get_standard_tools(self) -> List[ToolInfo]:
        """获取标准 Slack 工具列表"""
        return [
            ToolInfo(
                name="send_message",
                description="Send a message to a Slack channel",
                input_schema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel name (e.g., #general) or ID"
                        },
                        "text": {
                            "type": "string",
                            "description": "Message text"
                        },
                        "thread_ts": {
                            "type": "string",
                            "description": "Thread timestamp for replies"
                        }
                    },
                    "required": ["channel", "text"]
                }
            ),
            ToolInfo(
                name="list_channels",
                description="List all channels in the workspace",
                input_schema={
                    "type": "object",
                    "properties": {
                        "types": {
                            "type": "string",
                            "description": "Channel types: public_channel, private_channel"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of channels to return"
                        }
                    }
                }
            ),
            ToolInfo(
                name="get_messages",
                description="Get message history from a channel",
                input_schema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel name or ID"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Number of messages to retrieve"
                        }
                    },
                    "required": ["channel"]
                }
            ),
            ToolInfo(
                name="get_users",
                description="List users in the workspace",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of users to return"
                        }
                    }
                }
            ),
            ToolInfo(
                name="get_user",
                description="Get information about a user",
                input_schema={
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID"
                        }
                    },
                    "required": ["user_id"]
                }
            ),
            ToolInfo(
                name="add_reaction",
                description="Add an emoji reaction to a message",
                input_schema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel containing the message"
                        },
                        "timestamp": {
                            "type": "string",
                            "description": "Message timestamp"
                        },
                        "emoji": {
                            "type": "string",
                            "description": "Emoji name (without colons)"
                        }
                    },
                    "required": ["channel", "timestamp", "emoji"]
                }
            ),
            ToolInfo(
                name="upload_file",
                description="Upload a file to a channel",
                input_schema={
                    "type": "object",
                    "properties": {
                        "channel": {
                            "type": "string",
                            "description": "Channel to upload to"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to the file"
                        },
                        "title": {
                            "type": "string",
                            "description": "File title"
                        }
                    },
                    "required": ["channel", "file_path"]
                }
            ),
        ]
    
    # 便捷方法
    async def send_message(
        self,
        channel: str = None,
        text: str = "",
        thread_ts: str = None,
        blocks: List[Dict[str, Any]] = None,
    ) -> Any:
        """发送消息"""
        params = {
            "channel": channel or self._slack_config.default_channel,
            "text": text,
        }
        if thread_ts:
            params["thread_ts"] = thread_ts
        if blocks:
            params["blocks"] = blocks
        return await self.call_tool("send_message", params)
    
    async def list_channels(self, types: str = "public_channel", limit: int = 100) -> Any:
        """列出频道"""
        return await self.call_tool("list_channels", {"types": types, "limit": limit})
    
    async def get_messages(self, channel: str, limit: int = 10) -> Any:
        """获取消息历史"""
        return await self.call_tool("get_messages", {"channel": channel, "limit": limit})
    
    async def get_users(self, limit: int = 100) -> Any:
        """列出用户"""
        return await self.call_tool("get_users", {"limit": limit})
    
    async def get_user(self, user_id: str) -> Any:
        """获取用户信息"""
        return await self.call_tool("get_user", {"user_id": user_id})
    
    async def add_reaction(self, channel: str, timestamp: str, emoji: str) -> Any:
        """添加 Emoji 反应"""
        return await self.call_tool("add_reaction", {
            "channel": channel,
            "timestamp": timestamp,
            "emoji": emoji.strip(":")
        })
    
    async def upload_file(self, channel: str, file_path: str, title: str = None) -> Any:
        """上传文件"""
        params = {"channel": channel, "file_path": file_path}
        if title:
            params["title"] = title
        return await self.call_tool("upload_file", params)
    
    async def reply(self, channel: str, thread_ts: str, text: str) -> Any:
        """回复消息 (在线程中)"""
        return await self.send_message(channel=channel, text=text, thread_ts=thread_ts)
