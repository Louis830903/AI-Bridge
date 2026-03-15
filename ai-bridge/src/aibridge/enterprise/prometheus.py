"""
Prometheus 指标模块

提供 Prometheus 兼容的指标收集和导出功能：
- Counter（计数器）
- Gauge（仪表盘）
- Histogram（直方图）
- Summary（摘要）

支持标签和多维度指标
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from contextlib import contextmanager
import time
import threading
import asyncio
import logging

logger = logging.getLogger(__name__)


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
        if not self.labels:
            return ""
        items = sorted(self.labels.items())
        return ",".join(f'{k}="{v}"' for k, v in items)
    
    def __hash__(self):
        return hash(self.key())
    
    def __eq__(self, other):
        if isinstance(other, MetricLabels):
            return self.key() == other.key()
        return False


class CounterMetric:
    """计数器指标
    
    只能增加，不能减少。适合记录请求数、错误数等。
    """
    
    def __init__(self, name: str, help_text: str, label_names: List[str] = None):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names or []
        self._values: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def inc(self, labels: MetricLabels = None, value: float = 1.0) -> None:
        """增加计数
        
        Args:
            labels: 标签
            value: 增加值（必须 > 0）
        """
        if value < 0:
            raise ValueError("Counter can only increase")
        
        key = labels.key() if labels else ""
        with self._lock:
            self._values[key] = self._values.get(key, 0) + value
    
    def get(self, labels: MetricLabels = None) -> float:
        """获取当前值"""
        key = labels.key() if labels else ""
        return self._values.get(key, 0)
    
    def labels(self, **kwargs) -> "CounterMetric":
        """创建带标签的计数器代理"""
        return _LabeledCounter(self, MetricLabels(labels=kwargs))
    
    def reset(self) -> None:
        """重置（仅用于测试）"""
        with self._lock:
            self._values.clear()


class _LabeledCounter:
    """带标签的计数器代理"""
    
    def __init__(self, counter: CounterMetric, labels: MetricLabels):
        self._counter = counter
        self._labels = labels
    
    def inc(self, value: float = 1.0) -> None:
        self._counter.inc(self._labels, value)
    
    def get(self) -> float:
        return self._counter.get(self._labels)


class GaugeMetric:
    """仪表盘指标
    
    可以增加或减少。适合记录当前连接数、内存使用等。
    """
    
    def __init__(self, name: str, help_text: str, label_names: List[str] = None):
        self.name = name
        self.help_text = help_text
        self.label_names = label_names or []
        self._values: Dict[str, float] = {}
        self._lock = threading.Lock()
    
    def set(self, value: float, labels: MetricLabels = None) -> None:
        """设置值"""
        key = labels.key() if labels else ""
        with self._lock:
            self._values[key] = value
    
    def inc(self, labels: MetricLabels = None, value: float = 1.0) -> None:
        """增加"""
        key = labels.key() if labels else ""
        with self._lock:
            self._values[key] = self._values.get(key, 0) + value
    
    def dec(self, labels: MetricLabels = None, value: float = 1.0) -> None:
        """减少"""
        key = labels.key() if labels else ""
        with self._lock:
            self._values[key] = self._values.get(key, 0) - value
    
    def get(self, labels: MetricLabels = None) -> float:
        """获取当前值"""
        key = labels.key() if labels else ""
        return self._values.get(key, 0)
    
    def labels(self, **kwargs) -> "GaugeMetric":
        """创建带标签的仪表盘代理"""
        return _LabeledGauge(self, MetricLabels(labels=kwargs))
    
    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._values.clear()


class _LabeledGauge:
    """带标签的仪表盘代理"""
    
    def __init__(self, gauge: GaugeMetric, labels: MetricLabels):
        self._gauge = gauge
        self._labels = labels
    
    def set(self, value: float) -> None:
        self._gauge.set(value, self._labels)
    
    def inc(self, value: float = 1.0) -> None:
        self._gauge.inc(self._labels, value)
    
    def dec(self, value: float = 1.0) -> None:
        self._gauge.dec(self._labels, value)
    
    def get(self) -> float:
        return self._gauge.get(self._labels)


class HistogramMetric:
    """直方图指标
    
    记录值的分布。适合记录请求延迟、响应大小等。
    """
    
    # 默认桶边界（秒）
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
    
    def __init__(
        self,
        name: str,
        help_text: str,
        buckets: tuple = None,
        label_names: List[str] = None
    ):
        self.name = name
        self.help_text = help_text
        self.buckets = tuple(sorted(buckets or self.DEFAULT_BUCKETS))
        self.label_names = label_names or []
        self._values: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
    
    def observe(self, value: float, labels: MetricLabels = None) -> None:
        """记录观测值"""
        key = labels.key() if labels else ""
        with self._lock:
            if key not in self._values:
                self._values[key] = {
                    "buckets": {b: 0 for b in self.buckets},
                    "sum": 0.0,
                    "count": 0,
                }
            data = self._values[key]
            data["sum"] += value
            data["count"] += 1
            for bucket in self.buckets:
                if value <= bucket:
                    data["buckets"][bucket] += 1
    
    @contextmanager
    def time(self, labels: MetricLabels = None):
        """计时上下文管理器
        
        用法:
            with histogram.time():
                do_something()
        """
        start = time.time()
        try:
            yield
        finally:
            self.observe(time.time() - start, labels)
    
    def get_data(self, labels: MetricLabels = None) -> Dict[str, Any]:
        """获取数据"""
        key = labels.key() if labels else ""
        return self._values.get(key, {"buckets": {}, "sum": 0, "count": 0})
    
    def labels(self, **kwargs) -> "HistogramMetric":
        """创建带标签的直方图代理"""
        return _LabeledHistogram(self, MetricLabels(labels=kwargs))
    
    def reset(self) -> None:
        """重置"""
        with self._lock:
            self._values.clear()


class _LabeledHistogram:
    """带标签的直方图代理"""
    
    def __init__(self, histogram: HistogramMetric, labels: MetricLabels):
        self._histogram = histogram
        self._labels = labels
    
    def observe(self, value: float) -> None:
        self._histogram.observe(value, self._labels)
    
    @contextmanager
    def time(self):
        with self._histogram.time(self._labels):
            yield


class PrometheusRegistry:
    """Prometheus 指标注册中心
    
    管理所有指标并提供导出功能
    """
    
    def __init__(self, prefix: str = "aibridge"):
        """
        Args:
            prefix: 指标名称前缀
        """
        self._prefix = prefix
        self._counters: Dict[str, CounterMetric] = {}
        self._gauges: Dict[str, GaugeMetric] = {}
        self._histograms: Dict[str, HistogramMetric] = {}
        self._lock = threading.Lock()
    
    def counter(
        self,
        name: str,
        help_text: str,
        label_names: List[str] = None
    ) -> CounterMetric:
        """获取或创建计数器"""
        full_name = f"{self._prefix}_{name}"
        with self._lock:
            if full_name not in self._counters:
                self._counters[full_name] = CounterMetric(
                    name=full_name,
                    help_text=help_text,
                    label_names=label_names
                )
            return self._counters[full_name]
    
    def gauge(
        self,
        name: str,
        help_text: str,
        label_names: List[str] = None
    ) -> GaugeMetric:
        """获取或创建仪表盘"""
        full_name = f"{self._prefix}_{name}"
        with self._lock:
            if full_name not in self._gauges:
                self._gauges[full_name] = GaugeMetric(
                    name=full_name,
                    help_text=help_text,
                    label_names=label_names
                )
            return self._gauges[full_name]
    
    def histogram(
        self,
        name: str,
        help_text: str,
        buckets: tuple = None,
        label_names: List[str] = None
    ) -> HistogramMetric:
        """获取或创建直方图"""
        full_name = f"{self._prefix}_{name}"
        with self._lock:
            if full_name not in self._histograms:
                self._histograms[full_name] = HistogramMetric(
                    name=full_name,
                    help_text=help_text,
                    buckets=buckets,
                    label_names=label_names
                )
            return self._histograms[full_name]
    
    def export(self) -> str:
        """导出为 Prometheus 文本格式
        
        Returns:
            Prometheus exposition format 文本
        """
        lines = []
        
        # 导出 Counters
        for name, metric in sorted(self._counters.items()):
            lines.append(f"# HELP {name} {metric.help_text}")
            lines.append(f"# TYPE {name} counter")
            for labels_key, value in sorted(metric._values.items()):
                if labels_key:
                    lines.append(f"{name}{{{labels_key}}} {value}")
                else:
                    lines.append(f"{name} {value}")
        
        # 导出 Gauges
        for name, metric in sorted(self._gauges.items()):
            lines.append(f"# HELP {name} {metric.help_text}")
            lines.append(f"# TYPE {name} gauge")
            for labels_key, value in sorted(metric._values.items()):
                if labels_key:
                    lines.append(f"{name}{{{labels_key}}} {value}")
                else:
                    lines.append(f"{name} {value}")
        
        # 导出 Histograms
        for name, metric in sorted(self._histograms.items()):
            lines.append(f"# HELP {name} {metric.help_text}")
            lines.append(f"# TYPE {name} histogram")
            for labels_key, data in sorted(metric._values.items()):
                # Buckets（累积）
                cumulative = 0
                for bucket in sorted(data["buckets"].keys()):
                    cumulative += data["buckets"][bucket]
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
    
    def reset_all(self) -> None:
        """重置所有指标（仅用于测试）"""
        for metric in self._counters.values():
            metric.reset()
        for metric in self._gauges.values():
            metric.reset()
        for metric in self._histograms.values():
            metric.reset()


# 全局 Registry 实例
_default_registry: Optional[PrometheusRegistry] = None


def get_registry() -> PrometheusRegistry:
    """获取默认 Registry"""
    global _default_registry
    if _default_registry is None:
        _default_registry = PrometheusRegistry()
    return _default_registry


def set_registry(registry: PrometheusRegistry) -> None:
    """设置默认 Registry"""
    global _default_registry
    _default_registry = registry


class AIBridgeMetrics:
    """AI-Bridge 标准指标集
    
    预定义的 AI-Bridge 核心指标
    """
    
    def __init__(self, registry: PrometheusRegistry = None):
        self._registry = registry or get_registry()
        
        # ========== 请求指标 ==========
        self.requests_total = self._registry.counter(
            "requests_total",
            "Total number of requests",
            label_names=["tool", "server"]
        )
        self.requests_failed = self._registry.counter(
            "requests_failed_total",
            "Total number of failed requests",
            label_names=["tool", "server", "error_type"]
        )
        
        # ========== 延迟指标 ==========
        self.request_duration = self._registry.histogram(
            "request_duration_seconds",
            "Request duration in seconds",
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
            label_names=["tool", "server"]
        )
        
        # ========== Agent 指标 ==========
        self.agents_registered = self._registry.gauge(
            "agents_registered",
            "Number of registered agents",
            label_names=["protocol"]
        )
        self.agent_tasks_active = self._registry.gauge(
            "agent_tasks_active",
            "Number of active agent tasks",
            label_names=["agent_id"]
        )
        self.agent_tasks_total = self._registry.counter(
            "agent_tasks_total",
            "Total agent tasks",
            label_names=["agent_id", "status"]
        )
        
        # ========== MCP 指标 ==========
        self.mcp_servers_connected = self._registry.gauge(
            "mcp_servers_connected",
            "Number of connected MCP servers"
        )
        self.mcp_tool_calls = self._registry.counter(
            "mcp_tool_calls_total",
            "Total MCP tool calls",
            label_names=["server", "tool"]
        )
        
        # ========== 企业级指标 ==========
        self.policy_evaluations = self._registry.counter(
            "policy_evaluations_total",
            "Total policy evaluations",
            label_names=["tool", "result"]
        )
        self.policy_denials = self._registry.counter(
            "policy_denials_total",
            "Total policy denials",
            label_names=["tool", "reason"]
        )
        self.quota_exceeded = self._registry.counter(
            "quota_exceeded_total",
            "Total quota exceeded events",
            label_names=["user", "quota_type"]
        )
        
        # ========== 资源指标 ==========
        self.memory_usage_bytes = self._registry.gauge(
            "memory_usage_bytes",
            "Memory usage in bytes"
        )
        self.cache_size = self._registry.gauge(
            "cache_size",
            "Cache size",
            label_names=["cache_name"]
        )
        self.cache_hits = self._registry.counter(
            "cache_hits_total",
            "Cache hits",
            label_names=["cache_name"]
        )
        self.cache_misses = self._registry.counter(
            "cache_misses_total",
            "Cache misses",
            label_names=["cache_name"]
        )
    
    def record_request(
        self,
        tool: str,
        server: str,
        success: bool,
        duration: float,
        error_type: str = None
    ) -> None:
        """记录请求
        
        Args:
            tool: 工具名称
            server: 服务器名称
            success: 是否成功
            duration: 耗时（秒）
            error_type: 错误类型（可选）
        """
        labels = MetricLabels(labels={"tool": tool, "server": server})
        self.requests_total.inc(labels)
        self.request_duration.observe(duration, labels)
        
        if not success:
            error_labels = MetricLabels(labels={
                "tool": tool,
                "server": server,
                "error_type": error_type or "unknown"
            })
            self.requests_failed.inc(error_labels)
    
    def record_policy_evaluation(
        self,
        tool: str,
        allowed: bool,
        denial_reason: str = None
    ) -> None:
        """记录策略评估
        
        Args:
            tool: 工具名称
            allowed: 是否允许
            denial_reason: 拒绝原因（可选）
        """
        result = "allow" if allowed else "deny"
        self.policy_evaluations.inc(MetricLabels(labels={"tool": tool, "result": result}))
        
        if not allowed:
            self.policy_denials.inc(MetricLabels(labels={
                "tool": tool,
                "reason": denial_reason or "policy_denied"
            }))
    
    def record_mcp_tool_call(self, server: str, tool: str) -> None:
        """记录 MCP 工具调用"""
        self.mcp_tool_calls.inc(MetricLabels(labels={"server": server, "tool": tool}))
    
    def record_agent_task(self, agent_id: str, status: str) -> None:
        """记录 Agent 任务"""
        self.agent_tasks_total.inc(MetricLabels(labels={
            "agent_id": agent_id,
            "status": status
        }))


class MetricsMiddleware:
    """指标收集中间件
    
    自动收集请求指标
    """
    
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
        error_type = None
        
        try:
            return await handler(*args, **kwargs)
        except Exception as e:
            success = False
            error_type = type(e).__name__
            raise
        finally:
            duration = time.time() - start_time
            self._metrics.record_request(tool, server, success, duration, error_type)


class MetricsExporter:
    """指标导出器
    
    提供 HTTP 端点导出 Prometheus 格式指标
    """
    
    def __init__(
        self,
        registry: PrometheusRegistry = None,
        port: int = 9090,
        path: str = "/metrics"
    ):
        """
        Args:
            registry: 指标注册中心
            port: HTTP 端口
            path: 指标端点路径
        """
        self._registry = registry or get_registry()
        self._port = port
        self._path = path
        self._server = None
        self._runner = None
    
    async def start(self) -> None:
        """启动 HTTP 服务器"""
        try:
            from aiohttp import web
        except ImportError:
            logger.warning("aiohttp not installed, MetricsExporter disabled")
            return
        
        app = web.Application()
        app.router.add_get(self._path, self._handle_metrics)
        app.router.add_get("/health", self._handle_health)
        
        self._runner = web.AppRunner(app)
        await self._runner.setup()
        self._server = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await self._server.start()
        
        logger.info(f"Metrics exporter started on port {self._port}")
    
    async def stop(self) -> None:
        """停止服务器"""
        if self._runner:
            await self._runner.cleanup()
        logger.info("Metrics exporter stopped")
    
    async def _handle_metrics(self, request) -> "web.Response":
        """处理指标请求"""
        from aiohttp import web
        content = self._registry.export()
        return web.Response(
            text=content,
            content_type="text/plain; charset=utf-8"
        )
    
    async def _handle_health(self, request) -> "web.Response":
        """处理健康检查请求"""
        from aiohttp import web
        return web.Response(
            text='{"status": "healthy"}',
            content_type="application/json"
        )
    
    @property
    def url(self) -> str:
        """获取指标 URL"""
        return f"http://localhost:{self._port}{self._path}"
