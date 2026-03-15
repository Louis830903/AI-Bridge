"""
企业级能力集成测试

测试 Policy、Metering、Tracing、Orchestrator 模块的协同工作场景。
"""

import asyncio
import pytest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock

# Policy imports
from aibridge.enterprise.policy import (
    PolicyEngine,
    PolicyMiddleware,
    PolicyStatement,
    PolicyEffect,
    PolicyAction,
    ToolPolicy,
    get_builtin_policy,
)

# Metering imports
from aibridge.enterprise.metering import (
    MeteringCollector,
    MeteringConfig,
    QuotaManager,
    QuotaConfig,
    QuotaExceeded,
)

# Tracing imports
from aibridge.enterprise.tracing import (
    Tracer,
    TracerConfig,
    SpanKind,
    SpanStatus,
    InMemoryExporter,
)

# Orchestrator imports
from aibridge.core.orchestrator import (
    TaskGraph,
    TaskNode,
    TaskState,
    ExecutionResult,
)


# ===== Mock Classes =====

@dataclass
class MockRole:
    name: str


@dataclass
class MockAuthContext:
    user_id: str
    role: Optional[MockRole] = None
    authenticated: bool = True


# ===== Integration Test: Policy + Metering =====

class TestPolicyMeteringIntegration:
    """测试 Policy 和 Metering 集成"""
    
    @pytest.fixture
    def policy_engine(self):
        engine = PolicyEngine()
        
        # 创建开发者策略：允许 browser，拒绝 filesystem
        dev_policy = ToolPolicy(
            policy_id="dev-policy",
            name="Developer Policy",
            statements=[
                PolicyStatement(
                    sid="allow-browser",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["browser/*"],
                ),
                PolicyStatement(
                    sid="deny-filesystem",
                    effect=PolicyEffect.DENY,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["filesystem/*"],
                ),
            ]
        )
        engine.register_policy(dev_policy)
        engine.attach_policy("user:dev1", "dev-policy")
        
        return engine
    
    @pytest.fixture
    def metering_collector(self):
        config = MeteringConfig(
            cost_per_call=0.001,
            cost_per_second=0.0001,
        )
        return MeteringCollector(config)
    
    @pytest.mark.asyncio
    async def test_policy_check_then_metering(self, policy_engine, metering_collector):
        """测试先策略检查再计量"""
        await metering_collector.start()
        
        try:
            user_id = "dev1"
            tool_name = "browser/navigate"
            
            # 1. 策略检查
            result = policy_engine.evaluate(
                user_id=user_id,
                action=PolicyAction.CALL_TOOL,
                resource=tool_name,
            )
            assert result.allowed is True
            
            # 2. 执行并计量
            record = await metering_collector.record(
                user_id=user_id,
                tool_name=tool_name,
                server_name="browser-use",
                duration_ms=100.0,
                success=True,
            )
            
            assert record.user_id == user_id
            assert record.tool_name == tool_name
            
            # 3. 检查统计
            stats = await metering_collector.get_user_stats(user_id, "day")
            assert stats is not None
            assert stats.total_calls == 1
            
        finally:
            await metering_collector.stop()
    
    @pytest.mark.asyncio
    async def test_policy_denied_no_metering(self, policy_engine, metering_collector):
        """测试策略拒绝时不计量"""
        await metering_collector.start()
        
        try:
            user_id = "dev1"
            tool_name = "filesystem/read"
            
            # 1. 策略检查 - 应该拒绝
            result = policy_engine.evaluate(
                user_id=user_id,
                action=PolicyAction.CALL_TOOL,
                resource=tool_name,
            )
            assert result.allowed is False
            
            # 2. 不记录计量（因为被拒绝）
            if result.allowed:
                await metering_collector.record(
                    user_id=user_id,
                    tool_name=tool_name,
                    duration_ms=100.0,
                    success=True,
                )
            
            # 3. 检查统计 - 应该没有记录
            stats = await metering_collector.get_user_stats(user_id, "day")
            assert stats is None or stats.total_calls == 0
            
        finally:
            await metering_collector.stop()
    
    @pytest.mark.asyncio
    async def test_quota_enforcement_with_policy(self, policy_engine, metering_collector):
        """测试配额强制执行与策略结合"""
        await metering_collector.start()
        
        try:
            quota_manager = QuotaManager(metering_collector)
            
            # 设置低配额便于测试
            quota_manager.set_user_quota("dev1", QuotaConfig(
                quota_id="test-quota",
                name="Test Quota",
                max_calls_per_day=3,
                block_on_exceed=True,
            ))
            
            user_id = "dev1"
            tool_name = "browser/navigate"
            
            # 模拟多次调用
            for i in range(3):
                # 策略检查
                result = policy_engine.evaluate(
                    user_id=user_id,
                    action=PolicyAction.CALL_TOOL,
                    resource=tool_name,
                )
                assert result.allowed is True
                
                # 配额检查
                await quota_manager.check_quota(user_id)
                
                # 记录调用
                await metering_collector.record(
                    user_id=user_id,
                    tool_name=tool_name,
                    duration_ms=50.0,
                    success=True,
                )
            
            # 第4次调用应该超配额
            with pytest.raises(QuotaExceeded):
                await quota_manager.check_quota(user_id)
                
        finally:
            await metering_collector.stop()


