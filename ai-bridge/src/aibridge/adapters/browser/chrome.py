"""Chrome Adapter - Browser automation via Playwright

支持两种启动模式：
- launch（默认）: 自动启动浏览器，开箱即用
- connect: 连接已有浏览器（CDP模式）

核心能力：
- A11y 树快照 + uid 定位
- 多页面管理
- 完整的交互操作（hover/drag/press_key）
- 批量表单填写
"""

import base64
import json
import logging
import re
from collections import OrderedDict
from typing import Any, Dict, List, Optional
from aibridge.adapters.base import BaseAdapter, AdapterInfo, AdapterType
from aibridge.utils.security import validate_css_selector, DANGEROUS_CHARS, DANGEROUS_PATTERNS, VALID_SELECTOR_RE

logger = logging.getLogger(__name__)

# Lazy import to avoid dependency issues
playwright = None


def get_playwright():
    global playwright
    if playwright is None:
        from playwright.async_api import async_playwright
        playwright = async_playwright
    return playwright


class ChromeAdapter(BaseAdapter):
    """
    Chrome browser adapter using Playwright.
    
    支持两种启动模式：
    - launch（默认）: 自动启动浏览器，无需手动配置
    - connect: 连接已有浏览器（CDP模式）
    
    实现与 Chrome DevTools MCP 同等能力：
    - take_snapshot: A11y 树快照，带 uid 定位
    - 多页面管理: list_pages/select_page/new_page/close_page
    - 交互操作: hover/drag/press_key/fill_form
    
    使用方式：
        # 方式1: 自动启动（推荐，开箱即用）
        adapter = ChromeAdapter()  # 或 ChromeAdapter({"mode": "launch"})
        
        # 方式2: 连接已有浏览器（需手动启动 Chrome）
        adapter = ChromeAdapter({"mode": "connect", "cdp_url": "http://localhost:9222"})
    """
    @property
    def page(self):
        """获取当前 Playwright Page 对象"""
        return self._page

    @property
    def has_page(self) -> bool:
        """检查是否有活跃页面"""
        return self._page is not None

    def _escape_js_string(self, s: str) -> str:
        """转义 JavaScript 字符串，防止注入攻击"""
        if not s:
            return ""
        # 转义危险字符
        s = s.replace("\\", "\\\\")  # 先转义反斜杠
        s = s.replace("'", "\\'")
        s = s.replace('"', '\\"')
        s = s.replace("\n", "\\n")
        s = s.replace("\r", "\\r")
        s = s.replace("\x00", "")  # 移除 null 字节
        return s
    
    # 安全白名单：允许执行的预定义脚本
    SAFE_SCRIPTS = {
        "get_title": "document.title",
        "get_url": "window.location.href",
        "get_body_text": "document.body?.innerText || ''",
        "get_links_count": "document.querySelectorAll('a').length",
        "get_images_count": "document.querySelectorAll('img').length",
        "get_forms_count": "document.querySelectorAll('form').length",
        "get_scroll_height": "document.body?.scrollHeight || 0",
        "get_viewport_height": "window.innerHeight",
        "is_scrollable": "document.body?.scrollHeight > window.innerHeight",
    }
    
    # 快照缓存最大数量
    MAX_SNAPSHOT_CACHE = 1000
    
    def _validate_css_selector(self, selector: str) -> bool:
        """
        验证 CSS 选择器是否安全
        
        检查：
        - 长度限制（防止 DoS）
        - 危险字符和模式
        - 格式有效性
        
        委托到 aibridge.utils.security.validate_css_selector 共享实现。
        """
        valid, _ = validate_css_selector(selector, allow_empty=False)
        return valid

    
    info = AdapterInfo(
        id="chrome",
        name="Google Chrome",
        type=AdapterType.BROWSER,
        version="2.4.0",  # 添加extract action数据提取功能
        platforms=["windows", "macos", "linux"],
        actions=[
            # 原有能力
            "goto", "click", "type", "read", "screenshot",
            "list_elements", "wait", "scroll", "back", "forward",
            "reload", "execute", "focus",
            # 新增能力 - A11y 快照
            "take_snapshot",
            # 新增能力 - 多页面管理
            "list_pages", "select_page", "new_page", "close_page",
            # 新增能力 - 更多交互
            "hover", "drag", "press_key", "fill_form",
            # 新增能力 - 网络/控制台
            "get_url", "get_title",
        ],
        description="Chrome browser automation - 支持自动启动，开箱即用",
    )
    
    # 配置常量
    DEFAULT_SCROLL_DISTANCE = 500
    MAX_INTERACTIVE_ELEMENTS = 50
    MAX_TEXT_LENGTH = 100
    DEFAULT_TIMEOUT = 10000
    DEFAULT_BLANK_URL = "about:blank"  # 默认空白页地址
    UID_PREFIX = "e_"  # A11y 快照 uid 前缀
    
    # 启动模式
    MODE_LAUNCH = "launch"    # 自动启动浏览器（默认）
    MODE_CONNECT = "connect"  # 连接已有浏览器（CDP）
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # 启动模式：launch（默认）或 connect
        self.mode = self.config.get("mode", self.MODE_LAUNCH)
        # CDP 连接地址（仅 connect 模式使用）
        self.cdp_url = self.config.get("cdp_url", "http://localhost:9222")
        # launch 模式配置
        self.headless = self.config.get("headless", False)  # 默认有头模式，方便调试
        self.user_data_dir = self.config.get("user_data_dir", None)  # 用户数据目录，可选
        self.slow_mo = self.config.get("slow_mo", 0)  # 操作延迟，方便观察
        
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None
        # A11y 快照中的元素缓存，用于 uid 定位（LRU 淘汰策略）
        self._snapshot_elements: OrderedDict[str, Any] = OrderedDict()
        # 策略模式：action → handler 分发字典
        self._action_handlers: Dict[str, callable] = {
            "goto": self._handle_goto,
            "click": self._handle_click,
            "type": self._handle_type,
            "read": self._handle_read,
            "screenshot": self._handle_screenshot,
            "list_elements": self._handle_list_elements,
            "wait": self._handle_wait,
            "scroll": self._handle_scroll,
            "back": self._handle_back,
            "forward": self._handle_forward,
            "reload": self._handle_reload,
            "execute": self._handle_execute_script,
            "focus": self._handle_focus,
            "take_snapshot": self._handle_take_snapshot,
            "list_pages": self._handle_list_pages,
            "select_page": self._handle_select_page,
            "new_page": self._handle_new_page,
            "close_page": self._handle_close_page,
            "extract": self._handle_extract,
            "hover": self._handle_hover,
            "drag": self._handle_drag,
            "press_key": self._handle_press_key,
            "fill_form": self._handle_fill_form,
            "get_url": self._handle_get_url,
            "get_title": self._handle_get_title,
        }
    
    async def connect(self) -> bool:
        """Connect to Chrome - 支持 launch 和 connect 两种模式"""
        try:
            async_playwright = get_playwright()
            self._playwright = await async_playwright().start()
            
            if self.mode == self.MODE_CONNECT:
                # CDP 模式：连接已有浏览器
                self._browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
                # 获取已有页面
                contexts = self._browser.contexts
                if contexts and contexts[0].pages:
                    self._context = contexts[0]
                    self._page = contexts[0].pages[0]
                else:
                    self._context = await self._browser.new_context()
                    self._page = await self._context.new_page()
            else:
                # Launch 模式：自动启动浏览器（默认）
                launch_options = {
                    "headless": self.headless,
                    "slow_mo": self.slow_mo,
                }
                
                # 如果指定了用户数据目录，使用 launch_persistent_context
                if self.user_data_dir:
                    self._context = await self._playwright.chromium.launch_persistent_context(
                        self.user_data_dir,
                        **launch_options
                    )
                    self._browser = None  # persistent context 没有 browser 对象
                    self._page = self._context.pages[0] if self._context.pages else await self._context.new_page()
                else:
                    # 普通启动
                    self._browser = await self._playwright.chromium.launch(**launch_options)
                    self._context = await self._browser.new_context()
                    self._page = await self._context.new_page()
            
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            logger.error(f"连接 Chrome 失败: {e}")
            await self._cleanup_resources()
            raise ConnectionError(f"Failed to connect/launch Chrome: {e}") from e

    async def _cleanup_resources(self):
        """清理所有已分配的资源（容错清理，任一资源清理失败不影响其他资源，且仅在成功关闭后置None）"""
        cleanup_order = [
            ('_page', 'close'),
            ('_context', 'close'),
            ('_browser', 'close'),
            ('_playwright', 'stop'),
        ]
        cleanup_errors = []

        for resource_name, close_method in cleanup_order:
            resource = getattr(self, resource_name, None)
            if resource is not None:
                try:
                    close_func = getattr(resource, close_method)
                    await close_func()
                    # 仅在成功关闭后清除引用
                    setattr(self, resource_name, None)
                except Exception as exc:
                    cleanup_errors.append(f"{resource_name}: {exc}")
                    # 保留引用以便后续诊断，不置 None

        if cleanup_errors:
            logger.warning(f"资源清理时部分失败: {'; '.join(cleanup_errors)}")

        self._snapshot_elements = OrderedDict()
    
    async def disconnect(self) -> bool:
        """断开与 Chrome 的连接，清理所有资源"""
        try:
            # 先关闭 context（无论哪种模式都需要）
            if self._context:
                try:
                    await self._context.close()
                except Exception as e:
                    logger.debug(f"关闭 context 时出错（可能已关闭）: {e}")
            
            # 再关闭 browser（非 persistent context 模式）
            if self._browser:
                try:
                    await self._browser.close()
                except Exception as e:
                    logger.debug(f"关闭 browser 时出错: {e}")
            
            # 最后停止 playwright
            if self._playwright:
                await self._playwright.stop()
            
            # 清理引用
            self._context = None
            self._browser = None
            self._page = None
            self._playwright = None
            self._snapshot_elements = OrderedDict()
            self._connected = False
            return True
        except Exception as e:
            logger.error(f"disconnect 过程中发生错误: {e}")
            # 即使出错也要强制清理引用
            self._context = None
            self._browser = None
            self._page = None
            self._playwright = None
            self._snapshot_elements = OrderedDict()
            self._connected = False
            return False
    
    async def is_available(self) -> bool:
        """检查 Chrome/Playwright 是否可用"""
        pw = None
        browser = None
        try:
            async_playwright = get_playwright()
            pw = await async_playwright().start()
            
            if self.mode == self.MODE_CONNECT:
                # CDP 模式：检查是否能连接
                browser = await pw.chromium.connect_over_cdp(self.cdp_url)
            else:
                # Launch 模式：检查是否能启动
                browser = await pw.chromium.launch(headless=True)
            
            await browser.close()
            await pw.stop()
            return True
        except Exception:
            # 清理资源
            if browser:
                try:
                    await browser.close()
                except Exception:
                    pass
            if pw:
                try:
                    await pw.stop()
                except Exception:
                    pass
            return False
    
    async def execute(
        self,
        action: str,
        target: Optional[Dict[str, Any]] = None,
        value: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a browser action."""
        # 连接状态检查
        if not self._connected or not self._page:
            return {"success": False, "error": "未连接到 Chrome，请先调用 connect()"}
        
        # 转换 Target 对象为 dict（如果传入的是 Target 对象）
        if target is not None and hasattr(target, 'to_dict'):
            target = target.to_dict()
        
        options = options or {}
        timeout = options.get("timeout", self.DEFAULT_TIMEOUT)
        
        try:
            handler = self._action_handlers.get(action)
            if not handler:
                return {"success": False, "error": f"Unknown action: {action}"}
            return await handler(target, value, options, timeout)
        except Exception as e:
            logger.error(f"Action '{action}' failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
    
    # ============ Action Handlers ============
    
    async def _handle_goto(self, target, value, options, timeout) -> Dict[str, Any]:
        url = value if isinstance(value, str) else target.get("url") if target else None
        if not url:
            return {"success": False, "error": "goto 操作需要提供 url"}
        await self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")
        return {"success": True, "data": {"url": self._page.url}}
    
    async def _handle_click(self, target, value, options, timeout) -> Dict[str, Any]:
        force = options.get("force", False)
        element = await self._find_element_with_fallback(target, timeout, force)
        if not element:
            return {"success": False, "error": f"无法找到可点击的元素: {target}"}
        try:
            await element.click(timeout=timeout)
        except Exception as e:
            if force and target and target.get("css"):
                selector = target["css"]
                if not self._validate_css_selector(selector):
                    raise ValueError(f"Invalid CSS selector: {selector}")
                await self._page.evaluate(
                    """(sel) => {
                        const el = document.querySelector(sel);
                        if (el) el.click();
                    }""",
                    selector
                )
            else:
                raise
        return {"success": True}
    
    async def _handle_type(self, target, value, options, timeout) -> Dict[str, Any]:
        text = value or ""
        force = options.get("force", False)
        element = await self._find_element_with_fallback(target, timeout, force)
        if not element:
            return {"success": False, "error": f"无法找到可输入的元素: {target}"}
        try:
            await element.fill(text, timeout=timeout)
        except Exception as e:
            if force and target and target.get("css"):
                selector = target["css"]
                if not self._validate_css_selector(selector):
                    raise ValueError(f"Invalid CSS selector: {selector}")
                await self._page.evaluate(
                    """(sel, val) => {
                        const el = document.querySelector(sel);
                        if (el) el.value = val;
                    }""",
                    selector, text
                )
            else:
                raise
        return {"success": True}
    
    async def _handle_read(self, target, value, options, timeout) -> Dict[str, Any]:
        force = options.get("force", False)
        element = await self._find_element_with_fallback(target, timeout, force)
        if not element:
            if target and target.get("css") == "title":
                title = await self._page.title()
                return {"success": True, "data": title}
            return {"success": False, "error": f"无法找到可读取的元素: {target}"}
        try:
            text = await element.inner_text()
        except Exception as e:
            if force and target and target.get("css"):
                selector = target["css"]
                if not self._validate_css_selector(selector):
                    raise ValueError(f"Invalid CSS selector: {selector}")
                text = await self._page.evaluate(
                    """(sel) => {
                        const el = document.querySelector(sel);
                        return el?.innerText || el?.value || '';
                    }""",
                    selector
                )
            else:
                raise
        return {"success": True, "data": text}
    
    async def _handle_screenshot(self, target, value, options, timeout) -> Dict[str, Any]:
        import os
        path = options.get("path")
        full_page = options.get("full_page", False)
        if path:
            dir_path = os.path.dirname(path)
            if dir_path and not os.path.exists(dir_path):
                return {"success": False, "error": f"目录不存在: {dir_path}"}
            await self._page.screenshot(path=path, full_page=full_page)
            return {"success": True, "path": path}
        else:
            screenshot = await self._page.screenshot(full_page=full_page)
            b64 = base64.b64encode(screenshot).decode()
            return {"success": True, "screenshot": b64}
    
    async def _handle_list_elements(self, target, value, options, timeout) -> Dict[str, Any]:
        elements = await self._get_interactive_elements()
        return {"success": True, "elements": elements}
    
    async def _handle_wait(self, target, value, options, timeout) -> Dict[str, Any]:
        selector = self._build_selector(target)
        await self._page.wait_for_selector(selector, timeout=timeout)
        return {"success": True}
    
    async def _handle_scroll(self, target, value, options, timeout) -> Dict[str, Any]:
        direction = value or "down"
        distance = self.DEFAULT_SCROLL_DISTANCE
        if options and "distance" in options:
            try:
                distance = int(options["distance"])
            except (ValueError, TypeError):
                return {"success": False, "error": "distance must be an integer"}
        if direction == "down":
            await self._page.mouse.wheel(0, distance)
        elif direction == "up":
            await self._page.mouse.wheel(0, -distance)
        return {"success": True}
    
    async def _handle_back(self, target, value, options, timeout) -> Dict[str, Any]:
        await self._page.go_back(timeout=timeout)
        return {"success": True}
    
    async def _handle_forward(self, target, value, options, timeout) -> Dict[str, Any]:
        await self._page.go_forward(timeout=timeout)
        return {"success": True}
    
    async def _handle_reload(self, target, value, options, timeout) -> Dict[str, Any]:
        await self._page.reload(timeout=timeout)
        return {"success": True}
    
    async def _handle_execute_script(self, target, value, options, timeout) -> Dict[str, Any]:
        script_name = value or ""
        if not script_name:
            return {
                "success": False,
                "error": "execute 操作需要提供脚本名称",
                "available_scripts": list(self.SAFE_SCRIPTS.keys())
            }
        if script_name not in self.SAFE_SCRIPTS:
            return {
                "success": False,
                "error": f"不允许执行任意 JavaScript。可用脚本: {list(self.SAFE_SCRIPTS.keys())}",
                "available_scripts": list(self.SAFE_SCRIPTS.keys())
            }
        try:
            safe_script = self.SAFE_SCRIPTS[script_name]
            result = await self._page.evaluate(safe_script)
            if result is None:
                return {"success": True, "data": None, "script": script_name}
            try:
                json.dumps(result)
                return {"success": True, "data": result, "script": script_name}
            except (TypeError, ValueError):
                return {"success": True, "data": str(result), "script": script_name}
        except Exception as e:
            logger.error(f"JavaScript 执行失败: {e}")
            return {"success": False, "error": f"JavaScript 执行失败: {str(e)}"}
    
    async def _handle_focus(self, target, value, options, timeout) -> Dict[str, Any]:
        await self._page.bring_to_front()
        return {"success": True}
    
    async def _handle_take_snapshot(self, target, value, options, timeout) -> Dict[str, Any]:
        result = await self._take_accessibility_snapshot()
        if result.get("success"):
            return {
                "success": True,
                "snapshot": result.get("snapshot", ""),
                "snapshot_type": result.get("snapshot_type", "unknown"),
                "elements": result.get("elements", []),
                "element_count": result.get("element_count", 0)
            }
        else:
            return {"success": False, "error": result.get("error", "快照失败")}
    
    async def _handle_list_pages(self, target, value, options, timeout) -> Dict[str, Any]:
        pages = await self._list_pages()
        return {"success": True, "pages": pages}
    
    async def _handle_select_page(self, target, value, options, timeout) -> Dict[str, Any]:
        page_id = value if isinstance(value, int) else target.get("page_id") if target else 0
        await self._select_page(page_id)
        return {"success": True, "selected": page_id}
    
    async def _handle_new_page(self, target, value, options, timeout) -> Dict[str, Any]:
        url = value if isinstance(value, str) else target.get("url") if target else self.DEFAULT_BLANK_URL
        page_info = await self._new_page(url)
        return {"success": True, "page": page_info}
    
    async def _handle_close_page(self, target, value, options, timeout) -> Dict[str, Any]:
        page_id = value if isinstance(value, int) else target.get("page_id") if target else None
        await self._close_page(page_id)
        return {"success": True}
    
    async def _handle_extract(self, target, value, options, timeout) -> Dict[str, Any]:
        return await self._extract_data(target, value, options, timeout)
    
    async def _handle_hover(self, target, value, options, timeout) -> Dict[str, Any]:
        selector = self._build_selector(target)
        await self._page.wait_for_selector(selector, state="visible", timeout=timeout)
        await self._page.hover(selector, timeout=timeout)
        return {"success": True}
    
    async def _handle_drag(self, target, value, options, timeout) -> Dict[str, Any]:
        if not target:
            return {"success": False, "error": "drag 操作需要 target 参数"}
        from_sel = target.get("from")
        to_sel = target.get("to")
        if not from_sel or not to_sel:
            return {"success": False, "error": "drag 操作需要 from 和 to 参数"}
        await self._page.wait_for_selector(from_sel, state="visible", timeout=timeout)
        await self._page.wait_for_selector(to_sel, state="visible", timeout=timeout)
        await self._page.drag_and_drop(from_sel, to_sel, timeout=timeout)
        return {"success": True}
    
    async def _handle_press_key(self, target, value, options, timeout) -> Dict[str, Any]:
        key = value if isinstance(value, str) else target.get("key") if target else None
        if not key:
            return {"success": False, "error": "press_key 操作需要提供 key"}
        await self._page.keyboard.press(key)
        return {"success": True}
    
    async def _handle_fill_form(self, target, value, options, timeout) -> Dict[str, Any]:
        form_data = value if isinstance(value, list) else []
        filled_count = 0
        for item in form_data:
            if not isinstance(item, dict):
                continue
            sel = item.get("selector")
            val = item.get("value", "")
            if sel and isinstance(val, str):
                await self._page.wait_for_selector(sel, state="visible", timeout=timeout)
                await self._page.fill(sel, val, timeout=timeout)
                filled_count += 1
        return {"success": True, "filled": filled_count}
    
    async def _handle_get_url(self, target, value, options, timeout) -> Dict[str, Any]:
        return {"success": True, "url": self._page.url}
    
    async def _handle_get_title(self, target, value, options, timeout) -> Dict[str, Any]:
        title = await self._page.title()
        return {"success": True, "title": title}
    
    def _build_selector(self, target) -> str:
        """构建 Playwright 选择器，支持 uid/css/xpath/name/role 多种方式"""
        # 转换 Target 对象为 dict
        if target is not None and hasattr(target, 'to_dict'):
            target = target.to_dict()
        
        if not target:
            return "*"
        
        # 支持 uid 定位（通过 take_snapshot 获取的 uid）
        if target.get("uid"):
            uid = target["uid"]
            element_info = self._snapshot_elements.get(uid)
            if element_info:
                role = element_info.get("role")
                name = element_info.get("name")
                # 通过 role + name 组合定位
                if role and name:
                    # 转义引号，防止选择器注入
                    escaped_name = name.replace('"', '\\"')
                    return f'role={role}[name="{escaped_name}"]'
                elif name:
                    escaped_name = name.replace('"', '\\"')
                    return f'text="{escaped_name}"'
                elif role:
                    return f'role={role}'
            raise ValueError(f"未知的 uid: {uid}，请先调用 take_snapshot 获取最新快照")
        
        if target.get("css"):
            return target["css"]
        if target.get("xpath"):
            return f"xpath={target['xpath']}"
        if target.get("name"):
            # 转义引号，防止注入
            name = target['name'].replace('"', '\\"')
            return f'text="{name}"'
        if target.get("role"):
            return f"role={target['role']}"
        
        return "*"
    
    async def _get_interactive_elements(self) -> List[Dict[str, Any]]:
        """Get list of interactive elements on the page."""
        elements = await self._page.evaluate("""
            () => {
                const selectors = 'button, a, input, select, textarea, [role="button"], [onclick]';
                const elements = document.querySelectorAll(selectors);
                return Array.from(elements).slice(0, 50).map(el => ({
                    tag: el.tagName.toLowerCase(),
                    text: el.innerText?.slice(0, 100) || '',
                    id: el.id || null,
                    name: el.name || null,
                    type: el.type || null,
                    role: el.getAttribute('role') || null,
                    href: el.href || null,
                }));
            }
        """)
        return elements
    
    # ==================== 新增辅助方法 ====================
    
    async def _take_accessibility_snapshot(self, interesting_only: bool = False) -> Dict[str, Any]:
        """
        获取 A11y 树快照，返回带 uid 的可访问性树。
        如果 A11y API 返回空，则使用 DOM 快照作为 fallback。
        
        Args:
            interesting_only: 是否只返回有交互意义的节点（默认 False，返回所有节点）
        
        Returns:
            Dict: 包含快照数据的字典，格式统一
        """
        # 确保返回字典类型
        try:
            # 等待页面加载完成
            try:
                await self._page.wait_for_load_state("domcontentloaded", timeout=5000)
            except Exception as e:
                logger.debug(f"页面加载等待超时，继续执行: {e}")
            
            # 获取 A11y 树
            snapshot = None
            try:
                snapshot = await self._page.accessibility.snapshot(interesting_only=interesting_only)
            except Exception as e:
                logger.debug(f"A11y snapshot 失败: {e}")
            
            # 如果 A11y 快照为空，使用 DOM 快照作为 fallback
            if not snapshot:
                logger.info("A11y 快照为空，使用 DOM fallback")
                dom_result = await self._take_dom_snapshot()
                # 确保返回的是字典
                if isinstance(dom_result, dict):
                    return dom_result
                else:
                    return {
                        "success": False,
                        "snapshot_type": "error",
                        "error": "DOM fallback 返回类型错误",
                        "elements": [],
                        "element_count": 0
                    }
            
            # 为每个元素分配 uid 并缓存（带大小限制）
            self._snapshot_elements = OrderedDict()
            uid_counter = [0]
            
            def assign_uids(node: dict, prefix: str = "") -> dict:
                """递归为节点分配 uid，带缓存大小限制"""
                if not node or not isinstance(node, dict):
                    return node
                
                # 检查缓存大小限制，使用 LRU 淘汰最旧条目
                if len(self._snapshot_elements) >= self.MAX_SNAPSHOT_CACHE:
                    # 淘汰最旧的 20% 条目
                    evict_count = max(1, self.MAX_SNAPSHOT_CACHE // 5)
                    for _ in range(evict_count):
                        self._snapshot_elements.popitem(last=False)
                
                uid = f"{prefix}{uid_counter[0]}"
                uid_counter[0] += 1
                node["uid"] = uid
                
                # 缓存元素信息（LRU: 最近访问的移到末尾）
                self._snapshot_elements[uid] = {
                    "role": node.get("role"),
                    "name": node.get("name"),
                    "value": node.get("value"),
                }
                self._snapshot_elements.move_to_end(uid)
                
                if "children" in node and isinstance(node["children"], list):
                    for child in node["children"]:
                        assign_uids(child, prefix)
                
                return node
            
            assign_uids(snapshot, self.UID_PREFIX)
            
            formatted = self._format_snapshot(snapshot)
            # 确保 formatted 是字符串
            if not isinstance(formatted, str):
                formatted = str(formatted)
            
            return {
                "success": True,
                "snapshot_type": "accessibility",
                "snapshot": formatted,
                "elements": list(self._snapshot_elements.values()),
                "element_count": len(self._snapshot_elements)
            }
            
        except Exception as e:
            logger.error(f"A11y 快照异常: {e}")
            return {
                "success": False,
                "snapshot_type": "error",
                "error": str(e),
                "elements": [],
                "element_count": 0
            }
    
    async def _take_dom_snapshot(self) -> Dict[str, Any]:
        """
        DOM 快照作为 A11y 快照的 fallback
        提取页面中所有可交互元素
        """
        try:
            elements = await self._page.evaluate("""
                () => {
                    const interactiveSelectors = [
                        'button', 'a', 'input', 'select', 'textarea',
                        '[role="button"]', '[role="link"]', '[role="input"]',
                        '[onclick]', '[tabindex]:not([tabindex="-1"])'
                    ];
                    
                    const elements = [];
                    interactiveSelectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach((el, idx) => {
                            const rect = el.getBoundingClientRect();
                            if (rect.width > 0 && rect.height > 0) {  // 可见元素
                                elements.push({
                                    tag: el.tagName.toLowerCase(),
                                    role: el.getAttribute('role') || el.tagName.toLowerCase(),
                                    name: el.getAttribute('aria-label') || 
                                          el.getAttribute('placeholder') ||
                                          el.textContent?.slice(0, 100) ||
                                          el.value ||
                                          el.name ||
                                          el.id ||
                                          `element_${idx}`,
                                    id: el.id || null,
                                    class: el.className || null,
                                    type: el.type || null,
                                    href: el.href || null,
                                    visible: true
                                });
                            }
                        });
                    });
                    
                    // 去重
                    return elements.filter((el, idx, self) => 
                        idx === self.findIndex(e => 
                            e.name === el.name && e.tag === el.tag
                        )
                    ).slice(0, 100);  // 限制数量
                }
            """)
            
            # 为 DOM 元素分配 uid
            self._snapshot_elements = OrderedDict()
            for i, el in enumerate(elements):
                uid = f"{self.UID_PREFIX}dom_{i}"
                el["uid"] = uid
                self._snapshot_elements[uid] = el
            
            # 格式化输出
            lines = ["DOM Snapshot (fallback):"]
            for el in elements:
                line = f"  [{el['tag']}] {el['name'][:50]}"
                if el['id']:
                    line += f" (id={el['id']})"
                lines.append(line)
            
            return {
                "success": True,
                "snapshot_type": "dom_fallback",
                "snapshot": "\n".join(lines),
                "elements": elements,
                "element_count": len(elements)
            }
            
        except Exception as e:
            logger.error(f"DOM 快照失败: {e}")
            return {
                "success": False,
                "snapshot_type": "error",
                "error": str(e),
                "elements": [],
                "element_count": 0
            }
    
    def _format_snapshot(self, node: dict, indent: int = 0) -> str:
        """格式化 A11y 树为文本表示"""
        if not node or not isinstance(node, dict):
            return ""
        
        lines = []
        prefix = "  " * indent
        
        # 构建节点描述
        uid = node.get("uid", "")
        role = node.get("role", "")
        name = node.get("name", "")
        value = node.get("value", "")
        
        desc_parts = [f"uid={uid}", role]
        if name:
            desc_parts.append(f'"{name}"')
        if value:
            desc_parts.append(f'value="{value}"')
        
        lines.append(f"{prefix}{' '.join(desc_parts)}")
        
        # 递归处理子节点
        children = node.get("children", [])
        if isinstance(children, list):
            for child in children:
                child_lines = self._format_snapshot(child, indent + 1)
                if child_lines:
                    lines.append(child_lines)
        
        return "\n".join(filter(None, lines))
    
    async def _list_pages(self) -> List[Dict[str, Any]]:
        """列出所有页面"""
        pages = []
        # 支持 browser 模式和 persistent context 模式
        if self._browser:
            contexts = self._browser.contexts
        elif self._context:
            contexts = [self._context]
        else:
            return pages
        
        for ctx in contexts:
            for i, page in enumerate(ctx.pages):
                pages.append({
                    "id": len(pages),
                    "url": page.url,
                    "title": await page.title(),
                    "selected": page == self._page
                })
        return pages
    
    async def _select_page(self, page_id: int) -> bool:
        """选择指定页面，返回是否成功"""
        all_pages = []
        if self._browser:
            for ctx in self._browser.contexts:
                all_pages.extend(ctx.pages)
        elif self._context:
            all_pages = list(self._context.pages)
        
        if not (0 <= page_id < len(all_pages)):
            raise ValueError(f"page_id {page_id} 超出范围，当前共 {len(all_pages)} 个页面")
        
        self._page = all_pages[page_id]
        await self._page.bring_to_front()
        return True
    
    async def _new_page(self, url: str = "") -> Dict[str, Any]:
        """新建页面"""
        if not url:
            url = self.DEFAULT_BLANK_URL
        
        # 获取 context
        ctx = None
        if self._context:
            ctx = self._context
        elif self._browser and self._browser.contexts:
            ctx = self._browser.contexts[0]
        elif self._browser:
            ctx = await self._browser.new_context()
        else:
            raise RuntimeError("浏览器未连接，请先调用 connect()")
        
        page = await ctx.new_page()
        if url != self.DEFAULT_BLANK_URL:
            await page.goto(url, wait_until="domcontentloaded")
        self._page = page
        
        return {
            "url": page.url,
            "title": await page.title()
        }
    
    async def _close_page(self, page_id: Optional[int] = None) -> None:
        """关闭页面
        
        Args:
            page_id: 要关闭的页面ID，None 表示关闭当前页面
            
        Raises:
            ValueError: page_id 超出有效范围或没有可用页面
        """
        all_pages = []
        if self._browser:
            for ctx in self._browser.contexts:
                all_pages.extend(ctx.pages)
        elif self._context:
            all_pages = list(self._context.pages)
        
        # 确定要关闭的页面
        if page_id is not None:
            if not all_pages:
                raise ValueError("没有可用的页面")
            if not (0 <= page_id < len(all_pages)):
                raise ValueError(f"page_id {page_id} 超出范围，有效范围: 0-{len(all_pages) - 1}")
            target_page = all_pages[page_id]
        else:
            target_page = self._page
        
        # 不要关闭最后一个页面
        if len(all_pages) <= 1:
            logger.warning("无法关闭最后一个页面")
            return
        
        await target_page.close()
        # 如果关闭的是当前页面，切换到第一个页面
        if target_page == self._page:
            remaining_pages = [p for p in all_pages if p != target_page]
            if remaining_pages:
                self._page = remaining_pages[0]
    
    def get_element_by_uid(self, uid: str) -> Optional[Dict[str, Any]]:
        """通过 uid 获取缓存的元素信息"""
        return self._snapshot_elements.get(uid)
    
    async def _find_element_with_fallback(
        self, 
        target, 
        timeout: int = 10000,
        force: bool = False
    ) -> Optional[Any]:
        """
        多策略元素定位，带 fallback 机制
        
        Args:
            target: 定位目标 (dict 或 Target 对象)
            timeout: 超时时间
            force: 是否强制操作隐藏元素
        
        尝试顺序：
        1. CSS selector
        2. Playwright role locator
        3. Text content
        4. Placeholder attribute
        5. XPath
        """
        # 转换 Target 对象为 dict
        if target is not None and hasattr(target, 'to_dict'):
            target = target.to_dict()
        
        if not target:
            return None
        
        strategies = []
        
        # 策略1: CSS selector
        if target.get("css"):
            css = target["css"]
            strategies.append(lambda: self._page.locator(css))
        
        # 策略2: Role + name ( accessibility )
        if target.get("role"):
            role = target["role"]
            name = target.get("name")
            strategies.append(lambda r=role, n=name: 
                self._page.get_by_role(r, name=n) if n else self._page.get_by_role(r))
        
        # 策略3: Text content
        if target.get("name"):
            text = target["name"]
            strategies.append(lambda t=text: self._page.get_by_text(t, exact=False))
        
        # 策略4: Placeholder (for input elements)
        if target.get("placeholder"):
            ph = target["placeholder"]
            strategies.append(lambda p=ph: self._page.get_by_placeholder(p))
        
        # 策略5: XPath
        if target.get("xpath"):
            xpath = target["xpath"]
            strategies.append(lambda x=xpath: self._page.locator(f"xpath={x}"))
        
        # 策略6: UID (from snapshot)
        if target.get("uid"):
            uid = target["uid"]
            element_info = self._snapshot_elements.get(uid)
            if element_info:
                role = element_info.get("role")
                name = element_info.get("name")
                if role and name:
                    strategies.append(lambda r=role, n=name: 
                        self._page.get_by_role(r, name=n))
        
        # 尝试每种策略
        last_error = None
        for i, strategy in enumerate(strategies):
            try:
                locator = strategy()
                if locator:
                    # 根据 force 参数选择等待状态
                    wait_state = "attached" if force else "visible"
                    await locator.wait_for(state=wait_state, timeout=timeout)
                    # 确认元素存在
                    count = await locator.count()
                    if count > 0:
                        logger.debug(f"策略 {i+1} 成功定位元素: {target}")
                        return locator
            except Exception as e:
                last_error = e
                continue
        
        # 所有策略都失败，尝试通用的 query_selector 作为最后手段
        try:
            if target.get("css"):
                selector = target["css"]
                await self._page.wait_for_selector(selector, state="attached", timeout=timeout)
                element = await self._page.query_selector(selector)
                if element:
                    return self._page.locator(selector)
        except Exception as e:
            last_error = e
        
        # 如果 force=True，尝试通过 JS 直接获取元素
        if force and target.get("css"):
            try:
                selector = target["css"]
                # 安全检查：转义单引号，防止 JS 注入
                safe_selector = selector.replace("'", "\\'")
                # 使用安全的 JS 函数检查元素是否存在
                exists = await self._page.evaluate(
                    """(selector) => !!document.querySelector(selector)""",
                    safe_selector
                )
                if exists:
                    return self._page.locator(selector)
            except Exception as e:
                logger.debug(f"JS 检查元素失败: {e}")
        
        logger.warning(f"所有定位策略都失败: {target}, 最后错误: {last_error}")
        return None
    
    async def _extract_data(self, target, value, options, timeout):
        """
        从页面提取结构化数据
        
        Args:
            target: 提取目标区域的选择器
            value: 提取规则/schema
            options: 选项
            timeout: 超时
        
        Returns:
            Dict: 包含结构化数据的统一返回格式
        """
        try:
            # 获取提取配置
            selector = target.get("css") if target else None
            schema = value if isinstance(value, dict) else {}
            multiple = options.get("multiple", False)  # 是否提取多个
            
            if not selector:
                return {"success": False, "error": "extract 需要提供 css selector"}
            
            # 安全验证选择器
            if not self._validate_css_selector(selector):
                return {"success": False, "error": f"不安全的 CSS 选择器: {selector}"}
            
            # 等待元素出现
            await self._page.wait_for_selector(selector, state="attached", timeout=timeout)
            
            # 使用参数化调用，避免 JS 注入
            if schema:
                # 根据 schema 提取指定字段，使用安全的参数化方式
                fields = list(schema.keys())
                # 验证字段名安全性（严格的 JS 标识符规则 + 原型链污染防护）
                import re
                FIELD_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
                safe_fields = [
                    f for f in fields
                    if isinstance(f, str)
                    and FIELD_NAME_PATTERN.match(f)
                    and f not in ('__proto__', 'constructor', 'prototype')
                ]
                
                data = await self._page.evaluate(
                    """(selector, fields, multiple) => {
                        const elements = document.querySelectorAll(selector);
                        const results = Array.from(elements).map(el => {
                            const item = {};
                            fields.forEach(field => {
                                const dataEl = el.querySelector(`[data-field=${field}]`);
                                item[field] = dataEl?.innerText || el.getAttribute(field) || '';
                            });
                            return item;
                        });
                        return multiple ? results : (results[0] || {});
                    }""",
                    selector, safe_fields, multiple
                )
            else:
                # 默认提取文本和属性，使用参数化调用
                data = await self._page.evaluate(
                    """(selector, multiple) => {
                        const elements = document.querySelectorAll(selector);
                        const results = Array.from(elements).map(el => ({
                            text: el.innerText?.trim() || '',
                            html: el.innerHTML?.slice(0, 500) || '',
                            href: el.href || el.getAttribute('href') || '',
                            src: el.src || el.getAttribute('src') || ''
                        }));
                        return multiple ? results : (results[0] || {});
                    }""",
                    selector, multiple
                )
            
            # 构建统一返回格式
            return {
                "success": True,
                "action": "extract",
                "data": data,
                "summary": f"从页面提取了 {len(data) if isinstance(data, list) else 1} 条数据",
                "metadata": {
                    "selector": selector,
                    "schema": schema,
                    "multiple": multiple
                }
            }
            
        except Exception as e:
            logger.error(f"数据提取失败: {e}")
            return {
                "success": False,
                "action": "extract",
                "error": str(e),
                "data": None
            }
    
    def _build_extraction_js(self, fields):
        """根据字段列表构建 JS 提取代码（已废弃，保留向后兼容）"""
        # 该方法已不再使用，改用参数化调用
        return ""
