"""
MCP Server - 将 AI-Bridge 能力通过 MCP 协议暴露给外部 AI 工具

MCP (Model Context Protocol) 是 Anthropic 推出的标准协议，
让 AI 工具能够统一调用外部能力。

支持的工具:
- browser_navigate: 浏览器导航
- browser_click: 点击元素
- browser_type: 输入文本
- browser_extract: 提取数据
- browser_execute_intent: 执行自然语言意图
- browser_execute_task: 执行复杂任务(O-R-A循环)
"""

import asyncio
import json
import logging
import socket
import ipaddress
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

from aibridge.utils.security import validate_css_selector

# MCP 协议相关类型（如果不安装mcp包，使用简化版本）
try:
    from mcp.server import Server
    from mcp.types import Tool, TextContent, ImageContent
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logging.warning("mcp package not installed, using mock implementation")

from aibridge.adapters.browser.chrome import ChromeAdapter
from aibridge.core.intent_engine import IntentEngine
from aibridge.core.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


# ============ 工具定义 ============

BROWSER_TOOLS = [
    {
        "name": "browser_navigate",
        "description": "导航浏览器到指定URL，并返回页面基本信息",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "目标URL，例如 https://www.baidu.com"
                },
                "wait_until": {
                    "type": "string",
                    "enum": ["load", "domcontentloaded", "networkidle"],
                    "description": "等待页面加载的状态",
                    "default": "domcontentloaded"
                }
            },
            "required": ["url"]
        }
    },
    {
        "name": "browser_click",
        "description": "点击页面上的元素，支持多种定位方式",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS选择器，例如 #submit-button"
                },
                "text": {
                    "type": "string",
                    "description": "通过文本内容定位元素"
                },
                "force": {
                    "type": "boolean",
                    "description": "是否强制点击（即使元素隐藏）",
                    "default": False
                }
            },
            "anyOf": [{"required": ["selector"]}, {"required": ["text"]}]
        }
    },
    {
        "name": "browser_type",
        "description": "在输入框中输入文本",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "输入框的CSS选择器"
                },
                "text": {
                    "type": "string",
                    "description": "要输入的文本"
                },
                "force": {
                    "type": "boolean",
                    "description": "是否强制输入（即使元素隐藏）",
                    "default": False
                }
            },
            "required": ["selector", "text"]
        }
    },
    {
        "name": "browser_extract",
        "description": "从页面提取结构化数据",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "要提取的元素CSS选择器"
                },
                "fields": {
                    "type": "object",
                    "description": "要提取的字段及其类型，例如 {\"title\": \"string\", \"price\": \"number\"}"
                },
                "multiple": {
                    "type": "boolean",
                    "description": "是否提取多个元素",
                    "default": False
                }
            },
            "required": ["selector"]
        }
    },
    {
        "name": "browser_screenshot",
        "description": "截取当前页面或指定元素的截图",
        "inputSchema": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "元素选择器（不传则截取全屏）"
                },
                "full_page": {
                    "type": "boolean",
                    "description": "是否截取完整页面",
                    "default": False
                }
            }
        }
    },
    {
        "name": "browser_execute_intent",
        "description": "使用自然语言描述意图，AI-Bridge 自动执行相应操作。例如：'搜索iPhone 15'、'点击提交按钮'、'提取所有商品名称'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "自然语言意图描述"
                },
                "context": {
                    "type": "object",
                    "description": "额外的上下文信息",
                    "default": {}
                }
            },
            "required": ["intent"]
        }
    },
    {
        "name": "browser_execute_task",
        "description": "执行复杂的多步骤任务，使用O-R-A（观察-推理-行动）循环自动完成。例如：'在京东上搜索iPhone 15，提取前3个商品的价格和评分'",
        "inputSchema": {
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "任务目标描述"
                },
                "max_steps": {
                    "type": "integer",
                    "description": "最大执行步数",
                    "default": 10
                },
                "callback_url": {
                    "type": "string",
                    "description": "可选的回调URL，用于接收进度更新"
                }
            },
            "required": ["goal"]
        }
    }
]


# ============ MCP Server 实现 ============

