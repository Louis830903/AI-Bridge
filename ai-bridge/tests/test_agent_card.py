"""
Agent Card 模块测试

测试 Agent Card 扩展数据结构、发布器和发现服务
"""

import pytest
from datetime import datetime, timedelta

from aibridge.gateway.agent_card import (
    AgentCardExtended,
    AgentCardMetadata,
    AgentCapability,
    AgentCapabilitySchema,
    CardVisibility,
    CardStatus,
    create_card,
)
from aibridge.gateway.card_publisher import (
    LocalCardPublisher,
    MultiRegistryPublisher,
    PublishResult,
)
from aibridge.gateway.card_discovery import (
    CardDiscovery,
    DiscoveryQuery,
    DiscoveryResult,
    DiscoverySortBy,
)


class TestAgentCapability:
    """AgentCapability 测试"""
    
    def test_capability_creation(self):
        """测试能力创建"""
        cap = AgentCapability(
            name="translate",
            description="Translate text between languages"
        )
        assert cap.name == "translate"
        assert cap.description == "Translate text between languages"
    
    def test_capability_with_schema(self):
        """测试带 Schema 的能力"""
        input_schema = AgentCapabilitySchema(
            type="object",
            properties={
                "text": {"type": "string"},
                "target_lang": {"type": "string"}
            },
            required=["text", "target_lang"]
        )
        cap = AgentCapability(
            name="translate",
            description="Translate text",
            input_schema=input_schema
        )
        
        data = cap.to_dict()
        assert "input_schema" in data
        assert data["input_schema"]["properties"]["text"]["type"] == "string"
    
    def test_capability_from_dict(self):
        """测试从字典构造"""
        data = {
            "name": "summarize",
            "description": "Summarize text",
            "input_schema": {
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"]
            }
        }
        cap = AgentCapability.from_dict(data)
        assert cap.name == "summarize"
        assert cap.input_schema is not None
        assert "text" in cap.input_schema.properties


class TestAgentCardMetadata:
    """AgentCardMetadata 测试"""
    
    def test_metadata_defaults(self):
        """测试默认值"""
        meta = AgentCardMetadata()
        assert meta.version == "1.0.0"
        assert meta.visibility == CardVisibility.PUBLIC
        assert meta.status == CardStatus.ACTIVE
        assert isinstance(meta.created_at, datetime)
    
    def test_metadata_custom(self):
        """测试自定义值"""
        meta = AgentCardMetadata(
            version="2.0.0",
            visibility=CardVisibility.PRIVATE,
            tags=["ai", "nlp"],
            categories=["language"]
        )
        assert meta.version == "2.0.0"
        assert meta.visibility == CardVisibility.PRIVATE
        assert "ai" in meta.tags
    
    def test_metadata_serialization(self):
        """测试序列化"""
        meta = AgentCardMetadata(
            version="1.0.0",
            tags=["test"]
        )
        data = meta.to_dict()
        assert data["version"] == "1.0.0"
        assert "created_at" in data
        
        # 反序列化
        meta2 = AgentCardMetadata.from_dict(data)
        assert meta2.version == meta.version


