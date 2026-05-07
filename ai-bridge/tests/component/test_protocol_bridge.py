"""
Component Tests — 协议桥接器 (L1)

Phase IV v1.0.0 — ProtocolBridge MCP->A2A 与 A2A->MCP 类型映射。
"""

from __future__ import annotations

import pytest

from aibridge.gateway.protocol_bridge import ProtocolBridge, BridgeConfig
from aibridge.gateway.mcp_registry import MCPRegistry, ToolSchema
from aibridge.gateway.a2a_gateway import AgentCard, AgentCapability


class TestProtocolBridge:
    """ProtocolBridge 组件测试"""

    @pytest.fixture
    def bridge(self):
        mcp = MCPRegistry()
        from aibridge.gateway.a2a_gateway import A2AGateway
        a2a = A2AGateway()
        return ProtocolBridge(mcp, a2a)

    def test_bridge_config_defaults(self):
        """BridgeConfig 默认值正确"""
        config = BridgeConfig()
        assert config.auto_expose_mcp_as_a2a is True
        assert config.auto_expose_a2a_as_mcp is True
        assert config.mcp_agent_prefix == "mcp-"
        assert config.a2a_tool_prefix == "a2a-"

    def test_mcp_tool_to_capability_type_mapping(self, bridge):
        """MCP Tool schema 通过桥接器转换为 A2A Capability"""
        tool = ToolSchema(
            name="navigate",
            description="Navigate browser to URL",
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            server_name="browser-mcp",
        )
        capability = bridge.mcp_to_a2a_capability(tool)
        assert isinstance(capability, AgentCapability)
        assert capability.name == "navigate"
        assert capability.description == "Navigate browser to URL"
        assert capability.input_schema is not None
        assert capability.input_schema["properties"]["url"]["type"] == "string"

    def test_mcp_server_to_a2a_agent_card(self, bridge):
        """MCP Server 通过桥接器转换为 A2A AgentCard"""
        tools = [
            ToolSchema(
                name="search",
                description="Search the web",
                input_schema={
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                },
                server_name="search-mcp",
            ),
            ToolSchema(
                name="summarize",
                description="Summarize content",
                input_schema={"type": "object", "properties": {}},
                server_name="search-mcp",
            ),
        ]
        agent_card = bridge.mcp_server_to_a2a_agent("search-mcp", tools)
        assert isinstance(agent_card, AgentCard)
        assert agent_card.agent_id == "mcp-search-mcp"
        assert "search-mcp" in agent_card.name
        assert len(agent_card.capabilities) == 2
        cap_names = [c.name for c in agent_card.capabilities]
        assert "search" in cap_names
        assert "summarize" in cap_names
