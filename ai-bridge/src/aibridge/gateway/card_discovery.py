"""
Card 发现服务

提供 Agent Card 的发现功能，支持：
- 本地搜索
- 远程 Registry 搜索
- 多维度过滤（关键词、标签、分类、能力、协议）
- 多种排序方式（相关性、延迟、成功率、使用量）
- 结果合并与去重
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, AsyncIterator
from enum import Enum
import asyncio
import time
import logging

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

from .agent_card import (
    AgentCardExtended,
    AgentCardMetadata,
    AgentCapability,
    CardVisibility,
    CardStatus
)

logger = logging.getLogger(__name__)


class DiscoverySortBy(str, Enum):
    """发现排序方式"""
    RELEVANCE = "relevance"      # 相关性（综合评分）
    LATENCY = "latency"          # 响应时间
    SUCCESS_RATE = "success_rate"  # 成功率
    POPULARITY = "popularity"    # 使用量
    CREATED_AT = "created_at"    # 创建时间
    NAME = "name"                # 名称


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
    sort_desc: bool = True  # 降序
    limit: int = 50
    offset: int = 0
    
    def to_params(self) -> Dict[str, Any]:
        """转换为 HTTP 查询参数"""
        params: Dict[str, Any] = {
            "limit": self.limit,
            "offset": self.offset,
            "sort_by": self.sort_by.value,
            "sort_desc": self.sort_desc,
            "status": self.status.value,
        }
        if self.keywords:
            params["q"] = self.keywords
        if self.tags:
            params["tags"] = ",".join(self.tags)
        if self.categories:
            params["categories"] = ",".join(self.categories)
        if self.capabilities:
            params["capabilities"] = ",".join(self.capabilities)
        if self.protocols:
            params["protocols"] = ",".join(self.protocols)
        if self.min_success_rate is not None:
            params["min_success_rate"] = self.min_success_rate
        if self.max_latency_ms is not None:
            params["max_latency_ms"] = self.max_latency_ms
        if self.visibility:
            params["visibility"] = self.visibility.value
        return params


@dataclass
class DiscoveryResult:
    """发现结果"""
    cards: List[AgentCardExtended]
    total_count: int
    query_time_ms: float
    source: str  # 来源 Registry
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cards": [c.to_dict() for c in self.cards],
            "total_count": self.total_count,
            "query_time_ms": self.query_time_ms,
            "source": self.source,
        }


class CardDiscovery:
    """Agent Card 发现服务
    
    支持本地搜索和远程 Registry 搜索
    """
    
    def __init__(
        self,
        cache_ttl: float = 60.0,
        max_cache_size: int = 1000,
        remote_timeout: float = 10.0
    ):
        """
        Args:
            cache_ttl: 缓存 TTL（秒）
            max_cache_size: 最大缓存数量
            remote_timeout: 远程请求超时
        """
        self._local_cards: Dict[str, AgentCardExtended] = {}
        self._remote_registries: List[str] = []
        self._cache: Dict[str, tuple[float, DiscoveryResult]] = {}
        self._cache_ttl = cache_ttl
        self._max_cache_size = max_cache_size
        self._remote_timeout = remote_timeout
        self._lock = asyncio.Lock()
    
    # ========== 本地 Card 管理 ==========
    
    def add_local_card(self, card: AgentCardExtended) -> None:
        """添加本地 Card"""
        self._local_cards[card.id] = card
        logger.debug(f"Added local card: {card.id}")
    
    def remove_local_card(self, card_id: str) -> bool:
        """移除本地 Card"""
        if card_id in self._local_cards:
            del self._local_cards[card_id]
            logger.debug(f"Removed local card: {card_id}")
            return True
        return False
    
    def get_local_card(self, card_id: str) -> Optional[AgentCardExtended]:
        """获取本地 Card"""
        return self._local_cards.get(card_id)
    
    def list_local_cards(self) -> List[AgentCardExtended]:
        """列出所有本地 Cards"""
        return list(self._local_cards.values())
    
    # ========== Remote Registry 管理 ==========
    
    def add_registry(self, registry_url: str) -> None:
        """添加远程 Registry"""
        url = registry_url.rstrip("/")
        if url not in self._remote_registries:
            self._remote_registries.append(url)
            logger.info(f"Added remote registry: {url}")
    
    def remove_registry(self, registry_url: str) -> bool:
        """移除远程 Registry"""
        url = registry_url.rstrip("/")
        if url in self._remote_registries:
            self._remote_registries.remove(url)
            logger.info(f"Removed remote registry: {url}")
            return True
        return False
    
    def list_registries(self) -> List[str]:
        """列出所有远程 Registries"""
        return list(self._remote_registries)
    
    # ========== 发现功能 ==========
    
    async def discover(self, query: DiscoveryQuery) -> List[DiscoveryResult]:
        """执行发现查询
        
        Args:
            query: 查询条件
            
        Returns:
            各来源的查询结果列表
        """
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
                elif isinstance(result, Exception):
                    logger.warning(f"Remote discovery failed: {result}")
        
        return results
    
    async def discover_merged(self, query: DiscoveryQuery) -> DiscoveryResult:
        """执行发现查询并合并结果
        
        Args:
            query: 查询条件
            
        Returns:
            合并后的查询结果
        """
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
                    # 保留成功率更高的版本
                    if (card.success_rate or 0) > (existing.success_rate or 0):
                        merged_cards[card.id] = card
        
        # 排序
        cards = list(merged_cards.values())
        cards = self._sort_cards(cards, query.sort_by, query.sort_desc)
        
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
    
    async def discover_by_capability(
        self,
        capability_name: str,
        min_success_rate: float = 0.0
    ) -> List[AgentCardExtended]:
        """按能力名称发现 Agent
        
        Args:
            capability_name: 能力名称
            min_success_rate: 最小成功率
            
        Returns:
            匹配的 Agent 列表
        """
        query = DiscoveryQuery(
            capabilities=[capability_name],
            min_success_rate=min_success_rate if min_success_rate > 0 else None,
            sort_by=DiscoverySortBy.SUCCESS_RATE,
        )
        result = await self.discover_merged(query)
        return result.cards
    
    async def find_best_agent(
        self,
        capability_name: str,
        prefer_low_latency: bool = False
    ) -> Optional[AgentCardExtended]:
        """找到最佳 Agent
        
        Args:
            capability_name: 能力名称
            prefer_low_latency: 是否优先选择低延迟
            
        Returns:
            最佳 Agent 或 None
        """
        sort_by = DiscoverySortBy.LATENCY if prefer_low_latency else DiscoverySortBy.SUCCESS_RATE
        query = DiscoveryQuery(
            capabilities=[capability_name],
            sort_by=sort_by,
            limit=1,
        )
        result = await self.discover_merged(query)
        return result.cards[0] if result.cards else None
    
    # ========== 内部方法 ==========
    
    async def _discover_local(self, query: DiscoveryQuery) -> DiscoveryResult:
        """本地搜索"""
        start_time = time.time()
        
        matched = []
        for card in self._local_cards.values():
            if self._match_query(card, query):
                matched.append(card)
        
        matched = self._sort_cards(matched, query.sort_by, query.sort_desc)
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
        if not HAS_AIOHTTP:
            return DiscoveryResult(
                cards=[],
                total_count=0,
                query_time_ms=0,
                source=registry_url
            )
        
        # 检查缓存
        cache_key = f"{registry_url}:{hash(str(query.to_params()))}"
        cached = self._get_cached(cache_key)
        if cached:
            return cached
        
        start_time = time.time()
        url = f"{registry_url}/agents/discover"
        params = query.to_params()
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self._remote_timeout)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        cards = [
                            AgentCardExtended.from_dict(item)
                            for item in data.get("cards", [])
                        ]
                        query_time = (time.time() - start_time) * 1000
                        
                        result = DiscoveryResult(
                            cards=cards,
                            total_count=data.get("total", len(cards)),
                            query_time_ms=query_time,
                            source=registry_url
                        )
                        
                        # 缓存结果
                        self._set_cached(cache_key, result)
                        
                        return result
                    else:
                        logger.warning(f"Remote discovery failed: {registry_url} returned {resp.status}")
        except Exception as e:
            logger.warning(f"Remote discovery failed: {registry_url}: {e}")
        
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
            keywords_lower = query.keywords.lower()
            searchable = f"{card.name} {card.description}".lower()
            # 支持空格分隔的多关键词
            for keyword in keywords_lower.split():
                if keyword not in searchable:
                    return False
        
        # Tags 过滤（任一匹配）
        if query.tags:
            card_tags_lower = [t.lower() for t in card.metadata.tags]
            if not any(tag.lower() in card_tags_lower for tag in query.tags):
                return False
        
        # Categories 过滤（任一匹配）
        if query.categories:
            card_cats_lower = [c.lower() for c in card.metadata.categories]
            if not any(cat.lower() in card_cats_lower for cat in query.categories):
                return False
        
        # Capabilities 过滤（任一匹配）
        if query.capabilities:
            card_caps = {c.name.lower() for c in card.capabilities}
            if not any(cap.lower() in card_caps for cap in query.capabilities):
                return False
        
        # Protocols 过滤（任一匹配）
        if query.protocols:
            card_protocols = {p.lower() for p in card.protocols}
            if not any(p.lower() in card_protocols for p in query.protocols):
                return False
        
        # 性能过滤
        if query.min_success_rate is not None and card.success_rate is not None:
            if card.success_rate < query.min_success_rate:
                return False
        
        if query.max_latency_ms is not None and card.avg_latency_ms is not None:
            if card.avg_latency_ms > query.max_latency_ms:
                return False
        
        return True
    
    def _sort_cards(
        self,
        cards: List[AgentCardExtended],
        sort_by: DiscoverySortBy,
        desc: bool = True
    ) -> List[AgentCardExtended]:
        """排序 Cards"""
        
        if sort_by == DiscoverySortBy.LATENCY:
            # 延迟: desc=True 意味着高延迟在前, desc=False 意味着低延迟在前
            return sorted(
                cards,
                key=lambda c: c.avg_latency_ms if c.avg_latency_ms is not None else float('inf'),
                reverse=desc
            )
        elif sort_by == DiscoverySortBy.SUCCESS_RATE:
            return sorted(
                cards,
                key=lambda c: c.success_rate if c.success_rate is not None else 0,
                reverse=desc
            )
        elif sort_by == DiscoverySortBy.POPULARITY:
            return sorted(
                cards,
                key=lambda c: c.total_calls,
                reverse=desc
            )
        elif sort_by == DiscoverySortBy.CREATED_AT:
            return sorted(
                cards,
                key=lambda c: c.metadata.created_at,
                reverse=desc
            )
        elif sort_by == DiscoverySortBy.NAME:
            return sorted(
                cards,
                key=lambda c: c.name.lower(),
                reverse=desc
            )
        else:
            # RELEVANCE: 综合评分
            def score(c: AgentCardExtended) -> float:
                s = 0.0
                # 成功率权重最高
                if c.success_rate is not None:
                    s += c.success_rate * 50
                # 延迟（越低越好）
                if c.avg_latency_ms is not None:
                    # 归一化延迟得分（假设 1000ms 以上很差）
                    latency_score = max(0, 100 - c.avg_latency_ms / 10)
                    s += latency_score * 0.3
                # 使用量（取对数归一化）
                import math
                if c.total_calls > 0:
                    s += min(math.log10(c.total_calls + 1) * 10, 30)
                return s
            
            return sorted(cards, key=score, reverse=desc)
    
    def _get_cached(self, key: str) -> Optional[DiscoveryResult]:
        """获取缓存"""
        if key in self._cache:
            timestamp, result = self._cache[key]
            if time.time() - timestamp < self._cache_ttl:
                return result
            else:
                del self._cache[key]
        return None
    
    def _set_cached(self, key: str, result: DiscoveryResult) -> None:
        """设置缓存"""
        # 限制缓存大小
        if len(self._cache) >= self._max_cache_size:
            # 删除最旧的条目
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][0])
            del self._cache[oldest_key]
        
        self._cache[key] = (time.time(), result)
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
