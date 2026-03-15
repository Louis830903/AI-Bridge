"""
Metering-Prometheus 适配器

将 Metering 模块的使用量数据同步到 Prometheus 指标
"""

from typing import Optional, Dict, Any, Callable
import asyncio
import logging
import hashlib

from .prometheus import (
    PrometheusRegistry,
    MetricLabels,
    AIBridgeMetrics,
    get_registry,
    CounterMetric,
    GaugeMetric,
    HistogramMetric,
)

logger = logging.getLogger(__name__)


def _hash_user_id(user_id: str) -> str:
    """哈希用户 ID（隐私保护）"""
    return hashlib.sha256(user_id.encode()).hexdigest()[:12]


class MeteringPrometheusAdapter:
    """Metering 到 Prometheus 的适配器
    
    将 Metering 模块的使用量数据同步到 Prometheus 指标
    """
    
    def __init__(
        self,
        registry: PrometheusRegistry = None,
        hash_user_ids: bool = True,
        sync_interval: float = 60.0
    ):
        """
        Args:
            registry: Prometheus 注册中心
            hash_user_ids: 是否哈希用户 ID（隐私保护）
            sync_interval: 同步间隔（秒）
        """
        self._registry = registry or get_registry()
        self._hash_user_ids = hash_user_ids
        self._sync_interval = sync_interval
        self._metrics = AIBridgeMetrics(self._registry)
        self._running = False
        self._sync_task: Optional[asyncio.Task] = None
        
        # Metering 专用指标
        self.usage_cost = self._registry.counter(
            "metering_usage_cost_total",
            "Total usage cost",
            label_names=["user", "tool", "server"]
        )
        self.usage_tokens = self._registry.counter(
            "metering_usage_tokens_total",
            "Total tokens consumed",
            label_names=["user", "tool", "server"]
        )
        self.usage_calls = self._registry.counter(
            "metering_usage_calls_total",
            "Total API calls",
            label_names=["user", "tool", "server", "status"]
        )
        self.quota_usage_ratio = self._registry.gauge(
            "metering_quota_usage_ratio",
            "Current quota usage ratio (0-1)",
            label_names=["user", "quota_type"]
        )
        self.quota_limit = self._registry.gauge(
            "metering_quota_limit",
            "Quota limit value",
            label_names=["user", "quota_type"]
        )
        self.quota_used = self._registry.gauge(
            "metering_quota_used",
            "Quota used value",
            label_names=["user", "quota_type"]
        )
        
        # 聚合指标
        self.usage_cost_per_hour = self._registry.gauge(
            "metering_usage_cost_per_hour",
            "Usage cost in the last hour",
            label_names=["tool", "server"]
        )
        self.usage_calls_per_minute = self._registry.gauge(
            "metering_usage_calls_per_minute",
            "API calls in the last minute",
            label_names=["tool", "server"]
        )
    
    def _get_user_label(self, user_id: str) -> str:
        """获取用户标签值（可能哈希）"""
        if self._hash_user_ids:
            return _hash_user_id(user_id)
        return user_id
    
    def record_usage(
        self,
        user_id: str,
        tool_name: str,
        server_name: str,
        cost: float,
        tokens: int = 0,
        success: bool = True,
        duration_ms: float = 0.0
    ) -> None:
        """记录使用量
        
        Args:
            user_id: 用户 ID
            tool_name: 工具名称
            server_name: 服务器名称
            cost: 成本
            tokens: Token 数量
            success: 是否成功
            duration_ms: 耗时（毫秒）
        """
        user_label = self._get_user_label(user_id)
        
        # 成本
        if cost > 0:
            self.usage_cost.inc(
                MetricLabels(labels={
                    "user": user_label,
                    "tool": tool_name,
                    "server": server_name
                }),
                cost
            )
        
        # Tokens
        if tokens > 0:
            self.usage_tokens.inc(
                MetricLabels(labels={
                    "user": user_label,
                    "tool": tool_name,
                    "server": server_name
                }),
                tokens
            )
        
        # 调用次数
        status = "success" if success else "failed"
        self.usage_calls.inc(
            MetricLabels(labels={
                "user": user_label,
                "tool": tool_name,
                "server": server_name,
                "status": status
            })
        )
        
        # 同步到核心指标
        self._metrics.record_request(
            tool=tool_name,
            server=server_name,
            success=success,
            duration=duration_ms / 1000.0
        )
    
    def update_quota(
        self,
        user_id: str,
        quota_type: str,
        used: float,
        limit: float
    ) -> None:
        """更新配额状态
        
        Args:
            user_id: 用户 ID
            quota_type: 配额类型
            used: 已使用量
            limit: 限制值
        """
        user_label = self._get_user_label(user_id)
        labels = MetricLabels(labels={
            "user": user_label,
            "quota_type": quota_type
        })
        
        self.quota_used.set(used, labels)
        self.quota_limit.set(limit, labels)
        
        if limit > 0:
            ratio = min(used / limit, 1.0)
            self.quota_usage_ratio.set(ratio, labels)
    
    def record_quota_exceeded(
        self,
        user_id: str,
        quota_type: str
    ) -> None:
        """记录配额超限事件"""
        user_label = self._get_user_label(user_id)
        self._metrics.quota_exceeded.inc(
            MetricLabels(labels={
                "user": user_label,
                "quota_type": quota_type
            })
        )
    
    async def start_sync(self, metering_collector: Any = None) -> None:
        """启动定期同步
        
        Args:
            metering_collector: MeteringCollector 实例（可选）
        """
        if self._running:
            return
        
        self._running = True
        self._sync_task = asyncio.create_task(
            self._sync_loop(metering_collector)
        )
        logger.info("Metering-Prometheus sync started")
    
    async def stop_sync(self) -> None:
        """停止定期同步"""
        self._running = False
        if self._sync_task:
            self._sync_task.cancel()
            try:
                await self._sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Metering-Prometheus sync stopped")
    
    async def _sync_loop(self, metering_collector: Any) -> None:
        """同步循环"""
        while self._running:
            try:
                await asyncio.sleep(self._sync_interval)
                if metering_collector:
                    await self._sync_from_metering(metering_collector)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Sync error: {e}")
    
    async def _sync_from_metering(self, metering_collector: Any) -> None:
        """从 Metering 同步数据
        
        Args:
            metering_collector: MeteringCollector 实例
        """
        try:
            # 获取聚合数据
            if hasattr(metering_collector, 'get_aggregations'):
                aggregations = metering_collector.get_aggregations()
                for agg in aggregations:
                    labels = MetricLabels(labels={
                        "tool": agg.tool_name or "unknown",
                        "server": agg.server_name or "unknown"
                    })
                    
                    # 更新每小时成本
                    if hasattr(agg, 'cost'):
                        self.usage_cost_per_hour.set(agg.cost, labels)
                    
                    # 更新每分钟调用量
                    if hasattr(agg, 'call_count'):
                        self.usage_calls_per_minute.set(agg.call_count / 60.0, labels)
            
            # 获取配额状态
            if hasattr(metering_collector, 'quota_manager'):
                quota_manager = metering_collector.quota_manager
                if hasattr(quota_manager, 'get_all_quotas'):
                    quotas = quota_manager.get_all_quotas()
                    for user_id, user_quotas in quotas.items():
                        for quota_type, quota_info in user_quotas.items():
                            self.update_quota(
                                user_id=user_id,
                                quota_type=quota_type,
                                used=quota_info.get('used', 0),
                                limit=quota_info.get('limit', 0)
                            )
        except Exception as e:
            logger.warning(f"Failed to sync from metering: {e}")