class TestAgentCardExtended:
    """AgentCardExtended 测试"""
    
    def test_card_creation(self):
        """测试 Card 创建"""
        card = AgentCardExtended(
            id="test-agent-1",
            name="Test Agent",
            description="A test agent for unit testing",
            capabilities=[
                AgentCapability(name="echo", description="Echo input")
            ],
            endpoint="http://localhost:8001"
        )
        assert card.id == "test-agent-1"
        assert card.name == "Test Agent"
        assert len(card.capabilities) == 1
        assert card.metadata.status == CardStatus.ACTIVE
    
    def test_card_signing(self):
        """测试 Card 签名"""
        card = AgentCardExtended(
            id="test-agent-1",
            name="Test Agent",
            description="A test agent",
            capabilities=[],
            endpoint="http://localhost:8001"
        )
        secret = "test-secret-key-12345"
        
        # 签名
        signature = card.sign(secret)
        assert signature is not None
        assert card.metadata.signature == signature
        
        # 验证
        assert card.verify(secret)
        assert not card.verify("wrong-secret")
    
    def test_card_metrics_update(self):
        """测试性能指标更新"""
        card = AgentCardExtended(
            id="test-agent-1",
            name="Test Agent",
            description="Test",
            capabilities=[],
            endpoint="http://localhost:8001"
        )
        
        # 初始状态
        assert card.total_calls == 0
        assert card.avg_latency_ms is None
        assert card.success_rate is None
        
        # 更新指标
        card.update_metrics(latency_ms=100, success=True)
        assert card.total_calls == 1
        assert card.avg_latency_ms == 100
        assert card.success_rate == 1.0
        
        # 再次更新
        card.update_metrics(latency_ms=200, success=False)
        assert card.total_calls == 2
        # 指数移动平均
        assert card.avg_latency_ms > 100 and card.avg_latency_ms < 200
        assert card.success_rate < 1.0
    
    def test_card_serialization(self):
        """测试序列化"""
        card = AgentCardExtended(
            id="test-agent-1",
            name="Test Agent",
            description="Test",
            capabilities=[
                AgentCapability(name="test", description="Test capability")
            ],
            endpoint="http://localhost:8001",
            protocols=["a2a", "mcp"],
            auth_required=True,
            auth_schemes=["api_key"]
        )
        
        # 序列化
        data = card.to_dict()
        assert data["id"] == "test-agent-1"
        assert len(data["capabilities"]) == 1
        assert data["auth_required"] is True
        
        # 反序列化
        card2 = AgentCardExtended.from_dict(data)
        assert card2.id == card.id
        assert card2.name == card.name
        assert len(card2.capabilities) == 1
    
    def test_card_to_a2a_format(self):
        """测试转换为 A2A 格式"""
        card = AgentCardExtended(
            id="test-agent-1",
            name="Test Agent",
            description="Test agent description",
            capabilities=[
                AgentCapability(
                    name="translate",
                    description="Translate text",
                    input_schema=AgentCapabilitySchema(
                        properties={"text": {"type": "string"}}
                    )
                )
            ],
            endpoint="http://localhost:8001",
            auth_required=True,
            auth_schemes=["api_key"]
        )
        
        a2a_card = card.to_a2a_card()
        assert a2a_card["name"] == "Test Agent"
        assert "translate" in a2a_card["capabilities"]
        assert a2a_card["authentication"]["required"] is True


class TestCreateCard:
    """create_card 便捷函数测试"""
    
    def test_create_simple_card(self):
        """测试创建简单 Card"""
        card = create_card(
            id="simple-agent",
            name="Simple Agent",
            description="A simple agent",
            endpoint="http://localhost:8000"
        )
        assert card.id == "simple-agent"
        assert len(card.capabilities) == 0
    
    def test_create_card_with_capabilities(self):
        """测试创建带能力的 Card"""
        card = create_card(
            id="capable-agent",
            name="Capable Agent",
            description="Agent with capabilities",
            endpoint="http://localhost:8000",
            capabilities=[
                {"name": "search", "description": "Search for information"},
                {"name": "summarize", "description": "Summarize text"}
            ],
            tags=["search", "nlp"],
            categories=["utility"]
        )
        assert len(card.capabilities) == 2
        assert card.metadata.tags == ["search", "nlp"]


class TestLocalCardPublisher:
    """LocalCardPublisher 测试"""
    
    @pytest.mark.asyncio
    async def test_publish(self):
        """测试发布"""
        publisher = LocalCardPublisher()
        card = create_card(
            id="local-agent",
            name="Local Agent",
            description="Test",
            endpoint="http://localhost:8002"
        )
        
        result = await publisher.publish(card)
        assert result.success
        assert result.card_id == "local-agent"
    
    @pytest.mark.asyncio
    async def test_get(self):
        """测试获取"""
        publisher = LocalCardPublisher()
        card = create_card(
            id="get-test",
            name="Get Test",
            description="Test",
            endpoint="http://localhost:8003"
        )
        
        await publisher.publish(card)
        retrieved = await publisher.get("get-test")
        assert retrieved is not None
        assert retrieved.id == "get-test"
    
    @pytest.mark.asyncio
    async def test_unpublish(self):
        """测试取消发布"""
        publisher = LocalCardPublisher()
        card = create_card(
            id="to-remove",
            name="To Remove",
            description="Test",
            endpoint="http://localhost:8003"
        )
        
        await publisher.publish(card)
        assert await publisher.unpublish("to-remove")
        assert await publisher.get("to-remove") is None
        assert not await publisher.unpublish("non-existent")
    
    @pytest.mark.asyncio
    async def test_get_all(self):
        """测试获取所有"""
        publisher = LocalCardPublisher()
        
        for i in range(3):
            card = create_card(
                id=f"agent-{i}",
                name=f"Agent {i}",
                description="Test",
                endpoint=f"http://localhost:{8000 + i}"
            )
            await publisher.publish(card)
        
        all_cards = publisher.get_all()
        assert len(all_cards) == 3


