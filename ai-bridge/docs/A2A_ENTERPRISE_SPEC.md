# AI-Bridge v5.0 开发规范：A2A 协议增强 + 企业级可观测

> 战略方向：MCP + A2A 双协议网关，聚焦企业级能力
> 版本：v5.0
> 创建时间：2026-03-15

---

## 一、总体目标

基于现有的 MCP ↔ A2A 双向协议桥接和企业级治理能力，进一步强化：

1. **A2A 生态卡位**：Agent Card 发布与发现，成为 A2A 生态入口
2. **生产可观测**：Prometheus 指标导出，满足企业监控需求
3. **多 Agent 协作**：Agent Registry 注册中心，支持大规模 Agent 发现
4. **实时反馈**：A2A Streaming 支持，任务执行实时推送
5. **合规审计**：Audit Log 持久化，满足企业合规要求
6. **热插拔能力**：MCP Server 动态发现，无需重启即可扩展

---

## 二、开发计划总览

| 阶段 | 优先级 | 模块 | 功能 | 预估工作量 | 依赖 |
|------|--------|------|------|-----------|------|
| Phase 1 | P0 | A2A | Agent Card 发布与发现 | 3天 | 现有 a2a_gateway.py |
| Phase 1 | P0 | 企业级 | Prometheus 指标导出 | 2天 | 现有 metering.py |
| Phase 2 | P1 | A2A | Agent Registry 注册中心 | 3天 | Phase 1 Agent Card |
| Phase 2 | P1 | 协议 | A2A Streaming 支持 | 2天 | 现有 a2a_gateway.py |
| Phase 3 | P2 | 企业级 | Audit Log 持久化 | 2天 | 现有 audit.py |
| Phase 3 | P2 | 网关 | MCP Server 动态发现 | 2天 | 现有 mcp_registry.py |

---

## 三、Phase 1（P0）详细规范

### 3.1 Agent Card 发布与发现

#### 3.1.1 背景与目标

Agent Card 是 A2A 协议的核心，描述 Agent 的身份、能力和通信方式。当前实现仅支持本地注册，需要扩展为：

- **发布**：Agent 可以发布自己的 Card 到公共/私有 Registry
- **发现**：其他 Agent 可以按条件搜索和发现 Agent
- **验证**：Card 签名验证，防止冒充

#### 3.1.2 数据结构扩展

```python
# src/aibridge/gateway/agent_card.py (新建)

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import hashlib
import hmac
import json


class CardVisibility(str, Enum):
    """Card 可见性"""
    PUBLIC = "public"      # 公开可发现
    PRIVATE = "private"    # 仅限授权访问
    UNLISTED = "unlisted"  # 不可搜索但可直接访问


class CardStatus(str, Enum):
    """Card 状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


@dataclass
class AgentCardMetadata:
    """Agent Card 元数据"""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    visibility: CardVisibility = CardVisibility.PUBLIC
    status: CardStatus = CardStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    owner_id: Optional[str] = None
    signature: Optional[str] = None  # Card 签名，防止篡改


@dataclass
class AgentCardExtended:
    """扩展的 Agent Card，支持发布与发现"""
    # 基础信息（继承自现有 AgentCard）
    id: str
    name: str
    description: str
    capabilities: List[Dict[str, Any]]
    endpoint: str
    
    # 扩展字段
    metadata: AgentCardMetadata = field(default_factory=AgentCardMetadata)
    
    # 通信配置
    protocols: List[str] = field(default_factory=lambda: ["a2a", "mcp"])
    auth_required: bool = False
    auth_schemes: List[str] = field(default_factory=list)  # ["api_key", "jwt", "oauth2"]
    
    # 性能指标（用于发现排序）
    avg_latency_ms: Optional[float] = None
    success_rate: Optional[float] = None
    total_calls: int = 0
    
    def sign(self, secret_key: str) -> str:
        """生成 Card 签名"""
        payload = json.dumps({
            "id": self.id,
            "name": self.name,
            "endpoint": self.endpoint,
            "capabilities": [c["name"] for c in self.capabilities],
            "version": self.metadata.version,
        }, sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        self.metadata.signature = signature
        return signature
    
    def verify(self, secret_key: str) -> bool:
        """验证 Card 签名"""
        if not self.metadata.signature:
            return False
        expected = self.sign(secret_key)
        return hmac.compare_digest(self.metadata.signature, expected)
```

#### 3.1.3 Card Publisher 实现

```python
# src/aibridge/gateway/card_publisher.py (新建)

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from abc import ABC, abstractmethod
import aiohttp
import asyncio
from .agent_card import AgentCardExtended, CardVisibility


@dataclass
class PublishResult:
    """发布结果"""
    success: bool
    card_id: str
    registry_url: str
    error: Optional[str] = None
    published_at: Optional[str] = None


class CardPublisher(ABC):
    """Card 发布器抽象基类"""
    
    @abstractmethod
    async def publish(self, card: AgentCardExtended) -> PublishResult:
        """发布 Card"""
        pass
    
    @abstractmethod
    async def unpublish(self, card_id: str) -> bool:
        """取消发布"""
        pass
    
    @abstractmethod
    async def update(self, card: AgentCardExtended) -> PublishResult:
        """更新 Card"""
        pass


class LocalCardPublisher(CardPublisher):
    """本地 Card 发布器（用于私有部署）"""
    
    def __init__(self, storage_path: str = ".aibridge/cards"):
        self._storage_path = storage_path
        self._cards: Dict[str, AgentCardExtended] = {}
    
    async def publish(self, card: AgentCardExtended) -> PublishResult:
        self._cards[card.id] = card
        return PublishResult(
            success=True,
            card_id=card.id,
            registry_url=f"local://{self._storage_path}",
            published_at=card.metadata.updated_at.isoformat()
        )
    
    async def unpublish(self, card_id: str) -> bool:
        if card_id in self._cards:
            del self._cards[card_id]
            return True
        return False
    
    async def update(self, card: AgentCardExtended) -> PublishResult:
        return await self.publish(card)
    
    def get_all(self) -> List[AgentCardExtended]:
        return list(self._cards.values())


class RemoteCardPublisher(CardPublisher):
    """远程 Registry 发布器"""
    
    def __init__(
        self,
        registry_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        self._registry_url = registry_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers
    
    async def publish(self, card: AgentCardExtended) -> PublishResult:
        url = f"{self._registry_url}/agents"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=self._card_to_dict(card),
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        return PublishResult(
                            success=True,
                            card_id=card.id,
                            registry_url=self._registry_url,
                            published_at=data.get("published_at")
                        )
                    else:
                        error = await resp.text()
                        return PublishResult(
                            success=False,
                            card_id=card.id,
                            registry_url=self._registry_url,
                            error=f"HTTP {resp.status}: {error}"
                        )
        except Exception as e:
            return PublishResult(
                success=False,
                card_id=card.id,
                registry_url=self._registry_url,
                error=str(e)
            )
    
    async def unpublish(self, card_id: str) -> bool:
        url = f"{self._registry_url}/agents/{card_id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    url,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as resp:
                    return resp.status in (200, 204)
        except Exception:
            return False
    
    async def update(self, card: AgentCardExtended) -> PublishResult:
        url = f"{self._registry_url}/agents/{card.id}"
        try:
            async with aiohttp.ClientSession() as session:
                async with session.put(
                    url,
                    json=self._card_to_dict(card),
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self._timeout)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return PublishResult(
                            success=True,
                            card_id=card.id,
                            registry_url=self._registry_url,
                            published_at=data.get("updated_at")
                        )
                    else:
                        error = await resp.text()
                        return PublishResult(
                            success=False,
                            card_id=card.id,
                            registry_url=self._registry_url,
                            error=f"HTTP {resp.status}: {error}"
                        )
        except Exception as e:
            return PublishResult(
                success=False,
                card_id=card.id,
                registry_url=self._registry_url,
                error=str(e)
            )
    
    @staticmethod
    def _card_to_dict(card: AgentCardExtended) -> Dict[str, Any]:
        return {
            "id": card.id,
            "name": card.name,
            "description": card.description,
            "capabilities": card.capabilities,
            "endpoint": card.endpoint,
            "protocols": card.protocols,
            "auth_required": card.auth_required,
            "auth_schemes": card.auth_schemes,
            "metadata": {
                "version": card.metadata.version,
                "visibility": card.metadata.visibility.value,
                "status": card.metadata.status.value,
                "tags": card.metadata.tags,
                "categories": card.metadata.categories,
                "signature": card.metadata.signature,
            }
        }
```

