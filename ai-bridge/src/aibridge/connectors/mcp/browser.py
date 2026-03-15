"""
浏览器连接器

代理到成熟的浏览器自动化 MCP Server：
- Browser Use (推荐)
- Chrome DevTools MCP
- Playwright MCP

不再自研浏览器自动化实现，直接复用成熟方案。
"""

import asyncio
import logging
import shutil
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from ..base import (
    MCPConnector,
    ConnectorConfig,
    ConnectorStatus,
    ConnectorError,
    ToolInfo,
)
from aibridge.gateway.mcp_protocol import MCPProtocol, MCPTool

logger = logging.getLogger(__name__)


class BrowserBackend(Enum):
    """浏览器后端"""
    BROWSER_USE = "browser-use"           # Browser Use MCP (推荐)
    CHROME_DEVTOOLS = "chrome-devtools"   # Chrome DevTools MCP
    PLAYWRIGHT = "playwright"             # Playwright MCP
    AUTO = "auto"                         # 自动选择可用的后端


@dataclass
class BrowserConnectorConfig(ConnectorConfig):
    """浏览器连接器配置"""
    backend: BrowserBackend = BrowserBackend.AUTO
    headless: bool = True                 # 是否无头模式
    viewport_width: int = 1280            # 视口宽度
    viewport_height: int = 720            # 视口高度
    user_data_dir: Optional[str] = None   # 用户数据目录
    
    # Browser Use 特定配置
    browser_use_model: str = "gpt-4o"     # Browser Use 使用的 AI 模型
    
    # Chrome DevTools 特定配置
    chrome_path: Optional[str] = None     # Chrome 可执行文件路径
    remote_debugging_port: int = 9222     # 远程调试端口


# 后端启动配置
BACKEND_CONFIGS = {
    BrowserBackend.BROWSER_USE: {
        "command": "npx",
        "args": ["@anthropic-ai/browser-use-mcp"],
        "check_command": "npx",
        "check_args": ["--version"],
    },
    BrowserBackend.CHROME_DEVTOOLS: {
        "command": "npx",
        "args": ["@anthropic-ai/mcp-server-chrome-devtools"],
        "check_command": "npx",
        "check_args": ["--version"],
    },
    BrowserBackend.PLAYWRIGHT: {
        "command": "npx",
        "args": ["@anthropic-ai/mcp-server-playwright"],
        "check_command": "npx",
        "check_args": ["--version"],
    },
}