class TestMultiRegistryPublisher:
    """MultiRegistryPublisher 测试"""
    
    @pytest.mark.asyncio
    async def test_publish_to_multiple(self):
        """测试发布到多个 Registry"""
        pub1 = LocalCardPublisher()
        pub2 = LocalCardPublisher()
        
        multi_pub = MultiRegistryPublisher(publishers=[pub1, pub2])
        
        card = create_card(
            id="multi-agent",
            name="Multi Agent",
            description="Test",
            endpoint="http://localhost:8000"
        )
        
        result = await multi_pub.publish(card)
        assert result.success
        
        # 两个 Registry 都应该有
        assert await pub1.get("multi-agent") is not None
        assert await pub2.get("multi-agent") is not None
    
    @pytest.mark.asyncio
    async def test_get_from_first_available(self):
        """测试从第一个可用的 Registry 获取"""
        pub1 = LocalCardPublisher()
        pub2 = LocalCardPublisher()
        
        # 只在 pub2 发布
        card = create_card(
            id="only-in-pub2",
            name="Only In Pub2",
            description="Test",
            endpoint="http://localhost:8000"
        )
        await pub2.publish(card)
        
        multi_pub = MultiRegistryPublisher(publishers=[pub1, pub2])
        retrieved = await multi_pub.get("only-in-pub2")
        assert retrieved is not None


