"""
分布式链路追踪模块

提供 OpenTelemetry 兼容的追踪能力：
- Tracer: 追踪器，管理 Span 生命周期
- Span: 调用跨度，记录操作耗时和上下文
- SpanContext: 跨进程传播的上下文
- TracingMiddleware: 自动追踪中间件

设计原则：
- OpenTelemetry 兼容（可导出到 Jaeger、Zipkin）
- 低侵入性（装饰器 + 中间件）
- 支持跨服务追踪（Context Propagation）
"""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# 当前 Span 上下文（线程/协程安全）
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)


class SpanKind(Enum):
    """Span 类型"""
    INTERNAL = "internal"   # 内部操作
    CLIENT = "client"       # 客户端请求
    SERVER = "server"       # 服务端处理
    PRODUCER = "producer"   # 消息生产者
    CONSUMER = "consumer"   # 消息消费者


class SpanStatus(Enum):
    """Span 状态"""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


@dataclass
class SpanContext:
    """
    Span 上下文（用于跨进程传播）
    
    遵循 W3C Trace Context 标准。
    """
    trace_id: str           # 全局唯一追踪 ID
    span_id: str            # 当前 Span ID
    parent_span_id: Optional[str] = None  # 父 Span ID
    trace_flags: int = 1    # 追踪标志 (1 = sampled)
    trace_state: str = ""   # 追踪状态
    
    def to_traceparent(self) -> str:
        """转换为 W3C traceparent 格式"""
        # 格式: version-trace_id-span_id-flags
        return f"00-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}"
    
    @classmethod
    def from_traceparent(cls, header: str) -> Optional["SpanContext"]:
        """从 W3C traceparent 解析"""
        try:
            parts = header.split("-")
            if len(parts) != 4:
                return None
            version, trace_id, span_id, flags = parts
            return cls(
                trace_id=trace_id,
                span_id=span_id,
                trace_flags=int(flags, 16),
            )
        except Exception:
            return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "trace_flags": self.trace_flags,
            "trace_state": self.trace_state,
        }


@dataclass
class SpanEvent:
    """Span 事件"""
    name: str
    timestamp: float
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "timestamp": self.timestamp,
            "attributes": self.attributes,
        }


@dataclass
class SpanLink:
    """Span 链接（关联其他 Trace）"""
    context: SpanContext
    attributes: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "context": self.context.to_dict(),
            "attributes": self.attributes,
        }