class AIBridgeMCPServer:
    """
    AI-Bridge MCP Server
    
    将浏览器自动化能力通过 MCP 协议暴露给外部 AI 工具。
    支持 Claude Desktop、Cursor、Cline 等 MCP 客户端。
    """
    
    def __init__(self, allow_private_ips: bool = False):
        self.adapter: Optional[ChromeAdapter] = None
        self.intent_engine: Optional[IntentEngine] = None
        self.orchestrator: Optional[Orchestrator] = None
        self._connected = False
        self._shutdown_event: Optional[asyncio.Event] = None
        self._allow_private_ips = allow_private_ips
    
    async def initialize(self):
        """初始化所有组件"""
        logger.info("Initializing AI-Bridge MCP Server...")
        
        # 初始化浏览器适配器
        self.adapter = ChromeAdapter()
        await self.adapter.connect()
        
        # 初始化意图引擎
        self.intent_engine = IntentEngine(self.adapter)
        await self.intent_engine.initialize()
        
        # 初始化编排器
        self.orchestrator = Orchestrator(self.adapter, self.intent_engine)
        
        self._connected = True
        logger.info("AI-Bridge MCP Server initialized successfully")
    
    async def shutdown(self):
        """关闭所有组件"""
        logger.info("Shutting down AI-Bridge MCP Server...")
        
        # 触发关闭事件
        if self._shutdown_event:
            self._shutdown_event.set()
        
        if self.adapter:
            await self.adapter.disconnect()
        
        self._connected = False
        logger.info("AI-Bridge MCP Server shut down")
    
    # ============ 工具处理函数 ============
    
    async def _check_initialized(self) -> Optional[dict]:
        """检查服务器是否已初始化"""
        if not self._connected or not self.adapter:
            return {
                "success": False,
                "error": "MCP Server 未初始化，请先调用 initialize()",
                "summary": "服务器未就绪"
            }
        return None
    
    async def _validate_url(self, url: str) -> tuple[bool, str]:
        """
        验证 URL 安全性，防止 SSRF 攻击
        
        检查：
        - URL 存在性
        - 协议限制 (http/https)
        - 主机名有效性
        - 内网/私有地址检测（异步 DNS 解析，不阻塞事件循环）
        
        Returns:
            (is_valid, error_message)
        """
        from urllib.parse import urlparse
        
        if not url:
            return False, "URL 不能为空"
        
        if not isinstance(url, str):
            return False, "URL 必须是字符串"
        
        # 长度限制
        if len(url) > 2048:
            return False, "URL 过长"
        
        try:
            parsed = urlparse(url)
            
            # 只允许 http/https
            if parsed.scheme not in ('http', 'https'):
                return False, f"不支持的协议: {parsed.scheme}，只允许 http/https"
            
            # 检查主机名
            if not parsed.netloc:
                return False, "URL 缺少主机名"
            
            hostname = parsed.hostname
            if not hostname:
                return False, "无法解析主机名"
            
            # 检查是否为内网地址（异步 DNS 解析）
            if not self._allow_private_ips:
                try:
                    loop = asyncio.get_running_loop()
                    addr_info = await loop.run_in_executor(
                        None, socket.getaddrinfo, hostname, None
                    )
                    ip = addr_info[0][4][0]
                    addr = ipaddress.ip_address(ip)
                    
                    if addr.is_loopback:
                        return False, f"不允许访问回环地址: {hostname}"
                    if addr.is_private:
                        return False, f"不允许访问内网地址: {hostname}"
                    if addr.is_link_local:
                        return False, f"不允许访问本地链路地址: {hostname}"
                    if addr.is_multicast:
                        return False, f"不允许访问多播地址: {hostname}"
                    if addr.is_unspecified:
                        return False, f"不允许访问未指定地址: {hostname}"
                except (socket.gaierror, ValueError) as e:
                    return False, f"DNS 解析失败: {hostname} ({e})"
            
            return True, ""
            
        except Exception as e:
            return False, f"URL 解析错误: {e}"
    
    def _validate_selector(self, selector: str) -> tuple[bool, str]:
        """验证 CSS 选择器安全性 — 委托到 aibridge.utils.security"""
        return validate_css_selector(selector, allow_empty=True)
    
    def _validate_wait_until(self, wait_until: str) -> tuple[bool, str]:
        """验证 wait_until 参数"""
        allowed = ["load", "domcontentloaded", "networkidle"]
        if wait_until not in allowed:
            return False, f"无效的 wait_until 值: {wait_until}，允许值: {allowed}"
        return True, ""
    
    async def handle_navigate(self, args: dict) -> dict:
        """处理导航请求"""
        # 空指针保护
        if error := await self._check_initialized():
            return error
        
        url = args.get("url")
        wait_until = args.get("wait_until", "domcontentloaded")
        
        # URL 验证
        valid, err = await self._validate_url(url)
        if not valid:
            return {"success": False, "error": err}
        
        # wait_until 验证
        valid, err = self._validate_wait_until(wait_until)
        if not valid:
            return {"success": False, "error": err}
        
        result = await self.adapter.execute(
            "goto",
            target={"url": url},
            options={"wait_until": wait_until}
        )
        
        # 获取页面标题
        title_result = await self.adapter.execute(
            "read",
            target={"css": "title"}
        )
        
        return {
            "success": result.get("success"),
            "url": url,
            "title": title_result.get("data") if title_result.get("success") else None,
            "summary": f"成功导航到 {url}"
        }
    
    async def handle_click(self, args: dict) -> dict:
        """处理点击请求"""
        # 空指针保护
        if error := await self._check_initialized():
            return error
        
        selector = args.get("selector")
        text = args.get("text")
        
        # 选择器验证
        valid, err = self._validate_selector(selector)
        if not valid:
            return {"success": False, "error": err}
        force = args.get("force", False)
        
        target = {}
        if selector:
            target["css"] = selector
        elif text:
            target["text"] = text
        
        result = await self.adapter.execute(
            "click",
            target=target,
            options={"force": force}
        )
        
        return {
            "success": result.get("success"),
            "action": "click",
            "target": target,
            "summary": f"点击元素: {target}"
        }
    
    async def handle_type(self, args: dict) -> dict:
        """处理输入请求"""
        # 空指针保护
        if error := await self._check_initialized():
            return error
        
        selector = args.get("selector")
        text = args.get("text")
        force = args.get("force", False)
        
        # 选择器验证
        valid, err = self._validate_selector(selector)
        if not valid:
            return {"success": False, "error": err}
        
        # 文本验证
        if text is not None and not isinstance(text, str):
            return {"success": False, "error": "输入文本必须是字符串"}
        
        result = await self.adapter.execute(
            "type",
            target={"css": selector},
            value=text,
            options={"force": bool(force)}
        )
        
        return {
            "success": result.get("success"),
            "action": "type",
            "summary": f"在 {selector} 输入文本"
        }
    
    async def handle_extract(self, args: dict) -> dict:
        """处理数据提取请求"""
        # 空指针保护
        if error := await self._check_initialized():
            return error
        
        selector = args.get("selector")
        fields = args.get("fields", {})
        multiple = args.get("multiple", False)
        
        # 选择器验证
        valid, err = self._validate_selector(selector)
        if not valid:
            return {"success": False, "error": err}
        
        # fields 验证
        if fields is not None and not isinstance(fields, dict):
            return {"success": False, "error": "fields 必须是字典"}
        
        result = await self.adapter.execute(
            "extract",
            target={"css": selector},
            value=fields,
            options={"multiple": bool(multiple)}
        )
        
        return {
            "success": result.get("success"),
            "action": "extract",
            "data": result.get("data"),
            "summary": result.get("summary", f"从 {selector} 提取数据")
        }
    
    async def handle_screenshot(self, args: dict) -> dict:
        """处理截图请求"""
        if error := await self._check_initialized():
            return error
        
        selector = args.get("selector")
        full_page = args.get("full_page", False)
        
        if selector:
            result = await self.adapter.execute(
                "screenshot",
                target={"css": selector},
                options={"full_page": False}
            )
        else:
            result = await self.adapter.execute(
                "screenshot",
                options={"full_page": full_page}
            )
        
        screenshot_b64 = result.get("screenshot") or result.get("data", {}).get("screenshot")
        
        return {
            "success": result.get("success"),
            "screenshot_base64": screenshot_b64,
            "summary": "截图完成"
        }
    
    async def handle_execute_intent(self, args: dict) -> dict:
        """处理意图执行请求（第2层：意图识别）"""
        if error := await self._check_initialized():
            return error
        
        intent = args.get("intent")
        context = args.get("context", {})
        
        result = await self.intent_engine.execute(intent, context)
        
        return {
            "success": result.get("success"),
            "intent": intent,
            "actions_executed": result.get("actions", []),
            "data": result.get("data"),
            "summary": result.get("summary", f"执行意图: {intent}")
        }
    
    async def handle_execute_task(self, args: dict) -> dict:
        """处理复杂任务请求（第3层：O-R-A循环）"""
        if error := await self._check_initialized():
            return error
        
        goal = args.get("goal")
        max_steps = args.get("max_steps", 10)
        callback_url = args.get("callback_url")
        
        result = await self.orchestrator.execute_task(
            goal=goal,
            max_steps=max_steps,
            callback_url=callback_url
        )
        
        return {
            "success": result.get("success"),
            "goal": goal,
            "steps_executed": result.get("steps", []),
            "data": result.get("data"),
            "summary": result.get("summary", f"完成任务: {goal}")
        }
    
    # ============ MCP 协议处理 ============
    
    async def handle_tool_call(self, tool_name: str, arguments: dict) -> dict:
        """统一处理工具调用"""
        handlers = {
            "browser_navigate": self.handle_navigate,
            "browser_click": self.handle_click,
            "browser_type": self.handle_type,
            "browser_extract": self.handle_extract,
            "browser_screenshot": self.handle_screenshot,
            "browser_execute_intent": self.handle_execute_intent,
            "browser_execute_task": self.handle_execute_task,
        }
        
        handler = handlers.get(tool_name)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
        
        try:
            return await handler(arguments)
        except ValueError as e:
            # 参数验证错误，可以安全返回
            logger.warning(f"Validation error in {tool_name}: {e}")
            return {
                "success": False,
                "error": f"参数验证失败: {e}"
            }
        except TimeoutError as e:
            # 超时错误
            logger.warning(f"Timeout in {tool_name}: {e}")
            return {
                "success": False,
                "error": "操作超时，请重试"
            }
        except ConnectionError as e:
            # 连接错误
            logger.error(f"Connection error in {tool_name}: {e}")
            return {
                "success": False,
                "error": "浏览器连接失败，请检查连接状态"
            }
        except Exception as e:
            # 其他异常，记录详细日志但不返回内部信息
            logger.error(f"Unexpected error handling tool {tool_name}: {e}", exc_info=True)
            return {
                "success": False,
                "error": "内部错误，请稍后重试"
            }
    
    def get_tools(self) -> List[dict]:
        """获取所有可用工具定义"""
        return BROWSER_TOOLS


