"""
Prometheus 模块测试

测试 Prometheus 指标收集和导出功能
"""

import pytest
import time
import threading

from aibridge.enterprise.prometheus import (
    PrometheusRegistry,
    CounterMetric,
    GaugeMetric,
    HistogramMetric,
    MetricLabels,
    MetricType,
    AIBridgeMetrics,
    MetricsMiddleware,
    get_registry,
    set_registry,
)
from aibridge.enterprise.metering_prometheus import (
    MeteringPrometheusAdapter,
    MeteringHook,
    _hash_user_id,
)


class TestMetricLabels:
    """MetricLabels 测试"""
    
    def test_empty_labels(self):
        """测试空标签"""
        labels = MetricLabels()
        assert labels.key() == ""
    
    def test_single_label(self):
        """测试单个标签"""
        labels = MetricLabels(labels={"method": "GET"})
        assert labels.key() == 'method="GET"'
    
    def test_multiple_labels(self):
        """测试多个标签（排序）"""
        labels = MetricLabels(labels={"path": "/api", "method": "GET"})
        # 按字母顺序排序
        assert labels.key() == 'method="GET",path="/api"'
    
    def test_labels_equality(self):
        """测试标签相等性"""
        labels1 = MetricLabels(labels={"a": "1", "b": "2"})
        labels2 = MetricLabels(labels={"b": "2", "a": "1"})  # 顺序不同
        assert labels1 == labels2
        assert hash(labels1) == hash(labels2)


