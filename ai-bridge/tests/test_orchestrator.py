"""
测试 orchestrator.py - 多 Agent 编排器
"""

import asyncio
import pytest
from dataclasses import dataclass
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

from aibridge.core.orchestrator import (
    Orchestrator,
    TaskGraph,
    TaskNode,
    TaskState,
    ExecutionResult,
    TaskResult,
    TaskStatus,
    create_sequential_graph,
    create_parallel_graph,
    create_fan_out_fan_in_graph,
)


# ===== Mock ProtocolBridge =====

class MockProtocolBridge:
    """Mock 协议桥接器"""
    
    def __init__(self, responses: Dict[str, Any] = None):
        self._responses = responses or {}
        self._calls = []
    
    async def execute_task(self, task):
        self._calls.append({
            "agent_id": task.to_agent,
            "capability": task.capability,
            "input_data": task.input_data,
        })
        
        # 返回预设响应或默认响应
        key = f"{task.to_agent}:{task.capability}"
        if key in self._responses:
            response = self._responses[key]
            if isinstance(response, Exception):
                raise response
            return response
        
        return {"status": "ok", "task": task.capability}


# ===== TaskNode Tests =====

class TestTaskNode:
    """测试任务节点"""
    
    def test_task_node_creation(self):
        """测试创建任务节点"""
        task = TaskNode(
            task_id="t1",
            name="test",
            agent_id="agent1",
            capability="search",
        )
        
        assert task.task_id == "t1"
        assert task.state == TaskState.PENDING
        assert task.result is None
    
    def test_task_node_depends(self):
        """测试任务依赖"""
        task = TaskNode(
            task_id="t1",
            name="test",
            agent_id="agent1",
            capability="search",
            depends_on={"t0", "t00"},
        )
        
        assert "t0" in task.depends_on
        assert "t00" in task.depends_on
    
    def test_task_node_duration(self):
        """测试任务耗时"""
        task = TaskNode(
            task_id="t1",
            name="test",
            agent_id="agent1",
            capability="search",
        )
        
        assert task.duration_ms is None
        
        task.started_at = 1000.0
        task.completed_at = 1001.5
        
        assert task.duration_ms == 1500.0
    
    def test_task_node_to_dict(self):
        """测试转换为字典"""
        task = TaskNode(
            task_id="t1",
            name="test",
            agent_id="agent1",
            capability="search",
            depends_on={"t0"},
        )
        
        d = task.to_dict()
        
        assert d["task_id"] == "t1"
        assert d["name"] == "test"
        assert d["state"] == "pending"
        assert "t0" in d["depends_on"]


# ===== TaskGraph Tests =====