#### 3.1.4 Card Discovery 实现

```python
# src/aibridge/gateway/card_discovery.py (新建)

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Callable
from enum import Enum
import asyncio
import aiohttp
from .agent_card import AgentCardExtended, CardVisibility, CardStatus


class DiscoverySortBy(str, Enum):
    """发现排序方式"""
    RELEVANCE = "relevance"      # 相关性
    LATENCY = "latency"          # 响应时间
    SUCCESS_RATE = "success_rate"  # 成功率
    POPULARITY = "popularity"    # 使用量
    CREATED_AT = "created_at"    # 创建时间


@dataclass
class DiscoveryQuery:
    """发现查询条件"""
    keywords: Optional[str] = None           # 关键词搜索
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)  # 按能力名称过滤
    protocols: List[str] = field(default_factory=list)     # 支持的协议
    min_success_rate: Optional[float] = None
    max_latency_ms: Optional[float] = None
    visibility: Optional[CardVisibility] = CardVisibility.PUBLIC
    status: CardStatus = CardStatus.ACTIVE
    sort_by: DiscoverySortBy = DiscoverySortBy.RELEVANCE
    limit: int = 50
    offset: int = 0


@dataclass
class DiscoveryResult:
    """发现结果"""
    cards: List[AgentCardExtended]
    total_count: int
    query_time_ms: float
    source: str  # 来源 Registry


class CardDiscovery:
    """Agent Card 发现服务"""
    
    def __init__(self):
        self._local_cards: Dict[str, AgentCardExtended] = {}
        self._remote_registries: List[str] = []
        self._cache: Dict[str, DiscoveryResult] = {}
        self._cache_ttl: float = 60.0  # 缓存 60 秒
    
    def add_local_card(self, card: AgentCardExtended) -> None:
        """添加本地 Card"""
        self._local_cards[card.id] = card
    
    def remove_local_card(self, card_id: str) -> bool:
        """移除本地 Card"""
        if card_id in self._local_cards:
            del self._local_cards[card_id]
            return True
        return False
    
    def add_registry(self, registry_url: str) -> None:
        """添加远程 Registry"""
        if registry_url not in self._remote_registries:
            self._remote_registries.append(registry_url)
    
    async def discover(self, query: DiscoveryQuery) -> List[DiscoveryResult]:
        """执行发现查询"""
        results = []
        
        # 1. 搜索本地 Cards
        local_result = await self._discover_local(query)
        if local_result.cards:
            results.append(local_result)
        
        # 2. 并发搜索远程 Registries
        if self._remote_registries:
            remote_tasks = [
                self._discover_remote(registry, query)
                for registry in self._remote_registries
            ]
            remote_results = await asyncio.gather(*remote_tasks, return_exceptions=True)
            for result in remote_results:
                if isinstance(result, DiscoveryResult) and result.cards:
                    results.append(result)
        
        return results
    
    async def discover_merged(self, query: DiscoveryQuery) -> DiscoveryResult:
        """执行发现查询并合并结果"""
        import time
        start_time = time.time()
        
        all_results = await self.discover(query)
        
        # 合并所有结果
        merged_cards: Dict[str, AgentCardExtended] = {}
        for result in all_results:
            for card in result.cards:
                # 去重：同 ID 保留性能更好的
                if card.id not in merged_cards:
                    merged_cards[card.id] = card
                else:
                    existing = merged_cards[card.id]
                    if (card.success_rate or 0) > (existing.success_rate or 0):
                        merged_cards[card.id] = card
        
        # 排序
        cards = list(merged_cards.values())
        cards = self._sort_cards(cards, query.sort_by)
        
        # 分页
        total = len(cards)
        cards = cards[query.offset:query.offset + query.limit]
        
        query_time = (time.time() - start_time) * 1000
        
        return DiscoveryResult(
            cards=cards,
            total_count=total,
            query_time_ms=query_time,
            source="merged"
        )
    
    async def _discover_local(self, query: DiscoveryQuery) -> DiscoveryResult:
        """本地搜索"""
        import time
        start_time = time.time()
        
        matched = []
        for card in self._local_cards.values():
            if self._match_query(card, query):
                matched.append(card)
        
        matched = self._sort_cards(matched, query.sort_by)
        total = len(matched)
        matched = matched[query.offset:query.offset + query.limit]
        
        query_time = (time.time() - start_time) * 1000
        
        return DiscoveryResult(
            cards=matched,
            total_count=total,
            query_time_ms=query_time,
            source="local"
        )
    
    async def _discover_remote(
        self, 
        registry_url: str, 
        query: DiscoveryQuery
    ) -> DiscoveryResult:
        """远程搜索"""
        import time
        start_time = time.time()
        
        url = f"{registry_url.rstrip('/')}/agents/discover"
        params = self._query_to_params(query)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=10.0)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        cards = [
                            self._dict_to_card(item)
                            for item in data.get("cards", [])
                        ]
                        query_time = (time.time() - start_time) * 1000
                        return DiscoveryResult(
                            cards=cards,
                            total_count=data.get("total", len(cards)),
                            query_time_ms=query_time,
                            source=registry_url
                        )
        except Exception:
            pass
        
        return DiscoveryResult(
            cards=[],
            total_count=0,
            query_time_ms=0,
            source=registry_url
        )
    
    def _match_query(self, card: AgentCardExtended, query: DiscoveryQuery) -> bool:
        """检查 Card 是否匹配查询条件"""
        # 状态过滤
        if card.metadata.status != query.status:
            return False
        
        # 可见性过滤
        if query.visibility and card.metadata.visibility != query.visibility:
            return False
        
        # 关键词搜索
        if query.keywords:
            keywords = query.keywords.lower()
            searchable = f"{card.name} {card.description}".lower()
            if keywords not in searchable:
                return False
        
        # Tags 过滤
        if query.tags:
            if not any(tag in card.metadata.tags for tag in query.tags):
                return False
        
        # Categories 过滤
        if query.categories:
            if not any(cat in card.metadata.categories for cat in query.categories):
                return False
        
        # Capabilities 过滤
        if query.capabilities:
            card_caps = {c["name"] for c in card.capabilities}
            if not any(cap in card_caps for cap in query.capabilities):
                return False
        
        # Protocols 过滤
        if query.protocols:
            if not any(p in card.protocols for p in query.protocols):
                return False
        
        # 性能过滤
        if query.min_success_rate and card.success_rate:
            if card.success_rate < query.min_success_rate:
                return False
        
        if query.max_latency_ms and card.avg_latency_ms:
            if card.avg_latency_ms > query.max_latency_ms:
                return False
        
        return True
    
    def _sort_cards(
        self, 
        cards: List[AgentCardExtended], 
        sort_by: DiscoverySortBy
    ) -> List[AgentCardExtended]:
        """排序 Cards"""
        if sort_by == DiscoverySortBy.LATENCY:
            return sorted(cards, key=lambda c: c.avg_latency_ms or float('inf'))
        elif sort_by == DiscoverySortBy.SUCCESS_RATE:
            return sorted(cards, key=lambda c: c.success_rate or 0, reverse=True)
        elif sort_by == DiscoverySortBy.POPULARITY:
            return sorted(cards, key=lambda c: c.total_calls, reverse=True)
        elif sort_by == DiscoverySortBy.CREATED_AT:
            return sorted(cards, key=lambda c: c.metadata.created_at, reverse=True)
        else:
            # RELEVANCE: 综合评分
            def score(c: AgentCardExtended) -> float:
                s = 0.0
                if c.success_rate:
                    s += c.success_rate * 50
                if c.avg_latency_ms:
                    s += max(0, 100 - c.avg_latency_ms / 10)
                s += min(c.total_calls / 100, 50)
                return s
            return sorted(cards, key=score, reverse=True)
    
    @staticmethod
    def _query_to_params(query: DiscoveryQuery) -> Dict[str, Any]:
        """转换查询为 HTTP 参数"""
        params = {
            "limit": query.limit,
            "offset": query.offset,
            "sort_by": query.sort_by.value,
            "status": query.status.value,
        }
        if query.keywords:
            params["q"] = query.keywords
        if query.tags:
            params["tags"] = ",".join(query.tags)
        if query.categories:
            params["categories"] = ",".join(query.categories)
        if query.capabilities:
            params["capabilities"] = ",".join(query.capabilities)
        if query.protocols:
            params["protocols"] = ",".join(query.protocols)
        if query.min_success_rate:
            params["min_success_rate"] = query.min_success_rate
        if query.max_latency_ms:
            params["max_latency_ms"] = query.max_latency_ms
        if query.visibility:
            params["visibility"] = query.visibility.value
        return params
    
    @staticmethod
    def _dict_to_card(data: Dict[str, Any]) -> AgentCardExtended:
        """从字典构造 Card"""
        from .agent_card import AgentCardMetadata
        metadata = AgentCardMetadata(
            version=data.get("metadata", {}).get("version", "1.0.0"),
            visibility=CardVisibility(data.get("metadata", {}).get("visibility", "public")),
            status=CardStatus(data.get("metadata", {}).get("status", "active")),
            tags=data.get("metadata", {}).get("tags", []),
            categories=data.get("metadata", {}).get("categories", []),
        )
        return AgentCardExtended(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            capabilities=data.get("capabilities", []),
            endpoint=data.get("endpoint", ""),
            metadata=metadata,
            protocols=data.get("protocols", ["a2a"]),
            auth_required=data.get("auth_required", False),
            auth_schemes=data.get("auth_schemes", []),
            avg_latency_ms=data.get("avg_latency_ms"),
            success_rate=data.get("success_rate"),
            total_calls=data.get("total_calls", 0),
        )
```

