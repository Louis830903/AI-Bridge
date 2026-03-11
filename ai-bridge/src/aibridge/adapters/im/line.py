"""
LINE 适配器
LINE Adapter - Popular in Japan, Taiwan, Thailand

使用 LINE Messaging API 实现消息发送和管理。
官方文档: https://developers.line.biz/en/docs/messaging-api/

依赖: httpx (异步HTTP客户端)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class LINEConfig:
    """LINE 配置"""
    channel_access_token: str = ""  # Channel Access Token
    channel_secret: str = ""        # Channel Secret (用于验证签名)
    timeout: int = 30


class LINEAdapter(BaseAdapter):
    """
    LINE Messaging API 适配器
    
    通过 LINE Messaging API 实现:
    - 推送/回复消息
    - 发送各类消息 (文本/贴图/图片/视频/音频/位置/Flex)
    - 群组/多人聊天管理
    - Rich Menu 管理
    - 用户资料获取
    
    使用示例:
        config = LINEConfig(channel_access_token="xxx")
        adapter = LINEAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="user_id"), "Hello!")
    """
    
    BASE_URL = "https://api.line.me/v2"
    DATA_URL = "https://api-data.line.me/v2"
    
    def __init__(self, config: LINEConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="line",
            name="LINE",
            type=AdapterType.IM,
            version="1.0.0",
            description="LINE Messaging API adapter",
            actions=[
                "push_message",
                "reply_message",
                "multicast",
                "broadcast",
                "send_text",
                "send_sticker",
                "send_image",
                "send_video",
                "send_audio",
                "send_location",
                "send_flex",
                "get_profile",
                "get_group_summary",
                "leave_group",
                "get_rich_menu",
                "set_rich_menu",
            ]
        )
        
    async def connect(self) -> bool:
        """连接 LINE API"""
        if not self._config.channel_access_token:
            return False
            
        self._client = httpx.AsyncClient(
            timeout=self._config.timeout,
            headers={
                "Authorization": f"Bearer {self._config.channel_access_token}",
                "Content-Type": "application/json",
            }
        )
        
        # 验证 token
        try:
            resp = await self._client.get(f"{self.BASE_URL}/bot/info")
            self._connected = resp.status_code == 200
            return self._connected
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
        """执行 LINE 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            # 消息发送
            if action in ("send_message", "push_message"):
                return await self._push_message(target, value, options)
            elif action == "reply_message":
                return await self._reply_message(value, options)
            elif action == "multicast":
                return await self._multicast(value, options)
            elif action == "broadcast":
                return await self._broadcast(value, options)
            # 特定消息类型
            elif action == "send_text":
                return await self._push_message(target, value, options)
            elif action == "send_sticker":
                return await self._send_sticker(target, value, options)
            elif action == "send_image":
                return await self._send_image(target, value, options)
            elif action == "send_video":
                return await self._send_video(target, value, options)
            elif action == "send_audio":
                return await self._send_audio(target, value, options)
            elif action == "send_location":
                return await self._send_location(target, value, options)
            elif action == "send_flex":
                return await self._send_flex(target, value, options)
            # 其他功能
            elif action == "get_profile":
                return await self._get_profile(target)
            elif action == "get_group_summary":
                return await self._get_group_summary(target)
            elif action == "leave_group":
                return await self._leave_group(target)
            elif action == "get_rich_menu":
                return await self._get_rich_menu(target)
            elif action == "set_rich_menu":
                return await self._set_rich_menu(target, value)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _create_text_message(self, text: str) -> Dict:
        """创建文本消息对象"""
        return {"type": "text", "text": text}
        
    async def _push_message(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """推送消息"""
        user_id = target.name if target else ""
        
        # 构建消息
        if isinstance(value, str):
            messages = [self._create_text_message(value)]
        elif isinstance(value, dict):
            messages = [value]
        elif isinstance(value, list):
            messages = value
        else:
            messages = [self._create_text_message(str(value))]
            
        payload = {
            "to": user_id,
            "messages": messages[:5]  # LINE 限制最多 5 条
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/push",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _reply_message(self, value: Any, options: Dict) -> Dict:
        """回复消息"""
        reply_token = options.get("reply_token", "")
        
        if isinstance(value, str):
            messages = [self._create_text_message(value)]
        elif isinstance(value, list):
            messages = value
        else:
            messages = [value]
            
        payload = {
            "replyToken": reply_token,
            "messages": messages[:5]
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/reply",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _multicast(self, value: Any, options: Dict) -> Dict:
        """多人发送"""
        user_ids = options.get("user_ids", [])
        
        if isinstance(value, str):
            messages = [self._create_text_message(value)]
        else:
            messages = value if isinstance(value, list) else [value]
            
        payload = {
            "to": user_ids[:500],  # LINE 限制最多 500 人
            "messages": messages[:5]
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/multicast",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _broadcast(self, value: Any, options: Dict) -> Dict:
        """广播消息"""
        if isinstance(value, str):
            messages = [self._create_text_message(value)]
        else:
            messages = value if isinstance(value, list) else [value]
            
        payload = {"messages": messages[:5]}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/broadcast",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _send_sticker(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送贴图"""
        user_id = target.name if target else ""
        
        # value: {"packageId": "xxx", "stickerId": "xxx"}
        message = {
            "type": "sticker",
            "packageId": str(value.get("packageId", value.get("package_id"))),
            "stickerId": str(value.get("stickerId", value.get("sticker_id")))
        }
        
        payload = {"to": user_id, "messages": [message]}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/push",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _send_image(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送图片"""
        user_id = target.name if target else ""
        
        message = {
            "type": "image",
            "originalContentUrl": value,
            "previewImageUrl": options.get("preview_url", value)
        }
        
        payload = {"to": user_id, "messages": [message]}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/push",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _send_video(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送视频"""
        user_id = target.name if target else ""
        
        message = {
            "type": "video",
            "originalContentUrl": value,
            "previewImageUrl": options.get("preview_url", "")
        }
        
        payload = {"to": user_id, "messages": [message]}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/push",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _send_audio(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送音频"""
        user_id = target.name if target else ""
        
        message = {
            "type": "audio",
            "originalContentUrl": value,
            "duration": options.get("duration", 60000)  # 毫秒
        }
        
        payload = {"to": user_id, "messages": [message]}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/push",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _send_location(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送位置"""
        user_id = target.name if target else ""
        
        if isinstance(value, str):
            lat, lng = value.split(",")
            latitude, longitude = float(lat), float(lng)
        else:
            latitude = value.get("latitude")
            longitude = value.get("longitude")
            
        message = {
            "type": "location",
            "title": options.get("title", "Location"),
            "address": options.get("address", ""),
            "latitude": latitude,
            "longitude": longitude
        }
        
        payload = {"to": user_id, "messages": [message]}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/push",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _send_flex(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送 Flex Message"""
        user_id = target.name if target else ""
        
        message = {
            "type": "flex",
            "altText": options.get("alt_text", "Flex Message"),
            "contents": value
        }
        
        payload = {"to": user_id, "messages": [message]}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/message/push",
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _get_profile(self, target: Target) -> Dict:
        """获取用户资料"""
        user_id = target.name
        
        resp = await self._client.get(f"{self.BASE_URL}/bot/profile/{user_id}")
        
        if resp.status_code == 200:
            return {"success": True, "profile": resp.json()}
        else:
            return {"success": False, "error": resp.text}
            
    async def _get_group_summary(self, target: Target) -> Dict:
        """获取群组信息"""
        group_id = target.name
        
        resp = await self._client.get(f"{self.BASE_URL}/bot/group/{group_id}/summary")
        
        if resp.status_code == 200:
            return {"success": True, "group": resp.json()}
        else:
            return {"success": False, "error": resp.text}
            
    async def _leave_group(self, target: Target) -> Dict:
        """离开群组"""
        group_id = target.name
        
        resp = await self._client.post(f"{self.BASE_URL}/bot/group/{group_id}/leave")
        
        return {"success": resp.status_code == 200}
        
    async def _get_rich_menu(self, target: Optional[Target]) -> Dict:
        """获取 Rich Menu"""
        if target:
            # 获取用户的 Rich Menu
            resp = await self._client.get(
                f"{self.BASE_URL}/bot/user/{target.name}/richmenu"
            )
        else:
            # 获取所有 Rich Menu
            resp = await self._client.get(f"{self.BASE_URL}/bot/richmenu/list")
            
        if resp.status_code == 200:
            return {"success": True, "rich_menu": resp.json()}
        else:
            return {"success": False, "error": resp.text}
            
    async def _set_rich_menu(self, target: Target, rich_menu_id: str) -> Dict:
        """设置用户的 Rich Menu"""
        user_id = target.name
        
        resp = await self._client.post(
            f"{self.BASE_URL}/bot/user/{user_id}/richmenu/{rich_menu_id}"
        )
        
        return {"success": resp.status_code == 200}
