"""
DingTalk Adapter - 钉钉开放API集成
Glue code wrapping httpx for DingTalk REST API
"""

import time
import hmac
import hashlib
import base64
import urllib.parse
from typing import Any, Dict, Optional
import httpx
from aibridge.adapters.base import BaseAdapter, AdapterInfo, AdapterType


class DingtalkAdapter(BaseAdapter):
    """
    钉钉适配器 - 支持企业内部应用和Webhook机器人
    
    两种模式:
    1. Webhook机器人: 只需要 webhook_url 和 secret
    2. 企业应用: 需要 app_key 和 app_secret
    """
    
    BASE_URL = "https://oapi.dingtalk.com"
    API_URL = "https://api.dingtalk.com"
    
    info = AdapterInfo(
        id="dingtalk",
        name="钉钉",
        type=AdapterType.IM,
        version="1.0.0",
        platforms=["windows", "macos", "linux"],
        actions=[
            "send", "send_webhook", "send_work_notice",
            "list_departments", "list_users"
        ],
        description="钉钉开放API集成",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Webhook模式
        self.webhook_url = self.config.get("webhook_url", "")
        self.webhook_secret = self.config.get("webhook_secret", "")
        # 企业应用模式
        self.app_key = self.config.get("app_key", "")
        self.app_secret = self.config.get("app_secret", "")
        self._token = None
        self._client = None
    
    async def connect(self) -> bool:
        """连接钉钉（获取access_token）"""
        try:
            self._client = httpx.AsyncClient(timeout=30.0)
            
            # 如果有企业应用凭证，获取token
            if self.app_key and self.app_secret:
                resp = await self._client.post(
                    f"{self.API_URL}/v1.0/oauth2/accessToken",
                    json={
                        "appKey": self.app_key,
                        "appSecret": self.app_secret
                    }
                )
                data = resp.json()
                
                if "accessToken" in data:
                    self._token = data["accessToken"]
                    self._connected = True
                    return True
                else:
                    raise ConnectionError(f"DingTalk auth failed: {data}")
            
            # Webhook模式不需要token
            elif self.webhook_url:
                self._connected = True
                return True
            
            return False
            
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to DingTalk: {e}")
    
    async def disconnect(self) -> bool:
        """断开连接"""
        if self._client:
            await self._client.aclose()
        self._token = None
        self._connected = False
        return True
    
    async def is_available(self) -> bool:
        """检查是否可用"""
        return bool(self.webhook_url or (self.app_key and self.app_secret))
    
    async def execute(
        self,
        action: str,
        target: Optional[Dict[str, Any]] = None,
        value: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行钉钉操作"""
        target = target or {}
        
        try:
            if action == "send" or action == "send_webhook":
                return await self._send_webhook(value)
            
            elif action == "send_work_notice":
                return await self._send_work_notice(target, value)
            
            elif action == "list_departments":
                return await self._list_departments()
            
            elif action == "list_users":
                dept_id = target.get("dept_id") or value
                return await self._list_users(dept_id)
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _sign_webhook(self) -> tuple:
        """生成Webhook签名"""
        timestamp = str(round(time.time() * 1000))
        secret_enc = self.webhook_secret.encode('utf-8')
        string_to_sign = f'{timestamp}\n{self.webhook_secret}'
        string_to_sign_enc = string_to_sign.encode('utf-8')
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return timestamp, sign
    
    async def _send_webhook(self, value: Any) -> Dict[str, Any]:
        """通过Webhook发送消息"""
        if not self.webhook_url:
            return {"success": False, "error": "webhook_url is required"}
        
        url = self.webhook_url
        if self.webhook_secret:
            timestamp, sign = self._sign_webhook()
            url = f"{self.webhook_url}&timestamp={timestamp}&sign={sign}"
        
        # 构建消息
        if isinstance(value, str):
            message = {
                "msgtype": "text",
                "text": {"content": value}
            }
        elif isinstance(value, dict):
            message = value
        else:
            message = {
                "msgtype": "text",
                "text": {"content": str(value)}
            }
        
        resp = await self._client.post(url, json=message)
        data = resp.json()
        
        if data.get("errcode") == 0:
            return {"success": True}
        return {"success": False, "error": data.get("errmsg")}
    
    async def _send_work_notice(self, target: Dict, value: Any) -> Dict[str, Any]:
        """发送工作通知"""
        if not self._token:
            return {"success": False, "error": "Not authenticated with enterprise app"}
        
        userid_list = target.get("userid_list", [])
        if isinstance(userid_list, str):
            userid_list = userid_list.split(",")
        
        content = value if isinstance(value, str) else str(value)
        
        resp = await self._client.post(
            f"{self.API_URL}/v1.0/robot/oToMessages/batchSend",
            headers={"x-acs-dingtalk-access-token": self._token},
            json={
                "robotCode": self.app_key,
                "userIds": userid_list,
                "msgKey": "sampleText",
                "msgParam": f'{{"content": "{content}"}}'
            }
        )
        
        data = resp.json()
        if "processQueryKey" in data:
            return {"success": True, "data": data}
        return {"success": False, "error": str(data)}
    
    async def _list_departments(self) -> Dict[str, Any]:
        """获取部门列表"""
        if not self._token:
            return {"success": False, "error": "Not authenticated"}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/topapi/v2/department/listsub",
            params={"access_token": self._token},
            json={}
        )
        
        data = resp.json()
        if data.get("errcode") == 0:
            return {"success": True, "elements": data.get("result", [])}
        return {"success": False, "error": data.get("errmsg")}
    
    async def _list_users(self, dept_id: Any) -> Dict[str, Any]:
        """获取部门用户列表"""
        if not self._token:
            return {"success": False, "error": "Not authenticated"}
        
        dept_id = int(dept_id) if dept_id else 1
        
        resp = await self._client.post(
            f"{self.BASE_URL}/topapi/v2/user/list",
            params={"access_token": self._token},
            json={"dept_id": dept_id, "cursor": 0, "size": 100}
        )
        
        data = resp.json()
        if data.get("errcode") == 0:
            users = data.get("result", {}).get("list", [])
            return {"success": True, "elements": users}
        return {"success": False, "error": data.get("errmsg")}
