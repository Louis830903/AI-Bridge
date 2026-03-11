"""
Telegram 适配器
Telegram Adapter - Global instant messaging platform

使用 Telegram Bot API 实现消息发送和管理。
官方文档: https://core.telegram.org/bots/api

依赖: httpx (异步HTTP客户端)
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
import httpx

from ..base import BaseAdapter, AdapterInfo, AdapterType
from ...core.protocol import Target


@dataclass
class TelegramConfig:
    """Telegram 配置"""
    bot_token: str = ""      # Bot Token (从 @BotFather 获取)
    default_chat: str = ""   # 默认聊天 ID
    parse_mode: str = "HTML"  # 默认解析模式: HTML, Markdown, MarkdownV2
    timeout: int = 30


class TelegramAdapter(BaseAdapter):
    """
    Telegram 适配器
    
    通过 Telegram Bot API 实现:
    - 发送消息 (文本/图片/文档/音视频)
    - 编辑/删除消息
    - 管理群组
    - 内联键盘
    - Webhook 支持
    
    使用示例:
        config = TelegramConfig(bot_token="xxx:yyy")
        adapter = TelegramAdapter(config)
        await adapter.connect()
        await adapter.execute("send_message", Target(name="chat_id"), "Hello!")
    """
    
    BASE_URL = "https://api.telegram.org"
    
    def __init__(self, config: TelegramConfig):
        self._config = config
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False
        self._bot_info: Dict = {}
        
    @property
    def info(self) -> AdapterInfo:
        return AdapterInfo(
            id="telegram",
            name="Telegram",
            type=AdapterType.IM,
            version="1.0.0",
            description="Telegram Bot API adapter",
            actions=[
                "send_message",
                "send_photo",
                "send_document",
                "send_audio",
                "send_video",
                "send_location",
                "edit_message",
                "delete_message",
                "forward_message",
                "pin_message",
                "get_chat",
                "get_chat_members",
                "kick_member",
                "set_chat_title",
                "answer_callback",
            ]
        )
        
    @property
    def _api_url(self) -> str:
        return f"{self.BASE_URL}/bot{self._config.bot_token}"
        
    async def connect(self) -> bool:
        """连接 Telegram API"""
        if not self._config.bot_token:
            return False
            
        self._client = httpx.AsyncClient(timeout=self._config.timeout)
        
        # 验证 token 并获取 bot 信息
        try:
            resp = await self._client.get(f"{self._api_url}/getMe")
            data = resp.json()
            
            if data.get("ok"):
                self._bot_info = data.get("result", {})
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
        return True
        
    async def execute(
        self,
        action: str,
        target: Optional[Target],
        value: Optional[Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行 Telegram 操作"""
        
        if not self._connected:
            return {"success": False, "error": "Not connected"}
            
        try:
            if action == "send_message":
                return await self._send_message(target, value, options)
            elif action == "send_photo":
                return await self._send_photo(target, value, options)
            elif action == "send_document":
                return await self._send_document(target, value, options)
            elif action == "send_audio":
                return await self._send_audio(target, value, options)
            elif action == "send_video":
                return await self._send_video(target, value, options)
            elif action == "send_location":
                return await self._send_location(target, value, options)
            elif action == "edit_message":
                return await self._edit_message(target, value, options)
            elif action == "delete_message":
                return await self._delete_message(target, options)
            elif action == "forward_message":
                return await self._forward_message(target, options)
            elif action == "pin_message":
                return await self._pin_message(target, options)
            elif action == "get_chat":
                return await self._get_chat(target)
            elif action == "get_chat_members":
                return await self._get_chat_members(target)
            elif action == "kick_member":
                return await self._kick_member(target, value)
            elif action == "set_chat_title":
                return await self._set_chat_title(target, value)
            elif action == "answer_callback":
                return await self._answer_callback(value, options)
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
        chat_id = target.name if target else self._config.default_chat
        
        payload = {
            "chat_id": chat_id,
            "text": str(value),
            "parse_mode": options.get("parse_mode", self._config.parse_mode),
        }
        
        # 支持回复
        if options.get("reply_to"):
            payload["reply_to_message_id"] = options["reply_to"]
            
        # 支持内联键盘
        if options.get("keyboard"):
            payload["reply_markup"] = {
                "inline_keyboard": options["keyboard"]
            }
            
        # 禁用链接预览
        if options.get("disable_preview"):
            payload["disable_web_page_preview"] = True
            
        # 静默发送
        if options.get("silent"):
            payload["disable_notification"] = True
            
        resp = await self._client.post(
            f"{self._api_url}/sendMessage",
            json=payload
        )
        data = resp.json()
        
        if data.get("ok"):
            result = data.get("result", {})
            return {
                "success": True,
                "message_id": result.get("message_id"),
                "chat_id": result.get("chat", {}).get("id")
            }
        else:
            return {"success": False, "error": data.get("description")}
            
    async def _send_photo(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送图片"""
        chat_id = target.name if target else self._config.default_chat
        
        data = {
            "chat_id": chat_id,
            "caption": options.get("caption", ""),
            "parse_mode": options.get("parse_mode", self._config.parse_mode),
        }
        
        # 支持 URL 或文件路径
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            data["photo"] = value
            resp = await self._client.post(f"{self._api_url}/sendPhoto", data=data)
        else:
            with open(value, "rb") as f:
                files = {"photo": f}
                resp = await self._client.post(
                    f"{self._api_url}/sendPhoto",
                    data=data,
                    files=files
                )
                
        result = resp.json()
        return {"success": result.get("ok"), "result": result.get("result")}
        
    async def _send_document(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送文档"""
        chat_id = target.name if target else self._config.default_chat
        
        data = {
            "chat_id": chat_id,
            "caption": options.get("caption", ""),
        }
        
        with open(value, "rb") as f:
            files = {"document": f}
            resp = await self._client.post(
                f"{self._api_url}/sendDocument",
                data=data,
                files=files
            )
            
        result = resp.json()
        return {"success": result.get("ok"), "result": result.get("result")}
        
    async def _send_audio(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送音频"""
        chat_id = target.name if target else self._config.default_chat
        
        data = {
            "chat_id": chat_id,
            "caption": options.get("caption", ""),
            "title": options.get("title", ""),
            "performer": options.get("performer", ""),
        }
        
        with open(value, "rb") as f:
            files = {"audio": f}
            resp = await self._client.post(
                f"{self._api_url}/sendAudio",
                data=data,
                files=files
            )
            
        result = resp.json()
        return {"success": result.get("ok"), "result": result.get("result")}
        
    async def _send_video(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送视频"""
        chat_id = target.name if target else self._config.default_chat
        
        data = {
            "chat_id": chat_id,
            "caption": options.get("caption", ""),
        }
        
        with open(value, "rb") as f:
            files = {"video": f}
            resp = await self._client.post(
                f"{self._api_url}/sendVideo",
                data=data,
                files=files
            )
            
        result = resp.json()
        return {"success": result.get("ok"), "result": result.get("result")}
        
    async def _send_location(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """发送位置"""
        chat_id = target.name if target else self._config.default_chat
        
        # value 应为 {"latitude": x, "longitude": y} 或 "lat,lng" 字符串
        if isinstance(value, str):
            lat, lng = value.split(",")
            latitude, longitude = float(lat), float(lng)
        else:
            latitude = value.get("latitude")
            longitude = value.get("longitude")
            
        payload = {
            "chat_id": chat_id,
            "latitude": latitude,
            "longitude": longitude,
        }
        
        resp = await self._client.post(f"{self._api_url}/sendLocation", json=payload)
        result = resp.json()
        
        return {"success": result.get("ok"), "result": result.get("result")}
        
    async def _edit_message(
        self,
        target: Optional[Target],
        value: Any,
        options: Dict
    ) -> Dict:
        """编辑消息"""
        chat_id = target.name if target else self._config.default_chat
        message_id = options.get("message_id")
        
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": str(value),
            "parse_mode": options.get("parse_mode", self._config.parse_mode),
        }
        
        resp = await self._client.post(f"{self._api_url}/editMessageText", json=payload)
        result = resp.json()
        
        return {"success": result.get("ok")}
        
    async def _delete_message(
        self,
        target: Optional[Target],
        options: Dict
    ) -> Dict:
        """删除消息"""
        chat_id = target.name if target else self._config.default_chat
        message_id = options.get("message_id")
        
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
        }
        
        resp = await self._client.post(f"{self._api_url}/deleteMessage", json=payload)
        result = resp.json()
        
        return {"success": result.get("ok")}
        
    async def _forward_message(
        self,
        target: Optional[Target],
        options: Dict
    ) -> Dict:
        """转发消息"""
        to_chat_id = target.name if target else self._config.default_chat
        from_chat_id = options.get("from_chat")
        message_id = options.get("message_id")
        
        payload = {
            "chat_id": to_chat_id,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
        }
        
        resp = await self._client.post(f"{self._api_url}/forwardMessage", json=payload)
        result = resp.json()
        
        return {"success": result.get("ok"), "result": result.get("result")}
        
    async def _pin_message(
        self,
        target: Optional[Target],
        options: Dict
    ) -> Dict:
        """置顶消息"""
        chat_id = target.name if target else self._config.default_chat
        message_id = options.get("message_id")
        
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "disable_notification": options.get("silent", False),
        }
        
        resp = await self._client.post(f"{self._api_url}/pinChatMessage", json=payload)
        result = resp.json()
        
        return {"success": result.get("ok")}
        
    async def _get_chat(self, target: Target) -> Dict:
        """获取聊天信息"""
        resp = await self._client.post(
            f"{self._api_url}/getChat",
            json={"chat_id": target.name}
        )
        result = resp.json()
        
        if result.get("ok"):
            return {"success": True, "chat": result.get("result")}
        else:
            return {"success": False, "error": result.get("description")}
            
    async def _get_chat_members(self, target: Target) -> Dict:
        """获取群成员数"""
        resp = await self._client.post(
            f"{self._api_url}/getChatMemberCount",
            json={"chat_id": target.name}
        )
        result = resp.json()
        
        if result.get("ok"):
            return {"success": True, "count": result.get("result")}
        else:
            return {"success": False, "error": result.get("description")}
            
    async def _kick_member(self, target: Target, user_id: Any) -> Dict:
        """踢出成员"""
        payload = {
            "chat_id": target.name,
            "user_id": int(user_id),
        }
        
        resp = await self._client.post(f"{self._api_url}/banChatMember", json=payload)
        result = resp.json()
        
        return {"success": result.get("ok")}
        
    async def _set_chat_title(self, target: Target, title: str) -> Dict:
        """设置群标题"""
        payload = {
            "chat_id": target.name,
            "title": title,
        }
        
        resp = await self._client.post(f"{self._api_url}/setChatTitle", json=payload)
        result = resp.json()
        
        return {"success": result.get("ok")}
        
    async def _answer_callback(self, callback_id: str, options: Dict) -> Dict:
        """回应回调查询 (内联键盘点击)"""
        payload = {
            "callback_query_id": callback_id,
            "text": options.get("text", ""),
            "show_alert": options.get("show_alert", False),
        }
        
        resp = await self._client.post(f"{self._api_url}/answerCallbackQuery", json=payload)
        result = resp.json()
        
        return {"success": result.get("ok")}
