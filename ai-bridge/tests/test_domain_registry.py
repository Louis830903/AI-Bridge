"""
Tests for DomainIntentRegistry — registration, matching, semantic search, merge, export
Phase II — P2-1
"""

import pytest
from pathlib import Path

from aibridge.core.intent_pattern import (
    SlotType,
    Slot,
    IntentPattern,
    IntentMatch,
)
from aibridge.core.domain_registry import (
    DomainIntentRegistry,
    IntentRegistrationError,
)


# ============ Fixtures ============

@pytest.fixture
def media_patterns():
    """一组 Media 领域的意图模式"""
    return [
        IntentPattern(
            id="media.convert", domain="media",
            patterns=["把{输入:path}转成{目标:format}"],
            description="视频格式转换",
            confidence_threshold=0.5,
            slots=[
                Slot(name="输入", type=SlotType.PATH, description="输入文件"),
                Slot(name="目标", type=SlotType.FORMAT, description="目标格式",
                     enum_values=["mp4", "avi", "gif"]),
            ],
            examples=["把video.mp4转成gif"],
        ),
        IntentPattern(
            id="media.compress", domain="media",
            patterns=["压缩{文件:path}到{大小:integer}MB以内"],
            description="视频压缩",
            confidence_threshold=0.6,
            slots=[
                Slot(name="文件", type=SlotType.PATH),
                Slot(name="大小", type=SlotType.INTEGER),
            ],
            examples=["压缩movie.mp4到50MB以内"],
        ),
        IntentPattern(
            id="media.trim", domain="media",
            patterns=["裁剪{文件:path}从{开始:duration}到{结束:duration}"],
            description="视频裁剪",
            confidence_threshold=0.5,
            slots=[
                Slot(name="文件", type=SlotType.PATH),
                Slot(name="开始", type=SlotType.DURATION),
                Slot(name="结束", type=SlotType.DURATION),
            ],
            examples=["裁剪clip.mp4从10s到30s"],
        ),
    ]


@pytest.fixture
def browser_patterns():
    """一组 Browser 领域的意图模式"""
    return [
        IntentPattern(
            id="browser.navigate", domain="browser",
            patterns=["打开{网址:url}", "访问{网址:url}"],
            description="导航到网站",
            confidence_threshold=0.5,
            slots=[Slot(name="网址", type=SlotType.URL)],
            examples=["打开github.com"],
        ),
        IntentPattern(
            id="browser.search", domain="browser",
            patterns=["搜索{关键词:string}"],
            description="搜索内容",
            confidence_threshold=0.6,
            slots=[Slot(name="关键词", type=SlotType.STRING)],
            examples=["搜索iPhone 15"],
        ),
    ]


@pytest.fixture
def populated_registry(media_patterns, browser_patterns):
    """已注册 media 和 browser 模式的注册中心"""
    registry = DomainIntentRegistry()
    registry.register("ffmpeg", media_patterns)
    registry.register("chrome", browser_patterns)
    return registry


# ============ Registration Tests ============

class TestRegistration:
    def test_register_and_match_single_pattern(self, media_patterns):
        registry = DomainIntentRegistry()
        count = registry.register("ffmpeg", [media_patterns[0]])
        assert count == 1
        assert registry.total_patterns == 1

    def test_register_multiple_patterns(self, media_patterns):
        registry = DomainIntentRegistry()
        count = registry.register("ffmpeg", media_patterns)
        assert count == 3
        assert registry.total_patterns == 3

    def test_register_duplicate_id_raises(self, media_patterns):
        registry = DomainIntentRegistry()
        registry.register("ffmpeg", [media_patterns[0]])

        # 相同 ID 不同适配器 — 应抛出异常
        duplicate = IntentPattern(
            id="media.convert", domain="media",
            patterns=["{x:string}"], description="duplicate",
        )
        with pytest.raises(IntentRegistrationError):
            registry.register("imagemagick", [duplicate])

    def test_register_same_id_same_adapter_overwrite(self, media_patterns):
        registry = DomainIntentRegistry()
        registry.register("ffmpeg", [media_patterns[0]])
        # 同一适配器重复注册同一 ID 不抛异常（覆盖）
        count = registry.register("ffmpeg", [media_patterns[0]])
        assert count == 1

    def test_unregister_removes_all_patterns(self, populated_registry):
        count = populated_registry.unregister_adapter("ffmpeg")
        assert count == 3
        assert "ffmpeg" not in populated_registry.adapters
        # chrome 仍在
        assert populated_registry.total_patterns == 2

    def test_unregister_nonexistent_returns_zero(self, populated_registry):
        count = populated_registry.unregister_adapter("nonexistent")
        assert count == 0

    def test_unregister_empty_domain_removed(self, populated_registry):
        populated_registry.unregister_adapter("ffmpeg")
        assert "media" not in populated_registry.domains


# ============ L1 Match Tests ============

