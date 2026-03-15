"""
AI-Bridge Gateway - MCP + A2A 双协议网关

核心组件：
- MCPRegistry: MCP Server 注册中心，管理所有 MCP 连接
- A2AGateway: A2A 协议网关，支持 Agent 间协作
- ProtocolBridge: MCP ↔ A2A 协议桥接
- ServiceDiscovery: 服务发现与健康检查
"""

from .mcp_registry import MCPRegistry, MCPServerConfig, MCPServerProxy
from .a2a_gateway import A2AGateway, AgentCard, A2ATask, TaskStatus
from .protocol_bridge import ProtocolBridge
from .discovery import ServiceDiscovery

__all__ = [
    # MCP Registry
    "MCPRegistry",
    "MCPServerConfig", 
    "MCPServerProxy",
    # A2A Gateway
    "A2AGateway",
    "AgentCard",
    "A2ATask",
    "TaskStatus",
    # Protocol Bridge
    "ProtocolBridge",
    # Discovery
    "ServiceDiscovery",
]