#### 3.1.5 集成到 A2A Gateway

```python
# 修改 src/aibridge/gateway/a2a_gateway.py

# 在 A2AGateway 类中添加以下方法：

async def publish_self(
    self,
    publisher: "CardPublisher",
    visibility: CardVisibility = CardVisibility.PUBLIC,
    tags: List[str] = None,
    categories: List[str] = None,
) -> PublishResult:
    """发布自身为可发现的 Agent"""
    from .agent_card import AgentCardExtended, AgentCardMetadata
    
    # 收集所有注册 Agent 的能力
    all_capabilities = []
    for agent in self._agents.values():
        all_capabilities.extend(agent.capabilities)
    
    card = AgentCardExtended(
        id=f"gateway-{id(self)}",
        name="AI-Bridge Gateway",
        description="MCP + A2A 双协议网关",
        capabilities=all_capabilities,
        endpoint=self._endpoint or "http://localhost:8000",
        metadata=AgentCardMetadata(
            visibility=visibility,
            tags=tags or ["gateway", "mcp", "a2a"],
            categories=categories or ["infrastructure"],
        ),
        protocols=["a2a", "mcp"],
    )
    
    return await publisher.publish(card)
```

#### 3.1.6 测试用例

```python
# tests/test_agent_card.py (新建)

import pytest
from aibridge.gateway.agent_card import (
    AgentCardExtended, AgentCardMetadata, CardVisibility, CardStatus
)
from aibridge.gateway.card_publisher import LocalCardPublisher
from aibridge.gateway.card_discovery import CardDiscovery, DiscoveryQuery


class TestAgentCard:
    """Agent Card 单元测试"""
    
    def test_card_creation(self):
        """测试 Card 创建"""
        card = AgentCardExtended(
            id="test-agent-1",
            name="Test Agent",
            description="A test agent",
            capabilities=[{"name": "echo", "description": "Echo input"}],
            endpoint="http://localhost:8001"
        )
        assert card.id == "test-agent-1"
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
        secret = "test-secret-key"
        card.sign(secret)
        assert card.metadata.signature is not None
        assert card.verify(secret)
        assert not card.verify("wrong-secret")


class TestCardPublisher:
    """Card Publisher 测试"""
    
    @pytest.mark.asyncio
    async def test_local_publish(self):
        """测试本地发布"""
        publisher = LocalCardPublisher()
        card = AgentCardExtended(
            id="local-agent",
            name="Local Agent",
            description="Test",
            capabilities=[],
            endpoint="http://localhost:8002"
        )
        result = await publisher.publish(card)
        assert result.success
        assert result.card_id == "local-agent"
    
    @pytest.mark.asyncio
    async def test_local_unpublish(self):
        """测试取消发布"""
        publisher = LocalCardPublisher()
        card = AgentCardExtended(
            id="to-remove",
            name="To Remove",
            description="Test",
            capabilities=[],
            endpoint="http://localhost:8003"
        )
        await publisher.publish(card)
        assert await publisher.unpublish("to-remove")
        assert not await publisher.unpublish("non-existent")


class TestCardDiscovery:
    """Card Discovery 测试"""
    
    @pytest.mark.asyncio
    async def test_local_discovery(self):
        """测试本地发现"""
        discovery = CardDiscovery()
        
        # 添加测试 Cards
        card1 = AgentCardExtended(
            id="agent-1",
            name="Code Assistant",
            description="Helps with coding",
            capabilities=[{"name": "code_review"}],
            endpoint="http://localhost:8001",
            metadata=AgentCardMetadata(tags=["coding", "assistant"]),
        )
        card2 = AgentCardExtended(
            id="agent-2",
            name="Data Analyst",
            description="Analyzes data",
            capabilities=[{"name": "analyze"}],
            endpoint="http://localhost:8002",
            metadata=AgentCardMetadata(tags=["data", "analysis"]),
        )
        
        discovery.add_local_card(card1)
        discovery.add_local_card(card2)
        
        # 测试关键词搜索
        query = DiscoveryQuery(keywords="coding")
        result = await discovery.discover_merged(query)
        assert result.total_count == 1
        assert result.cards[0].id == "agent-1"
        
        # 测试 tags 过滤
        query = DiscoveryQuery(tags=["data"])
        result = await discovery.discover_merged(query)
        assert result.total_count == 1
        assert result.cards[0].id == "agent-2"
    
    @pytest.mark.asyncio
    async def test_capability_filter(self):
        """测试能力过滤"""
        discovery = CardDiscovery()
        
        card = AgentCardExtended(
            id="agent-3",
            name="Multi-skill Agent",
            description="Has multiple skills",
            capabilities=[
                {"name": "translate"},
                {"name": "summarize"},
            ],
            endpoint="http://localhost:8003",
        )
        discovery.add_local_card(card)
        
        query = DiscoveryQuery(capabilities=["translate"])
        result = await discovery.discover_merged(query)
        assert result.total_count == 1
        
        query = DiscoveryQuery(capabilities=["non_existent"])
        result = await discovery.discover_merged(query)
        assert result.total_count == 0
```

---

### 3.2 Prometheus 指标导出

#### 3.2.1 背景与目标

企业级部署需要生产级可观测性，Prometheus 是事实标准。需要：

- 导出核心指标：请求量、延迟、错误率、资源使用
- 兼容现有 Metering 模块数据
- 支持自定义标签和维度

#### 3.2.2 核心实现