# ===== Integration Test: Policy + Tracing =====

class TestPolicyTracingIntegration:
    """测试 Policy 和 Tracing 集成"""
    
    @pytest.fixture
    def tracer_with_exporter(self):
        exporter = InMemoryExporter()
        config = TracerConfig(service_name="test-service")
        tracer = Tracer(config)
        tracer.add_exporter(exporter)
        return tracer, exporter
    
    @pytest.fixture
    def policy_engine(self):
        engine = PolicyEngine()
        engine.register_policy(get_builtin_policy("admin-full-access"))
        engine.attach_policy("user:admin", "admin-full-access")
        return engine
    
    def test_traced_policy_evaluation(self, tracer_with_exporter, policy_engine):
        """测试带追踪的策略评估"""
        tracer, exporter = tracer_with_exporter
        
        with tracer.start_as_current_span("tool_call", kind=SpanKind.SERVER) as span:
            span.set_attribute("user.id", "admin")
            span.set_attribute("tool.name", "browser/navigate")
            
            # 策略评估
            result = policy_engine.evaluate(
                user_id="admin",
                action=PolicyAction.CALL_TOOL,
                resource="browser/navigate",
            )
            
            span.set_attribute("policy.allowed", result.allowed)
            span.set_attribute("policy.matched", result.matched_policy or "none")
            
            if result.allowed:
                span.set_status(SpanStatus.OK)
            else:
                span.set_status(SpanStatus.ERROR, "Access denied")
        
        # 验证 span 属性
        assert span.attributes["user.id"] == "admin"
        assert span.attributes["policy.allowed"] is True
        assert span.status == SpanStatus.OK
    
    def test_nested_spans_with_policy(self, tracer_with_exporter, policy_engine):
        """测试嵌套 span 与策略"""
        tracer, exporter = tracer_with_exporter
        
        with tracer.start_as_current_span("request", kind=SpanKind.SERVER) as parent:
            parent.set_attribute("request.id", "req-123")
            
            # 子 span: 策略评估
            with tracer.start_as_current_span("policy_check") as policy_span:
                result = policy_engine.evaluate(
                    user_id="admin",
                    action=PolicyAction.CALL_TOOL,
                    resource="database/query",
                )
                policy_span.set_attribute("policy.result", result.allowed)
            
            # 子 span: 工具执行
            with tracer.start_as_current_span("tool_execute") as tool_span:
                tool_span.set_attribute("tool.name", "database/query")
                tool_span.set_status(SpanStatus.OK)
        
        # 验证父子关系
        assert policy_span.parent is not None  # 有父 span
        assert tool_span.parent is not None  # 有父 span


