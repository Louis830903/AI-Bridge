"""
KakaoTalk 适配器
KakaoTalk Adapter - Dominant messaging platform in South Korea

使用 Kakao Talk Channel API 实现消息发送和管理。
官方文档: https://developers.kakao.com/docs/latest/ko/kakaotalk-channel/common

依赖: httpx (异步HTTP客户端)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import httpx

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class KakaoTalkConfig:
    """KakaoTalk 配置"""
    app_key: str = ""           # REST API 키
    admin_key: str = ""         # Admin 키 (服务端用)
    access_token: str = ""      # 用户 Access Token
    channel_id: str = ""        # 카카오톡 채널 ID
    timeout: int = 30


class KakaoTalkAdapter(BaseAdapter):
    """
    KakaoTalk Channel API 适配器
    
    通过 Kakao API 实现:
    - 发送消息 (文本/图片/列表/商业模板)
    - 好友管理
    - 消息模板管理
    - 用户信息获取
    
    注意: KakaoTalk API 主要面向韩国市场，需要韩国业务主体
    
    使用示例:
        config = KakaoTalkConfig(
            app_key="xxx",
            admin_key="xxx",
            channel_id="@channel"
        )
        adapter = KakaoTalkAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="user_uuid"), "안녕하세요!")
    """
    
    BASE_URL = "https://kapi.kakao.com"
    AUTH_URL = "https://kauth.kakao.com"
    
    def __init__(self, config: KakaoTalkConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="kakaotalk",
            name="KakaoTalk",
            type=AdapterType.IM,
            version="1.0.0",
            description="KakaoTalk Channel API adapter",
            actions=[
                "send_message",
                "send_to_me",
                "send_to_friend",
                "send_template",
                "list_friends",
                "get_profile",
                "send_commerce",
                "send_list",
            ]
        )
        
    async def connect(self) -> bool:
        """连接 Kakao API"""
        if not self._config.admin_key and not self._config.access_token:
            return False
            
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        
        # 优先使用 Admin Key
        if self._config.admin_key:
            headers["Authorization"] = f"KakaoAK {self._config.admin_key}"
        elif self._config.access_token:
            headers["Authorization"] = f"Bearer {self._config.access_token}"
            
        self._client = httpx.AsyncClient(
            timeout=self._config.timeout,
            headers=headers
        )
        
        # 验证连接
        try:
            # 尝试获取用户信息验证 token
            resp = await self._client.get(f"{self.BASE_URL}/v2/user/me")
            self._connected = resp.status_code in (200, 401)  # 401 也算连接成功，只是没权限
            return True
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
        """执行 KakaoTalk 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            if action == "send_message":
                return await self._send_message(target, value, options)
            elif action == "send_to_me":
                return await self._send_to_me(value, options)
            elif action == "send_to_friend":
                return await self._send_to_friend(target, value, options)
            elif action == "send_template":
                return await self._send_template(target, value, options)
            elif action == "list_friends":
                return await self._list_friends(options)
            elif action == "get_profile":
                return await self._get_profile()
            elif action == "send_commerce":
                return await self._send_commerce(target, value, options)
            elif action == "send_list":
                return await self._send_list(target, value, options)
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
        """发送消息 (通过模板)"""
        receiver_uuids = [target.name] if target else options.get("receiver_uuids", [])
        template_id = options.get("template_id")
        
        if template_id:
            # 使用已注册的模板
            return await self._send_template(target, template_id, options)
        else:
            # 默认文本消息 (需要通过模板)
            return await self._send_default_text(receiver_uuids, str(value), options)
            
    async def _send_default_text(
        self,
        receiver_uuids: List[str],
        text: str,
        options: Dict
    ) -> Dict:
        """发送默认文本消息"""
        # KakaoTalk 需要使用模板，这里使用默认文本模板格式
        template_object = {
            "object_type": "text",
            "text": text,
            "link": {
                "web_url": options.get("web_url", ""),
                "mobile_web_url": options.get("mobile_web_url", "")
            }
        }
        
        if options.get("button_title"):
            template_object["button_title"] = options["button_title"]
            
        import json
        data = {
            "receiver_uuids": json.dumps(receiver_uuids),
            "template_object": json.dumps(template_object)
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/v1/api/talk/friends/message/default/send",
            data=data
        )
        result = resp.json()
        
        if "successful_receiver_uuids" in result:
            return {
                "success": True,
                "successful": result.get("successful_receiver_uuids", []),
                "failed": result.get("failure_info", [])
            }
        else:
            return {"success": False, "error": result.get("msg", str(result))}
            
    async def _send_to_me(self, value: Any, options: Dict) -> Dict:
        """发送消息给自己"""
        template_object = {
            "object_type": "text",
            "text": str(value),
            "link": {
                "web_url": options.get("web_url", ""),
                "mobile_web_url": options.get("mobile_web_url", "")
            }
        }
        
        import json
        data = {"template_object": json.dumps(template_object)}
        
        resp = await self._client.post(
            f"{self.BASE_URL}/v2/api/talk/memo/default/send",
            data=data
        )
        result = resp.json()
        
        return {"success": result.get("result_code") == 0 or "result_code" not in result}
        
    async def _send_to_friend(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送消息给好友"""
        uuid = target.name if target else ""
        
        template_object = {
            "object_type": "text",
            "text": str(value),
            "link": {
                "web_url": options.get("web_url", ""),
                "mobile_web_url": options.get("mobile_web_url", "")
            }
        }
        
        import json
        data = {
            "receiver_uuids": json.dumps([uuid]),
            "template_object": json.dumps(template_object)
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/v1/api/talk/friends/message/default/send",
            data=data
        )
        result = resp.json()
        
        return {"success": "successful_receiver_uuids" in result}
        
    async def _send_template(
        self,
        target: Optional[Target],
        template_id: Any,
        options: Dict
    ) -> Dict:
        """发送模板消息"""
        receiver_uuids = [target.name] if target else options.get("receiver_uuids", [])
        
        import json
        data = {
            "receiver_uuids": json.dumps(receiver_uuids),
            "template_id": str(template_id)
        }
        
        # 模板参数
        if options.get("template_args"):
            data["template_args"] = json.dumps(options["template_args"])
            
        resp = await self._client.post(
            f"{self.BASE_URL}/v1/api/talk/friends/message/send",
            data=data
        )
        result = resp.json()
        
        if "successful_receiver_uuids" in result:
            return {"success": True, "result": result}
        else:
            return {"success": False, "error": result.get("msg", str(result))}
            
    async def _list_friends(self, options: Dict) -> Dict:
        """获取好友列表"""
        params = {
            "offset": options.get("offset", 0),
            "limit": options.get("limit", 100),
            "order": options.get("order", "asc")
        }
        
        resp = await self._client.get(
            f"{self.BASE_URL}/v1/api/talk/friends",
            params=params
        )
        result = resp.json()
        
        if "elements" in result:
            return {
                "success": True,
                "friends": result.get("elements", []),
                "total_count": result.get("total_count", 0)
            }
        else:
            return {"success": False, "error": result.get("msg", str(result))}
            
    async def _get_profile(self) -> Dict:
        """获取我的资料"""
        resp = await self._client.get(f"{self.BASE_URL}/v2/user/me")
        result = resp.json()
        
        if "id" in result:
            return {"success": True, "profile": result}
        else:
            return {"success": False, "error": result.get("msg", str(result))}
            
    async def _send_commerce(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送商业消息 (商品推荐)"""
        receiver_uuids = [target.name] if target else options.get("receiver_uuids", [])
        
        # Commerce 模板
        template_object = {
            "object_type": "commerce",
            "content": {
                "title": value.get("title", ""),
                "image_url": value.get("image_url", ""),
                "link": {
                    "web_url": value.get("web_url", ""),
                    "mobile_web_url": value.get("mobile_web_url", "")
                },
                "description": value.get("description", "")
            },
            "commerce": {
                "regular_price": value.get("regular_price", 0),
                "discount_price": value.get("discount_price"),
                "discount_rate": value.get("discount_rate"),
                "product_name": value.get("product_name", "")
            }
        }
        
        # 按钮
        if options.get("buttons"):
            template_object["buttons"] = options["buttons"]
            
        import json
        data = {
            "receiver_uuids": json.dumps(receiver_uuids),
            "template_object": json.dumps(template_object)
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/v1/api/talk/friends/message/default/send",
            data=data
        )
        result = resp.json()
        
        return {"success": "successful_receiver_uuids" in result}
        
    async def _send_list(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送列表消息"""
        receiver_uuids = [target.name] if target else options.get("receiver_uuids", [])
        
        # List 模板
        template_object = {
            "object_type": "list",
            "header_title": options.get("header_title", ""),
            "header_link": {
                "web_url": options.get("header_web_url", ""),
                "mobile_web_url": options.get("header_mobile_url", "")
            },
            "contents": value  # 列表内容数组
        }
        
        if options.get("buttons"):
            template_object["buttons"] = options["buttons"]
            
        import json
        data = {
            "receiver_uuids": json.dumps(receiver_uuids),
            "template_object": json.dumps(template_object)
        }
        
        resp = await self._client.post(
            f"{self.BASE_URL}/v1/api/talk/friends/message/default/send",
            data=data
        )
        result = resp.json()
        
        return {"success": "successful_receiver_uuids" in result}