```python
# src/aibridge/enterprise/prometheus.py (新建)

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import time
import threading
import asyncio
from contextlib import contextmanager


class MetricType(str, Enum):
    """Prometheus 指标类型"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class MetricLabels:
    """指标标签"""
    labels: Dict[str, str] = field(default_factory=dict)
    
    def key(self) -> str:
        """生成标签键（用于存储）"""
        items = sorted(self.labels.items())
        return ",".join(f'{k}="{v}"' for k, v in items)


@dataclass
class CounterMetric:
    """计数器指标"""
    name: str
    help: str
    values: Dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def inc(self, labels: MetricLabels = None, value: float = 1.0) -> None:
        key = labels.key() if labels else ""
        with self._lock:
            self.values[key] = self.values.get(key, 0) + value
    
    def get(self, labels: MetricLabels = None) -> float:
        key = labels.key() if labels else ""
        return self.values.get(key, 0)


@dataclass
class GaugeMetric:
    """仪表盘指标"""
    name: str
    help: str
    values: Dict[str, float] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def set(self, value: float, labels: MetricLabels = None) -> None:
        key = labels.key() if labels else ""
        with self._lock:
            self.values[key] = value
    
    def inc(self, labels: MetricLabels = None, value: float = 1.0) -> None:
        key = labels.key() if labels else ""
        with self._lock:
            self.values[key] = self.values.get(key, 0) + value
    
    def dec(self, labels: MetricLabels = None, value: float = 1.0) -> None:
        key = labels.key() if labels else ""
        with self._lock:
            self.values[key] = self.values.get(key, 0) - value
    
    def get(self, labels: MetricLabels = None) -> float:
        key = labels.key() if labels else ""
        return self.values.get(key, 0)


@dataclass
class HistogramBucket:
    """直方图桶"""
    le: float  # less than or equal
    count: int = 0


@dataclass
class HistogramMetric:
    """直方图指标"""
    name: str
    help: str
    buckets: List[float] = field(default_factory=lambda: [
        0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
    ])
    values: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def observe(self, value: float, labels: MetricLabels = None) -> None:
        key = labels.key() if labels else ""
        with self._lock:
            if key not in self.values:
                self.values[key] = {
                    "buckets": {b: 0 for b in self.buckets},
                    "sum": 0.0,
                    "count": 0,
                }
            data = self.values[key]
            data["sum"] += value
            data["count"] += 1
            for bucket in self.buckets:
                if value <= bucket:
                    data["buckets"][bucket] += 1
    
    @contextmanager
    def time(self, labels: MetricLabels = None):
        """计时上下文管理器"""
        start = time.time()
        try:
            yield
        finally:
            self.observe(time.time() - start, labels)


class PrometheusRegistry:
    """Prometheus 指标注册中心"""
    
    def __init__(self, prefix: str = "aibridge"):
        self._prefix = prefix
        self._counters: Dict[str, CounterMetric] = {}
        self._gauges: Dict[str, GaugeMetric] = {}
        self._histograms: Dict[str, HistogramMetric] = {}
        self._lock = threading.Lock()
    
    def counter(self, name: str, help: str) -> CounterMetric:
        """获取或创建计数器"""
        full_name = f"{self._prefix}_{name}"
        with self._lock:
            if full_name not in self._counters:
                self._counters[full_name] = CounterMetric(
                    name=full_name, help=help
                )
            return self._counters[full_name]
    
    def gauge(self, name: str, help: str) -> GaugeMetric:
        """获取或创建仪表盘"""
        full_name = f"{self._prefix}_{name}"
        with self._lock:
            if full_name not in self._gauges:
                self._gauges[full_name] = GaugeMetric(
                    name=full_name, help=help
                )
            return self._gauges[full_name]
    
    def histogram(
        self, 
        name: str, 
        help: str, 
        buckets: List[float] = None
    ) -> HistogramMetric:
        """获取或创建直方图"""
        full_name = f"{self._prefix}_{name}"
        with self._lock:
            if full_name not in self._histograms:
                self._histograms[full_name] = HistogramMetric(
                    name=full_name,
                    help=help,
                    buckets=buckets or [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
                )
            return self._histograms[full_name]
    
    def export(self) -> str:
        """导出为 Prometheus 文本格式"""
        lines = []
        
        # 导出 Counters
        for name, metric in self._counters.items():
            lines.append(f"# HELP {name} {metric.help}")
            lines.append(f"# TYPE {name} counter")
            for labels_key, value in metric.values.items():
                if labels_key:
                    lines.append(f"{name}{{{labels_key}}} {value}")
                else:
                    lines.append(f"{name} {value}")
        
        # 导出 Gauges
        for name, metric in self._gauges.items():
            lines.append(f"# HELP {name} {metric.help}")
            lines.append(f"# TYPE {name} gauge")
            for labels_key, value in metric.values.items():
                if labels_key:
                    lines.append(f"{name}{{{labels_key}}} {value}")
                else:
                    lines.append(f"{name} {value}")
        
        # 导出 Histograms
        for name, metric in self._histograms.items():
            lines.append(f"# HELP {name} {metric.help}")
            lines.append(f"# TYPE {name} histogram")
            for labels_key, data in metric.values.items():
                base_labels = f"{{{labels_key}}}" if labels_key else ""
                # Buckets
                cumulative = 0
                for bucket, count in sorted(data["buckets"].items()):
                    cumulative += count
                    le_label = f'le="{bucket}"'
                    if labels_key:
                        lines.append(f'{name}_bucket{{{labels_key},{le_label}}} {cumulative}')
                    else:
                        lines.append(f'{name}_bucket{{{le_label}}} {cumulative}')
                # +Inf bucket
                if labels_key:
                    lines.append(f'{name}_bucket{{{labels_key},le="+Inf"}} {data["count"]}')
                else:
                    lines.append(f'{name}_bucket{{le="+Inf"}} {data["count"]}')
                # Sum and Count
                if labels_key:
                    lines.append(f'{name}_sum{{{labels_key}}} {data["sum"]}')
                    lines.append(f'{name}_count{{{labels_key}}} {data["count"]}')
                else:
                    lines.append(f'{name}_sum {data["sum"]}')
                    lines.append(f'{name}_count {data["count"]}')
        
        return "\n".join(lines)


# 全局 Registry 实例
_default_registry = PrometheusRegistry()


def get_registry() -> PrometheusRegistry:
    """获取默认 Registry"""
    return _default_registry


class AIBridgeMetrics:
    """AI-Bridge 标准指标集"""
    
    def __init__(self, registry: PrometheusRegistry = None):
        self._registry = registry or get_registry()
        
        # 请求指标
        self.requests_total = self._registry.counter(
            "requests_total",
            "Total number of requests"
        )
        self.requests_failed = self._registry.counter(
            "requests_failed_total",
            "Total number of failed requests"
        )
        
        # 延迟指标
        self.request_duration = self._registry.histogram(
            "request_duration_seconds",
            "Request duration in seconds",
            buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
        )
        
        # Agent 指标
        self.agents_registered = self._registry.gauge(
            "agents_registered",
            "Number of registered agents"
        )
        self.agent_tasks_active = self._registry.gauge(
            "agent_tasks_active",
            "Number of active agent tasks"
        )
        
        # MCP 指标
        self.mcp_servers_connected = self._registry.gauge(
            "mcp_servers_connected",
            "Number of connected MCP servers"
        )
        self.mcp_tool_calls = self._registry.counter(
            "mcp_tool_calls_total",
            "Total MCP tool calls"
        )
        
        # 企业级指标
        self.policy_evaluations = self._registry.counter(
            "policy_evaluations_total",
            "Total policy evaluations"
        )
        self.policy_denials = self._registry.counter(
            "policy_denials_total",
            "Total policy denials"
        )
        self.quota_exceeded = self._registry.counter(
            "quota_exceeded_total",
            "Total quota exceeded events"
        )
        
        # 资源指标
        self.memory_usage_bytes = self._registry.gauge(
            "memory_usage_bytes",
            "Memory usage in bytes"
        )
    
    def record_request(
        self,
        tool: str,
        server: str,
        success: bool,
        duration: float
    ) -> None:
        """记录请求"""
        labels = MetricLabels(labels={"tool": tool, "server": server})
        self.requests_total.inc(labels)
        if not success:
            self.requests_failed.inc(labels)
        self.request_duration.observe(duration, labels)
    
    def record_policy_evaluation(
        self,
        user: str,
        tool: str,
        allowed: bool
    ) -> None:
        """记录策略评估"""
        labels = MetricLabels(labels={"tool": tool})
        self.policy_evaluations.inc(labels)
        if not allowed:
            self.policy_denials.inc(labels)


class MetricsMiddleware:
    """指标收集中间件"""
    
    def __init__(self, metrics: AIBridgeMetrics = None):
        self._metrics = metrics or AIBridgeMetrics()
    
    async def __call__(
        self,
        handler: Callable,
        tool: str,
        server: str,
        *args,
        **kwargs
    ) -> Any:
        """包装处理函数，自动收集指标"""
        start_time = time.time()
        success = True
        try:
            return await handler(*args, **kwargs)
        except Exception:
            success = False
            raise
        finally:
            duration = time.time() - start_time
            self._metrics.record_request(tool, server, success, duration)


class MetricsExporter:
    """指标导出器"""
    
    def __init__(
        self,
        registry: PrometheusRegistry = None,
        port: int = 9090,
        path: str = "/metrics"
    ):
        self._registry = registry or get_registry()
        self._port = port
        self._path = path
        self._server = None
    
    async def start(self) -> None:
        """启动 HTTP 服务器"""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_get(self._path, self._handle_metrics)
        
        runner = web.AppRunner(app)
        await runner.setup()
        self._server = web.TCPSite(runner, "0.0.0.0", self._port)
        await self._server.start()
    
    async def stop(self) -> None:
        """停止服务器"""
        if self._server:
            await self._server.stop()
    
    async def _handle_metrics(self, request) -> "web.Response":
        """处理指标请求"""
        from aiohttp import web
        content = self._registry.export()
        return web.Response(
            text=content,
            content_type="text/plain; charset=utf-8"
        )
```

