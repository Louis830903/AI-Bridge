"""
Viber 适配器
Viber Adapter - Popular in Eastern Europe, Africa, Southeast Asia

使用 Viber REST API 实现消息发送和管理。
官方文档: https://developers.viber.com/docs/api/rest-bot-api/

依赖: httpx (异步HTTP客户端)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class ViberConfig:
    """Viber 配置"""
    auth_token: str = ""      # Bot Auth Token
    bot_name: str = ""        # Bot 名称
    bot_avatar: str = ""      # Bot 头像 URL
    webhook_url: str = ""     # Webhook URL
    timeout: int = 30


class ViberAdapter(BaseAdapter):
    """
    Viber REST API 适配器
    
    通过 Viber API 实现:
    - 发送各类消息 (文本/图片/视频/文件/贴图/位置/联系人)
    - 广播消息
    - Keyboard 交互
    - 用户详情获取
    - 账户信息管理
    
    使用示例:
        config = ViberConfig(auth_token="xxx", bot_name="MyBot")
        adapter = ViberAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="user_id"), "Hello!")
    """
    
    BASE_URL = "https://chatapi.viber.com/pa"
    
    def __init__(self, config: ViberConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._account_info: Dict = {}
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="viber",
            name="Viber",
            type=AdapterType.IM,
            version="1.0.0",
            description="Viber REST API adapter",
            actions=[
                "send_message",
                "send_text",
                "send_picture",
                "send_video",
                "send_file",
                "send_sticker",
                "send_location",
                "send_contact",
                "send_url",
                "broadcast",
                "get_account_info",
                "get_user_details",
                "set_webhook",
            ]
        )
        
    async def connect(self) -> bool:
        """连接 Viber API"""
        if not self._config.auth_token:
            return False
            
        self._client = httpx.AsyncClient(
            timeout=self._config.timeout,
            headers={
                "X-Viber-Auth-Token": self._config.auth_token,
                "Content-Type": "application/json",
            }
        )
        
        # 获取账户信息验证连接
        try:
            resp = await self._client.post(f"{self.BASE_URL}/get_account_info")
            data = resp.json()
            
            if data.get("status") == 0:
                self._account_info = data
                self._connected = True
                return True
        except Exception:
            pass
            
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
        """执行 Viber 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            if action in ("send_message", "send_text"):
                return await self._send_text(target, value, options)
            elif action == "send_picture":
                return await self._send_picture(target, value, options)
            elif action == "send_video":
                return await self._send_video(target, value, options)
            elif action == "send_file":
                return await self._send_file(target, value, options)
            elif action == "send_sticker":
                return await self._send_sticker(target, value, options)
            elif action == "send_location":
                return await self._send_location(target, value, options)
            elif action == "send_contact":
                return await self._send_contact(target, value, options)
            elif action == "send_url":
                return await self._send_url(target, value, options)
            elif action == "broadcast":
                return await self._broadcast(value, options)
            elif action == "get_account_info":
                return await self._get_account_info()
            elif action == "get_user_details":
                return await self._get_user_details(target)
            elif action == "set_webhook":
                return await self._set_webhook(value, options)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    def _create_sender(self) -> Dict:
        """创建发送者信息"""
        sender = {"name": self._config.bot_name or "Bot"}
        if self._config.bot_avatar:
            sender["avatar"] = self._config.bot_avatar
        return sender
        
    async def _send_text(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送文本消息"""
        receiver = target.name if target else ""
        
        payload = {
            "receiver": receiver,
            "type": "text",
            "text": str(value),
            "sender": self._create_sender(),
        }
        
        # 添加键盘
        if options.get("keyboard"):
            payload["keyboard"] = options["keyboard"]
            
        # 追踪数据
        if options.get("tracking_data"):
            payload["tracking_data"] = options["tracking_data"]
            
        resp = await self._client.post(f"{self.BASE_URL}/send_message", json=payload)
        data = resp.json()
        
        if data.get("status") == 0:
            return {"success": True, "message_token": data.get("message_token")}
        else:
            return {"success": False, "error": data.get("status_message")}
            
    async def _send_picture(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送图片"""
        receiver = target.name if target else ""
        
        payload = {
            "receiver": receiver,
            "type": "picture",
            "media": value,  # 图片 URL
            "sender": self._create_sender(),
        }
        
        if options.get("text"):
            payload["text"] = options["text"]
        if options.get("thumbnail"):
            payload["thumbnail"] = options["thumbnail"]
            
        resp = await self._client.post(f"{self.BASE_URL}/send_message", json=payload)
        data = resp.json()
        
        return {"success": data.get("status") == 0, "message_token": data.get("message_token")}
        
    async def _send_video(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送视频"""
        receiver = target.name if target else ""
        
        payload = {
            "receiver": receiver,
            "type": "video",
            "media": value,  # 视频 URL
            "size": options.get("size", 10000000),  # 文件大小 (字节)
            "sender": self._create_sender(),
        }
        
        if options.get("thumbnail"):
            payload["thumbnail"] = options["thumbnail"]
        if options.get("duration"):
            payload["duration"] = options["duration"]
            
        resp = await self._client.post(f"{self.BASE_URL}/send_message", json=payload)
        data = resp.json()
        
        return {"success": data.get("status") == 0}
        
    async def _send_file(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送文件"""
        receiver = target.name if target else ""
        
        payload = {
            "receiver": receiver,
            "type": "file",
            "media": value,  # 文件 URL
            "size": options.get("size", 10000000),
            "file_name": options.get("filename", "file"),
            "sender": self._create_sender(),
        }
        
        resp = await self._client.post(f"{self.BASE_URL}/send_message", json=payload)
        data = resp.json()
        
        return {"success": data.get("status") == 0}
        
    async def _send_sticker(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送贴图"""
        receiver = target.name if target else ""
        
        payload = {
            "receiver": receiver,
            "type": "sticker",
            "sticker_id": value,
            "sender": self._create_sender(),
        }
        
        resp = await self._client.post(f"{self.BASE_URL}/send_message", json=payload)
        data = resp.json()
        
        return {"success": data.get("status") == 0}
        
    async def _send_location(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送位置"""
        receiver = target.name if target else ""
        
        if isinstance(value, str):
            lat, lng = value.split(",")
            latitude, longitude = float(lat), float(lng)
        else:
            latitude = value.get("latitude")
            longitude = value.get("longitude")
            
        payload = {
            "receiver": receiver,
            "type": "location",
            "location": {
                "lat": latitude,
                "lon": longitude
            },
            "sender": self._create_sender(),
        }
        
        resp = await self._client.post(f"{self.BASE_URL}/send_message", json=payload)
        data = resp.json()
        
        return {"success": data.get("status") == 0}
        
    async def _send_contact(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送联系人"""
        receiver = target.name if target else ""
        
        payload = {
            "receiver": receiver,
            "type": "contact",
            "contact": {
                "name": value.get("name", "Contact"),
                "phone_number": value.get("phone", "")
            },
            "sender": self._create_sender(),
        }
        
        resp = await self._client.post(f"{self.BASE_URL}/send_message", json=payload)
        data = resp.json()
        
        return {"success": data.get("status") == 0}
        
    async def _send_url(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送 URL"""
        receiver = target.name if target else ""
        
        payload = {
            "receiver": receiver,
            "type": "url",
            "media": value,  # URL
            "sender": self._create_sender(),
        }
        
        resp = await self._client.post(f"{self.BASE_URL}/send_message", json=payload)
        data = resp.json()
        
        return {"success": data.get("status") == 0}
        
    async def _broadcast(self, value: Any, options: Dict) -> Dict:
        """广播消息"""
        broadcast_list = options.get("broadcast_list", [])
        
        payload = {
            "broadcast_list": broadcast_list,
            "type": "text",
            "text": str(value),
            "sender": self._create_sender(),
        }
        
        resp = await self._client.post(f"{self.BASE_URL}/broadcast_message", json=payload)
        data = resp.json()
        
        return {
            "success": data.get("status") == 0,
            "failed_list": data.get("failed_list", [])
        }
        
    async def _get_account_info(self) -> Dict:
        """获取账户信息"""
        resp = await self._client.post(f"{self.BASE_URL}/get_account_info")
        data = resp.json()
        
        if data.get("status") == 0:
            return {"success": True, "account": data}
        else:
            return {"success": False, "error": data.get("status_message")}
            
    async def _get_user_details(self, target: Target) -> Dict:
        """获取用户详情"""
        payload = {"id": target.name}
        
        resp = await self._client.post(f"{self.BASE_URL}/get_user_details", json=payload)
        data = resp.json()
        
        if data.get("status") == 0:
            return {"success": True, "user": data.get("user")}
        else:
            return {"success": False, "error": data.get("status_message")}
            
    async def _set_webhook(self, url: str, options: Dict) -> Dict:
        """设置 Webhook"""
        payload = {
            "url": url,
            "event_types": options.get("event_types", [
                "delivered", "seen", "failed", "subscribed",
                "unsubscribed", "conversation_started"
            ]),
            "send_name": options.get("send_name", True),
            "send_photo": options.get("send_photo", True),
        }
        
        resp = await self._client.post(f"{self.BASE_URL}/set_webhook", json=payload)
        data = resp.json()
        
        return {"success": data.get("status") == 0}
