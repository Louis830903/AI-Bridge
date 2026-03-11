"""
Slack 适配器
Slack Adapter - Enterprise collaboration platform

使用 Slack Web API 和 Bot Token 实现消息发送和管理。
官方文档: https://api.slack.com/

依赖: httpx (异步HTTP客户端)
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import httpx

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class SlackConfig:
    """Slack 配置"""
    bot_token: str = ""  # xoxb-xxx Bot User OAuth Token
    app_token: str = ""  # xapp-xxx (可选，用于 Socket Mode)
    default_channel: str = ""  # 默认频道 ID
    timeout: int = 30


class SlackAdapter(BaseAdapter):
    """
    Slack 适配器
    
    通过 Slack Web API 实现:
    - 发送消息 (文本/Block Kit)
    - 发送文件
    - 读取频道消息
    - 管理频道
    
    使用示例:
        config = SlackConfig(bot_token="xoxb-xxx")
        adapter = SlackAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="#general"), "Hello!")
    """
    
    BASE_URL = "https://slack.com/api"
    
    def __init__(self, config: SlackConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._bot_info: Dict = {}
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="slack",
            name="Slack",
            type=AdapterType.IM,
            version="1.0.0",
            description="Slack Web API adapter",
            actions=[
                "send_message",
                "send_file",
                "read_messages",
                "list_channels",
                "create_channel",
                "archive_channel",
                "add_reaction",
                "get_user_info",
            ]
        )
        
    async def connect(self) -> bool:
        """连接 Slack API"""
        if not self._config.bot_token:
            return False
            
        self._client = httpx.AsyncClient(
            timeout=self._config.timeout,
            headers={
                "Authorization": f"Bearer {self._config.bot_token}",
                "Content-Type": "application/json; charset=utf-8",
            }
        )
        
        # 验证 token 并获取 bot 信息
        try:
            resp = await self._client.post(f"{self.BASE_URL}/auth.test")
            data = resp.json()
            
            if data.get("ok"):
                self._bot_info = data
                self._connected = True
                return True
            else:
                return False
                
        except Exception:
            return False
            
    async def disconnect(self) -> bool:
        """断开连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        return True
        
    async def execute(
        self,
        action: str,
        target: Optional[Target],
        value: Optional[Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行 Slack 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            if action == "send_message":
                return await self._send_message(target, value, options)
            elif action == "send_file":
                return await self._send_file(target, value, options)
            elif action == "read_messages":
                return await self._read_messages(target, options)
            elif action == "list_channels":
                return await self._list_channels(options)
            elif action == "create_channel":
                return await self._create_channel(value, options)
            elif action == "archive_channel":
                return await self._archive_channel(target)
            elif action == "add_reaction":
                return await self._add_reaction(target, value, options)
            elif action == "get_user_info":
                return await self._get_user_info(target)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _send_message(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送消息"""
        channel = target.name if target else self._config.default_channel
        
        payload = {
            "channel": channel,
            "text": str(value),
        }
        
        # 支持 Block Kit 富文本
        if options.get("blocks"):
            payload["blocks"] = options["blocks"]
            
        # 支持回复消息
        if options.get("thread_ts"):
            payload["thread_ts"] = options["thread_ts"]
            
        resp = await self._client.post(
            f"{self.BASE_URL}/chat.postMessage",
            json=payload
        )
        data = resp.json()
        
        if data.get("ok"):
            return {
                "success": True,
                "message_ts": data.get("ts"),
                "channel": data.get("channel")
            }
        else:
            return {"success": False, "error": data.get("error")}
            
    async def _send_file(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """上传文件"""
        channel = target.name if target else self._config.default_channel
        
        # 使用 files.upload API - 使用 context manager 确保文件正确关闭
        if isinstance(value, str):
            with open(value, "rb") as f:
                file_content = f.read()
            files = {"file": file_content}
        else:
            files = {"content": value}
        
        data = {
            "channels": channel,
            "filename": options.get("filename", "file"),
            "title": options.get("title", ""),
            "initial_comment": options.get("comment", ""),
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/files.upload",
            data=data,
            files=files
        )
        result = resp.json()
        
        return {"success": result.get("ok"), "file": result.get("file", {})}
        
    async def _read_messages(
        self,
        target: Optional[Target],
        options: Dict
    ) -> Dict:
        """读取频道消息"""
        channel = target.name if target else self._config.default_channel
        
        params = {
            "channel": channel,
            "limit": options.get("limit", 10),
        }
        
        if options.get("oldest"):
            params["oldest"] = options["oldest"]
        if options.get("latest"):
            params["latest"] = options["latest"]
            
        resp = await self._client.get(
            f"{self.BASE_URL}/conversations.history",
            params=params
        )
        data = resp.json()
        
        if data.get("ok"):
            return {
                "success": True,
                "messages": data.get("messages", []),
                "has_more": data.get("has_more", False)
            }
        else:
            return {"success": False, "error": data.get("error")}
            
    async def _list_channels(self, options: Dict) -> Dict:
        """列出频道"""
        params = {
            "types": options.get("types", "public_channel,private_channel"),
            "limit": options.get("limit", 100),
        }
        
        resp = await self._client.get(
            f"{self.BASE_URL}/conversations.list",
            params=params
        )
        data = resp.json()
        
        if data.get("ok"):
            return {
                "success": True,
                "channels": data.get("channels", [])
            }
        else:
            return {"success": False, "error": data.get("error")}
            
    async def _create_channel(self, value: str, options: Dict) -> Dict:
        """创建频道"""
        payload = {
            "name": value,
            "is_private": options.get("is_private", False),
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/conversations.create",
            json=payload
        )
        data = resp.json()
        
        if data.get("ok"):
            return {
                "success": True,
                "channel": data.get("channel", {})
            }
        else:
            return {"success": False, "error": data.get("error")}
            
    async def _archive_channel(self, target: Target) -> Dict:
        """归档频道"""
        resp = await self._client.post(
            f"{self.BASE_URL}/conversations.archive",
            json={"channel": target.name}
        )
        data = resp.json()
        
        return {"success": data.get("ok"), "error": data.get("error")}
        
    async def _add_reaction(
        self,
        target: Target,
        value: str,
        options: Dict
    ) -> Dict:
        """添加表情回应"""
        payload = {
            "channel": target.name,
            "timestamp": options.get("message_ts"),
            "name": value,  # emoji name without colons
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/reactions.add",
            json=payload
        )
        data = resp.json()
        
        return {"success": data.get("ok"), "error": data.get("error")}
        
    async def _get_user_info(self, target: Target) -> Dict:
        """获取用户信息"""
        resp = await self._client.get(
            f"{self.BASE_URL}/users.info",
            params={"user": target.name}
        )
        data = resp.json()
        
        if data.get("ok"):
            return {
                "success": True,
                "user": data.get("user", {})
            }
        else:
            return {"success": False, "error": data.get("error")}