class Span:
    """
    调用跨度
    
    记录一个操作的开始、结束、属性和事件。
    
    使用示例：
    ```python
    with tracer.start_span("process_request") as span:
        span.set_attribute("user_id", "alice")
        span.add_event("started_processing")
        
        # 嵌套 Span
        with tracer.start_span("database_query") as child:
            child.set_attribute("query", "SELECT ...")
            result = db.query(...)
        
        span.add_event("completed", {"items": len(result)})
    ```
    """
    
    def __init__(
        self,
        name: str,
        context: SpanContext,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional["Span"] = None,
        start_time: Optional[float] = None,
    ):
        self.name = name
        self.context = context
        self.kind = kind
        self.parent = parent
        
        self.start_time = start_time or time.time()
        self.end_time: Optional[float] = None
        
        self.status = SpanStatus.UNSET
        self.status_message: str = ""
        
        self.attributes: Dict[str, Any] = {}
        self.events: List[SpanEvent] = []
        self.links: List[SpanLink] = []
        
        self._ended = False
    
    @property
    def trace_id(self) -> str:
        return self.context.trace_id
    
    @property
    def span_id(self) -> str:
        return self.context.span_id
    
    @property
    def parent_span_id(self) -> Optional[str]:
        return self.context.parent_span_id
    
    @property
    def duration_ms(self) -> float:
        """持续时间（毫秒）"""
        if self.end_time is None:
            return (time.time() - self.start_time) * 1000
        return (self.end_time - self.start_time) * 1000
    
    @property
    def is_recording(self) -> bool:
        """是否正在记录"""
        return not self._ended
    
    def set_attribute(self, key: str, value: Any) -> "Span":
        """设置属性"""
        if self.is_recording:
            self.attributes[key] = value
        return self
    
    def set_attributes(self, attributes: Dict[str, Any]) -> "Span":
        """批量设置属性"""
        if self.is_recording:
            self.attributes.update(attributes)
        return self
    
    def add_event(
        self,
        name: str,
        attributes: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
    ) -> "Span":
        """添加事件"""
        if self.is_recording:
            self.events.append(SpanEvent(
                name=name,
                timestamp=timestamp or time.time(),
                attributes=attributes or {},
            ))
        return self
    
    def add_link(
        self,
        context: SpanContext,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> "Span":
        """添加链接"""
        if self.is_recording:
            self.links.append(SpanLink(
                context=context,
                attributes=attributes or {},
            ))
        return self
    
    def set_status(self, status: SpanStatus, message: str = "") -> "Span":
        """设置状态"""
        if self.is_recording:
            self.status = status
            self.status_message = message
        return self
    
    def record_exception(
        self,
        exception: Exception,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> "Span":
        """记录异常"""
        if self.is_recording:
            self.set_status(SpanStatus.ERROR, str(exception))
            exc_attrs = {
                "exception.type": type(exception).__name__,
                "exception.message": str(exception),
                **(attributes or {}),
            }
            self.add_event("exception", exc_attrs)
        return self
    
    def end(self, end_time: Optional[float] = None) -> None:
        """结束 Span"""
        if not self._ended:
            self.end_time = end_time or time.time()
            self._ended = True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于导出）"""
        return {
            "name": self.name,
            "context": self.context.to_dict(),
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": [e.to_dict() for e in self.events],
            "links": [l.to_dict() for l in self.links],
        }
    
    def __enter__(self) -> "Span":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_val:
            self.record_exception(exc_val)
        self.end()


class SpanExporter:
    """
    Span 导出器基类
    
    实现此接口将 Span 导出到外部系统。
    """
    
    async def export(self, spans: List[Span]) -> bool:
        """导出 Spans"""
        raise NotImplementedError
    
    async def shutdown(self) -> None:
        """关闭导出器"""
        pass


class ConsoleExporter(SpanExporter):
    """控制台导出器（用于调试）"""
    
    def __init__(self, pretty: bool = True):
        self._pretty = pretty
    
    async def export(self, spans: List[Span]) -> bool:
        import json
        for span in spans:
            data = span.to_dict()
            if self._pretty:
                print(json.dumps(data, indent=2, default=str))
            else:
                print(json.dumps(data, default=str))
        return True


class InMemoryExporter(SpanExporter):
    """内存导出器（用于测试）"""
    
    def __init__(self, max_spans: int = 1000):
        self._spans: List[Dict[str, Any]] = []
        self._max_spans = max_spans
    
    async def export(self, spans: List[Span]) -> bool:
        for span in spans:
            self._spans.append(span.to_dict())
            if len(self._spans) > self._max_spans:
                self._spans.pop(0)
        return True
    
    def get_spans(self) -> List[Dict[str, Any]]:
        """获取所有 Spans"""
        return list(self._spans)
    
    def clear(self) -> None:
        """清空 Spans"""
        self._spans.clear()
    
    def find_spans(
        self,
        name: Optional[str] = None,
        trace_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """查找 Spans"""
        results = []
        for span in self._spans:
            if name and span["name"] != name:
                continue
            if trace_id and span["context"]["trace_id"] != trace_id:
                continue
            results.append(span)
        return results


class OTLPExporter(SpanExporter):
    """
    OpenTelemetry Protocol 导出器
    
    支持导出到 Jaeger、Zipkin、OTLP 收集器等。
    """
    
    def __init__(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: float = 10.0,
    ):
        self._endpoint = endpoint
        self._headers = headers or {}
        self._timeout = timeout
    
    async def export(self, spans: List[Span]) -> bool:
        """导出到 OTLP 收集器"""
        try:
            import aiohttp
            
            # 转换为 OTLP 格式
            otlp_spans = []
            for span in spans:
                otlp_spans.append({
                    "traceId": span.trace_id,
                    "spanId": span.span_id,
                    "parentSpanId": span.parent_span_id,
                    "name": span.name,
                    "kind": span.kind.value,
                    "startTimeUnixNano": int(span.start_time * 1e9),
                    "endTimeUnixNano": int((span.end_time or time.time()) * 1e9),
                    "attributes": [
                        {"key": k, "value": {"stringValue": str(v)}}
                        for k, v in span.attributes.items()
                    ],
                    "status": {"code": span.status.value},
                })
            
            payload = {
                "resourceSpans": [{
                    "scopeSpans": [{
                        "spans": otlp_spans
                    }]
                }]
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._endpoint,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        **self._headers,
                    },
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                ) as resp:
                    return resp.status == 200
                    
        except ImportError:
            logger.warning("aiohttp not installed, OTLP export disabled")
            return False
        except Exception as e:
            logger.error(f"OTLP export failed: {e}")
            return False


@dataclass
class TracerConfig:
    """追踪器配置"""
    service_name: str = "ai-bridge"
    service_version: str = "1.0.0"
    
    # 采样配置
    sample_rate: float = 1.0  # 1.0 = 100% 采样
    
    # 缓冲配置
    batch_size: int = 100     # 批量导出大小
    flush_interval: float = 5.0  # 刷新间隔（秒）
    
    # 属性
    resource_attributes: Dict[str, str] = field(default_factory=dict)


class Tracer:
    """
    追踪器
    
    管理 Span 的创建、嵌套和导出。
    
    使用示例：
    ```python
    # 创建追踪器
    tracer = Tracer(TracerConfig(service_name="my-service"))
    tracer.add_exporter(ConsoleExporter())
    await tracer.start()
    
    # 手动创建 Span
    with tracer.start_span("operation") as span:
        span.set_attribute("key", "value")
        # ... 执行操作
    
    # 使用装饰器
    @tracer.trace("my_function")
    async def my_function():
        # ... 自动追踪
    
    await tracer.stop()
    ```
    """
    
    def __init__(self, config: Optional[TracerConfig] = None):
        self._config = config or TracerConfig()
        self._exporters: List[SpanExporter] = []
        self._pending_spans: List[Span] = []
        self._lock = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        
        # 线程安全的随机数生成器（用于采样）
        import random
        import threading
        self._random = random.Random()
        self._random_lock = threading.Lock()
    
    def add_exporter(self, exporter: SpanExporter) -> None:
        """添加导出器"""
        self._exporters.append(exporter)
    
    def remove_exporter(self, exporter: SpanExporter) -> None:
        """移除导出器"""
        if exporter in self._exporters:
            self._exporters.remove(exporter)
    
    async def start(self) -> None:
        """启动追踪器"""
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info(f"Tracer started for service: {self._config.service_name}")
    
    async def stop(self) -> None:
        """停止追踪器"""
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # 最终刷新
        await self._flush()
        
        # 关闭导出器
        for exporter in self._exporters:
            await exporter.shutdown()
        
        logger.info("Tracer stopped")
    
    def _should_sample(self) -> bool:
        """是否采样（线程安全）"""
        with self._random_lock:
            return self._random.random() < self._config.sample_rate
    
    def _generate_id(self, length: int = 16) -> str:
        """生成 ID"""
        return uuid.uuid4().hex[:length]
    
    def _generate_trace_id(self) -> str:
        """生成 Trace ID (32 字符)"""
        return uuid.uuid4().hex
    
    def _generate_span_id(self) -> str:
        """生成 Span ID (16 字符)"""
        return uuid.uuid4().hex[:16]
    
    def get_current_span(self) -> Optional[Span]:
        """获取当前 Span"""
        return _current_span.get()
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[Union[Span, SpanContext]] = None,
        links: Optional[List[SpanLink]] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> Span:
        """
        创建新 Span
        
        Args:
            name: Span 名称
            kind: Span 类型
            parent: 父 Span 或父上下文
            links: 关联链接
            attributes: 初始属性
            
        Returns:
            新创建的 Span
        """
        # 检查采样
        if not self._should_sample():
            # 返回一个不记录的 Span
            return Span(
                name=name,
                context=SpanContext(
                    trace_id="0" * 32,
                    span_id="0" * 16,
                ),
            )
        
        # 确定父 Span
        if parent is None:
            parent = self.get_current_span()
        
        # 确定 trace_id 和 parent_span_id
        if parent:
            if isinstance(parent, Span):
                trace_id = parent.trace_id
                parent_span_id = parent.span_id
            else:
                trace_id = parent.trace_id
                parent_span_id = parent.span_id
        else:
            trace_id = self._generate_trace_id()
            parent_span_id = None
        
        # 创建 Span
        span = Span(
            name=name,
            context=SpanContext(
                trace_id=trace_id,
                span_id=self._generate_span_id(),
                parent_span_id=parent_span_id,
            ),
            kind=kind,
            parent=parent if isinstance(parent, Span) else None,
        )
        
        # 设置服务属性
        span.set_attributes({
            "service.name": self._config.service_name,
            "service.version": self._config.service_version,
            **self._config.resource_attributes,
            **(attributes or {}),
        })
        
        # 添加链接
        if links:
            for link in links:
                span.add_link(link.context, link.attributes)
        
        return span
    
    @contextmanager
    def start_as_current_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        **kwargs
    ):
        """创建 Span 并设为当前（同步上下文管理器）"""
        span = self.start_span(name, kind, **kwargs)
        token = _current_span.set(span)
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            span.end()
            _current_span.reset(token)
            self._add_pending_span(span)
    
    @asynccontextmanager
    async def start_as_current_span_async(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        **kwargs
    ):
        """创建 Span 并设为当前（异步上下文管理器）"""
        span = self.start_span(name, kind, **kwargs)
        token = _current_span.set(span)
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            raise
        finally:
            span.end()
            _current_span.reset(token)
            self._add_pending_span(span)
    
    def _add_pending_span(self, span: Span) -> None:
        """添加待导出的 Span"""
        self._pending_spans.append(span)
        
        # 检查是否需要立即刷新
        if len(self._pending_spans) >= self._config.batch_size:
            asyncio.create_task(self._flush())
    
    async def _flush(self) -> None:
        """刷新待导出的 Spans"""
        async with self._lock:
            if not self._pending_spans:
                return
            
            spans_to_export = self._pending_spans
            self._pending_spans = []
        
        # 导出到所有导出器
        for exporter in self._exporters:
            try:
                await exporter.export(spans_to_export)
            except Exception as e:
                logger.error(f"Failed to export spans: {e}")
    
    async def _periodic_flush(self) -> None:
        """定期刷新"""
        while self._running:
            try:
                await asyncio.sleep(self._config.flush_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Periodic flush error: {e}")
    
    def trace(
        self,
        name: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: Optional[Dict[str, Any]] = None,
    ):
        """
        追踪装饰器
        
        ```python
        @tracer.trace("my_operation")
        async def my_operation(param):
            # 自动追踪
            pass
        ```
        """
        def decorator(func: Callable):
            span_name = name or func.__name__
            
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    async with self.start_as_current_span_async(
                        span_name, kind, attributes=attributes
                    ) as span:
                        span.set_attribute("function", func.__name__)
                        return await func(*args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    with self.start_as_current_span(
                        span_name, kind, attributes=attributes
                    ) as span:
                        span.set_attribute("function", func.__name__)
                        return func(*args, **kwargs)
                return sync_wrapper
        
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """获取追踪器统计"""
        return {
            "service_name": self._config.service_name,
            "running": self._running,
            "pending_spans": len(self._pending_spans),
            "exporters": len(self._exporters),
            "sample_rate": self._config.sample_rate,
        }


class TracingMiddleware:
    """
    追踪中间件
    
    自动为工具调用创建 Span。
    
    使用示例：
    ```python
    tracer = Tracer()
    middleware = TracingMiddleware(tracer)
    
    # 包装工具调用
    async def call_tool(name, params):
        async with middleware.trace_tool_call(name, params) as span:
            result = await actual_call(name, params)
            span.set_attribute("result_size", len(str(result)))
            return result
    ```
    """
    
    def __init__(self, tracer: Tracer):
        self._tracer = tracer
    
    @asynccontextmanager
    async def trace_tool_call(
        self,
        tool_name: str,
        params: Dict[str, Any],
        server_name: Optional[str] = None,
    ):
        """追踪工具调用"""
        async with self._tracer.start_as_current_span_async(
            f"tool:{tool_name}",
            kind=SpanKind.CLIENT,
            attributes={
                "tool.name": tool_name,
                "tool.server": server_name or "unknown",
                "tool.params_keys": list(params.keys()),
            }
        ) as span:
            yield span
    
    @asynccontextmanager
    async def trace_a2a_task(
        self,
        task_id: str,
        from_agent: str,
        to_agent: str,
        capability: str,
    ):
        """追踪 A2A 任务"""
        async with self._tracer.start_as_current_span_async(
            f"a2a:{capability}",
            kind=SpanKind.CLIENT,
            attributes={
                "a2a.task_id": task_id,
                "a2a.from_agent": from_agent,
                "a2a.to_agent": to_agent,
                "a2a.capability": capability,
            }
        ) as span:
            yield span
    
    @asynccontextmanager
    async def trace_mcp_call(
        self,
        server_name: str,
        method: str,
        tool_name: Optional[str] = None,
    ):
        """追踪 MCP 调用"""
        name = f"mcp:{server_name}/{method}"
        if tool_name:
            name = f"mcp:{server_name}/{tool_name}"
        
        async with self._tracer.start_as_current_span_async(
            name,
            kind=SpanKind.CLIENT,
            attributes={
                "mcp.server": server_name,
                "mcp.method": method,
                "mcp.tool": tool_name,
            }
        ) as span:
            yield span
    
    def extract_context(self, headers: Dict[str, str]) -> Optional[SpanContext]:
        """从请求头提取上下文"""
        traceparent = headers.get("traceparent")
        if traceparent:
            return SpanContext.from_traceparent(traceparent)
        return None
    
    def inject_context(self, headers: Dict[str, str]) -> Dict[str, str]:
        """注入上下文到请求头"""
        span = self._tracer.get_current_span()
        if span:
            headers["traceparent"] = span.context.to_traceparent()
        return headers


# ===== 全局追踪器实例 =====

_global_tracer: Optional[Tracer] = None


def get_tracer() -> Tracer:
    """获取全局追踪器"""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer()
    return _global_tracer


def set_tracer(tracer: Tracer) -> None:
    """设置全局追踪器"""
    global _global_tracer
    _global_tracer = tracer