#### 3.2.3 与 Metering 模块集成

```python
# src/aibridge/enterprise/metering_prometheus.py (新建)

from typing import Optional
from .metering import MeteringCollector, UsageRecord
from .prometheus import PrometheusRegistry, MetricLabels, AIBridgeMetrics


class MeteringPrometheusAdapter:
    """Metering 到 Prometheus 的适配器"""
    
    def __init__(
        self,
        metering: MeteringCollector,
        registry: PrometheusRegistry = None
    ):
        self._metering = metering
        self._metrics = AIBridgeMetrics(registry)
        
        # 额外的 Metering 专用指标
        from .prometheus import get_registry
        reg = registry or get_registry()
        
        self.usage_cost = reg.counter(
            "metering_usage_cost_total",
            "Total usage cost"
        )
        self.usage_tokens = reg.counter(
            "metering_usage_tokens_total",
            "Total tokens consumed"
        )
        self.quota_usage_ratio = reg.gauge(
            "metering_quota_usage_ratio",
            "Current quota usage ratio (0-1)"
        )
    
    def sync_metrics(self) -> None:
        """从 Metering 同步指标到 Prometheus"""
        # 同步聚合数据
        aggregations = self._metering.get_aggregations()
        for agg in aggregations:
            labels = MetricLabels(labels={
                "user": agg.user_id or "unknown",
                "tool": agg.tool_name or "unknown",
                "server": agg.server_name or "unknown",
            })
            
            # 这里简化处理，实际应该增量更新
            # 成本和 token 应该是增量的，这里仅作示例
            pass
    
    def on_record(self, record: UsageRecord) -> None:
        """处理新的使用记录"""
        labels = MetricLabels(labels={
            "user": record.user_id,
            "tool": record.tool_name,
            "server": record.server_name,
        })
        
        self.usage_cost.inc(labels, record.cost)
        if record.tokens:
            self.usage_tokens.inc(labels, record.tokens)
        
        # 同步到核心指标
        self._metrics.record_request(
            tool=record.tool_name,
            server=record.server_name,
            success=record.success,
            duration=record.duration_ms / 1000.0
        )
```

#### 3.2.4 测试用例

```python
# tests/test_prometheus.py (新建)

import pytest
from aibridge.enterprise.prometheus import (
    PrometheusRegistry, CounterMetric, GaugeMetric, HistogramMetric,
    MetricLabels, AIBridgeMetrics, MetricsExporter
)


class TestPrometheusMetrics:
    """Prometheus 指标测试"""
    
    def test_counter(self):
        """测试计数器"""
        registry = PrometheusRegistry(prefix="test")
        counter = registry.counter("requests", "Total requests")
        
        counter.inc()
        counter.inc(value=5)
        
        assert counter.get() == 6
    
    def test_counter_with_labels(self):
        """测试带标签的计数器"""
        registry = PrometheusRegistry(prefix="test")
        counter = registry.counter("requests", "Total requests")
        
        labels1 = MetricLabels(labels={"method": "GET", "path": "/api"})
        labels2 = MetricLabels(labels={"method": "POST", "path": "/api"})
        
        counter.inc(labels1)
        counter.inc(labels1)
        counter.inc(labels2)
        
        assert counter.get(labels1) == 2
        assert counter.get(labels2) == 1
    
    def test_gauge(self):
        """测试仪表盘"""
        registry = PrometheusRegistry(prefix="test")
        gauge = registry.gauge("connections", "Active connections")
        
        gauge.set(10)
        assert gauge.get() == 10
        
        gauge.inc()
        assert gauge.get() == 11
        
        gauge.dec(value=3)
        assert gauge.get() == 8
    
    def test_histogram(self):
        """测试直方图"""
        registry = PrometheusRegistry(prefix="test")
        histogram = registry.histogram(
            "latency",
            "Request latency",
            buckets=[0.1, 0.5, 1.0, 5.0]
        )
        
        histogram.observe(0.05)
        histogram.observe(0.3)
        histogram.observe(0.8)
        histogram.observe(2.0)
        
        data = histogram.values.get("", {})
        assert data["count"] == 4
        assert abs(data["sum"] - 3.15) < 0.01
    
    def test_histogram_time_context(self):
        """测试直方图计时上下文"""
        import time
        registry = PrometheusRegistry(prefix="test")
        histogram = registry.histogram("duration", "Duration")
        
        with histogram.time():
            time.sleep(0.01)
        
        data = histogram.values.get("", {})
        assert data["count"] == 1
        assert data["sum"] >= 0.01
    
    def test_export_format(self):
        """测试导出格式"""
        registry = PrometheusRegistry(prefix="test")
        
        counter = registry.counter("requests_total", "Total requests")
        counter.inc()
        
        gauge = registry.gauge("temperature", "Current temperature")
        gauge.set(25.5)
        
        output = registry.export()
        
        assert "# HELP test_requests_total Total requests" in output
        assert "# TYPE test_requests_total counter" in output
        assert "test_requests_total 1" in output
        assert "test_temperature 25.5" in output


class TestAIBridgeMetrics:
    """AI-Bridge 标准指标测试"""
    
    def test_record_request(self):
        """测试请求记录"""
        registry = PrometheusRegistry(prefix="test")
        metrics = AIBridgeMetrics(registry)
        
        metrics.record_request(
            tool="browser.navigate",
            server="chrome",
            success=True,
            duration=0.5
        )
        
        labels = MetricLabels(labels={"tool": "browser.navigate", "server": "chrome"})
        assert metrics.requests_total.get(labels) == 1
        assert metrics.requests_failed.get(labels) == 0
    
    def test_record_failed_request(self):
        """测试失败请求记录"""
        registry = PrometheusRegistry(prefix="test")
        metrics = AIBridgeMetrics(registry)
        
        metrics.record_request(
            tool="browser.click",
            server="chrome",
            success=False,
            duration=1.0
        )
        
        labels = MetricLabels(labels={"tool": "browser.click", "server": "chrome"})
        assert metrics.requests_failed.get(labels) == 1
    
    def test_policy_evaluation(self):
        """测试策略评估记录"""
        registry = PrometheusRegistry(prefix="test")
        metrics = AIBridgeMetrics(registry)
        
        metrics.record_policy_evaluation("user1", "tool1", allowed=True)
        metrics.record_policy_evaluation("user1", "tool1", allowed=False)
        
        labels = MetricLabels(labels={"tool": "tool1"})
        assert metrics.policy_evaluations.get(labels) == 2
        assert metrics.policy_denials.get(labels) == 1
```

