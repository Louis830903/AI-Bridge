"""
Domain intent patterns — six domain intent networks
"""
from aibridge.core.intents.browser import BROWSER_PATTERNS
from aibridge.core.intents.office import OFFICE_PATTERNS
from aibridge.core.intents.media import MEDIA_PATTERNS
from aibridge.core.intents.devops import DEVOPS_PATTERNS
from aibridge.core.intents.collab import COLLAB_PATTERNS
from aibridge.core.intents.webtools import WEBTOOLS_PATTERNS

__all__ = [
    "BROWSER_PATTERNS",
    "OFFICE_PATTERNS",
    "MEDIA_PATTERNS",
    "DEVOPS_PATTERNS",
    "COLLAB_PATTERNS",
    "WEBTOOLS_PATTERNS",
]
