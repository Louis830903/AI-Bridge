"""
AI-Bridge: MCP + A2A 双协议网关

AI Agent 生态的统一入口 —— 一次接入，调用所有工具

核心模块：
- gateway: 协议网关核心 (MCPRegistry, A2AGateway, ProtocolBridge)
- connectors: 外部服务连接器 (BrowserConnector, etc.)
- adapters: 原生适配器 (CLI, Office, IM, Desktop)
- core: 基础设施 (Protocol, Server, Manager)
"""

from aibridge.version import __version__

# Core Protocol
from aibridge.core.protocol import Action, Target, Request, Response
from aibridge.core.server import AIBridgeServer
from aibridge.core.manager import AdapterManager

# Adapters (Native)
from aibridge.adapters.base import BaseAdapter, AdapterInfo, AdapterType

# Gateway (New in v3.0)
from aibridge.gateway import (
    MCPRegistry,
    MCPServerConfig,
    A2AGateway,
    AgentCard,
    A2ATask,
    TaskStatus,
    ProtocolBridge,
    ServiceDiscovery,
)

# Connectors (New in v3.0)
from aibridge.connectors import (
    MCPConnector,
    ConnectorConfig,
    ConnectorStatus,
    ConnectorError,
)
from aibridge.connectors.mcp import (
    BrowserConnector,
    BrowserConnectorConfig,
)

__all__ = [
    # Version
    "__version__",
    
    # Core Protocol
    "Action",
    "Target", 
    "Request",
    "Response",
    "AIBridgeServer",
    "AdapterManager",
    
    # Adapters
    "BaseAdapter",
    "AdapterInfo",
    "AdapterType",
    
    # Gateway (v3.0+)
    "MCPRegistry",
    "MCPServerConfig",
    "A2AGateway",
    "AgentCard",
    "A2ATask",
    "TaskStatus",
    "ProtocolBridge",
    "ServiceDiscovery",
    
    # Connectors (v3.0+)
    "MCPConnector",
    "ConnectorConfig",
    "ConnectorStatus",
    "ConnectorError",
    "BrowserConnector",
    "BrowserConnectorConfig",
]