class TestTaskGraph:
    """测试任务图"""
    
    def test_add_task(self):
        """测试添加任务"""
        graph = TaskGraph(name="test-graph")
        
        task = graph.add_task(
            name="search",
            agent_id="search-agent",
            capability="web_search",
            input_data={"query": "test"},
        )
        
        assert task.task_id in graph.tasks
        assert task.name == "search"
        assert len(graph.tasks) == 1
    
    def test_add_task_with_dependency(self):
        """测试添加带依赖的任务"""
        graph = TaskGraph()
        
        t1 = graph.add_task(
            name="task1",
            agent_id="agent1",
            capability="cap1",
        )
        
        t2 = graph.add_task(
            name="task2",
            agent_id="agent2",
            capability="cap2",
            depends_on={t1.task_id},
        )
        
        assert t1.task_id in t2.depends_on
    
    def test_remove_task(self):
        """测试移除任务"""
        graph = TaskGraph()
        
        t1 = graph.add_task(name="t1", agent_id="a", capability="c")
        t2 = graph.add_task(name="t2", agent_id="a", capability="c", depends_on={t1.task_id})
        
        assert len(graph.tasks) == 2
        
        result = graph.remove_task(t1.task_id)
        
        assert result is True
        assert len(graph.tasks) == 1
        # 依赖也应该被移除
        assert t1.task_id not in t2.depends_on
    
    def test_get_root_tasks(self):
        """测试获取根任务"""
        graph = TaskGraph()
        
        t1 = graph.add_task(name="root1", agent_id="a", capability="c")
        t2 = graph.add_task(name="root2", agent_id="a", capability="c")
        t3 = graph.add_task(name="child", agent_id="a", capability="c", depends_on={t1.task_id})
        
        roots = graph.get_root_tasks()
        
        assert len(roots) == 2
        assert t1 in roots
        assert t2 in roots
        assert t3 not in roots
    
    def test_get_ready_tasks(self):
        """测试获取就绪任务"""
        graph = TaskGraph()
        
        t1 = graph.add_task(name="t1", agent_id="a", capability="c")
        t2 = graph.add_task(name="t2", agent_id="a", capability="c", depends_on={t1.task_id})
        t3 = graph.add_task(name="t3", agent_id="a", capability="c", depends_on={t2.task_id})
        
        # 初始状态，只有 t1 就绪
        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert t1 in ready
        
        # t1 完成后，t2 就绪
        t1.state = TaskState.COMPLETED
        ready = graph.get_ready_tasks()
        assert len(ready) == 1
        assert t2 in ready
    
    def test_validate_valid_graph(self):
        """测试验证有效图"""
        graph = TaskGraph()
        
        t1 = graph.add_task(name="t1", agent_id="a", capability="c")
        t2 = graph.add_task(name="t2", agent_id="a", capability="c", depends_on={t1.task_id})
        
        valid, errors = graph.validate()
        
        assert valid is True
        assert len(errors) == 0
    
    def test_validate_invalid_dependency(self):
        """测试验证无效依赖"""
        graph = TaskGraph()
        
        t1 = graph.add_task(name="t1", agent_id="a", capability="c")
        t1.depends_on.add("nonexistent")
        
        valid, errors = graph.validate()
        
        assert valid is False
        assert len(errors) > 0
    
    def test_validate_circular_dependency(self):
        """测试验证循环依赖"""
        graph = TaskGraph()
        
        t1 = graph.add_task(name="t1", agent_id="a", capability="c")
        t2 = graph.add_task(name="t2", agent_id="a", capability="c", depends_on={t1.task_id})
        
        # 手动创建循环
        t1.depends_on.add(t2.task_id)
        
        valid, errors = graph.validate()
        
        assert valid is False
        assert "Circular dependency" in errors[0]
    
    def test_get_execution_layers(self):
        """测试获取执行层次"""
        graph = TaskGraph()
        
        # 创建分层结构
        # Layer 0: t1, t2
        # Layer 1: t3 (depends on t1)
        # Layer 2: t4 (depends on t2, t3)
        
        t1 = graph.add_task(name="t1", agent_id="a", capability="c")
        t2 = graph.add_task(name="t2", agent_id="a", capability="c")
        t3 = graph.add_task(name="t3", agent_id="a", capability="c", depends_on={t1.task_id})
        t4 = graph.add_task(name="t4", agent_id="a", capability="c", depends_on={t2.task_id, t3.task_id})
        
        layers = graph.get_execution_layers()
        
        assert len(layers) == 3
        assert len(layers[0]) == 2  # t1, t2
        assert len(layers[1]) == 1  # t3
        assert len(layers[2]) == 1  # t4
    
    def test_to_dict(self):
        """测试转换为字典"""
        graph = TaskGraph(name="test")
        graph.add_task(name="t1", agent_id="a", capability="c")
        
        d = graph.to_dict()
        
        assert d["name"] == "test"
        assert len(d["tasks"]) == 1


# ===== ExecutionResult Tests =====

class TestExecutionResult:
    """测试执行结果"""
    
    def test_execution_result(self):
        """测试执行结果"""
        result = ExecutionResult(
            graph_id="g1",
            success=True,
            total_tasks=5,
            completed_tasks=5,
            start_time=1000.0,
            end_time=1002.0,
        )
        
        assert result.success is True
        assert result.duration_ms == 2000.0
    
    def test_to_dict(self):
        """测试转换为字典"""
        result = ExecutionResult(
            graph_id="g1",
            success=False,
            errors=["Error 1"],
            start_time=0,
            end_time=1,
        )
        
        d = result.to_dict()
        
        assert d["graph_id"] == "g1"
        assert d["success"] is False
        assert "Error 1" in d["errors"]


