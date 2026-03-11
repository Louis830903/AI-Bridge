"""
Edge Adapter - Browser automation via Chrome DevTools Protocol
Reuses Chrome adapter since Edge is Chromium-based
"""

from typing import Any, Dict, Optional
from aibridge.adapters.browser.chrome import ChromeAdapter
from aibridge.adapters.base import AdapterInfo, AdapterType


class EdgeAdapter(ChromeAdapter):
    """
    Microsoft Edge browser adapter.
    
    Edge is Chromium-based, so we reuse the Chrome adapter.
    Requires Edge to be running with remote debugging enabled:
        msedge.exe --remote-debugging-port=9223
    """
    
    info = AdapterInfo(
        id="edge",
        name="Microsoft Edge",
        type=AdapterType.BROWSER,
        version="1.0.0",
        platforms=["windows", "macos", "linux"],
        actions=[
            "goto", "click", "type", "read", "screenshot",
            "list_elements", "wait", "scroll", "back", "forward",
            "reload", "execute", "focus"
        ],
        description="Edge browser automation via CDP",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # Default port for Edge is different
        self.cdp_url = self.config.get("cdp_url", "http://localhost:9223")