---

## 四、Phase 2（P1）详细规范

### 4.1 Agent Registry 注册中心

#### 4.1.1 目标

构建独立的 Agent 注册中心服务，支持：

- Agent 注册与注销
- 健康检查与状态管理
- 服务发现 API
- 负载均衡（按性能指标）

#### 4.1.2 核心设计

```python
# src/aibridge/registry/agent_registry.py (新建)

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
import asyncio
import aiohttp
from enum import Enum


class AgentHealth(str, Enum):
    """Agent 健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class RegisteredAgent:
    """注册的 Agent"""
    card: "AgentCardExtended"
    health: AgentHealth = AgentHealth.UNKNOWN
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    consecutive_failures: int = 0
    registered_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RegistryConfig:
    """Registry 配置"""
    heartbeat_interval: float = 30.0       # 心跳间隔（秒）
    heartbeat_timeout: float = 90.0        # 心跳超时（秒）
    health_check_interval: float = 60.0    # 健康检查间隔
    max_consecutive_failures: int = 3      # 最大连续失败次数
    cleanup_interval: float = 300.0        # 清理间隔


class AgentRegistry:
    """Agent 注册中心"""
    
    def __init__(self, config: RegistryConfig = None):
        self._config = config or RegistryConfig()
        self._agents: Dict[str, RegisteredAgent] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._tasks: List[asyncio.Task] = []
    
    async def start(self) -> None:
        """启动 Registry"""
        self._running = True
        self._tasks = [
            asyncio.create_task(self._heartbeat_checker()),
            asyncio.create_task(self._health_checker()),
            asyncio.create_task(self._cleanup_task()),
        ]
    
    async def stop(self) -> None:
        """停止 Registry"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
    
    async def register(self, card: "AgentCardExtended") -> bool:
        """注册 Agent"""
        async with self._lock:
            self._agents[card.id] = RegisteredAgent(card=card)
        return True
    
    async def unregister(self, agent_id: str) -> bool:
        """注销 Agent"""
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                return True
        return False
    
    async def heartbeat(self, agent_id: str) -> bool:
        """接收心跳"""
        async with self._lock:
            if agent_id in self._agents:
                agent = self._agents[agent_id]
                agent.last_heartbeat = datetime.utcnow()
                agent.consecutive_failures = 0
                if agent.health == AgentHealth.UNHEALTHY:
                    agent.health = AgentHealth.HEALTHY
                return True
        return False
    
    async def get_agent(self, agent_id: str) -> Optional[RegisteredAgent]:
        """获取 Agent"""
        return self._agents.get(agent_id)
    
    async def list_agents(
        self,
        health: Optional[AgentHealth] = None,
        capabilities: Optional[List[str]] = None,
    ) -> List[RegisteredAgent]:
        """列出 Agents"""
        agents = list(self._agents.values())
        
        if health:
            agents = [a for a in agents if a.health == health]
        
        if capabilities:
            def has_caps(agent: RegisteredAgent) -> bool:
                agent_caps = {c["name"] for c in agent.card.capabilities}
                return any(cap in agent_caps for cap in capabilities)
            agents = [a for a in agents if has_caps(a)]
        
        return agents
    
    async def select_agent(
        self,
        capability: str,
        strategy: str = "round_robin"
    ) -> Optional[RegisteredAgent]:
        """选择 Agent（负载均衡）"""
        candidates = await self.list_agents(
            health=AgentHealth.HEALTHY,
            capabilities=[capability]
        )
        
        if not candidates:
            # 降级：尝试 DEGRADED 状态的
            candidates = await self.list_agents(
                health=AgentHealth.DEGRADED,
                capabilities=[capability]
            )
        
        if not candidates:
            return None
        
        if strategy == "round_robin":
            # 简单轮询：按调用次数最少
            return min(candidates, key=lambda a: a.card.total_calls)
        elif strategy == "latency":
            # 延迟优先
            return min(
                candidates,
                key=lambda a: a.card.avg_latency_ms or float('inf')
            )
        elif strategy == "success_rate":
            # 成功率优先
            return max(
                candidates,
                key=lambda a: a.card.success_rate or 0
            )
        else:
            return candidates[0]
    
    async def _heartbeat_checker(self) -> None:
        """心跳检查任务"""
        while self._running:
            await asyncio.sleep(self._config.heartbeat_interval)
            
            now = datetime.utcnow()
            timeout = timedelta(seconds=self._config.heartbeat_timeout)
            
            async with self._lock:
                for agent in self._agents.values():
                    if now - agent.last_heartbeat > timeout:
                        agent.health = AgentHealth.UNHEALTHY
    
    async def _health_checker(self) -> None:
        """健康检查任务"""
        while self._running:
            await asyncio.sleep(self._config.health_check_interval)
            
            for agent_id, agent in list(self._agents.items()):
                healthy = await self._check_agent_health(agent)
                async with self._lock:
                    if agent_id in self._agents:
                        if healthy:
                            self._agents[agent_id].health = AgentHealth.HEALTHY
                            self._agents[agent_id].consecutive_failures = 0
                        else:
                            self._agents[agent_id].consecutive_failures += 1
                            if self._agents[agent_id].consecutive_failures >= self._config.max_consecutive_failures:
                                self._agents[agent_id].health = AgentHealth.UNHEALTHY
                            else:
                                self._agents[agent_id].health = AgentHealth.DEGRADED
    
    async def _check_agent_health(self, agent: RegisteredAgent) -> bool:
        """检查单个 Agent 健康"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{agent.card.endpoint.rstrip('/')}/health"
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    async def _cleanup_task(self) -> None:
        """清理不健康的 Agent"""
        while self._running:
            await asyncio.sleep(self._config.cleanup_interval)
            
            to_remove = []
            async with self._lock:
                for agent_id, agent in self._agents.items():
                    if agent.health == AgentHealth.UNHEALTHY:
                        # 超过最大失败次数的标记删除
                        if agent.consecutive_failures > self._config.max_consecutive_failures * 2:
                            to_remove.append(agent_id)
            
            for agent_id in to_remove:
                await self.unregister(agent_id)
```

### 4.2 A2A Streaming 支持

#### 4.2.1 目标

实现 A2A 任务执行的实时流式反馈：

- Server-Sent Events (SSE) 支持
- WebSocket 支持
- 任务状态实时推送
- 中间结果流式返回

#### 4.2.2 核心设计

