"""
DomainIntentRegistry — 领域意图注册中心

所有适配器意图模式的统一索引。支持:
- L1 精确模板匹配 (P99 < 10ms)
- L2 语义搜索 (P99 < 200ms, 使用 sentence-transformers)
- 注册中心合并（组合爆炸效应）
- 统计/导出/LLM 提示词生成

Phase II — 意图引擎通用化 (v0.10.0)
"""

from __future__ import annotations

from typing import Callable, Optional
from pathlib import Path
import logging

from aibridge.core.intent_pattern import (
    IntentPattern,
    IntentMatch,
    SlotType,
    SlotParser,
    PatternMatcher,
)

logger = logging.getLogger(__name__)


class IntentRegistrationError(Exception):
    """意图注册错误"""
    pass


class DomainIntentRegistry:
    """领域意图注册中心——所有适配器意图模式的统一索引"""

    def __init__(self):
        # domain → patterns 列表
        self._patterns: dict[str, list[IntentPattern]] = {}
        # adapter_id → pattern_id 列表
        self._by_adapter: dict[str, list[str]] = {}
        # id → pattern 快速索引
        self._pattern_index: dict[str, IntentPattern] = {}
        # 语义搜索模型（延迟加载）
        self._embedding_model = None
        self._embeddings_cache: dict[str, list[float]] = {}

    # ========== 注册 / 注销 ==========

    def register(self, adapter_id: str, patterns: list[IntentPattern]) -> int:
        """注册一组意图模式，返回成功注册的数量。

        Args:
            adapter_id: 适配器 ID (如 "ffmpeg")
            patterns: 该适配器的意图模式列表

        Returns:
            成功注册的模式数量

        Raises:
            IntentRegistrationError: 模式 ID 冲突时
        """
        count = 0
        if adapter_id not in self._by_adapter:
            self._by_adapter[adapter_id] = []

        for p in patterns:
            # 始终以注册时的 adapter_id 为准（覆盖 __post_init__ 自动推断）
            p.adapter_id = adapter_id

            # ID 冲突检查
            if p.id in self._pattern_index:
                existing = self._pattern_index[p.id]
                if existing.adapter_id != adapter_id:
                    raise IntentRegistrationError(
                        f"Pattern ID '{p.id}' already registered by "
                        f"adapter '{existing.adapter_id}', cannot re-register "
                        f"by '{adapter_id}'"
                    )
                # 同适配器重复注册——覆盖
                logger.debug(f"Re-registering pattern '{p.id}' for adapter '{adapter_id}'")

            # 按领域索引
            domain = p.domain
            if domain not in self._patterns:
                self._patterns[domain] = []
            self._patterns[domain].append(p)

            # 按适配器索引
            self._by_adapter[adapter_id].append(p.id)

            # 按 ID 索引
            self._pattern_index[p.id] = p

            # 清除语义搜索缓存
            if p.description in self._embeddings_cache:
                del self._embeddings_cache[p.description]

            count += 1

        logger.info(
            f"Registered {count} patterns from adapter '{adapter_id}'"
        )
        return count

    def unregister_adapter(self, adapter_id: str) -> int:
        """注销某适配器的所有模式，返回移除数量。

        Args:
            adapter_id: 待注销的适配器 ID

        Returns:
            移除的模式数量
        """
        if adapter_id not in self._by_adapter:
            return 0

        pattern_ids = self._by_adapter.pop(adapter_id)
        count = 0

        for pid in pattern_ids:
            pattern = self._pattern_index.pop(pid, None)
            if pattern is None:
                continue
            domain = pattern.domain
            if domain in self._patterns:
                try:
                    self._patterns[domain].remove(pattern)
                except ValueError:
                    pass
                if not self._patterns[domain]:
                    del self._patterns[domain]
            # 清除缓存
            if pattern.description in self._embeddings_cache:
                del self._embeddings_cache[pattern.description]
            count += 1

        logger.info(
            f"Unregistered {count} patterns from adapter '{adapter_id}'"
        )
        return count

    # ========== L1 精确匹配 ==========

    def match(
        self,
        user_input: str,
        domain: str | None = None,
        min_confidence: float = 0.0,
    ) -> list[IntentMatch]:
        """L1 精确匹配——用注册的模式模板匹配用户输入。

        Args:
            user_input: 用户自然语言输入
            domain: 限定的领域 (None = 全领域)
            min_confidence: 最低置信度阈值

        Returns:
            匹配结果列表，按置信度降序排列
        """
        results: list[IntentMatch] = []

        domains = [domain] if domain else list(self._patterns.keys())
        for d in domains:
            if d not in self._patterns:
                continue
            for pattern in self._patterns[d]:
                match_result = PatternMatcher.match_pattern(user_input, pattern)
                if match_result and match_result.confidence >= min_confidence:
                    results.append(match_result)

        results.sort(key=lambda r: r.confidence, reverse=True)
        return results

    # ========== L2 语义搜索 ==========

    def _get_embedding_model(self):
        """延迟加载 sentence-transformers 模型"""
        if self._embedding_model is not None:
            return self._embedding_model

        try:
            from sentence_transformers import SentenceTransformer
            # 使用轻量模型，80MB 左右，P99 < 200ms
            self._embedding_model = SentenceTransformer(
                'all-MiniLM-L6-v2'
            )
            logger.info("Loaded sentence-transformers model: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning(
                "sentence-transformers not installed; "
                "semantic search will return empty results. "
                "Install with: pip install sentence-transformers"
            )
            self._embedding_model = None
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._embedding_model = None

        return self._embedding_model

    def _compute_similarity(self, query: str, description: str) -> float:
        """计算查询与描述的余弦相似度"""
        model = self._get_embedding_model()
        if model is None:
            return 0.0

        # 缓存描述 embedding
        if description not in self._embeddings_cache:
            try:
                emb = model.encode(description, convert_to_numpy=True)
                self._embeddings_cache[description] = emb.tolist()
            except Exception:
                return 0.0

        # 编码查询
        try:
            query_emb = model.encode(query, convert_to_numpy=True)
        except Exception:
            return 0.0

        # 余弦相似度
        import numpy as np
        desc_emb = np.array(self._embeddings_cache[description])
        similarity = np.dot(query_emb, desc_emb) / (
            np.linalg.norm(query_emb) * np.linalg.norm(desc_emb)
        )
        return float(similarity)

    def semantic_search(
        self,
        user_input: str,
        top_k: int = 5,
    ) -> list[IntentMatch]:
        """L2 语义搜索——跨领域模糊匹配。

        使用 embedding 计算 user_input 与所有 pattern.description 的相似度。

        Args:
            user_input: 用户自然语言输入
            top_k: 返回前 k 个结果

        Returns:
            匹配结果列表，按置信度降序排列
        """
        if not self._pattern_index:
            return []

        # 计算所有模式的相似度
        scored: list[tuple[float, IntentPattern]] = []
        for pattern in self._pattern_index.values():
            sim = self._compute_similarity(user_input, pattern.description)
            if sim > 0:
                scored.append((sim, pattern))

        # 按相似度降序
        scored.sort(key=lambda x: x[0], reverse=True)

        # 取 top_k
        results: list[IntentMatch] = []
        for sim, pattern in scored[:top_k]:
            results.append(IntentMatch(
                pattern=pattern,
                confidence=sim,
                matched_text=user_input,
                route="semantic",
            ))

        return results

    # ========== 合并 ==========

    def merge(self, other: "DomainIntentRegistry") -> "DomainIntentRegistry":
        """合并另一个注册中心，返回新的联合注册中心。

        用于组合多个适配器的意图空间，形成"组合爆炸"效应。
        原始注册中心不受影响。

        Returns:
            新的联合注册中心
        """
        merged = DomainIntentRegistry()

        # 复制本注册中心的所有模式
        for domain, patterns in self._patterns.items():
            for p in patterns:
                try:
                    merged.register(p.adapter_id, [p])
                except IntentRegistrationError:
                    pass  # 跳过冲突

        # 合并另一个注册中心
        for domain, patterns in other._patterns.items():
            for p in patterns:
                try:
                    merged.register(p.adapter_id, [p])
                except IntentRegistrationError:
                    pass

        return merged

    # ========== 查询 ==========

    def get_domain_stats(self) -> dict[str, int]:
        """获取各领域注册模式数量统计"""
        return {
            domain: len(patterns)
            for domain, patterns in self._patterns.items()
        }

    def get_adapter_patterns(self, adapter_id: str) -> list[IntentPattern]:
        """获取某适配器的所有模式"""
        if adapter_id not in self._by_adapter:
            return []
        return [
            self._pattern_index[pid]
            for pid in self._by_adapter[adapter_id]
            if pid in self._pattern_index
        ]

    def get_pattern(self, pattern_id: str) -> IntentPattern | None:
        """按 ID 获取模式"""
        return self._pattern_index.get(pattern_id)

    @property
    def total_patterns(self) -> int:
        """注册的模式总数"""
        return len(self._pattern_index)

    @property
    def domains(self) -> list[str]:
        """已注册的领域列表"""
        return list(self._patterns.keys())

    @property
    def adapters(self) -> list[str]:
        """已注册的适配器列表"""
        return list(self._by_adapter.keys())

    # ========== 导出 ==========

    def export_patterns(self) -> list[dict]:
        """导出所有模式为可序列化格式（用于 Agent Card 发布）"""
        result = []
        for pattern in self._pattern_index.values():
            result.append({
                "id": pattern.id,
                "domain": pattern.domain,
                "patterns": pattern.patterns,
                "description": pattern.description,
                "confidence_threshold": pattern.confidence_threshold,
                "slots": [
                    {
                        "name": s.name,
                        "type": s.type.value,
                        "required": s.required,
                        "default": s.default,
                        "description": s.description,
                        "enum_values": s.enum_values,
                    }
                    for s in pattern.slots
                ],
                "examples": pattern.examples,
                "adapter_id": pattern.adapter_id,
                "tags": pattern.tags,
            })
        return result

    def to_prompt_context(self, max_patterns: int = 50) -> str:
        """生成 LLM 可用的意图模式上下文（用于 L3 LLM Fallback）

        Args:
            max_patterns: 最大包含模式数（避免 token 溢出）

        Returns:
            格式化的提示词上下文字符串
        """
        lines = ["Available intent patterns:"]
        count = 0

        for domain, patterns in sorted(self._patterns.items()):
            lines.append(f"\n[{domain}] domain:")
            for p in patterns:
                if count >= max_patterns:
                    lines.append(f"\n... ({self.total_patterns - count} more patterns omitted)")
                    return "\n".join(lines)
                examples_str = f" (e.g. {', '.join(p.examples[:2])})" if p.examples else ""
                lines.append(
                    f"  - {p.id}: {p.description}{examples_str}"
                )
                count += 1

        lines.append(f"\nTotal: {count} patterns across {len(self._patterns)} domains.")
        return "\n".join(lines)