# ===== Integration Test: Metering + Tracing =====

class TestMeteringTracingIntegration:
    """测试 Metering 和 Tracing 集成"""
    
    @pytest.fixture
    def tracer_with_exporter(self):
        exporter = InMemoryExporter()
        config = TracerConfig(service_name="test-service")
        tracer = Tracer(config)
        tracer.add_exporter(exporter)
        return tracer, exporter
    
    @pytest.fixture
    def metering_collector(self):
        return MeteringCollector(MeteringConfig())
    
    @pytest.mark.asyncio
    async def test_metering_with_trace_context(self, tracer_with_exporter, metering_collector):
        """测试计量记录包含追踪上下文"""
        tracer, exporter = tracer_with_exporter
        await metering_collector.start()
        
        try:
            with tracer.start_as_current_span("tool_call") as span:
                trace_id = span.context.trace_id
                span_id = span.context.span_id
                
                # 记录调用，包含追踪信息
                record = await metering_collector.record(
                    user_id="user1",
                    tool_name="browser/click",
                    duration_ms=75.0,
                    success=True,
                    trace_id=trace_id,
                    span_id=span_id,
                )
                
                assert record.metadata.get("trace_id") == trace_id
                assert record.metadata.get("span_id") == span_id
                
        finally:
            await metering_collector.stop()
    
    @pytest.mark.asyncio
    async def test_traced_metering_workflow(self, tracer_with_exporter, metering_collector):
        """测试追踪计量工作流"""
        tracer, exporter = tracer_with_exporter
        await metering_collector.start()
        
        try:
            with tracer.start_as_current_span("metered_workflow") as span:
                # 记录调用
                await metering_collector.record(
                    user_id="user1",
                    tool_name="test/operation",
                    duration_ms=50.0,
                    success=True,
                )
                span.set_status(SpanStatus.OK)
            
            # 验证计量
            stats = await metering_collector.get_user_stats("user1", "day")
            assert stats.total_calls == 1
            
            # 验证追踪
            assert span.status == SpanStatus.OK
            
        finally:
            await metering_collector.stop()


# ===== Integration Test: Full Enterprise Flow =====

class TestFullEnterpriseFlow:
    """测试完整的企业级流程"""
    
    @pytest.fixture
    def enterprise_stack(self):
        """创建完整的企业级栈"""
        # Policy
        policy_engine = PolicyEngine()
        policy_engine.register_policy(get_builtin_policy("admin-full-access"))
        policy_engine.attach_policy("user:admin", "admin-full-access")
        
        # Metering
        metering = MeteringCollector(MeteringConfig(
            cost_per_call=0.01,
            cost_per_second=0.001,
        ))
        
        # Quota
        quota = QuotaManager(metering)
        
        # Tracing
        exporter = InMemoryExporter()
        config = TracerConfig(service_name="ai-bridge")
        tracer = Tracer(config)
        tracer.add_exporter(exporter)
        
        return {
            "policy": policy_engine,
            "metering": metering,
            "quota": quota,
            "tracer": tracer,
            "exporter": exporter,
        }
    
    @pytest.mark.asyncio
    async def test_full_tool_call_flow(self, enterprise_stack):
        """测试完整的工具调用流程"""
        policy = enterprise_stack["policy"]
        metering = enterprise_stack["metering"]
        tracer = enterprise_stack["tracer"]
        
        await metering.start()
        
        try:
            user_id = "admin"
            tool_name = "browser/navigate"
            
            with tracer.start_as_current_span("tool_call", kind=SpanKind.SERVER) as span:
                span.set_attribute("user.id", user_id)
                span.set_attribute("tool.name", tool_name)
                
                # 1. 策略检查
                policy_result = policy.evaluate(
                    user_id=user_id,
                    action=PolicyAction.CALL_TOOL,
                    resource=tool_name,
                )
                span.set_attribute("policy.allowed", policy_result.allowed)
                
                if not policy_result.allowed:
                    span.set_status(SpanStatus.ERROR, "Policy denied")
                    return
                
                # 2. 执行工具（模拟）
                span.add_event("tool_executed", {"url": "https://example.com"})
                
                # 3. 记录计量
                record = await metering.record(
                    user_id=user_id,
                    tool_name=tool_name,
                    server_name="browser-use",
                    duration_ms=100.0,
                    success=True,
                )
                
                span.set_attribute("metering.record_id", record.record_id)
                span.set_status(SpanStatus.OK)
            
            # 验证结果
            assert span.status == SpanStatus.OK
            assert span.attributes["policy.allowed"] is True
            
            stats = await metering.get_user_stats(user_id, "day")
            assert stats.total_calls == 1
            
        finally:
            await metering.stop()
    
    @pytest.mark.asyncio
    async def test_denied_user_flow(self, enterprise_stack):
        """测试拒绝用户流程"""
        policy = enterprise_stack["policy"]
        metering = enterprise_stack["metering"]
        
        await metering.start()
        
        try:
            # 未授权用户
            user_id = "unauthorized"
            
            # 策略检查 - 应该拒绝（无策略）
            denied_result = policy.evaluate(
                user_id=user_id,
                action=PolicyAction.CALL_TOOL,
                resource="browser/navigate",
            )
            assert denied_result.allowed is False
            
            # 不应该有计量记录
            stats = await metering.get_user_stats(user_id, "day")
            assert stats is None
                
        finally:
            await metering.stop()


