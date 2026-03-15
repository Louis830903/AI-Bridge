"""
Gateway 模块单元测试

测试 MCPRegistry, A2AGateway, ProtocolBridge, ServiceDiscovery
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aibridge.gateway import (
    MCPRegistry,
    MCPServerConfig,
    MCPServerProxy,
    A2AGateway,
    AgentCard,
    A2ATask,
    TaskStatus,
    ProtocolBridge,
    ServiceDiscovery,
)
from aibridge.gateway.mcp_registry import MCPTransport
from aibridge.gateway.a2a_gateway import AgentCapability
from aibridge.gateway.discovery import ServiceInfo, ServiceStatus


class TestMCPRegistry:
    """MCPRegistry 测试"""
    
    @pytest.fixture
    def registry(self):
        return MCPRegistry()
    
    @pytest.mark.asyncio
    async def test_register_server(self, registry):
        """测试注册 MCP Server"""
        config = MCPServerConfig(
            name="test-server",
            transport=MCPTransport.STDIO,
            command="echo",
            args=["hello"],
            auto_start=False,
        )
        
        proxy = await registry.register(config)
        
        assert proxy is not None
        assert proxy.config.name == "test-server"
        assert "test-server" in await registry.list_servers()
    
    @pytest.mark.asyncio
    async def test_unregister_server(self, registry):
        """测试注销 MCP Server"""
        config = MCPServerConfig(
            name="test-server",
            transport=MCPTransport.STDIO,
            command="echo",
            auto_start=False,
        )
        
        await registry.register(config)
        await registry.unregister("test-server")
        
        assert "test-server" not in await registry.list_servers()
    
    @pytest.mark.asyncio
    async def test_get_server_status(self, registry):
        """测试获取 Server 状态"""
        config = MCPServerConfig(
            name="test-server",
            transport=MCPTransport.STDIO,
            command="echo",
            auto_start=False,
        )
        
        await registry.register(config)
        status = registry.get_server_status()
        
        assert "test-server" in status
        assert status["test-server"]["connected"] is False
    
    @pytest.mark.asyncio
    async def test_duplicate_register_updates(self, registry):
        """测试重复注册更新配置"""
        config = MCPServerConfig(
            name="test-server",
            transport=MCPTransport.STDIO,
            command="echo",
            auto_start=False,
        )
        
        await registry.register(config)
        
        # 重复注册应更新配置，不抛异常
        config2 = MCPServerConfig(
            name="test-server",
            transport=MCPTransport.STDIO,
            command="echo2",
            auto_start=False,
        )
        proxy = await registry.register(config2)
        assert proxy is not None


class TestA2AGateway:
    """A2AGateway 测试"""
    
    @pytest.fixture
    def gateway(self):
        return A2AGateway()
    
    @pytest.mark.asyncio
    async def test_register_agent(self, gateway):
        """测试注册 Agent"""
        agent = AgentCard(
            agent_id="test-agent",
            name="Test Agent",
            description="A test agent",
            capabilities=[
                AgentCapability(name="test", description="Test capability")
            ]
        )
        
        await gateway.register_agent(agent)
        agents = await gateway.list_agents()
        
        assert len(agents) == 1
        assert agents[0].agent_id == "test-agent"
    
    @pytest.mark.asyncio
    async def test_discover_agents_by_capability(self, gateway):
        """测试按能力发现 Agent"""
        agent1 = AgentCard(
            agent_id="agent-1",
            name="Agent 1",
            description="Agent 1 description",
            capabilities=[AgentCapability(name="search", description="Search")]
        )
        agent2 = AgentCard(
            agent_id="agent-2",
            name="Agent 2",
            description="Agent 2 description",
            capabilities=[AgentCapability(name="analyze", description="Analyze")]
        )
        
        await gateway.register_agent(agent1)
        await gateway.register_agent(agent2)
        
        found = await gateway.discover_agents("search")
        
        assert len(found) == 1
        assert found[0].agent_id == "agent-1"
    
    @pytest.mark.asyncio
    async def test_unregister_agent(self, gateway):
        """测试注销 Agent"""
        agent = AgentCard(
            agent_id="test-agent",
            name="Test Agent",
            description="Test Agent description",
            capabilities=[]
        )
        
        await gateway.register_agent(agent)
        await gateway.unregister_agent("test-agent")
        
        agents = await gateway.list_agents()
        assert len(agents) == 0
    
    def test_task_lifecycle(self):
        """测试任务生命周期"""
        task = A2ATask(
            from_agent="orchestrator",
            to_agent="worker",
            capability="process",
            input_data={"key": "value"},
        )
        
        assert task.status == TaskStatus.PENDING
        assert task.task_id is not None
        
        # 完成任务
        task.complete({"result": "done"})
        
        assert task.status == TaskStatus.COMPLETED
        assert task.result == {"result": "done"}
    
    def test_task_fail(self):
        """测试任务失败"""
        task = A2ATask(
            from_agent="orchestrator",
            to_agent="worker",
            capability="process",
        )
        
        task.fail("Something went wrong")
        
        assert task.status == TaskStatus.FAILED
        assert "Something went wrong" in task.error


class TestProtocolBridge:
    """ProtocolBridge 测试"""
    
    @pytest.fixture
    def bridge(self):
        registry = MCPRegistry()
        gateway = A2AGateway()
        return ProtocolBridge(mcp_registry=registry, a2a_gateway=gateway)
    
    def test_mcp_to_a2a_capability(self, bridge):
        """测试 MCP 工具转 A2A 能力"""
        from aibridge.connectors.base import ToolInfo
        
        tool = ToolInfo(
            name="navigate",
            description="Navigate to URL",
            input_schema={
                "type": "object",
                "properties": {"url": {"type": "string"}}
            }
        )
        
        capability = bridge.mcp_to_a2a_capability(tool)
        
        assert capability.name == "navigate"
        assert capability.description == "Navigate to URL"
    
    def test_get_bridge_status(self, bridge):
        """测试获取桥接状态"""
        status = bridge.get_bridge_status()
        
        assert "mcp_agents" in status
        assert "config" in status


class TestServiceDiscovery:
    """ServiceDiscovery 测试"""
    
    @pytest.fixture
    def discovery(self):
        return ServiceDiscovery()
    
    def test_register_service(self, discovery):
        """测试注册服务"""
        service = ServiceInfo(
            name="test-service",
            type="mcp",
            status=ServiceStatus.HEALTHY,
        )
        
        discovery.register_service(service)
        
        all_services = discovery.get_all_services()
        assert len(all_services) == 1
        assert all_services[0].name == "test-service"
    
    def test_unregister_service(self, discovery):
        """测试注销服务"""
        service = ServiceInfo(name="test-service", type="mcp")
        
        discovery.register_service(service)
        discovery.unregister_service("test-service")
        
        assert len(discovery.get_all_services()) == 0
    
    def test_get_healthy_services(self, discovery):
        """测试获取健康服务"""
        healthy = ServiceInfo(
            name="healthy-service",
            type="mcp",
            status=ServiceStatus.HEALTHY,
        )
        unhealthy = ServiceInfo(
            name="unhealthy-service",
            type="mcp",
            status=ServiceStatus.UNHEALTHY,
        )
        
        discovery.register_service(healthy)
        discovery.register_service(unhealthy)
        
        healthy_services = discovery.get_healthy_services()
        
        assert len(healthy_services) == 1
        assert healthy_services[0].name == "healthy-service"
    
    def test_service_status_change(self, discovery):
        """测试服务状态变化"""
        service = ServiceInfo(
            name="test-service",
            type="mcp",
            status=ServiceStatus.HEALTHY,
        )
        
        discovery.register_service(service)
        
        # 重新注册以更新状态
        service_updated = ServiceInfo(
            name="test-service",
            type="mcp",
            status=ServiceStatus.UNHEALTHY,
        )
        discovery.register_service(service_updated)
        
        services = discovery.get_all_services()
        assert services[0].status == ServiceStatus.UNHEALTHY
    
    def test_get_status_summary(self, discovery):
        """测试获取状态摘要"""
        discovery.register_service(ServiceInfo(
            name="s1", type="mcp", status=ServiceStatus.HEALTHY
        ))
        discovery.register_service(ServiceInfo(
            name="s2", type="a2a", status=ServiceStatus.HEALTHY
        ))
        discovery.register_service(ServiceInfo(
            name="s3", type="mcp", status=ServiceStatus.UNHEALTHY
        ))
        
        summary = discovery.get_status_summary()
        
        assert summary["total"] == 3
        assert summary["healthy"] == 2
        assert summary["unhealthy"] == 1
