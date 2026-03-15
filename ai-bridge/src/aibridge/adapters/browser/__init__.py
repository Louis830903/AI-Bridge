"""
Browser adapters module.

.. deprecated:: 3.0.0
    This module is deprecated and will be removed in v4.0.
    Use :mod:`aibridge.connectors.mcp.browser` instead, which provides
    better integration with mature browser automation solutions like
    Browser Use, Chrome DevTools MCP, and Playwright MCP.
    
    Migration example:
    ```python
    # Old way (deprecated)
    from aibridge.adapters.browser import ChromeAdapter
    adapter = ChromeAdapter({"headless": True})
    
    # New way (recommended)
    from aibridge.connectors.mcp import BrowserConnector, BrowserConnectorConfig
    config = BrowserConnectorConfig(name="browser", headless=True)
    connector = BrowserConnector(config)
    ```
"""

import warnings

# Emit deprecation warning on import
warnings.warn(
    "aibridge.adapters.browser is deprecated since v3.0 and will be removed in v4.0. "
    "Use aibridge.connectors.mcp.browser instead for better browser automation support.",
    DeprecationWarning,
    stacklevel=2
)

# Still export for backward compatibility
from aibridge.adapters.browser.chrome import ChromeAdapter
from aibridge.adapters.browser.edge import EdgeAdapter

__all__ = ["ChromeAdapter", "EdgeAdapter"]

# Provide migration helper
def get_recommended_connector():
    """
    Returns the recommended browser connector for new code.
    
    This helper function guides users to migrate from deprecated
    ChromeAdapter/EdgeAdapter to the new BrowserConnector.
    
    Returns:
        BrowserConnector class
    """
    from aibridge.connectors.mcp.browser import BrowserConnector
    return BrowserConnector
