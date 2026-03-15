"""
测试 tracing.py - 分布式链路追踪模块
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

from aibridge.enterprise.tracing import (
    Tracer,
    TracerConfig,
    Span,
    SpanContext,
    SpanKind,
    SpanStatus,
    SpanEvent,
    SpanLink,
    SpanExporter,
    ConsoleExporter,
    InMemoryExporter,
    TracingMiddleware,
    get_tracer,
    set_tracer,
)


# ===== SpanContext Tests =====

class TestSpanContext:
    """测试 Span 上下文"""
    
    def test_to_traceparent(self):
        """测试转换为 traceparent 格式"""
        ctx = SpanContext(
            trace_id="0123456789abcdef0123456789abcdef",
            span_id="0123456789abcdef",
            trace_flags=1,
        )
        
        tp = ctx.to_traceparent()
        assert tp == "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"
    
    def test_from_traceparent(self):
        """测试从 traceparent 解析"""
        tp = "00-0123456789abcdef0123456789abcdef-fedcba9876543210-01"
        
        ctx = SpanContext.from_traceparent(tp)
        
        assert ctx is not None
        assert ctx.trace_id == "0123456789abcdef0123456789abcdef"
        assert ctx.span_id == "fedcba9876543210"
        assert ctx.trace_flags == 1
    
    def test_from_invalid_traceparent(self):
        """测试解析无效 traceparent"""
        ctx = SpanContext.from_traceparent("invalid")
        assert ctx is None
        
        ctx = SpanContext.from_traceparent("")
        assert ctx is None
    
    def test_to_dict(self):
        """测试转换为字典"""
        ctx = SpanContext(
            trace_id="abc",
            span_id="def",
            parent_span_id="parent",
        )
        
        d = ctx.to_dict()
        
        assert d["trace_id"] == "abc"
        assert d["span_id"] == "def"
        assert d["parent_span_id"] == "parent"


# ===== Span Tests =====

class TestSpan:
    """测试 Span"""
    
    def test_span_creation(self):
        """测试 Span 创建"""
        ctx = SpanContext(trace_id="trace1", span_id="span1")
        span = Span(name="test", context=ctx)
        
        assert span.name == "test"
        assert span.trace_id == "trace1"
        assert span.span_id == "span1"
        assert span.is_recording is True
    
    def test_span_attributes(self):
        """测试 Span 属性"""
        ctx = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=ctx)
        
        span.set_attribute("key1", "value1")
        span.set_attributes({"key2": 123, "key3": True})
        
        assert span.attributes["key1"] == "value1"
        assert span.attributes["key2"] == 123
        assert span.attributes["key3"] is True
    
    def test_span_events(self):
        """测试 Span 事件"""
        ctx = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=ctx)
        
        span.add_event("event1")
        span.add_event("event2", {"detail": "info"})
        
        assert len(span.events) == 2
        assert span.events[0].name == "event1"
        assert span.events[1].attributes["detail"] == "info"
    
    def test_span_status(self):
        """测试 Span 状态"""
        ctx = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=ctx)
        
        span.set_status(SpanStatus.OK, "success")
        
        assert span.status == SpanStatus.OK
        assert span.status_message == "success"
    
    def test_record_exception(self):
        """测试记录异常"""
        ctx = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=ctx)
        
        try:
            raise ValueError("test error")
        except ValueError as e:
            span.record_exception(e)
        
        assert span.status == SpanStatus.ERROR
        assert len(span.events) == 1
        assert span.events[0].name == "exception"
        assert span.events[0].attributes["exception.type"] == "ValueError"
    
    def test_span_end(self):
        """测试 Span 结束"""
        ctx = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=ctx)
        
        assert span.end_time is None
        assert span.is_recording is True
        
        span.end()
        
        assert span.end_time is not None
        assert span.is_recording is False
        assert span.duration_ms >= 0
    
    def test_span_context_manager(self):
        """测试 Span 上下文管理器"""
        ctx = SpanContext(trace_id="t", span_id="s")
        
        with Span(name="test", context=ctx) as span:
            span.set_attribute("inside", True)
        
        assert span.is_recording is False
        assert span.end_time is not None
    
    def test_span_to_dict(self):
        """测试转换为字典"""
        ctx = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=ctx, kind=SpanKind.CLIENT)
        span.set_attribute("key", "value")
        span.add_event("event")
        span.end()
        
        d = span.to_dict()
        
        assert d["name"] == "test"
        assert d["kind"] == "client"
        assert d["attributes"]["key"] == "value"
        assert len(d["events"]) == 1


# ===== Exporter Tests =====

class TestExporters:
    """测试导出器"""
    
    @pytest.mark.asyncio
    async def test_in_memory_exporter(self):
        """测试内存导出器"""
        exporter = InMemoryExporter(max_spans=10)
        
        ctx = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=ctx)
        span.end()
        
        success = await exporter.export([span])
        
        assert success is True
        assert len(exporter.get_spans()) == 1
    
    @pytest.mark.asyncio
    async def test_in_memory_exporter_max_spans(self):
        """测试内存导出器最大限制"""
        exporter = InMemoryExporter(max_spans=3)
        
        for i in range(5):
            ctx = SpanContext(trace_id=f"t{i}", span_id=f"s{i}")
            span = Span(name=f"test{i}", context=ctx)
            span.end()
            await exporter.export([span])
        
        # 应该只保留最后 3 个
        assert len(exporter.get_spans()) == 3
    
    @pytest.mark.asyncio
    async def test_in_memory_exporter_find(self):
        """测试内存导出器查找"""
        exporter = InMemoryExporter()
        
        ctx1 = SpanContext(trace_id="trace1", span_id="s1")
        span1 = Span(name="search", context=ctx1)
        span1.end()
        
        ctx2 = SpanContext(trace_id="trace2", span_id="s2")
        span2 = Span(name="process", context=ctx2)
        span2.end()
        
        await exporter.export([span1, span2])
        
        # 按名称查找
        found = exporter.find_spans(name="search")
        assert len(found) == 1
        assert found[0]["name"] == "search"
        
        # 按 trace_id 查找
        found = exporter.find_spans(trace_id="trace2")
        assert len(found) == 1
        assert found[0]["context"]["trace_id"] == "trace2"
    
    @pytest.mark.asyncio
    async def test_in_memory_exporter_clear(self):
        """测试清空导出器"""
        exporter = InMemoryExporter()
        
        ctx = SpanContext(trace_id="t", span_id="s")
        span = Span(name="test", context=ctx)
        span.end()
        await exporter.export([span])
        
        assert len(exporter.get_spans()) == 1
        
        exporter.clear()
        
        assert len(exporter.get_spans()) == 0


# ===== Tracer Tests =====

class TestTracer:
    """测试追踪器"""
    
    @pytest.mark.asyncio
    async def test_tracer_lifecycle(self):
        """测试追踪器生命周期"""
        tracer = Tracer(TracerConfig(service_name="test-service"))
        
        await tracer.start()
        assert tracer._running is True
        
        await tracer.stop()
        assert tracer._running is False
    
    @pytest.mark.asyncio
    async def test_create_span(self):
        """测试创建 Span"""
        tracer = Tracer()
        
        span = tracer.start_span("test-operation")
        
        assert span.name == "test-operation"
        assert span.trace_id is not None
        assert span.span_id is not None
    
    @pytest.mark.asyncio
    async def test_nested_spans(self):
        """测试嵌套 Span"""
        tracer = Tracer()
        
        parent = tracer.start_span("parent")
        child = tracer.start_span("child", parent=parent)
        
        assert child.context.parent_span_id == parent.span_id
        assert child.trace_id == parent.trace_id
    
    @pytest.mark.asyncio
    async def test_start_as_current_span(self):
        """测试设置当前 Span"""
        tracer = Tracer()
        await tracer.start()
        
        try:
            with tracer.start_as_current_span("outer") as outer:
                assert tracer.get_current_span() == outer
                
                with tracer.start_as_current_span("inner") as inner:
                    assert tracer.get_current_span() == inner
                    assert inner.context.parent_span_id == outer.span_id
                
                assert tracer.get_current_span() == outer
            
            assert tracer.get_current_span() is None
        finally:
            await tracer.stop()
    
    @pytest.mark.asyncio
    async def test_trace_decorator(self):
        """测试追踪装饰器"""
        tracer = Tracer()
        exporter = InMemoryExporter()
        tracer.add_exporter(exporter)
        await tracer.start()
        
        try:
            @tracer.trace("decorated_function")
            async def my_function(x):
                return x * 2
            
            result = await my_function(5)
            
            assert result == 10
            
            # 等待刷新
            await asyncio.sleep(0.1)
            await tracer._flush()
            
            spans = exporter.get_spans()
            assert len(spans) >= 1
            assert spans[0]["name"] == "decorated_function"
        finally:
            await tracer.stop()
    
    @pytest.mark.asyncio
    async def test_sampling(self):
        """测试采样"""
        tracer = Tracer(TracerConfig(sample_rate=0.0))  # 0% 采样
        
        span = tracer.start_span("test")
        
        # 不采样时 trace_id 全 0
        assert span.trace_id == "0" * 32
    
    def test_stats(self):
        """测试统计信息"""
        tracer = Tracer(TracerConfig(
            service_name="test",
            sample_rate=0.5,
        ))
        
        stats = tracer.get_stats()
        
        assert stats["service_name"] == "test"
        assert stats["sample_rate"] == 0.5


# ===== TracingMiddleware Tests =====

class TestTracingMiddleware:
    """测试追踪中间件"""
    
    @pytest.mark.asyncio
    async def test_trace_tool_call(self):
        """测试追踪工具调用"""
        tracer = Tracer()
        exporter = InMemoryExporter()
        tracer.add_exporter(exporter)
        await tracer.start()
        
        try:
            middleware = TracingMiddleware(tracer)
            
            async with middleware.trace_tool_call(
                "browser/navigate",
                {"url": "https://example.com"},
                server_name="browser-use"
            ) as span:
                span.set_attribute("status", "success")
            
            await tracer._flush()
            
            spans = exporter.get_spans()
            assert len(spans) >= 1
            assert spans[0]["name"] == "tool:browser/navigate"
            assert spans[0]["attributes"]["tool.name"] == "browser/navigate"
        finally:
            await tracer.stop()
    
    @pytest.mark.asyncio
    async def test_trace_a2a_task(self):
        """测试追踪 A2A 任务"""
        tracer = Tracer()
        exporter = InMemoryExporter()
        tracer.add_exporter(exporter)
        await tracer.start()
        
        try:
            middleware = TracingMiddleware(tracer)
            
            async with middleware.trace_a2a_task(
                task_id="task-123",
                from_agent="orchestrator",
                to_agent="search-agent",
                capability="web_search"
            ) as span:
                pass
            
            await tracer._flush()
            
            spans = exporter.get_spans()
            assert len(spans) >= 1
            assert spans[0]["attributes"]["a2a.task_id"] == "task-123"
        finally:
            await tracer.stop()
    
    def test_extract_inject_context(self):
        """测试上下文提取和注入"""
        tracer = Tracer()
        middleware = TracingMiddleware(tracer)
        
        # 创建 Span 并设为当前
        with tracer.start_as_current_span("test"):
            headers = {}
            middleware.inject_context(headers)
            
            assert "traceparent" in headers
            
            # 提取
            ctx = middleware.extract_context(headers)
            assert ctx is not None
            assert ctx.trace_id is not None


# ===== Global Tracer Tests =====

class TestGlobalTracer:
    """测试全局追踪器"""
    
    def test_get_set_tracer(self):
        """测试获取/设置全局追踪器"""
        tracer = Tracer(TracerConfig(service_name="custom"))
        
        set_tracer(tracer)
        
        retrieved = get_tracer()
        assert retrieved._config.service_name == "custom"
