"""
AI-Bridge Gateway - MCP + A2A 双协议网关

核心组件：
- MCPRegistry: MCP Server 注册中心，管理所有 MCP 连接
- MCPProtocol: MCP 协议通信层 (JSON-RPC over STDIO)
- A2AGateway: A2A 协议网关，支持 Agent 间协作
- ProtocolBridge: MCP ↔ A2A 协议桥接
- ServiceDiscovery: 服务发现与健康检查

v5.0 新增：
- AgentCardExtended: 扩展的 Agent Card，支持发布与发现
- CardPublisher: Card 发布器（本地/远程）
- CardDiscovery: Card 发现服务
"""

from .mcp_registry import MCPRegistry, MCPServerConfig, MCPServerProxy
from .mcp_protocol import MCPProtocol, MCPTool, MCPMethod, JSONRPCRequest, JSONRPCResponse
from .a2a_gateway import A2AGateway, AgentCard, A2ATask, TaskStatus
from .protocol_bridge import ProtocolBridge
from .discovery import ServiceDiscovery

# v5.0: Agent Card 扩展
from .agent_card import (
    AgentCardExtended,
    AgentCardMetadata,
    AgentCapability,
    AgentCapabilitySchema,
    CardVisibility,
    CardStatus,
    create_card,
)
from .card_publisher import (
    CardPublisher,
    LocalCardPublisher,
    RemoteCardPublisher,
    MultiRegistryPublisher,
    PublishResult,
)
from .card_discovery import (
    CardDiscovery,
    DiscoveryQuery,
    DiscoveryResult,
    DiscoverySortBy,
)

__all__ = [
    # MCP Registry
    "MCPRegistry",
    "MCPServerConfig", 
    "MCPServerProxy",
    # MCP Protocol
    "MCPProtocol",
    "MCPTool",
    "MCPMethod",
    "JSONRPCRequest",
    "JSONRPCResponse",
    # A2A Gateway
    "A2AGateway",
    "AgentCard",
    "A2ATask",
    "TaskStatus",
    # Protocol Bridge
    "ProtocolBridge",
    # Discovery
    "ServiceDiscovery",
    # v5.0: Agent Card Extended
    "AgentCardExtended",
    "AgentCardMetadata",
    "AgentCapability",
    "AgentCapabilitySchema",
    "CardVisibility",
    "CardStatus",
    "create_card",
    # v5.0: Card Publisher
    "CardPublisher",
    "LocalCardPublisher",
    "RemoteCardPublisher",
    "MultiRegistryPublisher",
    "PublishResult",
    # v5.0: Card Discovery
    "CardDiscovery",
    "DiscoveryQuery",
    "DiscoveryResult",
    "DiscoverySortBy",
]
