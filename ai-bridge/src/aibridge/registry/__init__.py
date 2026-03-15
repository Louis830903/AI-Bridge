"""
AI-Bridge Registry 模块

v5.0 新增：Agent 注册中心与 A2A 流式支持
"""

# Agent Registry
from .agent_registry import (
    AgentHealth,
    LoadBalanceStrategy,
    RegistryConfig,
    RegisteredAgent,
    AgentRegistry,
    RegistryClient,
)

# A2A Streaming
from .a2a_streaming import (
    StreamEventType,
    StreamEvent,
    TaskProgress,
    StreamSubscription,
    StreamManager,
    TaskStreamHandler,
    SSEHandler,
    WebSocketHandler,
    A2AStreamingClient,
    create_sse_response,
    create_websocket_handler,
)


__all__ = [
    # Agent Registry
    "AgentHealth",
    "LoadBalanceStrategy",
    "RegistryConfig",
    "RegisteredAgent",
    "AgentRegistry",
    "RegistryClient",
    # A2A Streaming
    "StreamEventType",
    "StreamEvent",
    "TaskProgress",
    "StreamSubscription",
    "StreamManager",
    "TaskStreamHandler",
    "SSEHandler",
    "WebSocketHandler",
    "A2AStreamingClient",
    "create_sse_response",
    "create_websocket_handler",
]