class BrowserConnector(MCPConnector):
    """
    浏览器连接器
    
    代理到成熟的浏览器自动化 MCP Server，提供统一的浏览器操作接口。
    
    支持的后端：
    - Browser Use: 最强大的浏览器自动化，支持 AI 驱动
    - Chrome DevTools: 官方 Chrome 调试协议
    - Playwright: Microsoft 的浏览器自动化框架
    
    使用示例：
    ```python
    # 自动选择后端
    config = BrowserConnectorConfig(name="browser", backend=BrowserBackend.AUTO)
    connector = BrowserConnector(config)
    
    async with connector:
        # 导航
        await connector.navigate("https://example.com")
        
        # 点击
        await connector.click("button.submit")
        
        # 输入
        await connector.type("input#search", "AI-Bridge")
        
        # 截图
        screenshot = await connector.screenshot()
    ```
    """
    
    def __init__(self, config: BrowserConnectorConfig):
        super().__init__(config)
        self._browser_config = config
        self._active_backend: Optional[BrowserBackend] = None
        self._mcp: Optional[MCPProtocol] = None  # MCP 协议通信
    
    @property
    def active_backend(self) -> Optional[BrowserBackend]:
        """当前使用的后端"""
        return self._active_backend
    
    @property
    def mcp_protocol(self) -> Optional[MCPProtocol]:
        """MCP 协议实例"""
        return self._mcp
    
    async def _detect_available_backend(self) -> Optional[BrowserBackend]:
        """检测可用的后端"""
        # 检测顺序：Browser Use > Chrome DevTools > Playwright
        backends_to_check = [
            BrowserBackend.BROWSER_USE,
            BrowserBackend.CHROME_DEVTOOLS,
            BrowserBackend.PLAYWRIGHT,
        ]
        
        for backend in backends_to_check:
            if await self._is_backend_available(backend):
                logger.info(f"Detected available backend: {backend.value}")
                return backend
        
        return None
    
    async def _is_backend_available(self, backend: BrowserBackend) -> bool:
        """检查后端是否可用"""
        config = BACKEND_CONFIGS.get(backend)
        if not config:
            return False
        
        # 检查命令是否存在
        command = config["check_command"]
        if not shutil.which(command):
            return False
        
        # 尝试执行检查命令
        try:
            proc = await asyncio.create_subprocess_exec(
                command,
                *config["check_args"],
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10.0)
            return proc.returncode == 0
        except Exception:
            return False
    
    async def _do_start(self) -> None:
        """启动浏览器后端"""
        # 确定使用的后端
        if self._browser_config.backend == BrowserBackend.AUTO:
            self._active_backend = await self._detect_available_backend()
            if not self._active_backend:
                raise ConnectorError(
                    "No available browser backend found. "
                    "Please install one of: browser-use, chrome-devtools-mcp, playwright-mcp"
                )
        else:
            self._active_backend = self._browser_config.backend
            if not await self._is_backend_available(self._active_backend):
                raise ConnectorError(f"Backend {self._active_backend.value} is not available")
        
        # 启动后端并初始化 MCP 协议
        await self._start_backend(self._active_backend)
    
    async def _start_backend(self, backend: BrowserBackend) -> None:
        """启动指定后端并完成 MCP 协议握手"""
        config = BACKEND_CONFIGS[backend]
        
        logger.info(f"Starting browser backend: {backend.value}")
        
        # 构建环境变量
        import os
        env = dict(os.environ)
        
        # 添加配置相关的环境变量
        if self._browser_config.headless:
            env["HEADLESS"] = "true"
        env["VIEWPORT_WIDTH"] = str(self._browser_config.viewport_width)
        env["VIEWPORT_HEIGHT"] = str(self._browser_config.viewport_height)
        
        if self._browser_config.user_data_dir:
            env["USER_DATA_DIR"] = self._browser_config.user_data_dir
        
        # 创建 MCP 协议实例
        self._mcp = MCPProtocol(timeout=self._config.timeout)
        
        # 启动 MCP Server 进程
        await self._mcp.start(
            command=config["command"],
            args=config["args"],
            env=env,
        )
        
        # MCP 协议握手
        try:
            server_info = await self._mcp.initialize()
            logger.info(f"MCP Server initialized: {server_info.name} v{server_info.version}")
            
            # 获取工具列表
            mcp_tools = await self._mcp.list_tools()
            self._tools = [
                ToolInfo(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in mcp_tools
            ]
            logger.info(f"Got {len(self._tools)} tools from MCP Server")
            
        except Exception as e:
            # 如果握手失败，回退到标准工具列表
            logger.warning(f"MCP handshake failed, using standard tools: {e}")
            self._tools = self._get_standard_tools()
    
    async def _do_stop(self) -> None:
        """停止浏览器后端"""
        if self._mcp:
            await self._mcp.shutdown()
            self._mcp = None
        self._active_backend = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 MCP 协议调用工具"""
        if not self._mcp:
            raise ConnectorError("MCP protocol not initialized")
        
        return await self._mcp.call_tool(name, params)
    
    def _get_standard_tools(self) -> List[ToolInfo]:
        """获取标准浏览器工具列表"""
        return [
            ToolInfo(
                name="navigate",
                description="Navigate to a URL",
                input_schema={
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "The URL to navigate to"}
                    },
                    "required": ["url"]
                }
            ),
            ToolInfo(
                name="click",
                description="Click on an element",
                input_schema={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector or text to click"}
                    },
                    "required": ["selector"]
                }
            ),
            ToolInfo(
                name="type",
                description="Type text into an element",
                input_schema={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector of the input"},
                        "text": {"type": "string", "description": "Text to type"}
                    },
                    "required": ["selector", "text"]
                }
            ),
            ToolInfo(
                name="screenshot",
                description="Take a screenshot of the page",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path to save screenshot (optional)"},
                        "full_page": {"type": "boolean", "description": "Capture full page (default: false)"}
                    }
                }
            ),
            ToolInfo(
                name="get_text",
                description="Get text content of an element",
                input_schema={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector of the element"}
                    },
                    "required": ["selector"]
                }
            ),
            ToolInfo(
                name="scroll",
                description="Scroll the page",
                input_schema={
                    "type": "object",
                    "properties": {
                        "direction": {"type": "string", "enum": ["up", "down", "left", "right"]},
                        "amount": {"type": "integer", "description": "Scroll amount in pixels"}
                    },
                    "required": ["direction"]
                }
            ),
            ToolInfo(
                name="wait",
                description="Wait for an element or time",
                input_schema={
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "CSS selector to wait for"},
                        "timeout": {"type": "integer", "description": "Timeout in milliseconds"}
                    }
                }
            ),
            ToolInfo(
                name="execute_script",
                description="Execute JavaScript in the page",
                input_schema={
                    "type": "object",
                    "properties": {
                        "script": {"type": "string", "description": "JavaScript code to execute"}
                    },
                    "required": ["script"]
                }
            ),
        ]
    
    # ============ 便捷方法 ============
    
    async def navigate(self, url: str) -> Any:
        """导航到 URL"""
        return await self.call_tool("navigate", {"url": url})
    
    async def click(self, selector: str) -> Any:
        """点击元素"""
        return await self.call_tool("click", {"selector": selector})
    
    async def type(self, selector: str, text: str) -> Any:
        """输入文本"""
        return await self.call_tool("type", {"selector": selector, "text": text})
    
    async def screenshot(self, path: Optional[str] = None, full_page: bool = False) -> Any:
        """截图"""
        params = {"full_page": full_page}
        if path:
            params["path"] = path
        return await self.call_tool("screenshot", params)
    
    async def get_text(self, selector: str) -> Any:
        """获取文本"""
        return await self.call_tool("get_text", {"selector": selector})
    
    async def scroll(self, direction: str = "down", amount: int = 500) -> Any:
        """滚动页面"""
        return await self.call_tool("scroll", {"direction": direction, "amount": amount})
    
    async def wait(self, selector: Optional[str] = None, timeout: int = 30000) -> Any:
        """等待元素或时间"""
        params = {"timeout": timeout}
        if selector:
            params["selector"] = selector
        return await self.call_tool("wait", params)
    
    async def execute_script(self, script: str) -> Any:
        """执行 JavaScript"""
        return await self.call_tool("execute_script", {"script": script})
