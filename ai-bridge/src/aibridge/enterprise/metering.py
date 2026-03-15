"""
调用成本计量模块

提供 AI 工具调用的计量和配额管理：
- UsageRecord: 单次调用记录
- MeteringCollector: 使用量采集器
- QuotaManager: 配额管理器

支持多维度统计：
- 按用户
- 按工具
- 按时间
"""

import asyncio
import logging
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MeteringDimension(Enum):
    """计量维度"""
    USER = "user"
    TOOL = "tool"
    SERVER = "server"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"


@dataclass
class MeteringConfig:
    """计量配置"""
    # 是否启用
    enabled: bool = True
    
    # 成本单价
    cost_per_call: float = 0.001              # 每次调用
    cost_per_input_token: float = 0.00001     # 每输入 token
    cost_per_output_token: float = 0.00003    # 每输出 token
    cost_per_second: float = 0.0001           # 每秒执行时间
    
    # 工具特定成本（覆盖默认）
    tool_costs: Dict[str, float] = field(default_factory=dict)
    
    # 聚合配置
    aggregation_interval: float = 60.0  # 聚合间隔（秒）
    retention_days: int = 30            # 数据保留天数
    
    # 缓冲配置
    buffer_size: int = 100              # 缓冲区大小
    flush_interval: float = 10.0        # 刷新间隔（秒）


@dataclass
class UsageRecord:
    """
    使用记录
    
    记录单次工具调用的详细信息。
    """
    record_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = field(default_factory=time.time)
    
    # 调用信息
    user_id: str = ""
    tool_name: str = ""
    server_name: str = ""
    
    # 计量数据
    call_count: int = 1
    success: bool = True
    
    # 资源消耗
    duration_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    input_bytes: int = 0
    output_bytes: int = 0
    
    # 成本
    estimated_cost: float = 0.0
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "user_id": self.user_id,
            "tool_name": self.tool_name,
            "server_name": self.server_name,
            "call_count": self.call_count,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "input_bytes": self.input_bytes,
            "output_bytes": self.output_bytes,
            "estimated_cost": self.estimated_cost,
            "metadata": self.metadata,
        }


@dataclass
class UsageAggregation:
    """
    使用量聚合
    
    按维度聚合的统计数据。
    """
    dimension: MeteringDimension
    key: str  # 聚合键（如 user:xxx 或 tool:browser）
    period_start: datetime
    period_end: datetime
    
    # 聚合统计
    total_calls: int = 0
    success_calls: int = 0
    error_calls: int = 0
    total_duration_ms: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_input_bytes: int = 0
    total_output_bytes: int = 0
    total_cost: float = 0.0
    
    # 最后更新时间
    last_updated: float = field(default_factory=time.time)
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_calls == 0:
            return 0.0
        return self.success_calls / self.total_calls
    
    @property
    def avg_duration_ms(self) -> float:
        """平均耗时"""
        if self.total_calls == 0:
            return 0.0
        return self.total_duration_ms / self.total_calls
    
    @property
    def avg_cost(self) -> float:
        """平均成本"""
        if self.total_calls == 0:
            return 0.0
        return self.total_cost / self.total_calls
    
    def update(self, record: UsageRecord) -> None:
        """更新聚合数据"""
        self.total_calls += record.call_count
        if record.success:
            self.success_calls += record.call_count
        else:
            self.error_calls += record.call_count
        self.total_duration_ms += record.duration_ms
        self.total_input_tokens += record.input_tokens
        self.total_output_tokens += record.output_tokens
        self.total_input_bytes += record.input_bytes
        self.total_output_bytes += record.output_bytes
        self.total_cost += record.estimated_cost
        self.last_updated = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "dimension": self.dimension.value,
            "key": self.key,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "total_calls": self.total_calls,
            "success_calls": self.success_calls,
            "error_calls": self.error_calls,
            "success_rate": self.success_rate,
            "total_duration_ms": self.total_duration_ms,
            "avg_duration_ms": self.avg_duration_ms,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost": self.total_cost,
            "avg_cost": self.avg_cost,
        }


