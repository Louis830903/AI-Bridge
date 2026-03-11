"""
Facebook Messenger 适配器
Facebook Messenger Adapter - Meta's messaging platform

使用 Messenger Platform API 实现消息发送和管理。
官方文档: https://developers.facebook.com/docs/messenger-platform

依赖: httpx (异步HTTP客户端)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class MessengerConfig:
    """Facebook Messenger 配置"""
    page_access_token: str = ""  # Facebook Page Access Token
    app_secret: str = ""         # App Secret (用于验证)
    api_version: str = "v18.0"   # API 版本
    timeout: int = 30


class MessengerAdapter(BaseAdapter):
    """
    Facebook Messenger Platform 适配器
    
    通过 Messenger API 实现:
    - 发送文本/附件消息
    - 发送模板消息 (按钮/通用/收据等)
    - 发送快速回复
    - 用户资料获取
    - Persona 管理
    
    使用示例:
        config = MessengerConfig(page_access_token="xxx")
        adapter = MessengerAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="user_psid"), "Hello!")
    """
    
    BASE_URL = "https://graph.facebook.com"
    
    def __init__(self, config: MessengerConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="messenger",
            name="Facebook Messenger",
            type=AdapterType.IM,
            version="1.0.0",
            description="Facebook Messenger Platform adapter",
            actions=[
                "send_message",
                "send_attachment",
                "send_template",
                "send_quick_replies",
                "send_action",
                "get_user_profile",
                "set_persistent_menu",
                "upload_attachment",
            ]
        )
        
    @property
    def _api_url(self) -> str:
        return f"{self.BASE_URL}/{self._config.api_version}"
        
    async def connect(self) -> bool:
        """连接 Messenger API"""
        if not self._config.page_access_token:
            return False
            
        self._client = httpx.AsyncClient(
            timeout=self._config.timeout,
            params={"access_token": self._config.page_access_token}
        )
        
        # 验证 token
        try:
            resp = await self._client.get(f"{self._api_url}/me")
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
        """执行 Messenger 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            if action == "send_message":
                return await self._send_text(target, value, options)
            elif action == "send_attachment":
                return await self._send_attachment(target, value, options)
            elif action == "send_template":
                return await self._send_template(target, value, options)
            elif action == "send_quick_replies":
                return await self._send_quick_replies(target, value, options)
            elif action == "send_action":
                return await self._send_action(target, value)
            elif action == "get_user_profile":
                return await self._get_user_profile(target)
            elif action == "set_persistent_menu":
                return await self._set_persistent_menu(value)
            elif action == "upload_attachment":
                return await self._upload_attachment(value, options)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _send_text(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送文本消息"""
        recipient_id = target.name if target else ""
        
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": str(value)},
            "messaging_type": options.get("messaging_type", "RESPONSE"),
        }
        
        # 支持 Persona
        if options.get("persona_id"):
            payload["persona_id"] = options["persona_id"]
            
        resp = await self._client.post(
            f"{self._api_url}/me/messages",
            json=payload
        )
        data = resp.json()
        
        if "message_id" in data:
            return {
                "success": True,
                "message_id": data["message_id"],
                "recipient_id": data.get("recipient_id")
            }
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _send_attachment(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送附件 (图片/音频/视频/文件)"""
        recipient_id = target.name if target else ""
        attachment_type = options.get("type", "image")
        
        attachment = {"type": attachment_type}
        
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            attachment["payload"] = {
                "url": value,
                "is_reusable": options.get("is_reusable", False)
            }
        else:
            attachment["payload"] = {"attachment_id": value}
            
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"attachment": attachment},
        }
        
        resp = await self._client.post(f"{self._api_url}/me/messages", json=payload)
        data = resp.json()
        
        if "message_id" in data:
            return {"success": True, "message_id": data["message_id"]}
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _send_template(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送模板消息"""
        recipient_id = target.name if target else ""
        template_type = options.get("template_type", "generic")
        
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "attachment": {
                    "type": "template",
                    "payload": {
                        "template_type": template_type,
                        **value  # 模板具体内容
                    }
                }
            }
        }
        
        resp = await self._client.post(f"{self._api_url}/me/messages", json=payload)
        data = resp.json()
        
        if "message_id" in data:
            return {"success": True, "message_id": data["message_id"]}
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _send_quick_replies(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送快速回复"""
        recipient_id = target.name if target else ""
        text = options.get("text", "Please choose:")
        
        # value 应为 quick_replies 列表
        payload = {
            "recipient": {"id": recipient_id},
            "message": {
                "text": text,
                "quick_replies": value
            }
        }
        
        resp = await self._client.post(f"{self._api_url}/me/messages", json=payload)
        data = resp.json()
        
        if "message_id" in data:
            return {"success": True, "message_id": data["message_id"]}
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _send_action(
        self,
        target: Optional[Target],
        action: str
    ) -> Dict:
        """发送操作状态 (typing_on, typing_off, mark_seen)"""
        recipient_id = target.name if target else ""
        
        payload = {
            "recipient": {"id": recipient_id},
            "sender_action": action
        }
        
        resp = await self._client.post(f"{self._api_url}/me/messages", json=payload)
        return {"success": resp.status_code == 200}
        
    async def _get_user_profile(self, target: Target) -> Dict:
        """获取用户资料"""
        user_id = target.name
        
        resp = await self._client.get(
            f"{self._api_url}/{user_id}",
            params={
                "fields": "first_name,last_name,profile_pic,locale,timezone,gender",
                "access_token": self._config.page_access_token
            }
        )
        data = resp.json()
        
        if "error" not in data:
            return {"success": True, "profile": data}
        else:
            return {"success": False, "error": data.get("error", {}).get("message")}
            
    async def _set_persistent_menu(self, menu: List[Dict]) -> Dict:
        """设置持久菜单"""
        payload = {
            "persistent_menu": [{
                "locale": "default",
                "composer_input_disabled": False,
                "call_to_actions": menu
            }]
        }
        
        resp = await self._client.post(
            f"{self._api_url}/me/messenger_profile",
            json=payload
        )
        data = resp.json()
        
        return {"success": data.get("result") == "success"}
        
    async def _upload_attachment(self, file_path: str, options: Dict) -> Dict:
        """上传附件获取 attachment_id"""
        attachment_type = options.get("type", "image")
        
        with open(file_path, "rb") as f:
            payload = {
                "message": {
                    "attachment": {
                        "type": attachment_type,
                        "payload": {"is_reusable": True}
                    }
                }
            }
            
            files = {"filedata": f}
            data = {"message": str(payload["message"])}
            
            resp = await self._client.post(
                f"{self._api_url}/me/message_attachments",
                data=data,
                files=files
            )
            
        result = resp.json()
        
        if "attachment_id" in result:
            return {"success": True, "attachment_id": result["attachment_id"]}
        else:
            return {"success": False, "error": result.get("error", {}).get("message")}