# ============ 简化版 MCP Server（不依赖mcp包） ============

class SimpleMCPServer:
    """
    简化版 MCP Server，不依赖 mcp 包
    可以直接通过 HTTP/WebSocket 暴露接口
    """
    
    def __init__(self):
        self.aibridge_server = AIBridgeMCPServer()
    
    async def start(self):
        """启动服务器"""
        await self.aibridge_server.initialize()
        logger.info("Simple MCP Server started")
    
    async def stop(self):
        """停止服务器"""
        await self.aibridge_server.shutdown()
        logger.info("Simple MCP Server stopped")
    
    async def call_tool(self, tool_name: str, arguments: dict) -> dict:
        """调用工具"""
        return await self.aibridge_server.handle_tool_call(tool_name, arguments)
    
    def list_tools(self) -> List[dict]:
        """列出所有工具"""
        return self.aibridge_server.get_tools()


# ============ 启动入口 ============

async def main():
    """MCP Server 启动入口"""
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建并启动服务器
    server = SimpleMCPServer()
    
    try:
        await server.start()
        
        # 打印可用工具
        print("\n" + "="*60)
        print("🚀 AI-Bridge MCP Server 已启动")
        print("="*60)
        print("\n可用工具:")
        for tool in server.list_tools():
            print(f"  • {tool['name']}: {tool['description'][:50]}...")
        
        print("\n按 Ctrl+C 停止服务器\n")
        
        # 保持运行 - 使用可中断的循环
        server._shutdown_event = asyncio.Event()
        try:
            await server._shutdown_event.wait()
        except asyncio.CancelledError:
            pass
            
    except KeyboardInterrupt:
        print("\n\n正在停止服务器...")
    finally:
        await server.stop()
        print("服务器已停止")


if __name__ == "__main__":
    asyncio.run(main())
