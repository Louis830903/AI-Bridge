"""
Agent Registry 测试
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone

from aibridge.registry import (
    AgentHealth,
    LoadBalanceStrategy,
    RegistryConfig,
    RegisteredAgent,
    AgentRegistry,
)


class TestRegisteredAgent:
    """RegisteredAgent 测试"""
    
    def test_create_agent(self):
        """测试创建 Agent"""
        agent = RegisteredAgent(
            agent_id="agent-1",
            name="Test Agent",
            endpoint="http://localhost:8080",
            capabilities=["chat", "code"],
        )
        
        assert agent.agent_id == "agent-1"
        assert agent.name == "Test Agent"
        assert agent.health == AgentHealth.UNKNOWN
        assert agent.consecutive_failures == 0
    
    def test_is_available(self):
        """测试可用性判断"""
        agent = RegisteredAgent(
            agent_id="agent-1",
            name="Test Agent",
            endpoint="http://localhost:8080",
        )
        
        # UNKNOWN 状态不可用
        assert not agent.is_available()
        
        # HEALTHY 可用
        agent.health = AgentHealth.HEALTHY
        assert agent.is_available()
        
        # DEGRADED 可用（降级）
        agent.health = AgentHealth.DEGRADED
        assert agent.is_available()
        
        # UNHEALTHY 不可用
        agent.health = AgentHealth.UNHEALTHY
        assert not agent.is_available()
    
    def test_update_heartbeat(self):
        """测试心跳更新"""
        agent = RegisteredAgent(
            agent_id="agent-1",
            name="Test Agent",
            endpoint="http://localhost:8080",
            health=AgentHealth.UNHEALTHY,
        )
        agent.consecutive_failures = 5
        
        old_heartbeat = agent.last_heartbeat
        agent.update_heartbeat()
        
        assert agent.last_heartbeat >= old_heartbeat
        assert agent.consecutive_failures == 0
        assert agent.health == AgentHealth.HEALTHY
    
    def test_record_request(self):
        """测试请求记录"""
        agent = RegisteredAgent(
            agent_id="agent-1",
            name="Test Agent",
            endpoint="http://localhost:8080",
        )
        
        # 第一次请求
        agent.record_request(100.0, True)
        assert agent.total_requests == 1
        assert agent.avg_latency_ms == 100.0
        assert agent.success_rate == 1.0
        
        # 第二次请求（失败）
        agent.record_request(200.0, False)
        assert agent.total_requests == 2
        # 使用 EMA，不是简单平均
        assert agent.avg_latency_ms > 100.0
        assert agent.success_rate < 1.0
    
    def test_to_dict(self):
        """测试字典转换"""
        agent = RegisteredAgent(
            agent_id="agent-1",
            name="Test Agent",
            endpoint="http://localhost:8080",
            capabilities=["chat"],
            tags=["prod"],
        )
        
        data = agent.to_dict()
        
        assert data["agent_id"] == "agent-1"
        assert data["name"] == "Test Agent"
        assert data["endpoint"] == "http://localhost:8080"
        assert data["capabilities"] == ["chat"]
        assert data["tags"] == ["prod"]
        assert "last_heartbeat" in data


class TestAgentRegistry:
    """AgentRegistry 测试"""
    
    @pytest.fixture
    def registry(self):
        """创建 Registry"""
        config = RegistryConfig(
            heartbeat_interval=1.0,  # 快速测试
            heartbeat_timeout=3.0,
            enable_health_check=False,  # 禁用远程检查
        )
        return AgentRegistry(config)
    
    @pytest.mark.asyncio
    async def test_register_agent(self, registry):
        """测试注册 Agent"""
        agent = await registry.register(
            agent_id="agent-1",
            name="Test Agent",
            endpoint="http://localhost:8080",
            capabilities=["chat", "code"],
            tags=["prod"],
        )
        
        assert agent.agent_id == "agent-1"
        assert agent.name == "Test Agent"
        
        # 验证可以获取
        found = await registry.get("agent-1")
        assert found is not None
        assert found.agent_id == "agent-1"
    
    @pytest.mark.asyncio
    async def test_unregister_agent(self, registry):
        """测试注销 Agent"""
        await registry.register(
            agent_id="agent-1",
            name="Test Agent",
            endpoint="http://localhost:8080",
        )
        
        result = await registry.unregister("agent-1")
        assert result is True
        
        found = await registry.get("agent-1")
        assert found is None
        
        # 重复注销
        result = await registry.unregister("agent-1")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_heartbeat(self, registry):
        """测试心跳"""
        agent = await registry.register(
            agent_id="agent-1",
            name="Test Agent",
            endpoint="http://localhost:8080",
        )
        old_heartbeat = agent.last_heartbeat
        
        await asyncio.sleep(0.1)
        result = await registry.heartbeat("agent-1")
        
        assert result is True
        updated = await registry.get("agent-1")
        assert updated.last_heartbeat > old_heartbeat
    
    @pytest.mark.asyncio
    async def test_heartbeat_unknown_agent(self, registry):
        """测试未知 Agent 心跳"""
        result = await registry.heartbeat("unknown")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_agents_filter_health(self, registry):
        """测试按健康状态过滤"""
        agent1 = await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
        )
        agent2 = await registry.register(
            agent_id="agent-2",
            name="Agent 2",
            endpoint="http://localhost:8082",
        )
        
        # 设置不同状态
        agent1.health = AgentHealth.HEALTHY
        agent2.health = AgentHealth.UNHEALTHY
        
        healthy = await registry.list_agents(health=AgentHealth.HEALTHY)
        assert len(healthy) == 1
        assert healthy[0].agent_id == "agent-1"
    
    @pytest.mark.asyncio
    async def test_list_agents_filter_capabilities(self, registry):
        """测试按能力过滤"""
        await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
            capabilities=["chat", "code"],
        )
        await registry.register(
            agent_id="agent-2",
            name="Agent 2",
            endpoint="http://localhost:8082",
            capabilities=["search"],
        )
        
        chat_agents = await registry.list_agents(capabilities=["chat"])
        assert len(chat_agents) == 1
        assert chat_agents[0].agent_id == "agent-1"
        
        # 多能力匹配（OR）
        multi = await registry.list_agents(capabilities=["chat", "search"])
        assert len(multi) == 2
    
    @pytest.mark.asyncio
    async def test_list_agents_filter_tags(self, registry):
        """测试按标签过滤"""
        await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
            tags=["prod", "v2"],
        )
        await registry.register(
            agent_id="agent-2",
            name="Agent 2",
            endpoint="http://localhost:8082",
            tags=["dev"],
        )
        
        prod_agents = await registry.list_agents(tags=["prod"])
        assert len(prod_agents) == 1
        assert prod_agents[0].agent_id == "agent-1"
    
    @pytest.mark.asyncio
    async def test_list_agents_available_only(self, registry):
        """测试仅可用 Agent"""
        agent1 = await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
        )
        agent2 = await registry.register(
            agent_id="agent-2",
            name="Agent 2",
            endpoint="http://localhost:8082",
        )
        
        agent1.health = AgentHealth.HEALTHY
        agent2.health = AgentHealth.UNHEALTHY
        
        available = await registry.list_agents(available_only=True)
        assert len(available) == 1
        assert available[0].agent_id == "agent-1"
    
    @pytest.mark.asyncio
    async def test_count(self, registry):
        """测试计数"""
        agent1 = await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
        )
        agent2 = await registry.register(
            agent_id="agent-2",
            name="Agent 2",
            endpoint="http://localhost:8082",
        )
        
        agent1.health = AgentHealth.HEALTHY
        agent2.health = AgentHealth.UNHEALTHY
        
        total = await registry.count()
        assert total == 2
        
        healthy = await registry.count(health=AgentHealth.HEALTHY)
        assert healthy == 1
        
        available = await registry.count(available_only=True)
        assert available == 1


class TestLoadBalancing:
    """负载均衡测试"""
    
    @pytest.fixture
    def registry(self):
        """创建 Registry"""
        config = RegistryConfig(enable_health_check=False)
        return AgentRegistry(config)
    
    @pytest.mark.asyncio
    async def test_select_round_robin(self, registry):
        """测试轮询选择"""
        for i in range(3):
            agent = await registry.register(
                agent_id=f"agent-{i}",
                name=f"Agent {i}",
                endpoint=f"http://localhost:{8080+i}",
                capabilities=["chat"],
            )
            agent.health = AgentHealth.HEALTHY
        
        # 轮询选择
        selected_ids = []
        for _ in range(6):
            agent = await registry.select("chat", LoadBalanceStrategy.ROUND_ROBIN)
            selected_ids.append(agent.agent_id)
        
        # 验证轮询 (顺序可能不同，但应该是循环的)
        # 每个 agent 应该被选中两次
        from collections import Counter
        counts = Counter(selected_ids)
        assert all(c == 2 for c in counts.values())
    
    @pytest.mark.asyncio
    async def test_select_least_connections(self, registry):
        """测试最少连接选择"""
        agent1 = await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
            capabilities=["chat"],
        )
        agent2 = await registry.register(
            agent_id="agent-2",
            name="Agent 2",
            endpoint="http://localhost:8082",
            capabilities=["chat"],
        )
        
        agent1.health = AgentHealth.HEALTHY
        agent2.health = AgentHealth.HEALTHY
        agent1.active_connections = 10
        agent2.active_connections = 5
        
        selected = await registry.select("chat", LoadBalanceStrategy.LEAST_CONNECTIONS)
        assert selected.agent_id == "agent-2"
    
    @pytest.mark.asyncio
    async def test_select_by_latency(self, registry):
        """测试延迟选择"""
        agent1 = await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
            capabilities=["chat"],
        )
        agent2 = await registry.register(
            agent_id="agent-2",
            name="Agent 2",
            endpoint="http://localhost:8082",
            capabilities=["chat"],
        )
        
        agent1.health = AgentHealth.HEALTHY
        agent2.health = AgentHealth.HEALTHY
        agent1.avg_latency_ms = 100.0
        agent2.avg_latency_ms = 50.0
        
        selected = await registry.select("chat", LoadBalanceStrategy.LATENCY)
        assert selected.agent_id == "agent-2"
    
    @pytest.mark.asyncio
    async def test_select_by_success_rate(self, registry):
        """测试成功率选择"""
        agent1 = await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
            capabilities=["chat"],
        )
        agent2 = await registry.register(
            agent_id="agent-2",
            name="Agent 2",
            endpoint="http://localhost:8082",
            capabilities=["chat"],
        )
        
        agent1.health = AgentHealth.HEALTHY
        agent2.health = AgentHealth.HEALTHY
        agent1.success_rate = 0.8
        agent2.success_rate = 0.95
        
        selected = await registry.select("chat", LoadBalanceStrategy.SUCCESS_RATE)
        assert selected.agent_id == "agent-2"
    
    @pytest.mark.asyncio
    async def test_select_with_exclude(self, registry):
        """测试排除选择"""
        for i in range(3):
            agent = await registry.register(
                agent_id=f"agent-{i}",
                name=f"Agent {i}",
                endpoint=f"http://localhost:{8080+i}",
                capabilities=["chat"],
            )
            agent.health = AgentHealth.HEALTHY
        
        selected = await registry.select(
            "chat",
            LoadBalanceStrategy.ROUND_ROBIN,
            exclude=["agent-0", "agent-1"]
        )
        assert selected.agent_id == "agent-2"
    
    @pytest.mark.asyncio
    async def test_select_no_available(self, registry):
        """测试无可用 Agent"""
        await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
            capabilities=["chat"],
        )
        # Agent 默认是 UNKNOWN，不可用
        
        selected = await registry.select("chat")
        assert selected is None
    
    @pytest.mark.asyncio
    async def test_select_fallback_to_degraded(self, registry):
        """测试降级回退"""
        agent = await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
            capabilities=["chat"],
        )
        agent.health = AgentHealth.DEGRADED
        
        selected = await registry.select("chat")
        # 应该回退到 DEGRADED
        assert selected.agent_id == "agent-1"


class TestRegistryCallbacks:
    """Registry 回调测试"""
    
    @pytest.fixture
    def registry(self):
        """创建 Registry"""
        config = RegistryConfig(enable_health_check=False)
        return AgentRegistry(config)
    
    @pytest.mark.asyncio
    async def test_on_register_callback(self, registry):
        """测试注册回调"""
        registered = []
        
        async def callback(agent):
            registered.append(agent.agent_id)
        
        registry.on_register(callback)
        
        await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
        )
        
        assert "agent-1" in registered
    
    @pytest.mark.asyncio
    async def test_on_unregister_callback(self, registry):
        """测试注销回调"""
        unregistered = []
        
        async def callback(agent_id):
            unregistered.append(agent_id)
        
        registry.on_unregister(callback)
        
        await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
        )
        await registry.unregister("agent-1")
        
        assert "agent-1" in unregistered
    
    @pytest.mark.asyncio
    async def test_on_health_change_callback(self, registry):
        """测试健康变化回调"""
        changes = []
        
        async def callback(agent_id, old_health, new_health):
            changes.append((agent_id, old_health, new_health))
        
        registry.on_health_change(callback)
        
        agent = await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
        )
        
        # 手动触发健康状态变化
        await registry._notify_health_change(
            "agent-1",
            AgentHealth.HEALTHY,
            AgentHealth.UNHEALTHY
        )
        
        assert len(changes) == 1
        assert changes[0] == ("agent-1", AgentHealth.HEALTHY, AgentHealth.UNHEALTHY)


class TestRegistryLifecycle:
    """Registry 生命周期测试"""
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """测试启动停止"""
        config = RegistryConfig(
            heartbeat_interval=0.1,
            enable_health_check=False,
        )
        registry = AgentRegistry(config)
        
        await registry.start()
        assert registry._running is True
        
        await asyncio.sleep(0.2)  # 让心跳检查运行一次
        
        await registry.stop()
        assert registry._running is False
    
    @pytest.mark.asyncio
    async def test_heartbeat_timeout(self):
        """测试心跳超时"""
        config = RegistryConfig(
            heartbeat_interval=0.1,
            heartbeat_timeout=0.2,  # 很短的超时
            enable_health_check=False,
        )
        registry = AgentRegistry(config)
        
        agent = await registry.register(
            agent_id="agent-1",
            name="Agent 1",
            endpoint="http://localhost:8081",
        )
        agent.health = AgentHealth.HEALTHY
        
        health_changes = []
        
        async def on_change(agent_id, old, new):
            health_changes.append((agent_id, old, new))
        
        registry.on_health_change(on_change)
        
        await registry.start()
        
        # 等待超时
        await asyncio.sleep(0.5)
        
        await registry.stop()
        
        # 验证健康状态变为 UNHEALTHY
        updated = await registry.get("agent-1")
        assert updated.health == AgentHealth.UNHEALTHY
