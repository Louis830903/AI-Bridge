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
from typing import Any, Dict, List, Optional
from aibridge.adapters.base import BaseAdapter, AdapterInfo, AdapterType

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
    
    info = AdapterInfo(
        id="chrome",
        name="Google Chrome",
        type=AdapterType.BROWSER,
        version="2.3.1",  # 修复hidden元素支持、A11y快照类型安全
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
        # A11y 快照中的元素缓存，用于 uid 定位（实例变量，避免多实例共享）
        self._snapshot_elements: Dict[str, Any] = {}
    
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
            raise ConnectionError(f"Failed to connect/launch Chrome: {e}")
    
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
            self._snapshot_elements = {}
            self._connected = False
            return True
        except Exception as e:
            logger.warning(f"disconnect 过程中发生错误: {e}")
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
        
        options = options or {}
        timeout = options.get("timeout", self.DEFAULT_TIMEOUT)
        
        try:
            if action == "goto":
                url = value if isinstance(value, str) else target.get("url") if target else None
                if not url:
                    return {"success": False, "error": "goto 操作需要提供 url"}
                # 等待页面加载到 domcontentloaded 状态
                await self._page.goto(url, timeout=timeout, wait_until="domcontentloaded")
                return {"success": True, "data": {"url": self._page.url}}
            
            elif action == "click":
                # 支持 force 参数强制操作隐藏元素
                force = options.get("force", False)
                # 尝试多种定位策略
                element = await self._find_element_with_fallback(target, timeout, force)
                if not element:
                    return {"success": False, "error": f"无法找到可点击的元素: {target}"}
                try:
                    await element.click(timeout=timeout)
                except Exception as e:
                    # 如果 click 失败且 force=True，尝试通过 JS 点击
                    if force and target and target.get("css"):
                        selector = target["css"]
                        await self._page.evaluate(f"document.querySelector('{selector}').click()")
                    else:
                        raise
                return {"success": True}
            
            elif action == "type":
                text = value or ""
                # 支持 force 参数强制操作隐藏元素
                force = options.get("force", False)
                # 尝试多种定位策略
                element = await self._find_element_with_fallback(target, timeout, force)
                if not element:
                    return {"success": False, "error": f"无法找到可输入的元素: {target}"}
                # 使用 Playwright 的 locator fill 方法
                try:
                    await element.fill(text, timeout=timeout)
                except Exception as e:
                    # 如果 fill 失败且 force=True，尝试通过 JS 设置值
                    if force and target and target.get("css"):
                        selector = target["css"]
                        await self._page.evaluate(f"document.querySelector('{selector}').value = '{text}'")
                    else:
                        raise
                return {"success": True}
            
            elif action == "read":
                # 支持 force 参数强制读取隐藏元素
                force = options.get("force", False)
                # 尝试多种定位策略
                element = await self._find_element_with_fallback(target, timeout, force)
                if not element:
                    # 如果找不到元素，尝试通过 JS 读取页面标题
                    if target and target.get("css") == "title":
                        title = await self._page.title()
                        return {"success": True, "data": title}
                    return {"success": False, "error": f"无法找到可读取的元素: {target}"}
                # 获取元素文本内容
                try:
                    text = await element.inner_text()
                except Exception as e:
                    # 如果 inner_text 失败，尝试通过 JS 获取
                    if force and target and target.get("css"):
                        selector = target["css"]
                        text = await self._page.evaluate(f"document.querySelector('{selector}')?.innerText || document.querySelector('{selector}')?.value || ''")
                    else:
                        raise
                return {"success": True, "data": text}
            
            elif action == "screenshot":
                # 支持保存到文件：options={"path": "/path/to/file.png"}
                import os
                path = options.get("path")
                full_page = options.get("full_page", False)
                
                if path:
                    # 校验目录是否存在
                    dir_path = os.path.dirname(path)
                    if dir_path and not os.path.exists(dir_path):
                        return {"success": False, "error": f"目录不存在: {dir_path}"}
                    # 保存到文件
                    await self._page.screenshot(path=path, full_page=full_page)
                    return {"success": True, "path": path}
                else:
                    # 返回 base64
                    screenshot = await self._page.screenshot(full_page=full_page)
                    b64 = base64.b64encode(screenshot).decode()
                    return {"success": True, "screenshot": b64}
            
            elif action == "list_elements":
                elements = await self._get_interactive_elements()
                return {"success": True, "elements": elements}
            
            elif action == "wait":
                selector = self._build_selector(target)
                await self._page.wait_for_selector(selector, timeout=timeout)
                return {"success": True}
            
            elif action == "scroll":
                direction = value or "down"
                distance = self.DEFAULT_SCROLL_DISTANCE
                if direction == "down":
                    await self._page.evaluate(f"window.scrollBy(0, {distance})")
                elif direction == "up":
                    await self._page.evaluate(f"window.scrollBy(0, -{distance})")
                return {"success": True}
            
            elif action == "back":
                await self._page.go_back(timeout=timeout)
                return {"success": True}
            
            elif action == "forward":
                await self._page.go_forward(timeout=timeout)
                return {"success": True}
            
            elif action == "reload":
                await self._page.reload(timeout=timeout)
                return {"success": True}
            
            elif action == "execute":
                script = value or ""
                if not script:
                    return {"success": False, "error": "execute 操作需要提供 JavaScript 代码"}
                try:
                    result = await self._page.evaluate(script)
                    # 处理 None 返回值，确保结果可序列化
                    if result is None:
                        return {"success": True, "data": None, "result_type": "None"}
                    # 处理复杂对象，确保可以 JSON 序列化
                    try:
                        json.dumps(result)
                        return {"success": True, "data": result, "result_type": type(result).__name__}
                    except (TypeError, ValueError):
                        # 不可序列化的对象转为字符串
                        return {"success": True, "data": str(result), "result_type": "str"}
                except Exception as e:
                    logger.error(f"JavaScript 执行失败: {e}")
                    return {"success": False, "error": f"JavaScript 执行失败: {str(e)}"}
            
            elif action == "focus":
                await self._page.bring_to_front()
                return {"success": True}
            
            # ==================== 新增能力 ====================
            
            # A11y 树快照 - 核心能力，支持 uid 定位
            elif action == "take_snapshot":
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
            
            # 多页面管理
            elif action == "list_pages":
                pages = await self._list_pages()
                return {"success": True, "pages": pages}
            
            elif action == "select_page":
                page_id = value if isinstance(value, int) else target.get("page_id") if target else 0
                await self._select_page(page_id)
                return {"success": True, "selected": page_id}
            
            elif action == "new_page":
                url = value if isinstance(value, str) else target.get("url") if target else self.DEFAULT_BLANK_URL
                page_info = await self._new_page(url)
                return {"success": True, "page": page_info}
            
            elif action == "close_page":
                page_id = value if isinstance(value, int) else target.get("page_id") if target else None
                await self._close_page(page_id)
                return {"success": True}
            
            # 更多交互操作
            elif action == "hover":
                selector = self._build_selector(target)
                # 先等待元素可见
                await self._page.wait_for_selector(selector, state="visible", timeout=timeout)
                await self._page.hover(selector, timeout=timeout)
                return {"success": True}
            
            elif action == "drag":
                if not target:
                    return {"success": False, "error": "drag 操作需要 target 参数"}
                from_sel = target.get("from")
                to_sel = target.get("to")
                if not from_sel or not to_sel:
                    return {"success": False, "error": "drag 操作需要 from 和 to 参数"}
                # 先等待两个元素都可见
                await self._page.wait_for_selector(from_sel, state="visible", timeout=timeout)
                await self._page.wait_for_selector(to_sel, state="visible", timeout=timeout)
                await self._page.drag_and_drop(from_sel, to_sel, timeout=timeout)
                return {"success": True}
            
            elif action == "press_key":
                key = value if isinstance(value, str) else target.get("key") if target else None
                if not key:
                    return {"success": False, "error": "press_key 操作需要提供 key"}
                await self._page.keyboard.press(key)
                return {"success": True}
            
            elif action == "fill_form":
                # 批量填写表单：value = [{"selector": "#id", "value": "text"}, ...]
                form_data = value if isinstance(value, list) else []
                filled_count = 0
                for item in form_data:
                    # 类型校验：跳过非字典元素
                    if not isinstance(item, dict):
                        continue
                    sel = item.get("selector")
                    val = item.get("value", "")
                    if sel and isinstance(val, str):
                        # 等待元素可见再填充
                        await self._page.wait_for_selector(sel, state="visible", timeout=timeout)
                        await self._page.fill(sel, val, timeout=timeout)
                        filled_count += 1
                return {"success": True, "filled": filled_count}
            
            # 获取页面信息
            elif action == "get_url":
                return {"success": True, "url": self._page.url}
            
            elif action == "get_title":
                title = await self._page.title()
                return {"success": True, "title": title}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _build_selector(self, target: Optional[Dict[str, Any]]) -> str:
        """构建 Playwright 选择器，支持 uid/css/xpath/name/role 多种方式"""
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
            
            # 为每个元素分配 uid 并缓存
            self._snapshot_elements = {}
            uid_counter = [0]
            
            def assign_uids(node: dict, prefix: str = "") -> dict:
                """递归为节点分配 uid"""
                if not node or not isinstance(node, dict):
                    return node
                
                uid = f"{prefix}{uid_counter[0]}"
                uid_counter[0] += 1
                node["uid"] = uid
                
                # 缓存元素信息
                self._snapshot_elements[uid] = {
                    "role": node.get("role"),
                    "name": node.get("name"),
                    "value": node.get("value"),
                }
                
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
            self._snapshot_elements = {}
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
        if not node:
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
        if "children" in node:
            for child in node["children"]:
                lines.append(self._format_snapshot(child, indent + 1))
        
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
        target: Optional[Dict[str, Any]], 
        timeout: int = 10000,
        force: bool = False
    ) -> Optional[Any]:
        """
        多策略元素定位，带 fallback 机制
        
        Args:
            target: 定位目标
            timeout: 超时时间
            force: 是否强制操作隐藏元素
        
        尝试顺序：
        1. CSS selector
        2. Playwright role locator
        3. Text content
        4. Placeholder attribute
        5. XPath
        """
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
                # 检查元素是否存在（即使是 hidden）
                exists = await self._page.evaluate(f"() => !!document.querySelector('{selector}')")
                if exists:
                    return self._page.locator(selector)
            except Exception as e:
                logger.debug(f"JS 检查元素失败: {e}")
        
        logger.warning(f"所有定位策略都失败: {target}, 最后错误: {last_error}")
        return None