class TestCardDiscovery:
    """CardDiscovery 测试"""
    
    @pytest.fixture
    def discovery_with_cards(self):
        """创建带测试数据的 Discovery"""
        discovery = CardDiscovery()
        
        # 添加测试 Cards
        card1 = AgentCardExtended(
            id="agent-1",
            name="Code Assistant",
            description="Helps with coding tasks",
            capabilities=[
                AgentCapability(name="code_review"),
                AgentCapability(name="refactor")
            ],
            endpoint="http://localhost:8001",
            metadata=AgentCardMetadata(
                tags=["coding", "assistant"],
                categories=["development"]
            ),
            success_rate=0.95,
            avg_latency_ms=100,
            total_calls=1000
        )
        card2 = AgentCardExtended(
            id="agent-2",
            name="Data Analyst",
            description="Analyzes data and generates reports",
            capabilities=[
                AgentCapability(name="analyze"),
                AgentCapability(name="visualize")
            ],
            endpoint="http://localhost:8002",
            metadata=AgentCardMetadata(
                tags=["data", "analysis"],
                categories=["analytics"]
            ),
            success_rate=0.90,
            avg_latency_ms=200,
            total_calls=500
        )
        card3 = AgentCardExtended(
            id="agent-3",
            name="Language Translator",
            description="Translates between languages",
            capabilities=[
                AgentCapability(name="translate"),
                AgentCapability(name="detect_language")
            ],
            endpoint="http://localhost:8003",
            metadata=AgentCardMetadata(
                tags=["language", "translation"],
                categories=["language"]
            ),
            success_rate=0.98,
            avg_latency_ms=50,
            total_calls=2000
        )
        
        discovery.add_local_card(card1)
        discovery.add_local_card(card2)
        discovery.add_local_card(card3)
        
        return discovery
    
    @pytest.mark.asyncio
    async def test_discover_all(self, discovery_with_cards):
        """测试发现所有"""
        query = DiscoveryQuery()
        result = await discovery_with_cards.discover_merged(query)
        assert result.total_count == 3
    
    @pytest.mark.asyncio
    async def test_discover_by_keywords(self, discovery_with_cards):
        """测试关键词搜索"""
        query = DiscoveryQuery(keywords="coding")
        result = await discovery_with_cards.discover_merged(query)
        assert result.total_count == 1
        assert result.cards[0].id == "agent-1"
    
    @pytest.mark.asyncio
    async def test_discover_by_tags(self, discovery_with_cards):
        """测试标签过滤"""
        query = DiscoveryQuery(tags=["data"])
        result = await discovery_with_cards.discover_merged(query)
        assert result.total_count == 1
        assert result.cards[0].id == "agent-2"
    
    @pytest.mark.asyncio
    async def test_discover_by_capability(self, discovery_with_cards):
        """测试能力过滤"""
        query = DiscoveryQuery(capabilities=["translate"])
        result = await discovery_with_cards.discover_merged(query)
        assert result.total_count == 1
        assert result.cards[0].id == "agent-3"
    
    @pytest.mark.asyncio
    async def test_discover_by_performance(self, discovery_with_cards):
        """测试性能过滤"""
        query = DiscoveryQuery(
            min_success_rate=0.95,
            max_latency_ms=150
        )
        result = await discovery_with_cards.discover_merged(query)
        # agent-1 (0.95, 100ms) 和 agent-3 (0.98, 50ms) 满足条件
        assert result.total_count == 2
    
    @pytest.mark.asyncio
    async def test_sort_by_latency(self, discovery_with_cards):
        """测试延迟排序"""
        query = DiscoveryQuery(sort_by=DiscoverySortBy.LATENCY, sort_desc=False)
        result = await discovery_with_cards.discover_merged(query)
        # 延迟从低到高：agent-3 (50), agent-1 (100), agent-2 (200)
        assert len(result.cards) == 3
        assert result.cards[0].avg_latency_ms == 50  # agent-3
        assert result.cards[1].avg_latency_ms == 100  # agent-1
        assert result.cards[2].avg_latency_ms == 200  # agent-2
    
    @pytest.mark.asyncio
    async def test_sort_by_popularity(self, discovery_with_cards):
        """测试使用量排序"""
        query = DiscoveryQuery(sort_by=DiscoverySortBy.POPULARITY)
        result = await discovery_with_cards.discover_merged(query)
        # 使用量从高到低：agent-3 (2000), agent-1 (1000), agent-2 (500)
        assert result.cards[0].id == "agent-3"
    
    @pytest.mark.asyncio
    async def test_pagination(self, discovery_with_cards):
        """测试分页"""
        # 获取前 2 个
        query = DiscoveryQuery(limit=2, offset=0)
        result = await discovery_with_cards.discover_merged(query)
        assert len(result.cards) == 2
        # total_count 应该是总数
        total_from_first = result.total_count
        
        # 获取剩余的
        query2 = DiscoveryQuery(limit=2, offset=2)
        result2 = await discovery_with_cards.discover_merged(query2)
        # 剩余数量应该是 total - offset
        assert len(result2.cards) <= 2
    
    @pytest.mark.asyncio
    async def test_discover_by_capability_helper(self, discovery_with_cards):
        """测试按能力发现辅助函数"""
        cards = await discovery_with_cards.discover_by_capability("code_review")
        assert len(cards) == 1
        assert cards[0].id == "agent-1"
    
    @pytest.mark.asyncio
    async def test_find_best_agent(self, discovery_with_cards):
        """测试找最佳 Agent"""
        # 按成功率
        best = await discovery_with_cards.find_best_agent("translate")
        assert best.id == "agent-3"
        
        # 按延迟
        best_low_latency = await discovery_with_cards.find_best_agent(
            "translate",
            prefer_low_latency=True
        )
        assert best_low_latency.id == "agent-3"
    
    def test_add_remove_local_card(self):
        """测试添加和移除本地 Card"""
        discovery = CardDiscovery()
        
        card = create_card(
            id="test-card",
            name="Test Card",
            description="Test",
            endpoint="http://localhost:8000"
        )
        
        discovery.add_local_card(card)
        assert discovery.get_local_card("test-card") is not None
        
        discovery.remove_local_card("test-card")
        assert discovery.get_local_card("test-card") is None
    
    def test_registry_management(self):
        """测试 Registry 管理"""
        discovery = CardDiscovery()
        
        discovery.add_registry("http://registry1.example.com")
        discovery.add_registry("http://registry2.example.com")
        
        assert len(discovery.list_registries()) == 2
        
        discovery.remove_registry("http://registry1.example.com")
        assert len(discovery.list_registries()) == 1
