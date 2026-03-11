"""
Feishu Adapter - 飞书开放API集成
Glue code wrapping httpx for Feishu REST API
"""

import json
from typing import Any, Dict, List, Optional
import httpx
from aibridge.adapters.base import BaseAdapter, AdapterInfo, AdapterType


class FeishuAdapter(BaseAdapter):
    """
    飞书适配器 - 通过开放API进行消息发送和群组管理
    
    需要在飞书开放平台创建应用并获取:
    - app_id: 应用ID
    - app_secret: 应用密钥
    """
    
    BASE_URL = "https://open.feishu.cn/open-apis"
    
    info = AdapterInfo(
        id="feishu",
        name="飞书",
        type=AdapterType.IM,
        version="1.0.0",
        platforms=["windows", "macos", "linux"],
        actions=[
            "send", "send_card", "list_chats", "list_members",
            "create_chat", "read"
        ],
        description="飞书开放API集成",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.app_id = self.config.get("app_id", "")
        self.app_secret = self.config.get("app_secret", "")
        self._token = None
        self._client = None
    
    async def connect(self) -> bool:
        """获取 tenant_access_token"""
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            
            resp = await self._client.post(
                f"{self.BASE_URL}/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.app_id,
                    "app_secret": self.app_secret
                }
            )
            data = resp.json()
            
            if data.get("code") == 0:
                self._token = data.get("tenant_access_token")
                self._connected = True
                return True
            else:
                raise ConnectionError(f"Feishu auth failed: {data.get('msg')}")
                
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to Feishu: {e}")
    
    async def disconnect(self) -> bool:
        """断开连接"""
        if self._client:
            await self._client.aclose()
        self._token = None
        self._connected = False
        return True
    
    async def is_available(self) -> bool:
        """检查是否可用"""
        return bool(self.app_id and self.app_secret)
    
    async def execute(
        self,
        action: str,
        target: Optional[Dict[str, Any]] = None,
        value: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行飞书操作"""
        target = target or {}
        
        try:
            if action == "send":
                return await self._send_message(target, value)
            
            elif action == "send_card":
                return await self._send_card(target, value)
            
            elif action == "list_chats":
                return await self._list_chats()
            
            elif action == "list_members":
                chat_id = target.get("chat_id") or value
                return await self._list_members(chat_id)
            
            elif action == "create_chat":
                return await self._create_chat(target, value)
            
            elif action == "read":
                # 读取最近消息（需要额外权限）
                chat_id = target.get("chat_id") or value
                return await self._read_messages(chat_id)
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _send_message(self, target: Dict, value: Any) -> Dict[str, Any]:
        """发送文本消息"""
        chat_id = target.get("chat_id") or target.get("name")
        text = value if isinstance(value, str) else str(value)
        
        if not chat_id:
            return {"success": False, "error": "chat_id is required"}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/im/v1/messages",
            headers={"Authorization": f"Bearer {self._token}"},
            params={"receive_id_type": "chat_id"},
            json={
                "receive_id": chat_id,
                "msg_type": "text",
                "content": json.dumps({"text": text})
            }
        )
        
        data = resp.json()
        if data.get("code") == 0:
            return {"success": True, "data": data.get("data")}
        return {"success": False, "error": data.get("msg")}
    
    async def _send_card(self, target: Dict, value: Any) -> Dict[str, Any]:
        """发送卡片消息"""
        chat_id = target.get("chat_id")
        
        if isinstance(value, dict):
            card = value
        else:
            # 简单卡片
            card = {
                "config": {"wide_screen_mode": True},
                "elements": [
                    {"tag": "div", "text": {"content": str(value), "tag": "plain_text"}}
                ]
            }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/im/v1/messages",
            headers={"Authorization": f"Bearer {self._token}"},
            params={"receive_id_type": "chat_id"},
            json={
                "receive_id": chat_id,
                "msg_type": "interactive",
                "content": json.dumps(card)
            }
        )
        
        data = resp.json()
        if data.get("code") == 0:
            return {"success": True, "data": data.get("data")}
        return {"success": False, "error": data.get("msg")}
    
    async def _list_chats(self) -> Dict[str, Any]:
        """获取机器人所在的群列表"""
        resp = await self._client.get(
            f"{self.BASE_URL}/im/v1/chats",
            headers={"Authorization": f"Bearer {self._token}"}
        )
        
        data = resp.json()
        if data.get("code") == 0:
            items = data.get("data", {}).get("items", [])
            chats = [
                {"chat_id": c.get("chat_id"), "name": c.get("name", "未命名群组")}
                for c in items
            ]
            return {"success": True, "elements": chats}
        return {"success": False, "error": data.get("msg")}
    
    async def _list_members(self, chat_id: str) -> Dict[str, Any]:
        """获取群成员列表"""
        if not chat_id:
            return {"success": False, "error": "chat_id is required"}
        
        resp = await self._client.get(
            f"{self.BASE_URL}/im/v1/chats/{chat_id}/members",
            headers={"Authorization": f"Bearer {self._token}"}
        )
        
        data = resp.json()
        if data.get("code") == 0:
            items = data.get("data", {}).get("items", [])
            return {"success": True, "elements": items}
        return {"success": False, "error": data.get("msg")}
    
    async def _create_chat(self, target: Dict, value: Any) -> Dict[str, Any]:
        """创建群聊"""
        name = target.get("name") or value or "新群组"
        
        resp = await self._client.post(
            f"{self.BASE_URL}/im/v1/chats",
            headers={"Authorization": f"Bearer {self._token}"},
            json={"name": name}
        )
        
        data = resp.json()
        if data.get("code") == 0:
            return {"success": True, "data": data.get("data")}
        return {"success": False, "error": data.get("msg")}
    
    async def _read_messages(self, chat_id: str) -> Dict[str, Any]:
        """读取群消息（需要权限）"""
        # 注意：此功能需要申请额外权限
        return {"success": False, "error": "Not implemented - requires additional permissions"}