@dataclass
class QuotaConfig:
    """
    配额配置
    
    定义用户的使用限制。
    """
    quota_id: str
    name: str
    description: str = ""
    
    # 调用次数限制
    max_calls_per_hour: Optional[int] = None
    max_calls_per_day: Optional[int] = None
    max_calls_per_month: Optional[int] = None
    
    # 成本限制
    max_cost_per_hour: Optional[float] = None
    max_cost_per_day: Optional[float] = None
    max_cost_per_month: Optional[float] = None
    
    # Token 限制
    max_tokens_per_day: Optional[int] = None
    max_tokens_per_month: Optional[int] = None
    
    # 告警阈值（百分比）
    warning_threshold: float = 0.8  # 80% 时告警
    
    # 超限行为
    block_on_exceed: bool = True  # 超限时阻止
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "quota_id": self.quota_id,
            "name": self.name,
            "max_calls_per_hour": self.max_calls_per_hour,
            "max_calls_per_day": self.max_calls_per_day,
            "max_calls_per_month": self.max_calls_per_month,
            "max_cost_per_day": self.max_cost_per_day,
            "max_cost_per_month": self.max_cost_per_month,
            "warning_threshold": self.warning_threshold,
            "block_on_exceed": self.block_on_exceed,
        }


class QuotaExceeded(Exception):
    """配额超限异常"""
    def __init__(
        self,
        message: str,
        quota_type: str,
        current: float,
        limit: float,
        reset_at: Optional[datetime] = None,
    ):
        super().__init__(message)
        self.quota_type = quota_type
        self.current = current
        self.limit = limit
        self.reset_at = reset_at
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error": "QuotaExceeded",
            "message": str(self),
            "quota_type": self.quota_type,
            "current": self.current,
            "limit": self.limit,
            "reset_at": self.reset_at.isoformat() if self.reset_at else None,
        }


