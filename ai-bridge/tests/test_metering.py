"""
测试 metering.py - 调用成本计量模块
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from aibridge.enterprise.metering import (
    MeteringCollector,
    MeteringConfig,
    MeteringDimension,
    UsageRecord,
    UsageAggregation,
    QuotaManager,
    QuotaConfig,
    QuotaExceeded,
    BUILTIN_QUOTAS,
    get_builtin_quota,
    list_builtin_quotas,
)


# ===== UsageRecord Tests =====

class TestUsageRecord:
    """测试使用记录"""
    
    def test_default_record(self):
        """测试默认记录"""
        record = UsageRecord()
        
        assert record.record_id is not None
        assert record.timestamp > 0
        assert record.call_count == 1
        assert record.success is True
        assert record.estimated_cost == 0.0
    
    def test_custom_record(self):
        """测试自定义记录"""
        record = UsageRecord(
            user_id="alice",
            tool_name="browser/navigate",
            server_name="browser-use",
            duration_ms=150.5,
            success=True,
            input_tokens=100,
            output_tokens=50,
            estimated_cost=0.005,
            metadata={"url": "https://example.com"}
        )
        
        assert record.user_id == "alice"
        assert record.tool_name == "browser/navigate"
        assert record.duration_ms == 150.5
        assert record.input_tokens == 100
        assert record.metadata["url"] == "https://example.com"
    
    def test_to_dict(self):
        """测试转换为字典"""
        record = UsageRecord(
            user_id="alice",
            tool_name="test/tool",
            success=True,
        )
        
        d = record.to_dict()
        
        assert d["user_id"] == "alice"
        assert d["tool_name"] == "test/tool"
        assert d["success"] is True
        assert "timestamp" in d
        assert "timestamp_iso" in d


# ===== UsageAggregation Tests =====

class TestUsageAggregation:
    """测试使用量聚合"""
    
    def test_default_aggregation(self):
        """测试默认聚合"""
        now = datetime.now()
        agg = UsageAggregation(
            dimension=MeteringDimension.USER,
            key="alice",
            period_start=now,
            period_end=now + timedelta(days=1),
        )
        
        assert agg.total_calls == 0
        assert agg.success_rate == 0.0
        assert agg.avg_duration_ms == 0.0
    
    def test_update_aggregation(self):
        """测试更新聚合"""
        now = datetime.now()
        agg = UsageAggregation(
            dimension=MeteringDimension.USER,
            key="alice",
            period_start=now,
            period_end=now + timedelta(days=1),
        )
        
        # 添加成功记录
        agg.update(UsageRecord(
            success=True,
            duration_ms=100.0,
            estimated_cost=0.01,
        ))
        
        assert agg.total_calls == 1
        assert agg.success_calls == 1
        assert agg.error_calls == 0
        
        # 添加失败记录
        agg.update(UsageRecord(
            success=False,
            duration_ms=50.0,
            estimated_cost=0.005,
        ))
        
        assert agg.total_calls == 2
        assert agg.success_calls == 1
        assert agg.error_calls == 1
        assert agg.success_rate == 0.5
        assert agg.total_duration_ms == 150.0
        assert agg.avg_duration_ms == 75.0
        assert agg.total_cost == 0.015
    
    def test_to_dict(self):
        """测试转换为字典"""
        now = datetime.now()
        agg = UsageAggregation(
            dimension=MeteringDimension.TOOL,
            key="browser/navigate",
            period_start=now,
            period_end=now + timedelta(hours=1),
            total_calls=100,
            success_calls=95,
            total_cost=1.5,
        )
        
        d = agg.to_dict()
        
        assert d["dimension"] == "tool"
        assert d["key"] == "browser/navigate"
        assert d["total_calls"] == 100
        assert d["success_rate"] == 0.95


# ===== MeteringCollector Tests =====

class TestMeteringCollector:
    """测试计量采集器"""
    
    @pytest.mark.asyncio
    async def test_collector_lifecycle(self):
        """测试采集器生命周期"""
        collector = MeteringCollector()
        
        await collector.start()
        assert collector._running is True
        
        await collector.stop()
        assert collector._running is False
    
    @pytest.mark.asyncio
    async def test_disabled_collector(self):
        """测试禁用的采集器"""
        config = MeteringConfig(enabled=False)
        collector = MeteringCollector(config)
        
        await collector.start()
        assert collector._running is False
        
        record = await collector.record(
            user_id="alice",
            tool_name="test/tool",
        )
        
        # 禁用时返回空记录
        assert record.user_id == ""
    
    @pytest.mark.asyncio
    async def test_record_usage(self):
        """测试记录使用量"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            record = await collector.record(
                user_id="alice",
                tool_name="browser/navigate",
                server_name="browser-use",
                duration_ms=100.0,
                success=True,
                input_tokens=50,
                output_tokens=100,
            )
            
            assert record.user_id == "alice"
            assert record.tool_name == "browser/navigate"
            assert record.estimated_cost > 0  # 应该计算了成本
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_cost_calculation(self):
        """测试成本计算"""
        config = MeteringConfig(
            cost_per_call=0.001,
            cost_per_input_token=0.00001,
            cost_per_output_token=0.00003,
            cost_per_second=0.0001,
        )
        collector = MeteringCollector(config)
        await collector.start()
        
        try:
            record = await collector.record(
                user_id="alice",
                tool_name="test/tool",
                duration_ms=1000,  # 1 秒
                input_tokens=100,
                output_tokens=200,
            )
            
            # 预期成本: 0.001 + 100*0.00001 + 200*0.00003 + 1*0.0001
            # = 0.001 + 0.001 + 0.006 + 0.0001 = 0.0081
            expected = 0.001 + 0.001 + 0.006 + 0.0001
            assert abs(record.estimated_cost - expected) < 0.0001
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_tool_specific_cost(self):
        """测试工具特定成本"""
        config = MeteringConfig(
            tool_costs={"expensive/tool": 0.1}
        )
        collector = MeteringCollector(config)
        await collector.start()
        
        try:
            record = await collector.record(
                user_id="alice",
                tool_name="expensive/tool",
                duration_ms=100,
            )
            
            assert record.estimated_cost == 0.1
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_get_user_stats(self):
        """测试获取用户统计"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            # 记录多次调用
            for _ in range(5):
                await collector.record(
                    user_id="alice",
                    tool_name="browser/navigate",
                    duration_ms=100.0,
                    success=True,
                )
            
            # 记录一次失败
            await collector.record(
                user_id="alice",
                tool_name="browser/click",
                duration_ms=50.0,
                success=False,
            )
            
            # 获取统计
            stats = await collector.get_user_stats("alice", period="day")
            
            assert stats is not None
            assert stats.total_calls == 6
            assert stats.success_calls == 5
            assert stats.error_calls == 1
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_get_tool_stats(self):
        """测试获取工具统计"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            # 记录多次调用
            for _ in range(3):
                await collector.record(
                    user_id="alice",
                    tool_name="browser/navigate",
                    duration_ms=100.0,
                )
            
            stats = await collector.get_tool_stats("browser/navigate", period="day")
            
            assert stats is not None
            assert stats.total_calls == 3
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_generate_report(self):
        """测试生成报告"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            # 记录多个用户的调用
            for user in ["alice", "bob", "charlie"]:
                for _ in range(3):
                    await collector.record(
                        user_id=user,
                        tool_name="test/tool",
                        duration_ms=100.0,
                    )
            
            # 生成报告
            now = datetime.now()
            report = await collector.generate_report(
                period_start=now - timedelta(hours=1),
                period_end=now + timedelta(hours=1),
                group_by=MeteringDimension.USER,
            )
            
            # 应该有 3 个用户的聚合（每日）
            assert len(report) >= 3
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_stats(self):
        """测试采集器统计"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            stats = collector.get_stats()
            
            assert stats["enabled"] is True
            assert stats["running"] is True
            assert "records_in_buffer" in stats
        finally:
            await collector.stop()


