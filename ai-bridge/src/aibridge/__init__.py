"""
AI-Bridge: AI Application Interaction Protocol
Bridge AI Assistants to GUI Applications
"""

from aibridge.version import __version__
from aibridge.core.protocol import Action, Target, Request, Response
from aibridge.core.server import AIBridgeServer
from aibridge.core.manager import AdapterManager
from aibridge.adapters.base import BaseAdapter, AdapterInfo, AdapterType

__all__ = [
    "__version__",
    "Action",
    "Target", 
    "Request",
    "Response",
    "AIBridgeServer",
    "AdapterManager",
    "BaseAdapter",
    "AdapterInfo",
    "AdapterType",
]
