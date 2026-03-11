"""
Chrome Adapter - Browser automation via Chrome DevTools Protocol
Glue code wrapping Playwright
"""

import base64
from typing import Any, Dict, List, Optional
from aibridge.adapters.base import BaseAdapter, AdapterInfo, AdapterType

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
    
    This is glue code that wraps Playwright for browser automation.
    Requires Chrome to be running with remote debugging enabled:
        chrome.exe --remote-debugging-port=9222
    """
    
    info = AdapterInfo(
        id="chrome",
        name="Google Chrome",
        type=AdapterType.BROWSER,
        version="1.0.0",
        platforms=["windows", "macos", "linux"],
        actions=[
            "goto", "click", "type", "read", "screenshot",
            "list_elements", "wait", "scroll", "back", "forward",
            "reload", "execute", "focus"
        ],
        description="Chrome browser automation via CDP",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.cdp_url = self.config.get("cdp_url", "http://localhost:9222")
        self._playwright = None
        self._browser = None
        self._page = None
    
    async def connect(self) -> bool:
        """Connect to Chrome via CDP."""
        try:
            async_playwright = get_playwright()
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.connect_over_cdp(self.cdp_url)
            
            # Get the first page
            contexts = self._browser.contexts
            if contexts and contexts[0].pages:
                self._page = contexts[0].pages[0]
            else:
                # Create a new page if none exists
                context = await self._browser.new_context()
                self._page = await context.new_page()
            
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to Chrome: {e}")
    
    async def disconnect(self) -> bool:
        """Disconnect from Chrome."""
        try:
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._connected = False
            return True
        except Exception:
            self._connected = False
            return False
    
    async def is_available(self) -> bool:
        """Check if Chrome is available."""
        pw = None
        browser = None
        try:
            async_playwright = get_playwright()
            pw = await async_playwright().start()
            browser = await pw.chromium.connect_over_cdp(self.cdp_url)
            await browser.close()
            await pw.stop()
            return True
        except Exception:
            # Clean up resources in case of partial initialization
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
        options = options or {}
        timeout = options.get("timeout", 10000)
        
        try:
            if action == "goto":
                url = value if isinstance(value, str) else target.get("url") if target else None
                if url:
                    await self._page.goto(url, timeout=timeout)
                return {"success": True, "data": {"url": self._page.url}}
            
            elif action == "click":
                selector = self._build_selector(target)
                await self._page.click(selector, timeout=timeout)
                return {"success": True}
            
            elif action == "type":
                selector = self._build_selector(target)
                text = value or ""
                await self._page.fill(selector, text, timeout=timeout)
                return {"success": True}
            
            elif action == "read":
                selector = self._build_selector(target)
                element = await self._page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    return {"success": True, "data": text}
                return {"success": False, "error": "Element not found"}
            
            elif action == "screenshot":
                screenshot = await self._page.screenshot()
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
                if direction == "down":
                    await self._page.evaluate("window.scrollBy(0, 500)")
                elif direction == "up":
                    await self._page.evaluate("window.scrollBy(0, -500)")
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
                result = await self._page.evaluate(script)
                return {"success": True, "data": result}
            
            elif action == "focus":
                await self._page.bring_to_front()
                return {"success": True}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _build_selector(self, target: Optional[Dict[str, Any]]) -> str:
        """Build a Playwright selector from target."""
        if not target:
            return "*"
        
        if target.get("css"):
            return target["css"]
        if target.get("xpath"):
            return f"xpath={target['xpath']}"
        if target.get("name"):
            return f"text={target['name']}"
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