# ===== Integration Test: TaskGraph with Enterprise Stack =====

class TestTaskGraphEnterprise:
    """测试任务图与企业级功能集成"""
    
    def test_task_graph_creation_and_validation(self):
        """测试任务图创建和验证"""
        graph = TaskGraph(name="test-workflow")
        
        t1 = graph.add_task(
            name="task1",
            agent_id="agent-a",
            capability="process",
        )
        
        t2 = graph.add_task(
            name="task2",
            agent_id="agent-b",
            capability="analyze",
            depends_on={t1.task_id},
        )
        
        # 验证图结构
        assert len(graph.tasks) == 2
        assert t2.depends_on == {t1.task_id}
        
        # 验证图有效性
        valid, errors = graph.validate()
        assert valid is True
        assert len(errors) == 0
    
    def test_task_graph_with_tracing(self):
        """测试任务图与追踪集成"""
        exporter = InMemoryExporter()
        config = TracerConfig(service_name="orchestrator")
        tracer = Tracer(config)
        tracer.add_exporter(exporter)
        
        graph = TaskGraph(name="traced-workflow")
        
        with tracer.start_as_current_span("workflow_build") as span:
            span.set_attribute("workflow.name", graph.name)
            
            t1 = graph.add_task(
                name="step1",
                agent_id="agent-1",
                capability="fetch",
            )
            span.add_event("task_added", {"task_id": t1.task_id})
            
            t2 = graph.add_task(
                name="step2",
                agent_id="agent-2",
                capability="process",
                depends_on={t1.task_id},
            )
            span.add_event("task_added", {"task_id": t2.task_id})
            
            valid, _ = graph.validate()
            span.set_attribute("workflow.valid", valid)
            span.set_status(SpanStatus.OK)
        
        assert valid is True
        assert span.status == SpanStatus.OK
        assert len(span.events) == 2
    
    @pytest.mark.asyncio
    async def test_task_graph_with_metering(self):
        """测试任务图与计量集成"""
        metering = MeteringCollector(MeteringConfig())
        await metering.start()
        
        try:
            graph = TaskGraph(name="metered-workflow")
            
            # 添加任务
            for i in range(3):
                graph.add_task(
                    name=f"task{i}",
                    agent_id=f"agent-{i}",
                    capability="process",
                )
            
            # 记录工作流创建
            await metering.record(
                user_id="orchestrator",
                tool_name="workflow/create",
                duration_ms=5.0,
                success=True,
                workflow_name=graph.name,
                task_count=len(graph.tasks),
            )
            
            stats = await metering.get_user_stats("orchestrator", "day")
            assert stats.total_calls == 1
            
        finally:
            await metering.stop()


