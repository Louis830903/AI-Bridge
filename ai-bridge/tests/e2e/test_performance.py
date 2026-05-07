"""E2E Tests — 性能基准测试 (L3)

Phase IV v1.0.0 — 关键路径延时基准。
标记为 @pytest.mark.perf，需要 --perf 标志运行。
"""

from __future__ import annotations

import time
import pytest

from aibridge.core.domain_registry import DomainIntentRegistry
from aibridge.core.intent_pattern import IntentPattern


@pytest.mark.perf
class TestPerformance:
    """性能基准测试"""

    @pytest.fixture
    def registry_60_patterns(self):
        """创建含 60 个模式的注册中心"""
        reg = DomainIntentRegistry()
        domains = ["media", "office", "browser", "git", "docker", "ffmpeg"]
        for domain in domains:
            patterns = []
            for i in range(10):
                patterns.append(IntentPattern(
                    id=f"{domain}.action{i}",
                    domain=domain,
                    patterns=[f"执行{domain}操作{i}", f"{domain}任务{i}"],
                    description=f"{domain} action {i}",
                ))
            reg.register(f"adapter-{domain}", patterns)
        return reg

    def test_l1_intent_match_latency(self, registry_60_patterns):
        """L1 意图匹配延时 — P99 < 100ms"""
        # 预热
        for _ in range(10):
            registry_60_patterns.match("执行media操作5")

        # 计时
        start = time.perf_counter()
        for _ in range(100):
            registry_60_patterns.match("执行media操作5")
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 100) * 1000

        # 断言平均延时 < 100ms
        assert avg_ms < 100, f"L1 avg latency {avg_ms:.1f}ms exceeds 100ms threshold"

    def test_l1_no_match_latency(self, registry_60_patterns):
        """L1 无匹配延时 — 遍历全部模式后返回空"""
        start = time.perf_counter()
        for _ in range(100):
            registry_60_patterns.match("完全无关的输入xyz")
        elapsed = time.perf_counter() - start
        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 200, f"L1 no-match avg latency {avg_ms:.1f}ms exceeds 200ms"

    def test_adapter_cold_start_latency(self):
        """适配器冷启动延时 — < 2s"""
        from aibridge.adapters.office.factory import create_word_adapter

        start = time.perf_counter()
        adapter = create_word_adapter(backend="openxml")
        elapsed = (time.perf_counter() - start) * 1000

        assert adapter is not None
        assert elapsed < 2000, f"Adapter cold start {elapsed:.0f}ms exceeds 2000ms"

    def test_batch_pattern_registration(self, registry_60_patterns):
        """批量模式注册 — 60 个模式都在索引中"""
        assert registry_60_patterns.total_patterns == 60
        assert registry_60_patterns.get_pattern("media.action0") is not None
        assert registry_60_patterns.get_pattern("docker.action9") is not None