# ===== QuotaConfig Tests =====

class TestQuotaConfig:
    """测试配额配置"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = QuotaConfig(
            quota_id="test",
            name="Test Quota",
        )
        
        assert config.max_calls_per_hour is None
        assert config.warning_threshold == 0.8
        assert config.block_on_exceed is True
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = QuotaConfig(
            quota_id="custom",
            name="Custom Quota",
            max_calls_per_day=1000,
            max_cost_per_month=100.0,
            warning_threshold=0.9,
            block_on_exceed=False,
        )
        
        assert config.max_calls_per_day == 1000
        assert config.max_cost_per_month == 100.0
        assert config.warning_threshold == 0.9
        assert config.block_on_exceed is False
    
    def test_to_dict(self):
        """测试转换为字典"""
        config = QuotaConfig(
            quota_id="test",
            name="Test",
            max_calls_per_hour=100,
        )
        
        d = config.to_dict()
        
        assert d["quota_id"] == "test"
        assert d["max_calls_per_hour"] == 100


# ===== QuotaExceeded Tests =====

class TestQuotaExceeded:
    """测试配额超限异常"""
    
    def test_exception_attributes(self):
        """测试异常属性"""
        exc = QuotaExceeded(
            message="Quota exceeded",
            quota_type="calls_per_day",
            current=1001,
            limit=1000,
            reset_at=datetime(2025, 1, 2, 0, 0, 0),
        )
        
        assert exc.quota_type == "calls_per_day"
        assert exc.current == 1001
        assert exc.limit == 1000
        assert exc.reset_at is not None
    
    def test_to_dict(self):
        """测试转换为字典"""
        exc = QuotaExceeded(
            message="Test",
            quota_type="cost_per_month",
            current=101.5,
            limit=100.0,
        )
        
        d = exc.to_dict()
        
        assert d["error"] == "QuotaExceeded"
        assert d["quota_type"] == "cost_per_month"


# ===== QuotaManager Tests =====

class TestQuotaManager:
    """测试配额管理器"""
    
    @pytest.mark.asyncio
    async def test_set_default_quota(self):
        """测试设置默认配额"""
        collector = MeteringCollector()
        mgr = QuotaManager(collector)
        
        quota = QuotaConfig(
            quota_id="default",
            name="Default",
            max_calls_per_day=100,
        )
        
        mgr.set_default_quota(quota)
        
        user_quota = mgr.get_user_quota("any_user")
        assert user_quota is not None
        assert user_quota.max_calls_per_day == 100
    
    @pytest.mark.asyncio
    async def test_set_user_quota(self):
        """测试设置用户配额"""
        collector = MeteringCollector()
        mgr = QuotaManager(collector)
        
        mgr.set_default_quota(QuotaConfig(
            quota_id="default",
            name="Default",
            max_calls_per_day=100,
        ))
        
        mgr.set_user_quota("premium", QuotaConfig(
            quota_id="premium",
            name="Premium",
            max_calls_per_day=10000,
        ))
        
        # 普通用户使用默认配额
        normal_quota = mgr.get_user_quota("normal_user")
        assert normal_quota.max_calls_per_day == 100
        
        # premium 用户使用专属配额
        premium_quota = mgr.get_user_quota("premium")
        assert premium_quota.max_calls_per_day == 10000
    
    @pytest.mark.asyncio
    async def test_remove_user_quota(self):
        """测试移除用户配额"""
        collector = MeteringCollector()
        mgr = QuotaManager(collector)
        
        mgr.set_user_quota("alice", QuotaConfig(
            quota_id="alice",
            name="Alice",
        ))
        
        result = mgr.remove_user_quota("alice")
        assert result is True
        
        result = mgr.remove_user_quota("bob")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_check_quota_no_quota(self):
        """测试检查配额 - 无配额"""
        collector = MeteringCollector()
        mgr = QuotaManager(collector)
        
        result = await mgr.check_quota("alice")
        
        assert result["status"] == "no_quota"
    
    @pytest.mark.asyncio
    async def test_check_quota_within_limit(self):
        """测试检查配额 - 未超限"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            mgr = QuotaManager(collector)
            mgr.set_default_quota(QuotaConfig(
                quota_id="default",
                name="Default",
                max_calls_per_day=100,
                max_cost_per_month=10.0,
            ))
            
            # 记录少量调用
            for _ in range(5):
                await collector.record(
                    user_id="alice",
                    tool_name="test/tool",
                )
            
            result = await mgr.check_quota("alice")
            
            assert result["status"] == "ok"
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_check_quota_exceeded(self):
        """测试检查配额 - 超限"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            mgr = QuotaManager(collector)
            mgr.set_default_quota(QuotaConfig(
                quota_id="default",
                name="Default",
                max_calls_per_hour=5,
                block_on_exceed=True,
            ))
            
            # 记录超限调用
            for _ in range(10):
                await collector.record(
                    user_id="alice",
                    tool_name="test/tool",
                )
            
            with pytest.raises(QuotaExceeded) as exc_info:
                await mgr.check_quota("alice")
            
            assert exc_info.value.quota_type == "calls_per_hour"
            assert exc_info.value.current >= 10
            assert exc_info.value.limit == 5
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_check_quota_warning(self):
        """测试检查配额 - 告警"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            mgr = QuotaManager(collector)
            mgr.set_default_quota(QuotaConfig(
                quota_id="default",
                name="Default",
                max_calls_per_hour=10,
                warning_threshold=0.5,  # 50% 告警
                block_on_exceed=True,
            ))
            
            # 记录 6 次（超过 50%）
            for _ in range(6):
                await collector.record(
                    user_id="alice",
                    tool_name="test/tool",
                )
            
            result = await mgr.check_quota("alice")
            
            assert result["status"] == "warning"
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_warning_callback(self):
        """测试告警回调"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            mgr = QuotaManager(collector)
            mgr.set_default_quota(QuotaConfig(
                quota_id="default",
                name="Default",
                max_calls_per_hour=10,
                warning_threshold=0.5,
            ))
            
            # 添加回调
            warnings_received = []
            def on_warning(user_id, quota_type, current, limit):
                warnings_received.append({
                    "user_id": user_id,
                    "quota_type": quota_type,
                    "current": current,
                    "limit": limit,
                })
            
            mgr.add_warning_callback(on_warning)
            
            # 触发告警
            for _ in range(6):
                await collector.record(
                    user_id="alice",
                    tool_name="test/tool",
                )
            
            await mgr.check_quota("alice")
            
            assert len(warnings_received) > 0
            assert warnings_received[0]["user_id"] == "alice"
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_get_quota_status(self):
        """测试获取配额状态（不抛异常）"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            mgr = QuotaManager(collector)
            mgr.set_default_quota(QuotaConfig(
                quota_id="default",
                name="Default",
                max_calls_per_hour=5,
                block_on_exceed=True,
            ))
            
            # 记录超限调用
            for _ in range(10):
                await collector.record(
                    user_id="alice",
                    tool_name="test/tool",
                )
            
            # get_quota_status 不抛异常
            result = await mgr.get_quota_status("alice")
            
            assert result["status"] == "exceeded"
            assert "error" in result
        finally:
            await collector.stop()
    
    def test_stats(self):
        """测试统计信息"""
        collector = MeteringCollector()
        mgr = QuotaManager(collector)
        
        mgr.set_default_quota(QuotaConfig(quota_id="d", name="D"))
        mgr.set_user_quota("alice", QuotaConfig(quota_id="a", name="A"))
        mgr.set_user_quota("bob", QuotaConfig(quota_id="b", name="B"))
        
        stats = mgr.get_stats()
        
        assert stats["user_quotas_count"] == 2
        assert stats["has_default_quota"] is True


