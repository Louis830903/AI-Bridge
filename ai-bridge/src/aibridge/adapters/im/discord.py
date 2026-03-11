"""
Discord 适配器
Discord Adapter - Community and developer collaboration platform

使用 Discord Bot API 实现消息发送和管理。
官方文档: https://discord.com/developers/docs

依赖: httpx (异步HTTP客户端)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class DiscordConfig:
    """Discord 配置"""
    bot_token: str = ""       # Bot Token
    application_id: str = ""  # Application ID (可选)
    default_guild: str = ""   # 默认服务器 ID
    timeout: int = 30


class DiscordAdapter(BaseAdapter):
    """
    Discord 适配器
    
    通过 Discord REST API 实现:
    - 发送消息 (文本/Embed)
    - 发送文件
    - 管理频道
    - 管理角色
    - Webhook 支持
    
    使用示例:
        config = DiscordConfig(bot_token="xxx")
        adapter = DiscordAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="channel_id"), "Hello!")
    """
    
    BASE_URL = "https://discord.com/api/v10"
    
    def __init__(self, config: DiscordConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._bot_info: Dict = {}
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="discord",
            name="Discord",
            type=AdapterType.IM,
            version="1.0.0",
            description="Discord Bot API adapter",
            actions=[
                "send_message",
                "send_embed",
                "send_file",
                "edit_message",
                "delete_message",
                "add_reaction",
                "list_channels",
                "create_channel",
                "delete_channel",
                "list_members",
                "get_user",
                "create_thread",
            ]
        )
        
    async def connect(self) -> bool:
        """连接 Discord API"""
        if not self._config.bot_token:
            return False
            
        self._client = httpx.AsyncClient(
            timeout=self._config.timeout,
            headers={
                "Authorization": f"Bot {self._config.bot_token}",
                "Content-Type": "application/json",
            }
        )
        
        # 验证 token
        try:
            resp = await self._client.get(f"{self.BASE_URL}/users/@me")
            
            if resp.status_code == 200:
                self._bot_info = resp.json()
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
        """执行 Discord 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            if action == "send_message":
                return await self._send_message(target, value, options)
            elif action == "send_embed":
                return await self._send_embed(target, value, options)
            elif action == "send_file":
                return await self._send_file(target, value, options)
            elif action == "edit_message":
                return await self._edit_message(target, value, options)
            elif action == "delete_message":
                return await self._delete_message(target, options)
            elif action == "add_reaction":
                return await self._add_reaction(target, value, options)
            elif action == "list_channels":
                return await self._list_channels(target)
            elif action == "create_channel":
                return await self._create_channel(target, value, options)
            elif action == "delete_channel":
                return await self._delete_channel(target)
            elif action == "list_members":
                return await self._list_members(target, options)
            elif action == "get_user":
                return await self._get_user(target)
            elif action == "create_thread":
                return await self._create_thread(target, value, options)
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
        channel_id = target.name if target else ""
        
        payload = {
            "content": str(value),
        }
        
        # 支持回复
        if options.get("reply_to"):
            payload["message_reference"] = {
                "message_id": options["reply_to"]
            }
            
        # 支持组件 (按钮等)
        if options.get("components"):
            payload["components"] = options["components"]
            
        resp = await self._client.post(
            f"{self.BASE_URL}/channels/{channel_id}/messages",
            json=payload
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "message_id": data.get("id"),
                "channel_id": data.get("channel_id")
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _send_embed(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送 Embed 富文本"""
        channel_id = target.name if target else ""
        
        # value 可以是 embed dict 或 embeds list
        embeds = value if isinstance(value, list) else [value]
        
        payload = {
            "embeds": embeds,
        }
        
        if options.get("content"):
            payload["content"] = options["content"]
            
        resp = await self._client.post(
            f"{self.BASE_URL}/channels/{channel_id}/messages",
            json=payload
        )
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "message_id": data.get("id")
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _send_file(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送文件"""
        channel_id = target.name if target else ""
        
        # 使用 multipart/form-data
        with open(value, "rb") as f:
            files = {"file": (options.get("filename", "file"), f)}
            data = {}
            
            if options.get("content"):
                data["content"] = options["content"]
                
            resp = await self._client.post(
                f"{self.BASE_URL}/channels/{channel_id}/messages",
                files=files,
                data=data
            )
        
        if resp.status_code == 200:
            return {"success": True, "message": resp.json()}
        else:
            return {"success": False, "error": resp.text}
            
    async def _edit_message(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """编辑消息"""
        channel_id = target.name if target else ""
        message_id = options.get("message_id", "")
        
        payload = {"content": str(value)}
        
        resp = await self._client.patch(
            f"{self.BASE_URL}/channels/{channel_id}/messages/{message_id}",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _delete_message(
        self,
        target: Optional[Target],
        options: Dict
    ) -> Dict:
        """删除消息"""
        channel_id = target.name if target else ""
        message_id = options.get("message_id", "")
        
        resp = await self._client.delete(
            f"{self.BASE_URL}/channels/{channel_id}/messages/{message_id}"
        )
        
        return {"success": resp.status_code == 204}
        
    async def _add_reaction(
        self,
        target: Optional[Target],
        value: str,
        options: Dict
    ) -> Dict:
        """添加表情回应"""
        channel_id = target.name if target else ""
        message_id = options.get("message_id", "")
        emoji = value  # Unicode emoji 或 name:id 格式
        
        resp = await self._client.put(
            f"{self.BASE_URL}/channels/{channel_id}/messages/{message_id}/reactions/{emoji}/@me"
        )
        
        return {"success": resp.status_code == 204}
        
    async def _list_channels(self, target: Optional[Target]) -> Dict:
        """列出服务器频道"""
        guild_id = target.name if target else self._config.default_guild
        
        resp = await self._client.get(f"{self.BASE_URL}/guilds/{guild_id}/channels")
        
        if resp.status_code == 200:
            return {
                "success": True,
                "channels": resp.json()
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _create_channel(
        self,
        target: Optional[Target],
        value: str,
        options: Dict
    ) -> Dict:
        """创建频道"""
        guild_id = target.name if target else self._config.default_guild
        
        payload = {
            "name": value,
            "type": options.get("type", 0),  # 0=text, 2=voice, 4=category
        }
        
        if options.get("parent_id"):
            payload["parent_id"] = options["parent_id"]
        if options.get("topic"):
            payload["topic"] = options["topic"]
            
        resp = await self._client.post(
            f"{self.BASE_URL}/guilds/{guild_id}/channels",
            json=payload
        )
        
        if resp.status_code == 201:
            return {"success": True, "channel": resp.json()}
        else:
            return {"success": False, "error": resp.text}
            
    async def _delete_channel(self, target: Target) -> Dict:
        """删除频道"""
        resp = await self._client.delete(f"{self.BASE_URL}/channels/{target.name}")
        return {"success": resp.status_code == 200}
        
    async def _list_members(
        self,
        target: Optional[Target],
        options: Dict
    ) -> Dict:
        """列出服务器成员"""
        guild_id = target.name if target else self._config.default_guild
        
        params = {
            "limit": options.get("limit", 100),
        }
        
        resp = await self._client.get(
            f"{self.BASE_URL}/guilds/{guild_id}/members",
            params=params
        )
        
        if resp.status_code == 200:
            return {"success": True, "members": resp.json()}
        else:
            return {"success": False, "error": resp.text}
            
    async def _get_user(self, target: Target) -> Dict:
        """获取用户信息"""
        resp = await self._client.get(f"{self.BASE_URL}/users/{target.name}")
        
        if resp.status_code == 200:
            return {"success": True, "user": resp.json()}
        else:
            return {"success": False, "error": resp.text}
            
    async def _create_thread(
        self,
        target: Optional[Target],
        value: str,
        options: Dict
    ) -> Dict:
        """创建话题"""
        channel_id = target.name if target else ""
        
        payload = {
            "name": value,
            "auto_archive_duration": options.get("archive_duration", 1440),  # 分钟
        }
        
        # 从消息创建话题
        if options.get("message_id"):
            resp = await self._client.post(
                f"{self.BASE_URL}/channels/{channel_id}/messages/{options['message_id']}/threads",
                json=payload
            )
        else:
            # 创建独立话题
            payload["type"] = options.get("type", 11)  # 11=public, 12=private
            resp = await self._client.post(
                f"{self.BASE_URL}/channels/{channel_id}/threads",
                json=payload
            )
            
        if resp.status_code in (200, 201):
            return {"success": True, "thread": resp.json()}
        else:
            return {"success": False, "error": resp.text}