```python
# src/aibridge/gateway/a2a_streaming.py (新建)

from dataclasses import dataclass, field
from typing import AsyncIterator, Dict, Any, Optional, Callable
from enum import Enum
import asyncio
import json
from datetime import datetime


class StreamEventType(str, Enum):
    """流事件类型"""
    TASK_CREATED = "task.created"
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_OUTPUT = "task.output"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    HEARTBEAT = "heartbeat"


@dataclass
class StreamEvent:
    """流事件"""
    event_type: StreamEventType
    task_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    sequence: int = 0
    
    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        event_data = {
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
            **self.data
        }
        return f"event: {self.event_type.value}\ndata: {json.dumps(event_data)}\n\n"
    
    def to_json(self) -> str:
        """转换为 JSON 格式（WebSocket）"""
        return json.dumps({
            "event": self.event_type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
            "data": self.data
        })


class TaskStreamManager:
    """任务流管理器"""
    
    def __init__(self, heartbeat_interval: float = 15.0):
        self._streams: Dict[str, asyncio.Queue] = {}
        self._sequences: Dict[str, int] = {}
        self._heartbeat_interval = heartbeat_interval
        self._lock = asyncio.Lock()
    
    async def create_stream(self, task_id: str) -> asyncio.Queue:
        """创建任务流"""
        async with self._lock:
            if task_id not in self._streams:
                self._streams[task_id] = asyncio.Queue()
                self._sequences[task_id] = 0
            return self._streams[task_id]
    
    async def close_stream(self, task_id: str) -> None:
        """关闭任务流"""
        async with self._lock:
            if task_id in self._streams:
                del self._streams[task_id]
                del self._sequences[task_id]
    
    async def emit(
        self,
        task_id: str,
        event_type: StreamEventType,
        data: Dict[str, Any] = None
    ) -> None:
        """发送事件"""
        async with self._lock:
            if task_id not in self._streams:
                return
            
            self._sequences[task_id] += 1
            event = StreamEvent(
                event_type=event_type,
                task_id=task_id,
                data=data or {},
                sequence=self._sequences[task_id]
            )
            await self._streams[task_id].put(event)
    
    async def subscribe(
        self,
        task_id: str,
        timeout: float = None
    ) -> AsyncIterator[StreamEvent]:
        """订阅任务流"""
        queue = await self.create_stream(task_id)
        
        try:
            while True:
                try:
                    event = await asyncio.wait_for(
                        queue.get(),
                        timeout=timeout or self._heartbeat_interval
                    )
                    yield event
                    
                    # 终止事件
                    if event.event_type in (
                        StreamEventType.TASK_COMPLETED,
                        StreamEventType.TASK_FAILED,
                        StreamEventType.TASK_CANCELLED
                    ):
                        break
                except asyncio.TimeoutError:
                    # 发送心跳
                    yield StreamEvent(
                        event_type=StreamEventType.HEARTBEAT,
                        task_id=task_id
                    )
        finally:
            await self.close_stream(task_id)


class StreamingA2AHandler:
    """流式 A2A 处理器"""
    
    def __init__(self, stream_manager: TaskStreamManager = None):
        self._stream_manager = stream_manager or TaskStreamManager()
    
    async def handle_sse(
        self,
        task_id: str,
        request: Any  # aiohttp Request
    ) -> Any:  # aiohttp StreamResponse
        """处理 SSE 请求"""
        from aiohttp import web
        
        response = web.StreamResponse(
            status=200,
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        await response.prepare(request)
        
        async for event in self._stream_manager.subscribe(task_id):
            await response.write(event.to_sse().encode())
        
        return response
    
    async def handle_websocket(
        self,
        task_id: str,
        ws: Any  # aiohttp WebSocketResponse
    ) -> None:
        """处理 WebSocket 连接"""
        async for event in self._stream_manager.subscribe(task_id):
            await ws.send_str(event.to_json())
    
    @property
    def stream_manager(self) -> TaskStreamManager:
        return self._stream_manager
```

---

## 五、Phase 3（P2）详细规范

### 5.1 Audit Log 持久化

#### 5.1.1 目标

将审计日志持久化到外部存储：

- 支持多种存储后端（文件、数据库、云存储）
- 结构化日志格式
- 日志轮转与归档
- 合规查询接口

#### 5.1.2 核心设计

```python
# src/aibridge/enterprise/audit_storage.py (新建)

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any, AsyncIterator
from datetime import datetime, timedelta
from pathlib import Path
import json
import asyncio
import aiofiles


@dataclass
class AuditQuery:
    """审计查询条件"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    user_id: Optional[str] = None
    action: Optional[str] = None
    resource: Optional[str] = None
    success: Optional[bool] = None
    limit: int = 100
    offset: int = 0


class AuditStorage(ABC):
    """审计存储抽象基类"""
    
    @abstractmethod
    async def write(self, event: "AuditEvent") -> bool:
        """写入审计事件"""
        pass
    
    @abstractmethod
    async def query(self, query: AuditQuery) -> List["AuditEvent"]:
        """查询审计事件"""
        pass
    
    @abstractmethod
    async def count(self, query: AuditQuery) -> int:
        """统计事件数量"""
        pass


class FileAuditStorage(AuditStorage):
    """文件审计存储"""
    
    def __init__(
        self,
        base_path: str = "./audit_logs",
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        retention_days: int = 90
    ):
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
        self._max_file_size = max_file_size
        self._retention_days = retention_days
        self._current_file: Optional[Path] = None
        self._lock = asyncio.Lock()
    
    async def write(self, event: "AuditEvent") -> bool:
        async with self._lock:
            file_path = self._get_current_file()
            try:
                async with aiofiles.open(file_path, "a") as f:
                    await f.write(json.dumps(self._event_to_dict(event)) + "\n")
                return True
            except Exception:
                return False
    
    async def query(self, query: AuditQuery) -> List["AuditEvent"]:
        results = []
        for file_path in self._get_relevant_files(query):
            async for event in self._read_file(file_path):
                if self._match_query(event, query):
                    results.append(event)
                    if len(results) >= query.limit + query.offset:
                        break
        return results[query.offset:query.offset + query.limit]
    
    async def count(self, query: AuditQuery) -> int:
        count = 0
        for file_path in self._get_relevant_files(query):
            async for event in self._read_file(file_path):
                if self._match_query(event, query):
                    count += 1
        return count
    
    def _get_current_file(self) -> Path:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self._base_path / f"audit-{today}.jsonl"
    
    def _get_relevant_files(self, query: AuditQuery) -> List[Path]:
        files = sorted(self._base_path.glob("audit-*.jsonl"), reverse=True)
        # 可以根据 query 的时间范围过滤
        return files
    
    async def _read_file(self, file_path: Path) -> AsyncIterator["AuditEvent"]:
        try:
            async with aiofiles.open(file_path, "r") as f:
                async for line in f:
                    if line.strip():
                        yield self._dict_to_event(json.loads(line))
        except FileNotFoundError:
            pass
    
    def _match_query(self, event: "AuditEvent", query: AuditQuery) -> bool:
        if query.start_time and event.timestamp < query.start_time:
            return False
        if query.end_time and event.timestamp > query.end_time:
            return False
        if query.user_id and event.user_id != query.user_id:
            return False
        if query.action and event.action.value != query.action:
            return False
        if query.success is not None and event.success != query.success:
            return False
        return True
    
    @staticmethod
    def _event_to_dict(event: "AuditEvent") -> Dict[str, Any]:
        return {
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "action": event.action.value,
            "resource": event.resource,
            "success": event.success,
            "details": event.details,
            "ip_address": event.ip_address,
            "trace_id": event.trace_id,
        }
    
    @staticmethod
    def _dict_to_event(data: Dict[str, Any]) -> "AuditEvent":
        from .audit import AuditEvent, AuditAction
        return AuditEvent(
            timestamp=datetime.fromisoformat(data["timestamp"]),
            user_id=data["user_id"],
            action=AuditAction(data["action"]),
            resource=data.get("resource"),
            success=data.get("success", True),
            details=data.get("details", {}),
            ip_address=data.get("ip_address"),
            trace_id=data.get("trace_id"),
        )
```

### 5.2 MCP Server 动态发现

#### 5.2.1 目标

支持运行时动态发现和加载 MCP Server：

- 配置文件热重载
- 服务发现协议
- 健康检查与自动重连
- 无需重启即可扩展

#### 5.2.2 核心设计

