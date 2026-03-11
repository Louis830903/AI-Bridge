"""
Microsoft Teams 适配器
Microsoft Teams Adapter - Enterprise collaboration platform

使用 Microsoft Graph API 实现消息发送和管理。
官方文档: https://learn.microsoft.com/en-us/graph/api/resources/teams-api-overview

依赖: httpx (异步HTTP客户端)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class TeamsConfig:
    """Microsoft Teams 配置"""
    tenant_id: str = ""      # Azure AD 租户 ID
    client_id: str = ""      # 应用程序 (客户端) ID
    client_secret: str = ""  # 客户端密码
    timeout: int = 30


class TeamsAdapter(BaseAdapter):
    """
    Microsoft Teams 适配器
    
    通过 Microsoft Graph API 实现:
    - 发送频道消息
    - 发送聊天消息
    - 创建团队/频道
    - 管理成员
    
    使用示例:
        config = TeamsConfig(
            tenant_id="xxx",
            client_id="xxx",
            client_secret="xxx"
        )
        adapter = TeamsAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="channel_id"), "Hello!")
    """
    
    GRAPH_URL = "https://graph.microsoft.com/v1.0"
    AUTH_URL = "https://login.microsoftonline.com"
    
    def __init__(self, config: TeamsConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._access_token: str = ""
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="teams",
            name="Microsoft Teams",
            type=AdapterType.IM,
            version="1.0.0",
            description="Microsoft Teams Graph API adapter",
            actions=[
                "send_message",
                "send_channel_message",
                "send_chat_message",
                "list_teams",
                "list_channels",
                "create_channel",
                "list_members",
                "add_member",
            ]
        )
        
    async def connect(self) -> bool:
        """连接 Microsoft Graph API"""
        if not all([self._config.tenant_id, self._config.client_id, self._config.client_secret]):
            return False
            
        self._client = httpx.AsyncClient(timeout=self._config.timeout)
        
        # 获取访问令牌 (Client Credentials Flow)
        try:
            token_url = f"{self.AUTH_URL}/{self._config.tenant_id}/oauth2/v2.0/token"
            
            resp = await self._client.post(
                token_url,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                    "scope": "https://graph.microsoft.com/.default",
                }
            )
            data = resp.json()
            
            if "access_token" in data:
                self._access_token = data["access_token"]
                self._client.headers["Authorization"] = f"Bearer {self._access_token}"
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
        self._access_token = ""
        return True
        
    async def execute(
        self,
        action: str,
        target: Optional[Target],
        value: Optional[Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行 Teams 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            if action == "send_message":
                # 智能判断发送目标
                if options.get("chat_id"):
                    return await self._send_chat_message(options["chat_id"], value, options)
                else:
                    return await self._send_channel_message(target, value, options)
            elif action == "send_channel_message":
                return await self._send_channel_message(target, value, options)
            elif action == "send_chat_message":
                return await self._send_chat_message(target.name if target else "", value, options)
            elif action == "list_teams":
                return await self._list_teams()
            elif action == "list_channels":
                return await self._list_channels(target)
            elif action == "create_channel":
                return await self._create_channel(target, value, options)
            elif action == "list_members":
                return await self._list_members(target)
            elif action == "add_member":
                return await self._add_member(target, value, options)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _send_channel_message(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送频道消息"""
        team_id = options.get("team_id", "")
        channel_id = target.name if target else ""
        
        if not team_id or not channel_id:
            return {"success": False, "error": "team_id and channel_id required"}
            
        payload = {
            "body": {
                "contentType": options.get("content_type", "text"),
                "content": str(value),
            }
        }
        
        # 支持 @ 提及
        if options.get("mentions"):
            payload["mentions"] = options["mentions"]
            
        resp = await self._client.post(
            f"{self.GRAPH_URL}/teams/{team_id}/channels/{channel_id}/messages",
            json=payload
        )
        
        if resp.status_code == 201:
            data = resp.json()
            return {
                "success": True,
                "message_id": data.get("id"),
                "created_time": data.get("createdDateTime")
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _send_chat_message(
        self,
        chat_id: str,
        value: Any,
        options: Dict
    ) -> Dict:
        """发送聊天消息"""
        payload = {
            "body": {
                "contentType": options.get("content_type", "text"),
                "content": str(value),
            }
        }
        
        resp = await self._client.post(
            f"{self.GRAPH_URL}/chats/{chat_id}/messages",
            json=payload
        )
        
        if resp.status_code == 201:
            data = resp.json()
            return {
                "success": True,
                "message_id": data.get("id")
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _list_teams(self) -> Dict:
        """列出团队"""
        resp = await self._client.get(f"{self.GRAPH_URL}/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')")
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "teams": data.get("value", [])
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _list_channels(self, target: Target) -> Dict:
        """列出频道"""
        team_id = target.name
        
        resp = await self._client.get(f"{self.GRAPH_URL}/teams/{team_id}/channels")
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "channels": data.get("value", [])
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _create_channel(
        self,
        target: Target,
        value: str,
        options: Dict
    ) -> Dict:
        """创建频道"""
        team_id = target.name
        
        payload = {
            "displayName": value,
            "description": options.get("description", ""),
            "membershipType": options.get("membership_type", "standard"),  # standard, private, shared
        }
        
        resp = await self._client.post(
            f"{self.GRAPH_URL}/teams/{team_id}/channels",
            json=payload
        )
        
        if resp.status_code == 201:
            data = resp.json()
            return {
                "success": True,
                "channel": data
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _list_members(self, target: Target) -> Dict:
        """列出成员"""
        team_id = target.name
        
        resp = await self._client.get(f"{self.GRAPH_URL}/teams/{team_id}/members")
        
        if resp.status_code == 200:
            data = resp.json()
            return {
                "success": True,
                "members": data.get("value", [])
            }
        else:
            return {"success": False, "error": resp.text}
            
    async def _add_member(
        self,
        target: Target,
        value: str,
        options: Dict
    ) -> Dict:
        """添加成员"""
        team_id = target.name
        user_id = value  # Azure AD 用户 ID
        
        payload = {
            "@odata.type": "#microsoft.graph.aadUserConversationMember",
            "roles": options.get("roles", ["member"]),  # owner, member
            "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{user_id}')"
        }
        
        resp = await self._client.post(
            f"{self.GRAPH_URL}/teams/{team_id}/members",
            json=payload
        )
        
        if resp.status_code == 201:
            return {"success": True}
        else:
            return {"success": False, "error": resp.text}