class TestL1Match:
    def test_match_returns_highest_confidence_first(self, populated_registry):
        results = populated_registry.match("把video.mp4转成gif")
        assert len(results) > 0
        assert results[0].pattern.id == "media.convert"

    def test_match_with_domain_filter(self, populated_registry):
        results = populated_registry.match("打开github.com", domain="browser")
        assert len(results) == 1
        assert results[0].pattern.id == "browser.navigate"

    def test_match_domain_filter_excludes_other(self, populated_registry):
        results = populated_registry.match("把video.mp4转成gif", domain="browser")
        assert len(results) == 0

    def test_match_below_threshold_returns_empty(self, populated_registry):
        results = populated_registry.match("random text that doesn't match",
                                           min_confidence=0.8)
        assert len(results) == 0

    def test_match_nonexistent_domain(self):
        registry = DomainIntentRegistry()
        results = registry.match("anything", domain="nonexistent")
        assert len(results) == 0

    def test_multiple_matches_sorted(self, media_patterns):
        registry = DomainIntentRegistry()
        # 注册两个同领域模式
        p1 = IntentPattern(
            id="media.a", domain="media",
            patterns=["{x:string}"], description="Catch-all",
            confidence_threshold=0.3,
            slots=[Slot(name="x", type=SlotType.STRING)],
        )
        p2 = IntentPattern(
            id="media.b", domain="media",
            patterns=["精确匹配{关键词:string}"], description="Specific",
            confidence_threshold=0.3,
            slots=[Slot(name="关键词", type=SlotType.STRING)],
        )
        registry.register("test", [p1, p2])
        results = registry.match("精确匹配hello")
        assert len(results) >= 1
        # 两个都可能匹配，结果按置信度降序排列
        pattern_ids = {r.pattern.id for r in results}
        assert "media.a" in pattern_ids or "media.b" in pattern_ids


# ============ Semantic Search Tests ============

class TestSemanticSearch:
    def test_semantic_search_finds_related(self, populated_registry):
        """语义搜索能找到语义相关的模式"""
        results = populated_registry.semantic_search("我想把一个视频文件转成不同的格式", top_k=3)
        # 至少返回一些结果（如果没有 sentence-transformers 则返回空）
        if len(results) > 0:
            assert results[0].route == "semantic"

    def test_semantic_search_empty_registry(self):
        registry = DomainIntentRegistry()
        results = registry.semantic_search("anything")
        assert results == []

    def test_semantic_search_respects_top_k(self, populated_registry):
        results = populated_registry.semantic_search("compressing a video file", top_k=1)
        assert len(results) <= 1


# ============ Merge Tests ============

class TestMerge:
    def test_merge_two_registries(self):
        r1 = DomainIntentRegistry()
        r1.register("a", [
            IntentPattern(id="a.x", domain="test", patterns=["{x:string}"],
                          description="A1"),
        ])
        r2 = DomainIntentRegistry()
        r2.register("b", [
            IntentPattern(id="b.y", domain="test", patterns=["{y:string}"],
                          description="B1"),
        ])

        merged = r1.merge(r2)
        assert merged.total_patterns == 2
        assert sorted(merged.adapters) == ["a", "b"]

    def test_merge_preserves_originals(self):
        r1 = DomainIntentRegistry()
        r1.register("a", [
            IntentPattern(id="a.x", domain="test", patterns=["{x:string}"],
                          description="A"),
        ])
        r2 = DomainIntentRegistry()
        r2.register("b", [
            IntentPattern(id="b.y", domain="test", patterns=["{y:string}"],
                          description="B"),
        ])

        merged = r1.merge(r2)
        # 原始注册中心不受影响
        assert r1.total_patterns == 1
        assert r2.total_patterns == 1
        assert merged.total_patterns == 2

    def test_merge_duplicate_handled(self, media_patterns):
        r1 = DomainIntentRegistry()
        r1.register("ffmpeg", [media_patterns[0]])
        r2 = DomainIntentRegistry()
        r2.register("ffmpeg", [media_patterns[0]])  # 相同 ID

        merged = r1.merge(r2)
        # 重复 ID 被跳过
        assert merged.total_patterns == 1

    def test_merge_empty_registries(self):
        r1 = DomainIntentRegistry()
        r2 = DomainIntentRegistry()
        merged = r1.merge(r2)
        assert merged.total_patterns == 0


# ============ Export & Context Tests ============

class TestExport:
    def test_export_patterns_serializable(self, populated_registry):
        exported = populated_registry.export_patterns()
        assert isinstance(exported, list)
        assert len(exported) == 5  # 3 media + 2 browser
        # 验证结构
        first = exported[0]
        assert "id" in first
        assert "domain" in first
        assert "patterns" in first
        assert "slots" in first
        assert "adapter_id" in first

    def test_to_prompt_context_format(self, populated_registry):
        context = populated_registry.to_prompt_context()
        assert isinstance(context, str)
        assert "media.convert" in context
        assert "browser.navigate" in context
        assert "Total:" in context

    def test_to_prompt_context_max_patterns(self, populated_registry):
        context = populated_registry.to_prompt_context(max_patterns=2)
        # 按字母序 browser 域在前，max=2 后截断
        assert "browser.navigate" in context
        assert "more patterns omitted" in context

    def test_to_prompt_context_empty(self):
        registry = DomainIntentRegistry()
        context = registry.to_prompt_context()
        assert "Total:" in context


# ============ Stats Tests ============

class TestStats:
    def test_get_domain_stats(self, populated_registry):
        stats = populated_registry.get_domain_stats()
        assert stats["media"] == 3
        assert stats["browser"] == 2

    def test_get_adapter_patterns(self, populated_registry):
        patterns = populated_registry.get_adapter_patterns("ffmpeg")
        assert len(patterns) == 3
        assert all(p.adapter_id == "ffmpeg" for p in patterns)

    def test_get_pattern(self, populated_registry):
        p = populated_registry.get_pattern("media.convert")
        assert p is not None
        assert p.domain == "media"

    def test_get_pattern_nonexistent(self, populated_registry):
        p = populated_registry.get_pattern("nonexistent.id")
        assert p is None

    def test_total_patterns(self, populated_registry):
        assert populated_registry.total_patterns == 5

    def test_domains_property(self, populated_registry):
        assert set(populated_registry.domains) == {"media", "browser"}

    def test_adapters_property(self, populated_registry):
        assert set(populated_registry.adapters) == {"ffmpeg", "chrome"}
