"""
Google Chat 适配器
Google Chat Adapter - Google Workspace collaboration

使用 Google Chat API 实现消息发送和空间管理。
官方文档: https://developers.google.com/chat/api

依赖: httpx, google-auth (可选)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx
import json

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class GoogleChatConfig:
    """Google Chat 配置"""
    # 服务账号方式
    service_account_file: str = ""  # 服务账号 JSON 文件路径
    # 或直接提供凭证
    credentials_json: str = ""      # 服务账号 JSON 内容
    # Webhook 方式 (更简单)
    webhook_url: str = ""           # Webhook URL
    timeout: int = 30


class GoogleChatAdapter(BaseAdapter):
    """
    Google Chat API 适配器
    
    支持两种模式:
    1. Webhook 模式: 简单，只能发送消息
    2. API 模式: 完整功能，需要服务账号
    
    功能包括:
    - 发送文本/卡片消息
    - 创建/管理空间
    - 管理成员
    - 对话式消息
    
    使用示例:
        # Webhook 模式
        config = GoogleChatConfig(webhook_url="https://chat.googleapis.com/...")
        
        # API 模式
        config = GoogleChatConfig(service_account_file="service_account.json")
        
        adapter = GoogleChatAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="spaces/xxx"), "Hello!")
    """
    
    BASE_URL = "https://chat.googleapis.com/v1"
    
    def __init__(self, config: GoogleChatConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._access_token: str = ""
        self._is_webhook_mode = bool(config.webhook_url)
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="google_chat",
            name="Google Chat",
            type=AdapterType.IM,
            version="1.0.0",
            description="Google Chat API adapter",
            actions=[
                "send_message",
                "send_card",
                "update_message",
                "delete_message",
                "list_spaces",
                "get_space",
                "list_members",
                "create_message",
            ]
        )
        
    async def connect(self) -> bool:
        """连接 Google Chat API"""
        self._client = httpx.AsyncClient(timeout=self._config.timeout)
        
        if self._is_webhook_mode:
            # Webhook 模式不需要认证
            self._connected = True
            return True
            
        # API 模式需要获取访问令牌
        try:
            token = await self._get_access_token()
            if token:
                self._access_token = token
                self._client.headers["Authorization"] = f"Bearer {token}"
                self._connected = True
                return True
        except Exception:
            pass
            
        return False
        
    async def _get_access_token(self) -> Optional[str]:
        """获取 Google API 访问令牌"""
        # 尝试使用 google-auth 库
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request
            
            if self._config.service_account_file:
                credentials = service_account.Credentials.from_service_account_file(
                    self._config.service_account_file,
                    scopes=["https://www.googleapis.com/auth/chat.bot"]
                )
            elif self._config.credentials_json:
                info = json.loads(self._config.credentials_json)
                credentials = service_account.Credentials.from_service_account_info(
                    info,
                    scopes=["https://www.googleapis.com/auth/chat.bot"]
                )
            else:
                return None
                
            credentials.refresh(Request())
            return credentials.token
            
        except ImportError:
            # 如果没有 google-auth，返回 None
            return None
            
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
        """执行 Google Chat 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            if action == "send_message":
                return await self._send_message(target, value, options)
            elif action == "send_card":
                return await self._send_card(target, value, options)
            elif action == "update_message":
                return await self._update_message(target, value, options)
            elif action == "delete_message":
                return await self._delete_message(target)
            elif action == "list_spaces":
                return await self._list_spaces()
            elif action == "get_space":
                return await self._get_space(target)
            elif action == "list_members":
                return await self._list_members(target)
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
        """发送文本消息"""
        
        if self._is_webhook_mode:
            # Webhook 模式
            payload = {"text": str(value)}
            resp = await self._client.post(self._config.webhook_url, json=payload)
        else:
            # API 模式
            space = target.name if target else ""
            payload = {"text": str(value)}
            
            # 支持回复
            if options.get("thread_key"):
                payload["thread"] = {"threadKey": options["thread_key"]}
                
            resp = await self._client.post(
                f"{self.BASE_URL}/{space}/messages",
                json=payload
            )
            
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "message_name": data.get("name"),
                "thread_name": data.get("thread", {}).get("name")
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _send_card(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送卡片消息"""
        
        if self._is_webhook_mode:
            payload = {"cards": value if isinstance(value, list) else [value]}
            resp = await self._client.post(self._config.webhook_url, json=payload)
        else:
            space = target.name if target else ""
            payload = {
                "cardsV2": [{
                    "cardId": options.get("card_id", "card"),
                    "card": value
                }]
            }
            
            if options.get("text"):
                payload["text"] = options["text"]
                
            resp = await self._client.post(
                f"{self.BASE_URL}/{space}/messages",
                json=payload
            )
            
        if resp.status_code == 200:
            return {"success": True, "message": resp.json()}
        else:
            return {"success": False, "error": resp.text}
            
    async def _update_message(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """更新消息"""
        if self._is_webhook_mode:
            return {"success": False, "error": "Update not supported in webhook mode"}
            
        message_name = target.name if target else ""
        
        payload = {"text": str(value)}
        update_mask = "text"
        
        if options.get("cards"):
            payload["cardsV2"] = options["cards"]
            update_mask += ",cardsV2"
            
        resp = await self._client.patch(
            f"{self.BASE_URL}/{message_name}",
            params={"updateMask": update_mask},
            json=payload
        )
        
        return {"success": resp.status_code == 200}
        
    async def _delete_message(self, target: Target) -> Dict:
        """删除消息"""
        if self._is_webhook_mode:
            return {"success": False, "error": "Delete not supported in webhook mode"}
            
        message_name = target.name
        resp = await self._client.delete(f"{self.BASE_URL}/{message_name}")
        
        return {"success": resp.status_code == 200}
        
    async def _list_spaces(self) -> Dict:
        """列出空间"""
        if self._is_webhook_mode:
            return {"success": False, "error": "List spaces not supported in webhook mode"}
            
        resp = await self._client.get(f"{self.BASE_URL}/spaces")
        
        if resp.status_code == 200:
            data = resp.json()
            return {"success": True, "spaces": data.get("spaces", [])}
        else:
            return {"success": False, "error": resp.text}
            
    async def _get_space(self, target: Target) -> Dict:
        """获取空间详情"""
        if self._is_webhook_mode:
            return {"success": False, "error": "Get space not supported in webhook mode"}
            
        resp = await self._client.get(f"{self.BASE_URL}/{target.name}")
        
        if resp.status_code == 200:
            return {"success": True, "space": resp.json()}
        else:
            return {"success": False, "error": resp.text}
            
    async def _list_members(self, target: Target) -> Dict:
        """列出空间成员"""
        if self._is_webhook_mode:
            return {"success": False, "error": "List members not supported in webhook mode"}
            
        space = target.name
        resp = await self._client.get(f"{self.BASE_URL}/{space}/members")
        
        if resp.status_code == 200:
            data = resp.json()
            return {"success": True, "members": data.get("memberships", [])}
        else:
            return {"success": False, "error": resp.text}