# ===== Backward Compatibility Tests =====

class TestBackwardCompatibility:
    """测试向后兼容性"""
    
    def test_task_status_alias(self):
        """测试 TaskStatus 别名"""
        assert TaskStatus == TaskState
        assert TaskStatus.PENDING == TaskState.PENDING
        assert TaskStatus.COMPLETED == TaskState.COMPLETED
    
    def test_task_result_alias(self):
        """测试 TaskResult 别名"""
        assert TaskResult == ExecutionResult


# ===== Orchestrator Tests =====

class TestOrchestrator:
    """测试编排器"""
    
    @pytest.mark.asyncio
    async def test_execute_simple_graph(self):
        """测试执行简单图"""
        bridge = MockProtocolBridge()
        orchestrator = Orchestrator(bridge)
        
        graph = TaskGraph(name="simple")
        graph.add_task(
            name="task1",
            agent_id="agent1",
            capability="process",
            input_data={"key": "value"},
        )
        
        result = await orchestrator.execute(graph)
        
        assert result.success is True
        assert result.completed_tasks == 1
        assert len(bridge._calls) == 1
    
    @pytest.mark.asyncio
    async def test_execute_sequential_graph(self):
        """测试执行顺序图"""
        bridge = MockProtocolBridge({
            "agent1:step1": {"output": "result1"},
            "agent1:step2": {"output": "result2"},
        })
        orchestrator = Orchestrator(bridge)
        
        graph = TaskGraph(name="sequential")
        t1 = graph.add_task(name="step1", agent_id="agent1", capability="step1")
        graph.add_task(name="step2", agent_id="agent1", capability="step2", depends_on={t1.task_id})
        
        result = await orchestrator.execute(graph)
        
        assert result.success is True
        assert result.completed_tasks == 2
        assert len(bridge._calls) == 2
        # 验证顺序
        assert bridge._calls[0]["capability"] == "step1"
        assert bridge._calls[1]["capability"] == "step2"
    
    @pytest.mark.asyncio
    async def test_execute_parallel_graph(self):
        """测试执行并行图"""
        bridge = MockProtocolBridge()
        orchestrator = Orchestrator(bridge)
        
        graph = TaskGraph(name="parallel")
        graph.add_task(name="task1", agent_id="agent1", capability="cap1")
        graph.add_task(name="task2", agent_id="agent2", capability="cap2")
        graph.add_task(name="task3", agent_id="agent3", capability="cap3")
        
        result = await orchestrator.execute(graph)
        
        assert result.success is True
        assert result.completed_tasks == 3
    
    @pytest.mark.asyncio
    async def test_execute_with_failure(self):
        """测试执行失败"""
        bridge = MockProtocolBridge({
            "agent1:fail": ValueError("Test failure"),
        })
        orchestrator = Orchestrator(bridge, max_retries=0)
        
        graph = TaskGraph(name="failing", fail_fast=True)
        graph.add_task(name="fail", agent_id="agent1", capability="fail")
        
        result = await orchestrator.execute(graph)
        
        assert result.success is False
        assert result.failed_tasks == 1
    
    @pytest.mark.asyncio
    async def test_execute_fail_fast(self):
        """测试快速失败"""
        bridge = MockProtocolBridge({
            "agent1:fail": ValueError("Fail"),
        })
        orchestrator = Orchestrator(bridge, max_retries=0)
        
        graph = TaskGraph(name="fail-fast", fail_fast=True)
        t1 = graph.add_task(name="fail", agent_id="agent1", capability="fail")
        graph.add_task(name="skip", agent_id="agent2", capability="skip", depends_on={t1.task_id})
        
        result = await orchestrator.execute(graph)
        
        assert result.failed_tasks == 1
        assert result.skipped_tasks == 1
    
    @pytest.mark.asyncio
    async def test_execute_invalid_graph(self):
        """测试执行无效图"""
        bridge = MockProtocolBridge()
        orchestrator = Orchestrator(bridge)
        
        graph = TaskGraph()
        t1 = graph.add_task(name="t1", agent_id="a", capability="c")
        t1.depends_on.add("nonexistent")  # 无效依赖
        
        result = await orchestrator.execute(graph)
        
        assert result.success is False
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_result_passing(self):
        """测试结果传递"""
        responses = {}
        
        async def dynamic_response(task):
            if task.capability == "step2":
                # 验证前一个任务的结果被传递
                return {"received": task.input_data.get("previous_result")}
            return {"data": "from_step1"}
        
        bridge = MagicMock()
        bridge.execute_task = dynamic_response
        
        orchestrator = Orchestrator(bridge)
        
        graph = TaskGraph()
        t1 = graph.add_task(name="step1", agent_id="a", capability="step1")
        graph.add_task(
            name="step2",
            agent_id="a",
            capability="step2",
            depends_on={t1.task_id},
            input_data={"use_result_from": t1.task_id},
        )
        
        result = await orchestrator.execute(graph)
        
        assert result.success is True
        # step2 应该收到 step1 的结果
        step2_result = result.task_results.get(list(graph.tasks.keys())[1])
        assert step2_result["received"] == {"data": "from_step1"}
    
    def test_stats(self):
        """测试统计信息"""
        bridge = MockProtocolBridge()
        orchestrator = Orchestrator(bridge)
        
        stats = orchestrator.get_stats()
        
        assert "executions" in stats
        assert "successful" in stats
        assert "failed" in stats


