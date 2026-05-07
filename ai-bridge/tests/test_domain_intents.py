"""
Tests for 6 domain intent networks
Phase II — P2-2
"""

import pytest

from aibridge.core.domain_registry import DomainIntentRegistry
from aibridge.core.intents.browser import BROWSER_PATTERNS
from aibridge.core.intents.office import OFFICE_PATTERNS
from aibridge.core.intents.media import MEDIA_PATTERNS
from aibridge.core.intents.devops import DEVOPS_PATTERNS
from aibridge.core.intents.collab import COLLAB_PATTERNS
from aibridge.core.intents.webtools import WEBTOOLS_PATTERNS


ALL_DOMAIN_PATTERNS = {
    "browser": BROWSER_PATTERNS,
    "office": OFFICE_PATTERNS,
    "media": MEDIA_PATTERNS,
    "devops": DEVOPS_PATTERNS,
    "collab": COLLAB_PATTERNS,
    "webtools": WEBTOOLS_PATTERNS,
}


# ============ Count Verification ============

class TestPatternCount:
    def test_browser_has_6_patterns(self):
        assert len(BROWSER_PATTERNS) == 6

    def test_office_has_12_patterns(self):
        assert len(OFFICE_PATTERNS) == 12

    def test_media_has_18_patterns(self):
        assert len(MEDIA_PATTERNS) == 18

    def test_devops_has_9_patterns(self):
        assert len(DEVOPS_PATTERNS) == 9

    def test_collab_has_4_patterns(self):
        assert len(COLLAB_PATTERNS) == 4

    def test_webtools_has_4_patterns(self):
        assert len(WEBTOOLS_PATTERNS) == 4

    def test_total_at_least_53_patterns(self):
        total = sum(len(p) for p in ALL_DOMAIN_PATTERNS.values())
        assert total >= 53, f"Expected >=53 patterns, got {total}"


# ============ Quality Checks ============

class TestPatternQuality:
    @pytest.mark.parametrize("domain_name,patterns", ALL_DOMAIN_PATTERNS.items())
    def test_each_pattern_has_examples(self, domain_name, patterns):
        for p in patterns:
            assert len(p.examples) >= 2, (
                f"{p.id}: expected ≥2 examples, got {len(p.examples)}"
            )

    @pytest.mark.parametrize("domain_name,patterns", ALL_DOMAIN_PATTERNS.items())
    def test_each_slot_has_description(self, domain_name, patterns):
        for p in patterns:
            for s in p.slots:
                assert s.description, (
                    f"{p.id}: slot '{s.name}' missing description"
                )

    @pytest.mark.parametrize("domain_name,patterns", ALL_DOMAIN_PATTERNS.items())
    def test_each_pattern_has_description(self, domain_name, patterns):
        for p in patterns:
            assert p.description, f"{p.id}: missing description"

    @pytest.mark.parametrize("domain_name,patterns", ALL_DOMAIN_PATTERNS.items())
    def test_each_pattern_has_unique_id(self, domain_name, patterns):
        ids = [p.id for p in patterns]
        assert len(ids) == len(set(ids)), f"Duplicate pattern IDs in {domain_name}: {ids}"


# ============ Registration & Matching ============

@pytest.fixture
def full_registry():
    """包含所有领域模式的注册中心"""
    registry = DomainIntentRegistry()
    for domain, patterns in ALL_DOMAIN_PATTERNS.items():
        # 为每个领域使用虚拟适配器名
        registry.register(f"mock-{domain}", patterns)
    return registry


class TestFullRegistry:
    def test_all_domains_registered(self, full_registry):
        stats = full_registry.get_domain_stats()
        for domain in ALL_DOMAIN_PATTERNS:
            assert domain in stats, f"Domain '{domain}' not found in stats"
            assert stats[domain] == len(ALL_DOMAIN_PATTERNS[domain]), (
                f"Domain '{domain}': expected {len(ALL_DOMAIN_PATTERNS[domain])}, "
                f"got {stats[domain]}"
            )

    def test_total_patterns(self, full_registry):
        expected = sum(len(p) for p in ALL_DOMAIN_PATTERNS.values())
        assert full_registry.total_patterns == expected

    def test_browser_navigate_match(self, full_registry):
        results = full_registry.match("打开github.com", domain="browser")
        assert len(results) >= 1
        assert results[0].pattern.id == "browser.navigate"

    def test_media_convert_match(self, full_registry):
        results = full_registry.match("把video.mp4转成gif", domain="media")
        assert len(results) >= 1
        assert results[0].pattern.id == "media.convert"

    def test_devops_git_commit_match(self, full_registry):
        results = full_registry.match("git commit -m fix bug", domain="devops")
        assert len(results) >= 1
        assert results[0].pattern.id == "devops.git_commit"

    def test_cross_domain_no_match(self, full_registry):
        """跨域搜索不应返回错误结果"""
        results = full_registry.match("打开github.com", domain="media")
        assert len(results) == 0

    def test_export_all_patterns(self, full_registry):
        exported = full_registry.export_patterns()
        assert len(exported) == full_registry.total_patterns

    def test_to_prompt_context_full(self, full_registry):
        context = full_registry.to_prompt_context(max_patterns=100)
        # 所有域名都应出现
        for domain in ALL_DOMAIN_PATTERNS:
            assert f"[{domain}]" in context, f"Domain [{domain}] missing from context"