class TestCounterMetric:
    """CounterMetric 测试"""
    
    def test_counter_increment(self):
        """测试计数器增加"""
        counter = CounterMetric("test_counter", "Test counter")
        
        counter.inc()
        assert counter.get() == 1
        
        counter.inc(value=5)
        assert counter.get() == 6
    
    def test_counter_with_labels(self):
        """测试带标签的计数器"""
        counter = CounterMetric(
            "test_counter",
            "Test counter",
            label_names=["method", "path"]
        )
        
        labels_get = MetricLabels(labels={"method": "GET", "path": "/api"})
        labels_post = MetricLabels(labels={"method": "POST", "path": "/api"})
        
        counter.inc(labels_get)
        counter.inc(labels_get)
        counter.inc(labels_post)
        
        assert counter.get(labels_get) == 2
        assert counter.get(labels_post) == 1
    
    def test_counter_labels_helper(self):
        """测试 labels() 辅助方法"""
        counter = CounterMetric(
            "test_counter",
            "Test counter",
            label_names=["method"]
        )
        
        labeled = counter.labels(method="GET")
        labeled.inc()
        labeled.inc()
        
        assert labeled.get() == 2
    
    def test_counter_cannot_decrease(self):
        """测试计数器不能减少"""
        counter = CounterMetric("test_counter", "Test counter")
        
        with pytest.raises(ValueError):
            counter.inc(value=-1)
    
    def test_counter_thread_safety(self):
        """测试线程安全"""
        counter = CounterMetric("test_counter", "Test counter")
        
        def increment():
            for _ in range(1000):
                counter.inc()
        
        threads = [threading.Thread(target=increment) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        assert counter.get() == 10000


class TestGaugeMetric:
    """GaugeMetric 测试"""
    
    def test_gauge_set(self):
        """测试仪表盘设置"""
        gauge = GaugeMetric("test_gauge", "Test gauge")
        
        gauge.set(10)
        assert gauge.get() == 10
        
        gauge.set(5)
        assert gauge.get() == 5
    
    def test_gauge_inc_dec(self):
        """测试仪表盘增减"""
        gauge = GaugeMetric("test_gauge", "Test gauge")
        
        gauge.set(10)
        gauge.inc()
        assert gauge.get() == 11
        
        gauge.dec(value=3)
        assert gauge.get() == 8
    
    def test_gauge_with_labels(self):
        """测试带标签的仪表盘"""
        gauge = GaugeMetric(
            "connections",
            "Active connections",
            label_names=["server"]
        )
        
        labels1 = MetricLabels(labels={"server": "server1"})
        labels2 = MetricLabels(labels={"server": "server2"})
        
        gauge.set(10, labels1)
        gauge.set(20, labels2)
        
        assert gauge.get(labels1) == 10
        assert gauge.get(labels2) == 20


class TestHistogramMetric:
    """HistogramMetric 测试"""
    
    def test_histogram_observe(self):
        """测试直方图观测"""
        histogram = HistogramMetric(
            "latency",
            "Request latency",
            buckets=(0.1, 0.5, 1.0, 5.0)
        )
        
        histogram.observe(0.05)
        histogram.observe(0.3)
        histogram.observe(0.8)
        histogram.observe(2.0)
        
        data = histogram.get_data()
        assert data["count"] == 4
        assert abs(data["sum"] - 3.15) < 0.01
    
    def test_histogram_buckets(self):
        """测试直方图桶（Prometheus 是累积的）"""
        histogram = HistogramMetric(
            "latency",
            "Request latency",
            buckets=(0.1, 0.5, 1.0)
        )
        
        # 每个值会进入所有 >= value 的桶
        histogram.observe(0.05)  # 进入 0.1, 0.5, 1.0 桶
        histogram.observe(0.3)   # 进入 0.5, 1.0 桶
        histogram.observe(0.8)   # 进入 1.0 桶
        histogram.observe(2.0)   # 不进入任何桶
        
        data = histogram.get_data()
        # Prometheus 直方图是累积的
        # 0.1桶: 0.05 (1个)
        # 0.5桶: 0.05, 0.3 (2个)
        # 1.0桶: 0.05, 0.3, 0.8 (3个)
        assert data["buckets"][0.1] == 1
        assert data["buckets"][0.5] == 2
        assert data["buckets"][1.0] == 3
        assert data["count"] == 4  # 总数
    
    def test_histogram_time_context(self):
        """测试直方图计时上下文"""
        histogram = HistogramMetric("duration", "Duration")
        
        with histogram.time():
            time.sleep(0.01)
        
        data = histogram.get_data()
        assert data["count"] == 1
        assert data["sum"] >= 0.01


class TestPrometheusRegistry:
    """PrometheusRegistry 测试"""
    
    def test_create_metrics(self):
        """测试创建指标"""
        registry = PrometheusRegistry(prefix="test")
        
        counter = registry.counter("requests", "Total requests")
        gauge = registry.gauge("connections", "Active connections")
        histogram = registry.histogram("latency", "Request latency")
        
        assert counter.name == "test_requests"
        assert gauge.name == "test_connections"
        assert histogram.name == "test_latency"
    
    def test_get_same_metric(self):
        """测试获取同一指标"""
        registry = PrometheusRegistry(prefix="test")
        
        counter1 = registry.counter("requests", "Total requests")
        counter2 = registry.counter("requests", "Total requests")
        
        # 应该是同一个对象
        assert counter1 is counter2
    
    def test_export_format(self):
        """测试导出格式"""
        registry = PrometheusRegistry(prefix="test")
        
        counter = registry.counter("requests_total", "Total requests")
        counter.inc()
        
        gauge = registry.gauge("temperature", "Current temperature")
        gauge.set(25.5)
        
        output = registry.export()
        
        # 验证格式
        assert "# HELP test_requests_total Total requests" in output
        assert "# TYPE test_requests_total counter" in output
        assert "test_requests_total 1" in output
        assert "test_temperature 25.5" in output
    
    def test_export_histogram(self):
        """测试导出直方图"""
        registry = PrometheusRegistry(prefix="test")
        
        histogram = registry.histogram(
            "latency",
            "Request latency",
            buckets=(0.1, 0.5, 1.0)
        )
        histogram.observe(0.3)
        histogram.observe(0.8)
        
        output = registry.export()
        
        assert "# TYPE test_latency histogram" in output
        assert "test_latency_bucket" in output
        assert "test_latency_sum" in output
        assert "test_latency_count" in output
    
    def test_export_with_labels(self):
        """测试带标签的导出"""
        registry = PrometheusRegistry(prefix="test")
        
        counter = registry.counter("requests", "Total requests")
        counter.inc(MetricLabels(labels={"method": "GET"}))
        counter.inc(MetricLabels(labels={"method": "POST"}))
        
        output = registry.export()
        
        assert 'test_requests{method="GET"}' in output
        assert 'test_requests{method="POST"}' in output


class TestAIBridgeMetrics:
    """AIBridgeMetrics 测试"""
    
    def test_record_request(self):
        """测试记录请求"""
        registry = PrometheusRegistry(prefix="test")
        metrics = AIBridgeMetrics(registry)
        
        metrics.record_request(
            tool="browser.navigate",
            server="chrome",
            success=True,
            duration=0.5
        )
        
        labels = MetricLabels(labels={"tool": "browser.navigate", "server": "chrome"})
        assert metrics.requests_total.get(labels) == 1
        assert metrics.requests_failed.get(MetricLabels(labels={
            "tool": "browser.navigate",
            "server": "chrome",
            "error_type": "unknown"
        })) == 0
    
    def test_record_failed_request(self):
        """测试记录失败请求"""
        registry = PrometheusRegistry(prefix="test")
        metrics = AIBridgeMetrics(registry)
        
        metrics.record_request(
            tool="browser.click",
            server="chrome",
            success=False,
            duration=1.0,
            error_type="TimeoutError"
        )
        
        labels = MetricLabels(labels={
            "tool": "browser.click",
            "server": "chrome",
            "error_type": "TimeoutError"
        })
        assert metrics.requests_failed.get(labels) == 1
    
    def test_record_policy_evaluation(self):
        """测试记录策略评估"""
        registry = PrometheusRegistry(prefix="test")
        metrics = AIBridgeMetrics(registry)
        
        metrics.record_policy_evaluation("tool1", allowed=True)
        metrics.record_policy_evaluation("tool1", allowed=False, denial_reason="quota_exceeded")
        
        assert metrics.policy_evaluations.get(MetricLabels(labels={"tool": "tool1", "result": "allow"})) == 1
        assert metrics.policy_evaluations.get(MetricLabels(labels={"tool": "tool1", "result": "deny"})) == 1
        assert metrics.policy_denials.get(MetricLabels(labels={"tool": "tool1", "reason": "quota_exceeded"})) == 1


class TestMetricsMiddleware:
    """MetricsMiddleware 测试"""
    
    @pytest.mark.asyncio
    async def test_middleware_success(self):
        """测试中间件成功场景"""
        registry = PrometheusRegistry(prefix="test")
        metrics = AIBridgeMetrics(registry)
        middleware = MetricsMiddleware(metrics)
        
        async def handler():
            return "success"
        
        result = await middleware(handler, "test_tool", "test_server")
        assert result == "success"
        
        labels = MetricLabels(labels={"tool": "test_tool", "server": "test_server"})
        assert metrics.requests_total.get(labels) == 1
    
    @pytest.mark.asyncio
    async def test_middleware_failure(self):
        """测试中间件失败场景"""
        registry = PrometheusRegistry(prefix="test")
        metrics = AIBridgeMetrics(registry)
        middleware = MetricsMiddleware(metrics)
        
        async def handler():
            raise ValueError("test error")
        
        with pytest.raises(ValueError):
            await middleware(handler, "test_tool", "test_server")
        
        labels = MetricLabels(labels={
            "tool": "test_tool",
            "server": "test_server",
            "error_type": "ValueError"
        })
        assert metrics.requests_failed.get(labels) == 1


class TestMeteringPrometheusAdapter:
    """MeteringPrometheusAdapter 测试"""
    
    def test_hash_user_id(self):
        """测试用户 ID 哈希"""
        user_id = "test-user-123"
        hashed = _hash_user_id(user_id)
        
        # 应该是 12 字符的哈希
        assert len(hashed) == 12
        # 相同输入相同输出
        assert _hash_user_id(user_id) == hashed
    
    def test_record_usage(self):
        """测试记录使用量"""
        registry = PrometheusRegistry(prefix="test")
        adapter = MeteringPrometheusAdapter(registry=registry)
        
        adapter.record_usage(
            user_id="user1",
            tool_name="translate",
            server_name="translator",
            cost=0.01,
            tokens=100,
            success=True,
            duration_ms=500
        )
        
        # 验证指标已记录（用户 ID 被哈希）
        user_hash = _hash_user_id("user1")
        labels = MetricLabels(labels={
            "user": user_hash,
            "tool": "translate",
            "server": "translator"
        })
        assert adapter.usage_cost.get(labels) == 0.01
        assert adapter.usage_tokens.get(labels) == 100
    
    def test_update_quota(self):
        """测试更新配额"""
        registry = PrometheusRegistry(prefix="test")
        adapter = MeteringPrometheusAdapter(registry=registry)
        
        adapter.update_quota(
            user_id="user1",
            quota_type="daily_calls",
            used=500,
            limit=1000
        )
        
        user_hash = _hash_user_id("user1")
        labels = MetricLabels(labels={
            "user": user_hash,
            "quota_type": "daily_calls"
        })
        
        assert adapter.quota_used.get(labels) == 500
        assert adapter.quota_limit.get(labels) == 1000
        assert adapter.quota_usage_ratio.get(labels) == 0.5
    
    def test_record_quota_exceeded(self):
        """测试记录配额超限"""
        registry = PrometheusRegistry(prefix="test")
        adapter = MeteringPrometheusAdapter(registry=registry)
        
        adapter.record_quota_exceeded("user1", "daily_calls")
        
        user_hash = _hash_user_id("user1")
        labels = MetricLabels(labels={
            "user": user_hash,
            "quota_type": "daily_calls"
        })
        assert adapter._metrics.quota_exceeded.get(labels) == 1


class TestMeteringHook:
    """MeteringHook 测试"""
    
    def test_hook_on_record(self):
        """测试记录钩子"""
        registry = PrometheusRegistry(prefix="test")
        adapter = MeteringPrometheusAdapter(registry=registry)
        hook = MeteringHook(adapter)
        
        hook.on_record(
            user_id="user1",
            tool_name="tool1",
            server_name="server1",
            cost=0.05,
            tokens=50,
            success=True,
            duration_ms=100
        )
        
        user_hash = _hash_user_id("user1")
        labels = MetricLabels(labels={
            "user": user_hash,
            "tool": "tool1",
            "server": "server1"
        })
        assert adapter.usage_cost.get(labels) == 0.05
    
    def test_hook_on_quota_update(self):
        """测试配额更新钩子"""
        registry = PrometheusRegistry(prefix="test")
        adapter = MeteringPrometheusAdapter(registry=registry)
        hook = MeteringHook(adapter)
        
        hook.on_quota_update(
            user_id="user1",
            quota_type="monthly_cost",
            used=50,
            limit=100
        )
        
        user_hash = _hash_user_id("user1")
        labels = MetricLabels(labels={
            "user": user_hash,
            "quota_type": "monthly_cost"
        })
        assert adapter.quota_usage_ratio.get(labels) == 0.5


class TestGlobalRegistry:
    """全局 Registry 测试"""
    
    def test_get_default_registry(self):
        """测试获取默认 Registry"""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2
    
    def test_set_custom_registry(self):
        """测试设置自定义 Registry"""
        custom_registry = PrometheusRegistry(prefix="custom")
        set_registry(custom_registry)
        
        assert get_registry() is custom_registry
        
        # 恢复默认
        set_registry(PrometheusRegistry())