# ===== Convenience Functions Tests =====

class TestConvenienceFunctions:
    """测试便捷函数"""
    
    def test_create_sequential_graph(self):
        """测试创建顺序图"""
        tasks = [
            {"name": "t1", "agent_id": "a1", "capability": "c1"},
            {"name": "t2", "agent_id": "a2", "capability": "c2"},
            {"name": "t3", "agent_id": "a3", "capability": "c3"},
        ]
        
        graph = create_sequential_graph("seq-test", tasks)
        
        assert len(graph.tasks) == 3
        
        # 验证依赖链
        layers = graph.get_execution_layers()
        assert len(layers) == 3
    
    def test_create_parallel_graph(self):
        """测试创建并行图"""
        tasks = [
            {"name": "t1", "agent_id": "a1", "capability": "c1"},
            {"name": "t2", "agent_id": "a2", "capability": "c2"},
        ]
        
        graph = create_parallel_graph("par-test", tasks)
        
        assert len(graph.tasks) == 2
        
        # 所有任务应该在同一层
        layers = graph.get_execution_layers()
        assert len(layers) == 1
        assert len(layers[0]) == 2
    
    def test_create_parallel_graph_with_aggregator(self):
        """测试创建带聚合器的并行图"""
        tasks = [
            {"name": "t1", "agent_id": "a1", "capability": "c1"},
            {"name": "t2", "agent_id": "a2", "capability": "c2"},
        ]
        aggregator = {"name": "agg", "agent_id": "agg", "capability": "merge"}
        
        graph = create_parallel_graph("par-agg", tasks, aggregator)
        
        assert len(graph.tasks) == 3
        
        # 两层：并行任务 + 聚合任务
        layers = graph.get_execution_layers()
        assert len(layers) == 2
        assert len(layers[0]) == 2
        assert len(layers[1]) == 1
    
    def test_create_fan_out_fan_in_graph(self):
        """测试创建扇出扇入图"""
        splitter = {"name": "split", "agent_id": "s", "capability": "split"}
        workers = [
            {"name": "w1", "agent_id": "w", "capability": "work"},
            {"name": "w2", "agent_id": "w", "capability": "work"},
            {"name": "w3", "agent_id": "w", "capability": "work"},
        ]
        merger = {"name": "merge", "agent_id": "m", "capability": "merge"}
        
        graph = create_fan_out_fan_in_graph("fan", splitter, workers, merger)
        
        assert len(graph.tasks) == 5  # 1 split + 3 workers + 1 merge
        
        # 三层：split -> workers -> merge
        layers = graph.get_execution_layers()
        assert len(layers) == 3
        assert len(layers[0]) == 1  # split
        assert len(layers[1]) == 3  # workers
        assert len(layers[2]) == 1  # merge