class MeteringCollector:
    """
    计量采集器
    
    收集和聚合工具调用的使用量数据。
    
    使用示例：
    ```python
    collector = MeteringCollector()
    await collector.start()
    
    # 记录调用
    await collector.record(
        user_id="user123",
        tool_name="browser/navigate",
        server_name="browser-use",
        duration_ms=150.5,
        success=True,
    )
    
    # 获取统计
    stats = await collector.get_user_stats("user123", period="day")
    print(f"Today's calls: {stats.total_calls}")
    
    # 生成报告
    report = await collector.generate_report(
        period_start=datetime.now() - timedelta(days=7),
        period_end=datetime.now(),
        group_by=MeteringDimension.USER,
    )
    
    await collector.stop()
    ```
    """
    
    def __init__(self, config: Optional[MeteringConfig] = None):
        self._config = config or MeteringConfig()
        self._records: List[UsageRecord] = []
        self._aggregations: Dict[str, UsageAggregation] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动采集器"""
        if not self._config.enabled:
            logger.info("Metering collector is disabled")
            return
        
        self._running = True
        
        # 启动定期刷新任务
        self._flush_task = asyncio.create_task(self._periodic_flush())
        
        # 启动定期清理任务
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        logger.info("Metering collector started")
    
    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        
        # 停止任务
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
        
        logger.info("Metering collector stopped")
    
    async def record(
        self,
        user_id: str,
        tool_name: str,
        server_name: str = "",
        duration_ms: float = 0.0,
        success: bool = True,
        input_tokens: int = 0,
        output_tokens: int = 0,
        input_bytes: int = 0,
        output_bytes: int = 0,
        **metadata
    ) -> UsageRecord:
        """
        记录一次工具调用
        
        Args:
            user_id: 用户ID
            tool_name: 工具名称
            server_name: 服务器名称
            duration_ms: 耗时（毫秒）
            success: 是否成功
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            input_bytes: 输入字节数
            output_bytes: 输出字节数
            **metadata: 额外元数据
            
        Returns:
            UsageRecord
        """
        if not self._config.enabled:
            return UsageRecord()
        
        # 计算成本
        estimated_cost = self._calculate_cost(
            tool_name, duration_ms, input_tokens, output_tokens
        )
        
        record = UsageRecord(
            user_id=user_id,
            tool_name=tool_name,
            server_name=server_name,
            success=success,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_bytes=input_bytes,
            output_bytes=output_bytes,
            estimated_cost=estimated_cost,
            metadata=metadata,
        )
        
        async with self._lock:
            self._records.append(record)
            
            # 实时更新聚合
            self._update_aggregations(record)
            
            # 缓冲区满时刷新
            if len(self._records) >= self._config.buffer_size:
                # 清理旧记录（保留聚合）
                self._records = self._records[-100:]
        
        return record
    
    def _calculate_cost(
        self,
        tool_name: str,
        duration_ms: float,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """计算调用成本"""
        # 检查工具特定成本
        if tool_name in self._config.tool_costs:
            return self._config.tool_costs[tool_name]
        
        # 默认成本计算
        cost = self._config.cost_per_call
        cost += input_tokens * self._config.cost_per_input_token
        cost += output_tokens * self._config.cost_per_output_token
        cost += (duration_ms / 1000) * self._config.cost_per_second
        
        return round(cost, 6)
    
    def _update_aggregations(self, record: UsageRecord) -> None:
        """更新聚合数据"""
        now = datetime.now()
        
        # 按用户+天聚合
        user_day_key = f"user:{record.user_id}:day:{now.strftime('%Y-%m-%d')}"
        if user_day_key not in self._aggregations:
            self._aggregations[user_day_key] = UsageAggregation(
                dimension=MeteringDimension.USER,
                key=record.user_id,
                period_start=now.replace(hour=0, minute=0, second=0, microsecond=0),
                period_end=now.replace(hour=23, minute=59, second=59, microsecond=999999),
            )
        self._aggregations[user_day_key].update(record)
        
        # 按用户+小时聚合
        user_hour_key = f"user:{record.user_id}:hour:{now.strftime('%Y-%m-%d-%H')}"
        if user_hour_key not in self._aggregations:
            self._aggregations[user_hour_key] = UsageAggregation(
                dimension=MeteringDimension.USER,
                key=record.user_id,
                period_start=now.replace(minute=0, second=0, microsecond=0),
                period_end=now.replace(minute=59, second=59, microsecond=999999),
            )
        self._aggregations[user_hour_key].update(record)
        
        # 按用户+月聚合
        user_month_key = f"user:{record.user_id}:month:{now.strftime('%Y-%m')}"
        if user_month_key not in self._aggregations:
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            # 计算月末
            if now.month == 12:
                month_end = now.replace(year=now.year + 1, month=1, day=1) - timedelta(days=1)
            else:
                month_end = now.replace(month=now.month + 1, day=1) - timedelta(days=1)
            month_end = month_end.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            self._aggregations[user_month_key] = UsageAggregation(
                dimension=MeteringDimension.USER,
                key=record.user_id,
                period_start=month_start,
                period_end=month_end,
            )
        self._aggregations[user_month_key].update(record)
        
        # 按工具+天聚合
        tool_day_key = f"tool:{record.tool_name}:day:{now.strftime('%Y-%m-%d')}"
        if tool_day_key not in self._aggregations:
            self._aggregations[tool_day_key] = UsageAggregation(
                dimension=MeteringDimension.TOOL,
                key=record.tool_name,
                period_start=now.replace(hour=0, minute=0, second=0, microsecond=0),
                period_end=now.replace(hour=23, minute=59, second=59, microsecond=999999),
            )
        self._aggregations[tool_day_key].update(record)
    
    async def _periodic_flush(self) -> None:
        """定期刷新"""
        while self._running:
            try:
                await asyncio.sleep(self._config.flush_interval)
                # 可以在这里将数据持久化到存储
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metering flush error: {e}")
    
    async def _periodic_cleanup(self) -> None:
        """定期清理过期数据"""
        while self._running:
            try:
                await asyncio.sleep(3600)  # 每小时检查一次
                await self._cleanup_expired()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Metering cleanup error: {e}")
    
    async def _cleanup_expired(self) -> None:
        """清理过期的聚合数据"""
        cutoff = datetime.now() - timedelta(days=self._config.retention_days)
        
        async with self._lock:
            expired_keys = [
                key for key, agg in self._aggregations.items()
                if agg.period_end < cutoff
            ]
            
            for key in expired_keys:
                del self._aggregations[key]
            
            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired aggregations")
    
    async def get_user_stats(
        self,
        user_id: str,
        period: str = "day"
    ) -> Optional[UsageAggregation]:
        """
        获取用户统计
        
        Args:
            user_id: 用户ID
            period: 统计周期 ("hour", "day", "month")
            
        Returns:
            UsageAggregation 或 None
        """
        now = datetime.now()
        
        if period == "hour":
            key = f"user:{user_id}:hour:{now.strftime('%Y-%m-%d-%H')}"
        elif period == "day":
            key = f"user:{user_id}:day:{now.strftime('%Y-%m-%d')}"
        elif period == "month":
            key = f"user:{user_id}:month:{now.strftime('%Y-%m')}"
        else:
            return None
        
        return self._aggregations.get(key)
    
    async def get_tool_stats(
        self,
        tool_name: str,
        period: str = "day"
    ) -> Optional[UsageAggregation]:
        """获取工具统计"""
        now = datetime.now()
        
        if period == "day":
            key = f"tool:{tool_name}:day:{now.strftime('%Y-%m-%d')}"
        else:
            return None
        
        return self._aggregations.get(key)
    
    async def generate_report(
        self,
        period_start: datetime,
        period_end: datetime,
        group_by: MeteringDimension = MeteringDimension.USER,
        user_id: Optional[str] = None,
    ) -> List[UsageAggregation]:
        """
        生成使用报告
        
        Args:
            period_start: 开始时间
            period_end: 结束时间
            group_by: 分组维度
            user_id: 可选，筛选特定用户
            
        Returns:
            聚合数据列表
        """
        results = []
        prefix = f"{group_by.value}:"
        
        for key, agg in self._aggregations.items():
            if not key.startswith(prefix):
                continue
            
            # 时间范围筛选
            if agg.period_end < period_start or agg.period_start > period_end:
                continue
            
            # 用户筛选
            if user_id and group_by == MeteringDimension.USER:
                if agg.key != user_id:
                    continue
            
            results.append(agg)
        
        # 按调用次数排序
        return sorted(results, key=lambda x: x.total_calls, reverse=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """获取采集器统计"""
        return {
            "enabled": self._config.enabled,
            "running": self._running,
            "records_in_buffer": len(self._records),
            "aggregations_count": len(self._aggregations),
            "retention_days": self._config.retention_days,
        }


class QuotaManager:
    """
    配额管理器
    
    管理用户的使用配额，在超限时阻止或告警。
    
    使用示例：
    ```python
    collector = MeteringCollector()
    quota_mgr = QuotaManager(collector)
    
    # 设置默认配额
    quota_mgr.set_default_quota(QuotaConfig(
        quota_id="default",
        name="Default Quota",
        max_calls_per_day=1000,
        max_cost_per_month=100.0,
    ))
    
    # 设置用户特定配额
    quota_mgr.set_user_quota("premium_user", QuotaConfig(
        quota_id="premium",
        name="Premium Quota",
        max_calls_per_day=10000,
        max_cost_per_month=1000.0,
    ))
    
    # 检查配额
    try:
        await quota_mgr.check_quota("user123")
        # 执行调用...
    except QuotaExceeded as e:
        print(f"Quota exceeded: {e.quota_type}, current: {e.current}, limit: {e.limit}")
    ```
    """
    
    def __init__(self, collector: MeteringCollector):
        self._collector = collector
        self._user_quotas: Dict[str, QuotaConfig] = {}
        self._default_quota: Optional[QuotaConfig] = None
        self._warning_callbacks: List[Callable] = []
    
    def set_default_quota(self, quota: QuotaConfig) -> None:
        """设置默认配额"""
        self._default_quota = quota
        logger.info(f"Set default quota: {quota.name}")
    
    def set_user_quota(self, user_id: str, quota: QuotaConfig) -> None:
        """设置用户配额"""
        self._user_quotas[user_id] = quota
        logger.info(f"Set quota for user {user_id}: {quota.name}")
    
    def get_user_quota(self, user_id: str) -> Optional[QuotaConfig]:
        """获取用户配额"""
        return self._user_quotas.get(user_id, self._default_quota)
    
    def remove_user_quota(self, user_id: str) -> bool:
        """移除用户配额"""
        if user_id in self._user_quotas:
            del self._user_quotas[user_id]
            return True
        return False
    
    def add_warning_callback(self, callback: Callable[[str, str, float, float], None]) -> None:
        """
        添加告警回调
        
        回调签名: callback(user_id, quota_type, current, limit)
        """
        self._warning_callbacks.append(callback)
    
    async def check_quota(self, user_id: str) -> Dict[str, Any]:
        """
        检查用户配额
        
        Args:
            user_id: 用户ID
            
        Returns:
            配额状态信息
            
        Raises:
            QuotaExceeded: 配额超限
        """
        quota = self.get_user_quota(user_id)
        if not quota:
            return {"status": "no_quota", "checks": []}
        
        result = {
            "status": "ok",
            "checks": [],
            "quota": quota.to_dict(),
        }
        
        now = datetime.now()
        
        # 检查每小时调用限制
        if quota.max_calls_per_hour:
            stats = await self._collector.get_user_stats(user_id, "hour")
            current = stats.total_calls if stats else 0
            check_result = self._check_limit(
                "calls_per_hour",
                current,
                quota.max_calls_per_hour,
                quota.warning_threshold,
                quota.block_on_exceed,
                user_id,
                reset_at=now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1),
            )
            result["checks"].append(check_result)
            if check_result.get("exceeded") and quota.block_on_exceed:
                raise QuotaExceeded(
                    f"Hourly call quota exceeded for user {user_id}",
                    quota_type="calls_per_hour",
                    current=current,
                    limit=quota.max_calls_per_hour,
                    reset_at=check_result.get("reset_at"),
                )
            if check_result.get("warning"):
                result["status"] = "warning"
        
        # 检查每日调用限制
        if quota.max_calls_per_day:
            stats = await self._collector.get_user_stats(user_id, "day")
            current = stats.total_calls if stats else 0
            check_result = self._check_limit(
                "calls_per_day",
                current,
                quota.max_calls_per_day,
                quota.warning_threshold,
                quota.block_on_exceed,
                user_id,
                reset_at=now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
            )
            result["checks"].append(check_result)
            if check_result.get("exceeded") and quota.block_on_exceed:
                raise QuotaExceeded(
                    f"Daily call quota exceeded for user {user_id}",
                    quota_type="calls_per_day",
                    current=current,
                    limit=quota.max_calls_per_day,
                    reset_at=check_result.get("reset_at"),
                )
            if check_result.get("warning"):
                result["status"] = "warning"
        
        # 检查每月调用限制
        if quota.max_calls_per_month:
            stats = await self._collector.get_user_stats(user_id, "month")
            current = stats.total_calls if stats else 0
            # 计算下月初
            if now.month == 12:
                reset_at = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                reset_at = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
            check_result = self._check_limit(
                "calls_per_month",
                current,
                quota.max_calls_per_month,
                quota.warning_threshold,
                quota.block_on_exceed,
                user_id,
                reset_at=reset_at,
            )
            result["checks"].append(check_result)
            if check_result.get("exceeded") and quota.block_on_exceed:
                raise QuotaExceeded(
                    f"Monthly call quota exceeded for user {user_id}",
                    quota_type="calls_per_month",
                    current=current,
                    limit=quota.max_calls_per_month,
                    reset_at=check_result.get("reset_at"),
                )
            if check_result.get("warning"):
                result["status"] = "warning"
        
        # 检查每日成本限制
        if quota.max_cost_per_day:
            stats = await self._collector.get_user_stats(user_id, "day")
            current = stats.total_cost if stats else 0.0
            check_result = self._check_limit(
                "cost_per_day",
                current,
                quota.max_cost_per_day,
                quota.warning_threshold,
                quota.block_on_exceed,
                user_id,
                reset_at=now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1),
            )
            result["checks"].append(check_result)
            if check_result.get("exceeded") and quota.block_on_exceed:
                raise QuotaExceeded(
                    f"Daily cost quota exceeded for user {user_id}",
                    quota_type="cost_per_day",
                    current=current,
                    limit=quota.max_cost_per_day,
                    reset_at=check_result.get("reset_at"),
                )
            if check_result.get("warning"):
                result["status"] = "warning"
        
        # 检查每月成本限制
        if quota.max_cost_per_month:
            stats = await self._collector.get_user_stats(user_id, "month")
            current = stats.total_cost if stats else 0.0
            # 计算下月初
            if now.month == 12:
                reset_at = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                reset_at = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            
            check_result = self._check_limit(
                "cost_per_month",
                current,
                quota.max_cost_per_month,
                quota.warning_threshold,
                quota.block_on_exceed,
                user_id,
                reset_at=reset_at,
            )
            result["checks"].append(check_result)
            if check_result.get("exceeded") and quota.block_on_exceed:
                raise QuotaExceeded(
                    f"Monthly cost quota exceeded for user {user_id}",
                    quota_type="cost_per_month",
                    current=current,
                    limit=quota.max_cost_per_month,
                    reset_at=check_result.get("reset_at"),
                )
            if check_result.get("warning"):
                result["status"] = "warning"
        
        return result
    
    def _check_limit(
        self,
        quota_type: str,
        current: float,
        limit: float,
        warning_threshold: float,
        block_on_exceed: bool,
        user_id: str,
        reset_at: datetime,
    ) -> Dict[str, Any]:
        """检查单个限制"""
        usage_pct = current / limit if limit > 0 else 0
        
        check_result = {
            "type": quota_type,
            "current": current,
            "limit": limit,
            "usage_pct": usage_pct,
            "reset_at": reset_at,
            "warning": False,
            "exceeded": False,
        }
        
        if current >= limit:
            check_result["exceeded"] = True
            logger.warning(f"Quota exceeded: user={user_id}, type={quota_type}, current={current}, limit={limit}")
        elif usage_pct >= warning_threshold:
            check_result["warning"] = True
            # 触发告警回调
            for callback in self._warning_callbacks:
                try:
                    callback(user_id, quota_type, current, limit)
                except Exception as e:
                    logger.error(f"Warning callback error: {e}")
        
        return check_result
    
    async def get_quota_status(self, user_id: str) -> Dict[str, Any]:
        """获取用户配额状态（不抛出异常）"""
        try:
            return await self.check_quota(user_id)
        except QuotaExceeded as e:
            return {
                "status": "exceeded",
                "error": e.to_dict(),
            }
    
    def get_stats(self) -> Dict[str, Any]:
        """获取配额管理器统计"""
        return {
            "user_quotas_count": len(self._user_quotas),
            "has_default_quota": self._default_quota is not None,
            "warning_callbacks_count": len(self._warning_callbacks),
        }


# ===== 预定义配额模板 =====

BUILTIN_QUOTAS = {
    "free-tier": QuotaConfig(
        quota_id="free-tier",
        name="Free Tier",
        description="Free tier with limited usage",
        max_calls_per_hour=100,
        max_calls_per_day=500,
        max_calls_per_month=5000,
        max_cost_per_day=1.0,
        max_cost_per_month=10.0,
        warning_threshold=0.8,
        block_on_exceed=True,
    ),
    
    "basic-tier": QuotaConfig(
        quota_id="basic-tier",
        name="Basic Tier",
        description="Basic paid tier",
        max_calls_per_hour=500,
        max_calls_per_day=5000,
        max_calls_per_month=50000,
        max_cost_per_day=10.0,
        max_cost_per_month=100.0,
        warning_threshold=0.9,
        block_on_exceed=True,
    ),
    
    "premium-tier": QuotaConfig(
        quota_id="premium-tier",
        name="Premium Tier",
        description="Premium tier with high limits",
        max_calls_per_hour=2000,
        max_calls_per_day=20000,
        max_calls_per_month=200000,
        max_cost_per_day=100.0,
        max_cost_per_month=1000.0,
        warning_threshold=0.95,
        block_on_exceed=False,  # 只告警不阻止
    ),
    
    "enterprise-tier": QuotaConfig(
        quota_id="enterprise-tier",
        name="Enterprise Tier",
        description="Enterprise tier with no limits",
        max_calls_per_hour=None,
        max_calls_per_day=None,
        max_calls_per_month=None,
        max_cost_per_day=None,
        max_cost_per_month=None,
        block_on_exceed=False,
    ),
}


def get_builtin_quota(quota_id: str) -> Optional[QuotaConfig]:
    """获取内置配额"""
    return BUILTIN_QUOTAS.get(quota_id)


def list_builtin_quotas() -> List[str]:
    """列出所有内置配额ID"""
    return list(BUILTIN_QUOTAS.keys())
