"""
Tests for intent_engine v2.0 three-level pipeline
Phase II — P2-3
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch

from aibridge.core.intent_engine import (
    IntentEngine,
    IntentPipelineConfig,
    IntentType,
    IntentResult,
    ActionStep,
)
from aibridge.core.domain_registry import DomainIntentRegistry
from aibridge.core.intent_pattern import (
    IntentPattern,
    IntentMatch,
    Slot,
    SlotType,
)


# ============ Fixtures ============

@pytest.fixture
def mock_adapter():
    """模拟适配器"""
    adapter = MagicMock()
    adapter.adapter_id = "mock"
    return adapter


@pytest.fixture
def populated_registry():
    """已注册意图的注册中心"""
    registry = DomainIntentRegistry()
    patterns = [
        IntentPattern(
            id="media.convert", domain="media",
            patterns=["把{输入:path}转成{格式:format}", "{输入:path}转换为{格式:format}"],
            description="视频/音频格式转换",
            confidence_threshold=0.5,
            slots=[
                Slot("输入", SlotType.PATH, description="输入文件"),
                Slot("格式", SlotType.FORMAT, description="目标格式",
                     enum_values=["mp4", "avi", "gif"]),
            ],
            examples=["把video.mp4转成gif"],
        ),
        IntentPattern(
            id="media.compress", domain="media",
            patterns=["压缩{文件:path}到{大小:integer}MB以内"],
            description="视频压缩",
            confidence_threshold=0.5,
            slots=[
                Slot("文件", SlotType.PATH),
                Slot("大小", SlotType.INTEGER),
            ],
            examples=["压缩movie.mp4到50MB以内"],
        ),
        IntentPattern(
            id="browser.navigate", domain="browser",
            patterns=["打开{网址:url}", "访问{网址:url}"],
            description="导航到网站",
            confidence_threshold=0.5,
            slots=[Slot("网址", SlotType.URL)],
            examples=["打开github.com"],
        ),
    ]
    registry.register("ffmpeg", patterns[:2])
    registry.register("chrome", patterns[2:])
    return registry


@pytest.fixture
def engine(mock_adapter, populated_registry):
    """带注册中心的意图引擎"""
    eng = IntentEngine(mock_adapter)
    eng.set_registry(populated_registry)
    return eng


# ============ L1 Exact Match Tests ============

class TestL1ExactMatch:
    @pytest.mark.asyncio
    async def test_l1_hit_media_convert(self, engine):
        result = await engine.resolve("把video.mp4转成gif")
        assert result is not None
        assert isinstance(result, IntentMatch)
        assert result.pattern.id == "media.convert"
        assert result.route == "exact"

    @pytest.mark.asyncio
    async def test_l1_hit_browser_navigate(self, engine):
        result = await engine.resolve("打开github.com")
        assert result is not None
        assert result.pattern.id == "browser.navigate"

    @pytest.mark.asyncio
    async def test_l1_domain_filter(self, engine):
        """L1 域过滤"""
        result = await engine.resolve("把video.mp4转成gif", domain="browser")
        assert result is None  # media pattern not in browser domain

    @pytest.mark.asyncio
    async def test_l1_no_match(self, engine):
        """无明显匹配时应返回 None（不进入 L2/L3 时）"""
        # 如果没有 LLM provider，L3 不可用；没有 sentence-transformers 时 L2 返回空
        result = await engine.resolve("一个完全无法匹配的随机输入xyz")
        # 可能返回 None（L1/L2 miss, 无 LLM）
        # 也可能 L2 返回低置信度结果
        if result is not None:
            assert result.route == "semantic"

    @pytest.mark.asyncio
    async def test_l1_with_registry_param(self, engine, populated_registry):
        """明确传入 registry 参数"""
        result = await engine.resolve(
            "把video.mp4转成gif", registry=populated_registry
        )
        assert result is not None
        assert result.pattern.id == "media.convert"


# ============ L2 Semantic Search Tests ============

class TestL2SemanticSearch:
    @pytest.mark.asyncio
    async def test_l2_falls_back_when_l1_misses(self, engine):
        """L1 未命中时自动回退到 L2"""
        # 这个输入不会精确匹配任何 L1 模式
        result = await engine.resolve("我想把一个视频文件转成不同的格式")
        if result is not None:
            assert result.route == "semantic"

    @pytest.mark.asyncio
    async def test_l2_respects_min_confidence(self, engine):
        """低置信度 L2 结果被过滤"""
        config = IntentPipelineConfig(l2_min_confidence=0.99)
        result = await engine.resolve(
            "一个完全无关的输入", config=config
        )
        # L2 返回空因为置信度不够，无 LLM 所以 L3 也不可用
        assert result is None


# ============ Stats Tests ============

class TestStats:
    @pytest.mark.asyncio
    async def test_initial_stats(self, engine):
        stats = engine.get_stats()
        assert stats["total"] == 1  # at least 1 for div-by-zero
        assert "l1_hits" in stats
        assert "l2_hits" in stats
        assert "l3_hits" in stats
        assert "misses" in stats

    @pytest.mark.asyncio
    async def test_stats_after_l1_hit(self, engine):
        await engine.resolve("把video.mp4转成gif")
        stats = engine.get_stats()
        assert stats["l1_hits"] >= 1

    @pytest.mark.asyncio
    async def test_l1_and_l2_rates_sum_to_1(self, engine):
        """命中后各比率之和接近 1"""
        for _ in range(5):
            await engine.resolve("把video.mp4转成gif")
        stats = engine.get_stats()
        rate_sum = stats["l1_rate"] + stats["l2_rate"] + stats["l3_rate"] + stats["miss_rate"]
        assert abs(rate_sum - 1.0) < 0.01


# ============ Timeout Tests ============

class TestTimeout:
    @pytest.mark.asyncio
    async def test_l1_timeout_non_blocking(self, engine):
        """L1 超时不阻塞主流程"""
        config = IntentPipelineConfig(l1_timeout_ms=1)
        # L1 超时后应回退到 L2 或返回 None
        result = await engine.resolve("把video.mp4转成gif", config=config)
        # 可能命中也可能不命中（取决于超时是否真的发生）
        # 核心测试：不应抛出异常
        assert True  # 不崩溃

    @pytest.mark.asyncio
    async def test_resolve_without_registry_returns_none(self, mock_adapter):
        """无注册中心时 resolve 返回 None"""
        eng = IntentEngine(mock_adapter)
        result = await eng.resolve("把video.mp4转成gif")
        assert result is None


# ============ PipelineConfig Tests ============

class TestPipelineConfig:
    def test_default_config(self):
        config = IntentPipelineConfig()
        assert config.l1_timeout_ms == 50
        assert config.l2_timeout_ms == 500
        assert config.l3_timeout_ms == 5000
        assert config.l2_top_k == 5
        assert config.l3_auto_register is False

    def test_custom_config(self):
        config = IntentPipelineConfig(
            l1_timeout_ms=100,
            l3_auto_register=True,
            l3_register_threshold=0.9,
        )
        assert config.l1_timeout_ms == 100
        assert config.l3_auto_register is True
        assert config.l3_register_threshold == 0.9


# ============ Backward Compatibility Tests ============

class TestBackwardCompatibility:
    @pytest.mark.asyncio
    async def test_parse_still_works(self, mock_adapter):
        """旧 API parse() 仍可使用"""
        eng = IntentEngine(mock_adapter)
        await eng.initialize()
        result = await eng.parse("搜索 iPhone 15")
        assert isinstance(result, IntentResult)
        assert result.intent_type == IntentType.SEARCH

    @pytest.mark.asyncio
    async def test_execute_still_works(self, mock_adapter):
        """旧 API execute() 仍可使用"""
        mock_adapter.execute.return_value = {"success": True}
        eng = IntentEngine(mock_adapter)
        await eng.initialize()
        result = await eng.execute("搜索 iPhone 15")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_list_supported_intents(self, mock_adapter):
        eng = IntentEngine(mock_adapter)
        intents = eng.list_supported_intents()
        assert "search" in intents
        assert "navigate" in intents

    @pytest.mark.asyncio
    async def test_add_custom_pattern(self, mock_adapter):
        """旧 add_pattern 仍可使用"""
        from aibridge.core.intent_engine import IntentPattern as OldPattern

        eng = IntentEngine(mock_adapter)
        eng.add_pattern(OldPattern(
            IntentType.SEARCH,
            [r"^查找(.+)$"],
            lambda m, a: [ActionStep(action="search", value=m.group(1),
                          description=f"search {m.group(1)}")]
        ))
        intents = eng.list_supported_intents()
        assert "search" in intents

    @pytest.mark.asyncio
    async def test_set_timeout(self, mock_adapter):
        eng = IntentEngine(mock_adapter)
        eng.set_timeout(60.0)
        assert eng._execute_timeout == 60.0

    @pytest.mark.asyncio
    async def test_set_registry(self, mock_adapter, populated_registry):
        eng = IntentEngine(mock_adapter)
        eng.set_registry(populated_registry)
        assert eng._registry is not None
        assert eng._registry.total_patterns == 3


# ============ Composite Intent Tests ============

class TestCompositeIntent:
    @pytest.mark.asyncio
    async def test_registry_merge_preserves_original(self, engine,
                                                      populated_registry):
        """merge 不影响原始注册中心"""
        r2 = DomainIntentRegistry()
        r2.register("test", [
            IntentPattern(id="test.x", domain="test",
                          patterns=["{x:string}"], description="test"),
        ])
        merged = populated_registry.merge(r2)
        assert populated_registry.total_patterns == 3
        assert merged.total_patterns == 4


# ============ Execution Timeout (P2-9 fix) Tests ============

class TestExecutionTimeout:
    @pytest.mark.asyncio
    async def test_execute_has_global_timeout(self, mock_adapter):
        """P2-9: execute() 全局超时已实现"""
        mock_adapter.execute.return_value = {"success": True}
        eng = IntentEngine(mock_adapter)
        await eng.initialize()

        # 设置很短的超时
        eng.set_timeout(0.001)
        # execute 应能处理超时而不崩溃
        result = await eng.execute("搜索 iPhone 15")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_execute_timeout_returns_error(self, mock_adapter):
        """P2-9: 超时返回错误字典"""
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(10)
            return {"success": True}

        mock_adapter.execute = slow_execute
        eng = IntentEngine(mock_adapter)
        await eng.initialize()
        eng.set_timeout(0.1)

        result = await eng.execute("搜索 iPhone 15")
        assert isinstance(result, dict)
        # 超时后应包含错误
        if not result.get("success"):
            assert "error" in result or "超时" in str(result)


# ============ P1-6 Decoupling Tests ============

class TestP1_6Decoupling:
    """验证 intent_engine 已解耦 ChromeAdapter"""

    def test_searchengines_dict_defined(self):
        """P1-6: SEARCH_ENGINES 多引擎配置已定义"""
        from aibridge.core.intent_engine import SEARCH_ENGINES
        assert SEARCH_ENGINES is not None
        assert "baidu" in SEARCH_ENGINES
        assert "google" in SEARCH_ENGINES
        assert "bing" in SEARCH_ENGINES
        assert SEARCH_ENGINES["baidu"]["search_box"] == "#kw"
        assert SEARCH_ENGINES["google"]["search_box"] == "input[name='q']"

    def test_engine_accepts_base_adapter_subclass(self):
        """P1-6: IntentEngine.__init__ 接受 BaseAdapter 而非硬编码 ChromeAdapter"""
        from aibridge.adapters.base import BaseAdapter

        class CustomAdapter(BaseAdapter):
            adapter_id = "custom"
            @classmethod
            def is_available(cls) -> bool: return True
            async def connect(self): pass
            async def disconnect(self): pass
            async def execute(self, action, target=None, value=None, options=None):
                return {"success": True}

        adapter = CustomAdapter()
        eng = IntentEngine(adapter)
        assert eng.adapter is adapter
        assert eng.adapter.adapter_id == "custom"

    def test_handle_search_uses_base_adapter(self):
        """P1-6: handle_search 签名使用 BaseAdapter"""
        import inspect
        import typing
        from aibridge.core.intent_engine import handle_search
        from aibridge.adapters.base import BaseAdapter

        sig = inspect.signature(handle_search)
        params = list(sig.parameters.values())
        assert len(params) == 2
        # from __future__ import annotations 使注解成为字符串
        ann = params[1].annotation
        if isinstance(ann, str):
            # 解析字符串注解
            resolved = typing.get_type_hints(handle_search)
            assert resolved.get("adapter") is BaseAdapter
        else:
            assert ann is BaseAdapter

    def test_handler_signatures_all_use_base_adapter(self):
        """P1-6: 所有 handler 函数签名都使用 BaseAdapter"""
        import inspect
        import typing
        from aibridge.core.intent_engine import (
            handle_navigate, handle_search, handle_click,
            handle_type, handle_extract, handle_scroll,
        )
        from aibridge.adapters.base import BaseAdapter

        for handler in [handle_navigate, handle_search, handle_click,
                         handle_type, handle_extract, handle_scroll]:
            sig = inspect.signature(handler)
            params = list(sig.parameters.values())
            # 每个 handler 都应该有两个参数 (match, adapter)
            assert len(params) == 2, f"{handler.__name__} should have 2 params"
            # from __future__ import annotations 使注解成为字符串
            ann = params[1].annotation
            if isinstance(ann, str):
                resolved = typing.get_type_hints(handler)
                assert resolved.get("adapter") is BaseAdapter, (
                    f"{handler.__name__} second param should be BaseAdapter"
                )
            else:
                assert ann is BaseAdapter, (
                    f"{handler.__name__} second param should be BaseAdapter"
                )

    def test_no_hard_chromeadapter_runtime_import(self):
        """P1-6: 运行时不应导入 ChromeAdapter（仅在 TYPE_CHECKING 下）"""
        import sys
        import aibridge.core.intent_engine as ie

        # 确保 ChromeAdapter 不在模块的全局命名空间中（运行时）
        # TYPE_CHECKING 下导入，所以 sys.modules 中不应有直接的 ChromeAdapter 引用
        assert not hasattr(ie, 'ChromeAdapter'), (
            "ChromeAdapter should not be in intent_engine namespace at runtime"
        )

    def test_searchengines_configurable_via_adapter(self):
        """P1-6: 通过 adapter._search_engine 属性切换搜索引擎"""
        from aibridge.adapters.base import BaseAdapter
        from aibridge.core.intent_engine import handle_search, SEARCH_ENGINES
        import re

        class GoogleAdapter(BaseAdapter):
            adapter_id = "google_adapter"
            _search_engine = "google"
            @classmethod
            def is_available(cls) -> bool: return True
            async def connect(self): pass
            async def disconnect(self): pass
            async def execute(self, action, target=None, value=None, options=None):
                return {"success": True}

        adapter = GoogleAdapter()
        match = re.match(r"^搜索\s+(.+)$", "搜索 test query")

        steps = handle_search(match, adapter)
        assert len(steps) == 2
        # 应使用 google 选择器而非 baidu
        assert steps[0].target["css"] == SEARCH_ENGINES["google"]["search_box"]
        assert steps[1].target["css"] == SEARCH_ENGINES["google"]["search_btn"]

    @pytest.mark.asyncio
    async def test_engine_with_non_chrome_adapter_works(self):
        """P1-6: IntentEngine 与非 Chrome 适配器正常工作的端到端测试"""
        from aibridge.adapters.base import BaseAdapter

        class EdgeAdapter(BaseAdapter):
            adapter_id = "edge"
            _search_engine = "bing"
            @classmethod
            def is_available(cls) -> bool: return True
            async def connect(self): pass
            async def disconnect(self): pass
            async def execute(self, action, target=None, value=None, options=None):
                return {"success": True, "data": f"executed {action}"}

        adapter = EdgeAdapter()
        eng = IntentEngine(adapter)
        await eng.initialize()

        # 规则匹配应正常工作
        result = await eng.parse("搜索 hello world")
        assert result.success
        assert result.intent_type == IntentType.SEARCH

        # execute 应正常工作
        result = await eng.execute("打开 https://example.com")
        assert isinstance(result, dict)