# ===== Cross-Module Statistics =====

class TestCrossModuleStatistics:
    """测试跨模块统计"""
    
    @pytest.mark.asyncio
    async def test_enterprise_stats_aggregation(self):
        """测试企业级统计聚合"""
        # Policy
        policy_engine = PolicyEngine()
        policy_engine.register_policy(get_builtin_policy("admin-full-access"))
        policy_engine.attach_policy("user:test", "admin-full-access")
        
        # Metering
        metering = MeteringCollector(MeteringConfig())
        await metering.start()
        
        # Tracing
        exporter = InMemoryExporter()
        config = TracerConfig(service_name="test")
        tracer = Tracer(config)
        tracer.add_exporter(exporter)
        
        try:
            # 执行多次操作
            for i in range(5):
                with tracer.start_as_current_span(f"operation_{i}"):
                    policy_engine.evaluate(
                        user_id="test",
                        action=PolicyAction.CALL_TOOL,
                        resource=f"tool/{i}",
                    )
                    await metering.record(
                        user_id="test",
                        tool_name=f"tool/{i}",
                        duration_ms=10.0 * (i + 1),
                        success=True,
                    )
            
            # 验证 Policy 统计
            policy_stats = policy_engine.get_stats()
            assert "policies_count" in policy_stats
            
            # 验证 Metering 统计
            metering_stats = await metering.get_user_stats("test", "day")
            assert metering_stats.total_calls == 5
            
            # 验证 Tracing 统计
            tracer_stats = tracer.get_stats()
            assert "service_name" in tracer_stats
            
        finally:
            await metering.stop()


# ===== Error Handling Integration =====

class TestErrorHandlingIntegration:
    """测试错误处理集成"""
    
    @pytest.mark.asyncio
    async def test_policy_error_with_tracing(self):
        """测试策略错误与追踪"""
        exporter = InMemoryExporter()
        config = TracerConfig(service_name="test")
        tracer = Tracer(config)
        tracer.add_exporter(exporter)
        
        policy_engine = PolicyEngine()
        # 不注册任何策略，所有请求应该被拒绝
        
        with tracer.start_as_current_span("tool_call") as span:
            result = policy_engine.evaluate(
                user_id="unknown",
                action=PolicyAction.CALL_TOOL,
                resource="any/tool",
            )
            
            span.set_attribute("policy.allowed", result.allowed)
            
            if not result.allowed:
                span.set_status(SpanStatus.ERROR, result.reason)
        
        assert result.allowed is False
        assert span.status == SpanStatus.ERROR
    
    @pytest.mark.asyncio
    async def test_quota_exceeded_with_tracing(self):
        """测试配额超限与追踪"""
        metering = MeteringCollector(MeteringConfig())
        await metering.start()
        
        exporter = InMemoryExporter()
        config = TracerConfig(service_name="test")
        tracer = Tracer(config)
        tracer.add_exporter(exporter)
        
        try:
            quota_manager = QuotaManager(metering)
            quota_manager.set_user_quota("limited", QuotaConfig(
                quota_id="test",
                name="Test",
                max_calls_per_day=2,
                block_on_exceed=True,
            ))
            
            # 使用配额
            for _ in range(2):
                await metering.record(
                    user_id="limited",
                    tool_name="test/tool",
                    duration_ms=10.0,
                    success=True,
                )
            
            # 尝试超限
            with tracer.start_as_current_span("quota_check") as span:
                try:
                    await quota_manager.check_quota("limited")
                    span.set_status(SpanStatus.OK)
                except QuotaExceeded as e:
                    span.set_status(SpanStatus.ERROR, str(e))
                    span.set_attribute("quota.exceeded", True)
            
            assert span.status == SpanStatus.ERROR
            assert span.attributes.get("quota.exceeded") is True
            
        finally:
            await metering.stop()
