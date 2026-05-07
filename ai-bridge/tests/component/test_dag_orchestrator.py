"""
Component Tests — DAG 编排引擎 (L1)

Phase IV v1.0.0 — TaskGraph/TaskNode 任务依赖和执行顺序。
"""

from __future__ import annotations

import pytest

from aibridge.core.orchestrator import TaskGraph, TaskNode, TaskState


class TestDAGOrchestrator:
    """TaskGraph / TaskNode 组件测试"""

    def test_single_task_no_dependencies(self):
        """单任务无依赖 — 直接就绪"""
        graph = TaskGraph(name="single")
        task = graph.add_task(
            name="task1", agent_id="agent-a", capability="compute"
        )
        assert task.task_id is not None
        assert len(task.depends_on) == 0
        assert task.state == TaskState.PENDING
        # 无依赖的根任务就是就绪任务
        roots = graph.get_root_tasks()
        assert len(roots) == 1
        assert roots[0].task_id == task.task_id

    def test_sequential_two_node(self):
        """串行依赖 — task2 依赖 task1"""
        graph = TaskGraph(name="sequential")
        t1 = graph.add_task(name="step1", agent_id="a", capability="A")
        t2 = graph.add_task(
            name="step2", agent_id="b", capability="B",
            depends_on={t1.task_id},
        )
        assert t1.task_id in t2.depends_on
        assert t2.task_id not in (t1.depends_on or set())

        # 验证图结构
        roots = graph.get_root_tasks()
        assert len(roots) == 1
        assert roots[0].task_id == t1.task_id

    def test_parallel_independent_nodes(self):
        """无依赖并行 — 两个任务互相独立"""
        graph = TaskGraph(name="parallel")
        t1 = graph.add_task(name="A", agent_id="a1", capability="ca")
        t2 = graph.add_task(name="B", agent_id="a2", capability="cb")
        assert len(t1.depends_on) == 0
        assert len(t2.depends_on) == 0

        roots = graph.get_root_tasks()
        assert len(roots) == 2

    def test_dependency_chain_execution_order(self):
        """依赖链 — A→B→C，根任务只有 A"""
        graph = TaskGraph(name="chain")
        a = graph.add_task(name="A", agent_id="a1", capability="C")
        b = graph.add_task(name="B", agent_id="a2", capability="C",
                           depends_on={a.task_id})
        c = graph.add_task(name="C", agent_id="a3", capability="C",
                           depends_on={b.task_id})
        roots = graph.get_root_tasks()
        assert len(roots) == 1
        assert roots[0].task_id == a.task_id

    def test_node_failure_sets_state(self):
        """节点设置 FAILED 状态"""
        node = TaskNode(
            task_id="fail-1", name="fail", agent_id="a", capability="X",
        )
        assert node.state == TaskState.PENDING
        node.state = TaskState.FAILED
        node.error = "simulated crash"
        assert node.state == TaskState.FAILED
        assert "simulated crash" in node.error

    def test_remove_task_cleans_dependencies(self):
        """移除任务时清理依赖关系"""
        graph = TaskGraph(name="remove-test")
        a = graph.add_task(name="A", agent_id="a1", capability="X")
        b = graph.add_task(name="B", agent_id="a2", capability="X",
                           depends_on={a.task_id})

        graph.remove_task(a.task_id)
        # b 对 a 的依赖被清除
        b_after = graph.get_task(b.task_id)
        assert b_after is not None
        assert a.task_id not in b_after.depends_on
