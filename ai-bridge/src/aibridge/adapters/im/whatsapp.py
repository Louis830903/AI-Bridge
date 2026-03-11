"""
WhatsApp Business 适配器
WhatsApp Business Adapter - World's largest messaging platform

使用 WhatsApp Business Cloud API (Meta) 实现消息发送和管理。
官方文档: https://developers.facebook.com/docs/whatsapp/cloud-api

依赖: httpx (异步HTTP客户端)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class WhatsAppConfig:
    """WhatsApp Business 配置"""
    phone_number_id: str = ""    # WhatsApp Business 电话号码 ID
    access_token: str = ""       # Meta 访问令牌
    api_version: str = "v18.0"   # API 版本
    webhook_verify_token: str = ""  # Webhook 验证令牌
    timeout: int = 30


class WhatsAppAdapter(BaseAdapter):
    """
    WhatsApp Business Cloud API 适配器
    
    通过 Meta WhatsApp Business API 实现:
    - 发送文本/模板/交互式消息
    - 发送媒体文件 (图片/文档/音视频)
    - 消息状态追踪
    - 业务资料管理
    
    使用示例:
        config = WhatsAppConfig(
            phone_number_id="xxx",
            access_token="xxx"
        )
        adapter = WhatsAppAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="+1234567890"), "Hello!")
    """
    
    BASE_URL = "https://graph.facebook.com"
    
    def __init__(self, config: WhatsAppConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="whatsapp",
            name="WhatsApp Business",
            type=AdapterType.IM,
            version="1.0.0",
            description="WhatsApp Business Cloud API adapter",
            actions=[
                "send_message",
                "send_template",
                "send_image",
                "send_document",
                "send_audio",
                "send_video",
                "send_location",
                "send_contact",
                "send_interactive",
                "mark_read",
                "get_media",
                "upload_media",
            ]
        )
        
    @property
    def _api_url(self) -> str:
        return f"{self.BASE_URL}/{self._config.api_version}/{self._config.phone_number_id}"
        
    async def connect(self) -> bool:
        """连接 WhatsApp API"""
        if not self._config.access_token or not self._config.phone_number_id:
            return False
            
        self._client = httpx.AsyncClient(
            timeout=self._config.timeout,
            headers={
                "Authorization": f"Bearer {self._config.access_token}",
                "Content-Type": "application/json",
            }
        )
        
        # 验证连接
        try:
            resp = await self._client.get(self._api_url)
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
        """执行 WhatsApp 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            if action == "send_message":
                return await self._send_text_message(target, value, options)
            elif action == "send_template":
                return await self._send_template(target, value, options)
            elif action == "send_image":
                return await self._send_media(target, value, "image", options)
            elif action == "send_document":
                return await self._send_media(target, value, "document", options)
            elif action == "send_audio":
                return await self._send_media(target, value, "audio", options)
            elif action == "send_video":
                return await self._send_media(target, value, "video", options)
            elif action == "send_location":
                return await self._send_location(target, value, options)
            elif action == "send_contact":
                return await self._send_contact(target, value, options)
            elif action == "send_interactive":
                return await self._send_interactive(target, value, options)
            elif action == "mark_read":
                return await self._mark_read(value)
            elif action == "upload_media":
                return await self._upload_media(value, options)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _send_text_message(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送文本消息"""
        phone = target.name if target else ""
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": phone,
            "type": "text",
            "text": {
                "preview_url": options.get("preview_url", False),
                "body": str(value)
            }
        }
        
        resp = await self._client.post(f"{self._api_url}/messages", json=payload)
        data = resp.json()
        
        if "messages" in data:
            return {
                "success": True,
                "message_id": data["messages"][0]["id"]
            }
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _send_template(
        self,
        target: Optional[Target],
        value: str,
        options: Dict
    ) -> Dict:
        """发送模板消息"""
        phone = target.name if target else ""
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": value,
                "language": {"code": options.get("language", "en")},
            }
        }
        
        # 添加模板参数
        if options.get("components"):
            payload["template"]["components"] = options["components"]
            
        resp = await self._client.post(f"{self._api_url}/messages", json=payload)
        data = resp.json()
        
        if "messages" in data:
            return {"success": True, "message_id": data["messages"][0]["id"]}
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _send_media(
        self,
        target: Optional[Target],
        value: Any,
        media_type: str,
        options: Dict
    ) -> Dict:
        """发送媒体消息"""
        phone = target.name if target else ""
        
        media_obj = {}
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            media_obj["link"] = value
        else:
            media_obj["id"] = value  # Media ID
            
        if options.get("caption"):
            media_obj["caption"] = options["caption"]
        if options.get("filename"):
            media_obj["filename"] = options["filename"]
            
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": media_type,
            media_type: media_obj
        }
        
        resp = await self._client.post(f"{self._api_url}/messages", json=payload)
        data = resp.json()
        
        if "messages" in data:
            return {"success": True, "message_id": data["messages"][0]["id"]}
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _send_location(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送位置"""
        phone = target.name if target else ""
        
        # value: {"latitude": x, "longitude": y} 或 "lat,lng"
        if isinstance(value, str):
            lat, lng = value.split(",")
            latitude, longitude = float(lat), float(lng)
        else:
            latitude = value.get("latitude")
            longitude = value.get("longitude")
            
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "location",
            "location": {
                "latitude": latitude,
                "longitude": longitude,
                "name": options.get("name", ""),
                "address": options.get("address", ""),
            }
        }
        
        resp = await self._client.post(f"{self._api_url}/messages", json=payload)
        data = resp.json()
        
        if "messages" in data:
            return {"success": True, "message_id": data["messages"][0]["id"]}
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _send_contact(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送联系人"""
        phone = target.name if target else ""
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "contacts",
            "contacts": value if isinstance(value, list) else [value]
        }
        
        resp = await self._client.post(f"{self._api_url}/messages", json=payload)
        data = resp.json()
        
        if "messages" in data:
            return {"success": True, "message_id": data["messages"][0]["id"]}
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _send_interactive(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送交互式消息 (按钮/列表)"""
        phone = target.name if target else ""
        
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "interactive",
            "interactive": value  # 完整的 interactive 对象
        }
        
        resp = await self._client.post(f"{self._api_url}/messages", json=payload)
        data = resp.json()
        
        if "messages" in data:
            return {"success": True, "message_id": data["messages"][0]["id"]}
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _mark_read(self, message_id: str) -> Dict:
        """标记消息已读"""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        resp = await self._client.post(f"{self._api_url}/messages", json=payload)
        return {"success": resp.status_code == 200}
        
    async def _upload_media(self, file_path: str, options: Dict) -> Dict:
        """上传媒体文件"""
        with open(file_path, "rb") as f:
            files = {
                "file": (options.get("filename", "file"), f, options.get("type", "application/octet-stream"))
            }
            data = {"messaging_product": "whatsapp"}
            
            resp = await self._client.post(
                f"{self._api_url}/media",
                data=data,
                files=files
            )
            
        result = resp.json()
        
        if "id" in result:
            return {"success": True, "media_id": result["id"]}
        else:
            return {"success": False, "error": result.get("error", {}).get("message")}
