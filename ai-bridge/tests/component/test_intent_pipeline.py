"""
Component Tests — 意图流水线 (L1)

Phase IV v1.0.0 — IntentEngine 三级解析：精确匹配 → 语义搜索 → LLM 回退。
"""

from __future__ import annotations

import pytest

from aibridge.core.intent_pattern import IntentPattern, IntentMatch
from aibridge.core.domain_registry import DomainIntentRegistry


class TestIntentPipeline:
    """IntentEngine + DomainIntentRegistry 集成组件测试"""

    @pytest.fixture
    def registry(self):
        reg = DomainIntentRegistry()
        # 注册一些测试用的意图模式
        reg.register("test-media", [
            IntentPattern(id="media.convert", domain="media",
                          patterns=["把{输入}转成{目标}"],
                          description="视频/音频格式转换"),
            IntentPattern(id="media.compress", domain="media",
                          patterns=["压缩{输入}", "减小{输入}大小"],
                          description="压缩媒体文件"),
        ])
        reg.register("test-office", [
            IntentPattern(id="office.export_pdf", domain="office",
                          patterns=["导出PDF", "转成PDF", "输出PDF"],
                          description="文档导出为PDF"),
        ])
        return reg

    # ── L1 精确匹配 ─────────────────────────────────────────

    def test_l1_exact_match_single_pattern(self, registry):
        """精确匹配 — 单模式命中"""
        results = registry.match("导出PDF")
        assert len(results) >= 1
        result = results[0]
        assert isinstance(result, IntentMatch)
        assert result.pattern.id == "office.export_pdf"
        assert result.route == "exact"
        assert result.confidence >= 0.9

    def test_l1_exact_match_with_slots(self, registry):
        """精确匹配 — 带槽位参数"""
        results = registry.match("把video.mp4转成gif")
        assert len(results) >= 1
        assert results[0].pattern.id == "media.convert"

    def test_l1_no_match_returns_empty(self, registry):
        """无匹配返回空列表"""
        results = registry.match("做一些不存在的事情")
        assert results == []

    def test_l1_multiple_patterns_first_wins(self, registry):
        """多模式匹配 — 返回按置信度排序"""
        results = registry.match("压缩video.mp4")
        assert len(results) >= 1
        # 第一个是最高置信度
        assert results[0].pattern.id == "media.compress"

    # ── 注册中心操作 ─────────────────────────────────────────

    def test_registry_counts_patterns(self, registry):
        """注册中心跟踪模式数量"""
        assert registry.total_patterns == 3
        assert len(registry.domains) >= 1

    def test_registry_unregister_adapter(self, registry):
        """注销适配器后其模式不可匹配"""
        registry.unregister_adapter("test-office")
        results = registry.match("导出PDF")
        assert results == []

    def test_registry_get_by_id(self, registry):
        """按 ID 获取模式"""
        p = registry.get_pattern("media.convert")
        assert p is not None
        assert p.domain == "media"

    # ── L3 LLM 回退标记 ─────────────────────────────────────

    def test_llm_fallback_route_enum(self):
        """验证 route enum 值"""
        match = IntentMatch(
            pattern=IntentPattern(id="test.x", domain="test",
                                  patterns=["dummy"], description="dummy"),
            matched_text="dummy",
            route="llm", confidence=0.7,
        )
        assert match.route == "llm"