```python
# src/aibridge/gateway/dynamic_discovery.py (新建)

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Awaitable
from pathlib import Path
import asyncio
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import aiohttp


@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    name: str
    endpoint: str
    enabled: bool = True
    auth: Optional[Dict[str, str]] = None
    timeout: float = 30.0
    retry_attempts: int = 3
    tags: List[str] = field(default_factory=list)


class ConfigFileWatcher(FileSystemEventHandler):
    """配置文件监控"""
    
    def __init__(self, callback: Callable[[], Awaitable[None]]):
        self._callback = callback
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
    
    def on_modified(self, event):
        if not event.is_directory and self._loop:
            asyncio.run_coroutine_threadsafe(self._callback(), self._loop)


class DynamicMCPDiscovery:
    """MCP Server 动态发现"""
    
    def __init__(
        self,
        config_path: str = "./mcp_servers.json",
        discovery_interval: float = 60.0
    ):
        self._config_path = Path(config_path)
        self._discovery_interval = discovery_interval
        self._servers: Dict[str, MCPServerConfig] = {}
        self._healthy: Dict[str, bool] = {}
        self._callbacks: List[Callable[[str, MCPServerConfig, str], Awaitable[None]]] = []
        self._running = False
        self._observer: Optional[Observer] = None
        self._lock = asyncio.Lock()
    
    def on_change(
        self,
        callback: Callable[[str, MCPServerConfig, str], Awaitable[None]]
    ) -> None:
        """注册变更回调
        
        callback(server_name, config, event_type)
        event_type: "added", "removed", "updated"
        """
        self._callbacks.append(callback)
    
    async def start(self) -> None:
        """启动动态发现"""
        self._running = True
        
        # 初始加载
        await self._load_config()
        
        # 启动文件监控
        self._start_file_watcher()
        
        # 启动健康检查
        asyncio.create_task(self._health_check_loop())
    
    async def stop(self) -> None:
        """停止动态发现"""
        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
    
    async def _load_config(self) -> None:
        """加载配置文件"""
        if not self._config_path.exists():
            return
        
        try:
            with open(self._config_path, "r") as f:
                data = json.load(f)
        except Exception:
            return
        
        new_servers = {}
        for item in data.get("servers", []):
            config = MCPServerConfig(
                name=item["name"],
                endpoint=item["endpoint"],
                enabled=item.get("enabled", True),
                auth=item.get("auth"),
                timeout=item.get("timeout", 30.0),
                retry_attempts=item.get("retry_attempts", 3),
                tags=item.get("tags", []),
            )
            new_servers[config.name] = config
        
        await self._reconcile(new_servers)
    
    async def _reconcile(self, new_servers: Dict[str, MCPServerConfig]) -> None:
        """协调配置变更"""
        async with self._lock:
            old_names = set(self._servers.keys())
            new_names = set(new_servers.keys())
            
            # 新增的
            for name in new_names - old_names:
                self._servers[name] = new_servers[name]
                await self._notify("added", name, new_servers[name])
            
            # 删除的
            for name in old_names - new_names:
                config = self._servers.pop(name)
                self._healthy.pop(name, None)
                await self._notify("removed", name, config)
            
            # 更新的
            for name in old_names & new_names:
                if self._config_changed(self._servers[name], new_servers[name]):
                    self._servers[name] = new_servers[name]
                    await self._notify("updated", name, new_servers[name])
    
    def _config_changed(self, old: MCPServerConfig, new: MCPServerConfig) -> bool:
        """检查配置是否变更"""
        return (
            old.endpoint != new.endpoint or
            old.enabled != new.enabled or
            old.auth != new.auth or
            old.timeout != new.timeout
        )
    
    async def _notify(
        self,
        event_type: str,
        name: str,
        config: MCPServerConfig
    ) -> None:
        """通知变更"""
        for callback in self._callbacks:
            try:
                await callback(name, config, event_type)
            except Exception:
                pass
    
    def _start_file_watcher(self) -> None:
        """启动文件监控"""
        watcher = ConfigFileWatcher(self._load_config)
        watcher.set_loop(asyncio.get_event_loop())
        
        self._observer = Observer()
        self._observer.schedule(
            watcher,
            str(self._config_path.parent),
            recursive=False
        )
        self._observer.start()
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self._running:
            await asyncio.sleep(self._discovery_interval)
            
            for name, config in list(self._servers.items()):
                if not config.enabled:
                    continue
                
                healthy = await self._check_health(config)
                old_healthy = self._healthy.get(name)
                self._healthy[name] = healthy
                
                # 健康状态变更
                if old_healthy is not None and old_healthy != healthy:
                    event_type = "healthy" if healthy else "unhealthy"
                    await self._notify(event_type, name, config)
    
    async def _check_health(self, config: MCPServerConfig) -> bool:
        """检查服务器健康"""
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{config.endpoint.rstrip('/')}/health"
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=5.0)
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    def get_servers(self, tags: List[str] = None) -> List[MCPServerConfig]:
        """获取服务器列表"""
        servers = [s for s in self._servers.values() if s.enabled]
        if tags:
            servers = [
                s for s in servers
                if any(t in s.tags for t in tags)
            ]
        return servers
    
    def is_healthy(self, name: str) -> bool:
        """检查服务器是否健康"""
        return self._healthy.get(name, False)
```

---

## 六、交付物清单

### Phase 1（P0）

| 文件 | 类型 | 说明 |
|------|------|------|
| `src/aibridge/gateway/agent_card.py` | 新建 | Agent Card 扩展数据结构 |
| `src/aibridge/gateway/card_publisher.py` | 新建 | Card 发布器 |
| `src/aibridge/gateway/card_discovery.py` | 新建 | Card 发现服务 |
| `src/aibridge/enterprise/prometheus.py` | 新建 | Prometheus 指标模块 |
| `src/aibridge/enterprise/metering_prometheus.py` | 新建 | Metering-Prometheus 适配 |
| `tests/test_agent_card.py` | 新建 | Agent Card 测试 |
| `tests/test_prometheus.py` | 新建 | Prometheus 测试 |

### Phase 2（P1）

| 文件 | 类型 | 说明 |
|------|------|------|
| `src/aibridge/registry/agent_registry.py` | 新建 | Agent 注册中心 |
| `src/aibridge/registry/__init__.py` | 新建 | 模块入口 |
| `src/aibridge/gateway/a2a_streaming.py` | 新建 | A2A Streaming 支持 |
| `tests/test_agent_registry.py` | 新建 | Registry 测试 |
| `tests/test_a2a_streaming.py` | 新建 | Streaming 测试 |

### Phase 3（P2）

| 文件 | 类型 | 说明 |
|------|------|------|
| `src/aibridge/enterprise/audit_storage.py` | 新建 | 审计日志持久化 |
| `src/aibridge/gateway/dynamic_discovery.py` | 新建 | MCP 动态发现 |
| `tests/test_audit_storage.py` | 新建 | 审计存储测试 |
| `tests/test_dynamic_discovery.py` | 新建 | 动态发现测试 |

---

## 七、验收标准

### 功能验收

- [ ] Agent Card 可发布到本地/远程 Registry
- [ ] Agent Card 可按多维度发现和搜索
- [ ] Prometheus `/metrics` 端点返回标准格式
- [ ] 所有核心指标正确采集
- [ ] Agent Registry 支持注册、注销、心跳
- [ ] A2A 任务支持 SSE/WebSocket 流式反馈
- [ ] 审计日志可持久化到文件
- [ ] MCP Server 配置热重载生效

### 测试覆盖

- [ ] 单元测试覆盖率 > 80%
- [ ] 集成测试覆盖核心流程
- [ ] 压力测试验证性能

### 文档要求

- [ ] API 文档更新
- [ ] 配置说明更新
- [ ] CHANGELOG 更新

---

## 八、时间规划

| 阶段 | 开始 | 结束 | 里程碑 |
|------|------|------|--------|
| Phase 1 | Week 1 | Week 2 | Agent Card + Prometheus |
| Phase 2 | Week 3 | Week 4 | Registry + Streaming |
| Phase 3 | Week 5 | Week 6 | Audit + Discovery |
| 集成测试 | Week 7 | Week 7 | 全量验收 |
| 发布 | Week 8 | Week 8 | v5.0 Release |

---

**文档版本**: 1.0
**最后更新**: 2026-03-15
**维护者**: AI-Bridge Team
