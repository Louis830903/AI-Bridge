"""
WeCom Adapter - 企业微信开放API集成
Glue code wrapping httpx for WeCom REST API
"""

from typing import Any, Dict, Optional
import httpx
from aibridge.adapters.base import BaseAdapter, AdapterInfo, AdapterType


class WecomAdapter(BaseAdapter):
    """
    企业微信适配器 - 通过开放API进行消息发送和通讯录管理
    
    需要在企业微信管理后台创建应用并获取:
    - corp_id: 企业ID
    - corp_secret: 应用密钥
    - agent_id: 应用AgentId
    """
    
    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"
    
    info = AdapterInfo(
        id="wecom",
        name="企业微信",
        type=AdapterType.IM,
        version="1.0.0",
        platforms=["windows", "macos", "linux"],
        actions=[
            "send", "send_to_chat", "create_chat",
            "list_departments", "list_users", "list_chats"
        ],
        description="企业微信开放API集成",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.corp_id = self.config.get("corp_id", "")
        self.corp_secret = self.config.get("corp_secret", "")
        self.agent_id = self.config.get("agent_id", "")
        self._token = None
        self._client = None
    
    async def connect(self) -> bool:
        """获取 access_token"""
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            
            resp = await self._client.get(
                f"{self.BASE_URL}/gettoken",
                params={
                    "corpid": self.corp_id,
                    "corpsecret": self.corp_secret
                }
            )
            data = resp.json()
            
            if data.get("errcode") == 0:
                self._token = data.get("access_token")
                self._connected = True
                return True
            else:
                raise ConnectionError(f"WeCom auth failed: {data.get('errmsg')}")
                
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to WeCom: {e}")
    
    async def disconnect(self) -> bool:
        """断开连接"""
        if self._client:
            await self._client.aclose()
        self._token = None
        self._connected = False
        return True
    
    async def is_available(self) -> bool:
        """检查是否可用"""
        return bool(self.corp_id and self.corp_secret)
    
    async def execute(
        self,
        action: str,
        target: Optional[Dict[str, Any]] = None,
        value: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行企业微信操作"""
        target = target or {}
        
        try:
            if action == "send":
                return await self._send_message(target, value)
            
            elif action == "send_to_chat":
                return await self._send_to_chat(target, value)
            
            elif action == "create_chat":
                return await self._create_chat(target, value)
            
            elif action == "list_departments":
                return await self._list_departments()
            
            elif action == "list_users":
                dept_id = target.get("dept_id") or value
                return await self._list_users(dept_id)
            
            elif action == "list_chats":
                return {"success": False, "error": "list_chats requires appchat permissions"}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _send_message(self, target: Dict, value: Any) -> Dict[str, Any]:
        """发送应用消息"""
        touser = target.get("touser", "@all")
        toparty = target.get("toparty", "")
        totag = target.get("totag", "")
        content = value if isinstance(value, str) else str(value)
        
        message = {
            "touser": touser,
            "toparty": toparty,
            "totag": totag,
            "msgtype": "text",
            "agentid": int(self.agent_id) if self.agent_id else 0,
            "text": {"content": content}
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/message/send",
            params={"access_token": self._token},
            json=message
        )
        
        data = resp.json()
        if data.get("errcode") == 0:
            return {"success": True, "data": data}
        return {"success": False, "error": data.get("errmsg")}
    
    async def _send_to_chat(self, target: Dict, value: Any) -> Dict[str, Any]:
        """发送消息到群聊"""
        chatid = target.get("chatid") or target.get("chat_id")
        content = value if isinstance(value, str) else str(value)
        
        if not chatid:
            return {"success": False, "error": "chatid is required"}
        
        message = {
            "chatid": chatid,
            "msgtype": "text",
            "text": {"content": content}
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/appchat/send",
            params={"access_token": self._token},
            json=message
        )
        
        data = resp.json()
        if data.get("errcode") == 0:
            return {"success": True}
        return {"success": False, "error": data.get("errmsg")}
    
    async def _create_chat(self, target: Dict, value: Any) -> Dict[str, Any]:
        """创建群聊"""
        name = target.get("name") or value or "新群聊"
        owner = target.get("owner", "")
        userlist = target.get("userlist", [])
        
        if isinstance(userlist, str):
            userlist = userlist.split(",")
        
        chat_data = {
            "name": name,
            "userlist": userlist
        }
        if owner:
            chat_data["owner"] = owner
        
        resp = await self._client.post(
            f"{self.BASE_URL}/appchat/create",
            params={"access_token": self._token},
            json=chat_data
        )
        
        data = resp.json()
        if data.get("errcode") == 0:
            return {"success": True, "data": {"chatid": data.get("chatid")}}
        return {"success": False, "error": data.get("errmsg")}
    
    async def _list_departments(self) -> Dict[str, Any]:
        """获取部门列表"""
        resp = await self._client.get(
            f"{self.BASE_URL}/department/list",
            params={"access_token": self._token}
        )
        
        data = resp.json()
        if data.get("errcode") == 0:
            return {"success": True, "elements": data.get("department", [])}
        return {"success": False, "error": data.get("errmsg")}
    
    async def _list_users(self, dept_id: Any) -> Dict[str, Any]:
        """获取部门成员列表"""
        dept_id = int(dept_id) if dept_id else 1
        
        resp = await self._client.get(
            f"{self.BASE_URL}/user/list",
            params={
                "access_token": self._token,
                "department_id": dept_id
            }
        )
        
        data = resp.json()
        if data.get("errcode") == 0:
            users = data.get("userlist", [])
            return {"success": True, "elements": users}
        return {"success": False, "error": data.get("errmsg")}