# ===== Builtin Quotas Tests =====

class TestBuiltinQuotas:
    """测试内置配额"""
    
    def test_list_builtin_quotas(self):
        """测试列出内置配额"""
        quotas = list_builtin_quotas()
        
        assert len(quotas) >= 4
        assert "free-tier" in quotas
        assert "basic-tier" in quotas
        assert "premium-tier" in quotas
        assert "enterprise-tier" in quotas
    
    def test_free_tier(self):
        """测试免费层配额"""
        quota = get_builtin_quota("free-tier")
        
        assert quota is not None
        assert quota.max_calls_per_day == 500
        assert quota.max_cost_per_month == 10.0
        assert quota.block_on_exceed is True
    
    def test_enterprise_tier(self):
        """测试企业层配额"""
        quota = get_builtin_quota("enterprise-tier")
        
        assert quota is not None
        # 企业版无限制
        assert quota.max_calls_per_day is None
        assert quota.max_cost_per_month is None
        assert quota.block_on_exceed is False
    
    def test_nonexistent_quota(self):
        """测试获取不存在的配额"""
        quota = get_builtin_quota("nonexistent")
        assert quota is None


# ===== Integration Tests =====

class TestMeteringIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """测试完整工作流"""
        # 1. 创建采集器
        config = MeteringConfig(
            cost_per_call=0.001,
            buffer_size=50,
        )
        collector = MeteringCollector(config)
        await collector.start()
        
        try:
            # 2. 创建配额管理器
            quota_mgr = QuotaManager(collector)
            
            # 3. 设置配额
            quota_mgr.set_default_quota(get_builtin_quota("free-tier"))
            quota_mgr.set_user_quota("premium_user", get_builtin_quota("premium-tier"))
            
            # 4. 模拟调用
            for i in range(10):
                await collector.record(
                    user_id="free_user",
                    tool_name="browser/navigate",
                    duration_ms=100.0,
                    success=i % 3 != 0,  # 部分失败
                )
            
            for i in range(100):
                await collector.record(
                    user_id="premium_user",
                    tool_name="database/query",
                    duration_ms=50.0,
                    input_tokens=100,
                    output_tokens=500,
                )
            
            # 5. 检查统计
            free_stats = await collector.get_user_stats("free_user", "day")
            assert free_stats.total_calls == 10
            
            premium_stats = await collector.get_user_stats("premium_user", "day")
            assert premium_stats.total_calls == 100
            
            # 6. 检查配额
            free_status = await quota_mgr.get_quota_status("free_user")
            assert free_status["status"] == "ok"  # 10 次远低于 500/天
            
            premium_status = await quota_mgr.get_quota_status("premium_user")
            assert premium_status["status"] == "ok"  # 100 次远低于 20000/天
            
            # 7. 生成报告
            now = datetime.now()
            report = await collector.generate_report(
                period_start=now - timedelta(hours=1),
                period_end=now + timedelta(hours=1),
                group_by=MeteringDimension.USER,
            )
            
            assert len(report) >= 2
            
        finally:
            await collector.stop()
    
    @pytest.mark.asyncio
    async def test_multi_period_aggregation(self):
        """测试多周期聚合"""
        collector = MeteringCollector()
        await collector.start()
        
        try:
            # 记录调用
            for _ in range(5):
                await collector.record(
                    user_id="alice",
                    tool_name="test/tool",
                )
            
            # 检查各周期统计
            hour_stats = await collector.get_user_stats("alice", "hour")
            day_stats = await collector.get_user_stats("alice", "day")
            month_stats = await collector.get_user_stats("alice", "month")
            
            assert hour_stats.total_calls == 5
            assert day_stats.total_calls == 5
            assert month_stats.total_calls == 5
            
        finally:
            await collector.stop()