class MeteringHook:
    """Metering 钩子
    
    可以挂载到 MeteringCollector 以自动同步指标
    """
    
    def __init__(self, adapter: MeteringPrometheusAdapter):
        self._adapter = adapter
    
    def on_record(
        self,
        user_id: str,
        tool_name: str,
        server_name: str,
        cost: float,
        tokens: int,
        success: bool,
        duration_ms: float
    ) -> None:
        """记录钩子"""
        self._adapter.record_usage(
            user_id=user_id,
            tool_name=tool_name,
            server_name=server_name,
            cost=cost,
            tokens=tokens,
            success=success,
            duration_ms=duration_ms
        )
    
    def on_quota_update(
        self,
        user_id: str,
        quota_type: str,
        used: float,
        limit: float
    ) -> None:
        """配额更新钩子"""
        self._adapter.update_quota(
            user_id=user_id,
            quota_type=quota_type,
            used=used,
            limit=limit
        )
    
    def on_quota_exceeded(
        self,
        user_id: str,
        quota_type: str
    ) -> None:
        """配额超限钩子"""
        self._adapter.record_quota_exceeded(
            user_id=user_id,
            quota_type=quota_type
        )


def create_metering_prometheus_adapter(
    registry: PrometheusRegistry = None,
    metering_collector: Any = None,
    auto_hook: bool = True
) -> MeteringPrometheusAdapter:
    """创建 Metering-Prometheus 适配器的便捷函数
    
    Args:
        registry: Prometheus 注册中心
        metering_collector: MeteringCollector 实例
        auto_hook: 是否自动挂载钩子
        
    Returns:
        MeteringPrometheusAdapter 实例
    """
    adapter = MeteringPrometheusAdapter(registry=registry)
    
    if auto_hook and metering_collector:
        hook = MeteringHook(adapter)
        
        # 尝试挂载钩子
        if hasattr(metering_collector, 'add_hook'):
            metering_collector.add_hook(hook)
            logger.info("Metering hook attached")
        elif hasattr(metering_collector, 'on_record_callbacks'):
            metering_collector.on_record_callbacks.append(hook.on_record)
            logger.info("Metering callback attached")
    
    return adapter
