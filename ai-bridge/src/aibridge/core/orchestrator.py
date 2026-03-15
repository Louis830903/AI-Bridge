"""
多 Agent 编排器

提供 Agent 协作任务的调度和编排能力：
- TaskGraph: 任务依赖图
- Orchestrator: 编排器，调度多 Agent 协作
- ExecutionPlan: 执行计划
- ParallelExecutor: 并行执行器

支持功能：
- DAG 任务依赖
- 并行/串行执行
- 失败重试
- 超时控制
- 结果聚合
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ..gateway.protocol_bridge import ProtocolBridge
    from ..enterprise.tracing import Tracer

logger = logging.getLogger(__name__)


class TaskState(Enum):
    """任务状态"""
    PENDING = "pending"       # 等待执行
    READY = "ready"           # 就绪（依赖已满足）
    RUNNING = "running"       # 执行中
    COMPLETED = "completed"   # 完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 取消
    SKIPPED = "skipped"       # 跳过


@dataclass
class TaskNode:
    """
    任务节点
    
    代表执行图中的一个任务。
    """
    task_id: str
    name: str
    
    # 执行目标
    agent_id: str                          # 目标 Agent
    capability: str                        # 能力名称
    input_data: Dict[str, Any] = field(default_factory=dict)
    
    # 依赖关系
    depends_on: Set[str] = field(default_factory=set)  # 依赖的任务 ID
    
    # 执行配置
    timeout: float = 60.0                  # 超时（秒）
    retry_count: int = 0                   # 重试次数
    retry_delay: float = 1.0               # 重试延迟
    
    # 运行时状态
    state: TaskState = TaskState.PENDING
    result: Any = None
    error: Optional[str] = None
    
    # 时间戳
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """执行耗时（毫秒）"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "agent_id": self.agent_id,
            "capability": self.capability,
            "state": self.state.value,
            "depends_on": list(self.depends_on),
            "result": self.result,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }


@dataclass
class TaskGraph:
    """
    任务依赖图
    
    定义多个任务之间的依赖关系，形成 DAG（有向无环图）。
    
    使用示例：
    ```python
    graph = TaskGraph()
    
    # 添加任务
    task1 = graph.add_task(
        name="search",
        agent_id="search-agent",
        capability="web_search",
        input_data={"query": "AI news"}
    )
    
    task2 = graph.add_task(
        name="summarize",
        agent_id="llm-agent",
        capability="summarize",
        depends_on={task1.task_id}  # 依赖 task1
    )
    
    # 验证图
    if graph.validate():
        plan = graph.get_execution_plan()
    ```
    """
    graph_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = ""
    description: str = ""
    
    # 任务节点
    tasks: Dict[str, TaskNode] = field(default_factory=dict)
    
    # 配置
    fail_fast: bool = True    # 遇到失败立即停止
    max_parallel: int = 10    # 最大并行数
    
    def add_task(
        self,
        name: str,
        agent_id: str,
        capability: str,
        input_data: Optional[Dict[str, Any]] = None,
        depends_on: Optional[Set[str]] = None,
        timeout: float = 60.0,
        retry_count: int = 0,
    ) -> TaskNode:
        """
        添加任务节点
        
        Args:
            name: 任务名称
            agent_id: 目标 Agent ID
            capability: 能力名称
            input_data: 输入数据
            depends_on: 依赖的任务 ID 集合
            timeout: 超时秒数
            retry_count: 重试次数
            
        Returns:
            TaskNode
        """
        task_id = f"{self.graph_id}-{len(self.tasks):03d}"
        
        task = TaskNode(
            task_id=task_id,
            name=name,
            agent_id=agent_id,
            capability=capability,
            input_data=input_data or {},
            depends_on=depends_on or set(),
            timeout=timeout,
            retry_count=retry_count,
        )
        
        self.tasks[task_id] = task
        return task
    
    def remove_task(self, task_id: str) -> bool:
        """移除任务"""
        if task_id in self.tasks:
            # 同时移除其他任务对它的依赖
            for task in self.tasks.values():
                task.depends_on.discard(task_id)
            del self.tasks[task_id]
            return True
        return False
    
    def add_dependency(self, task_id: str, depends_on: str) -> bool:
        """添加依赖关系"""
        if task_id in self.tasks and depends_on in self.tasks:
            self.tasks[task_id].depends_on.add(depends_on)
            return True
        return False
    
    def get_task(self, task_id: str) -> Optional[TaskNode]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_root_tasks(self) -> List[TaskNode]:
        """获取根任务（无依赖）"""
        return [t for t in self.tasks.values() if not t.depends_on]
    
    def get_ready_tasks(self) -> List[TaskNode]:
        """获取就绪任务（依赖已完成）"""
        ready = []
        for task in self.tasks.values():
            if task.state != TaskState.PENDING:
                continue
            
            # 检查所有依赖是否完成
            deps_satisfied = all(
                self.tasks[dep].state == TaskState.COMPLETED
                for dep in task.depends_on
                if dep in self.tasks
            )
            
            if deps_satisfied:
                ready.append(task)
        
        return ready
    
    def get_downstream_tasks(self, task_id: str) -> List[TaskNode]:
        """获取下游任务（依赖此任务的）"""
        return [
            t for t in self.tasks.values()
            if task_id in t.depends_on
        ]
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        验证任务图
        
        检查：
        - 依赖引用有效
        - 无循环依赖
        
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        # 检查依赖引用
        for task in self.tasks.values():
            for dep in task.depends_on:
                if dep not in self.tasks:
                    errors.append(f"Task {task.task_id} depends on non-existent task {dep}")
        
        # 检查循环依赖
        visited = set()
        rec_stack = set()
        
        def has_cycle(task_id: str) -> bool:
            visited.add(task_id)
            rec_stack.add(task_id)
            
            for dep in self.tasks[task_id].depends_on:
                if dep not in self.tasks:
                    continue  # 跳过不存在的依赖（已在前面报错）
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(task_id)
            return False
        
        for task_id in self.tasks:
            if task_id not in visited:
                if has_cycle(task_id):
                    errors.append("Circular dependency detected")
                    break
        
        return len(errors) == 0, errors
    
    def get_execution_layers(self) -> List[List[TaskNode]]:
        """
        获取执行层次
        
        将任务按依赖关系分层，同一层的任务可并行执行。
        
        Returns:
            任务层次列表
        """
        layers = []
        remaining = set(self.tasks.keys())
        completed = set()
        
        while remaining:
            # 找出当前可执行的任务（依赖都已在 completed 中）
            layer = []
            for task_id in list(remaining):
                task = self.tasks[task_id]
                if task.depends_on.issubset(completed):
                    layer.append(task)
                    remaining.remove(task_id)
            
            if not layer:
                # 无法继续（存在循环依赖）
                break
            
            layers.append(layer)
            completed.update(t.task_id for t in layer)
        
        return layers
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
            "fail_fast": self.fail_fast,
            "max_parallel": self.max_parallel,
        }


@dataclass
class ExecutionResult:
    """执行结果"""
    graph_id: str
    success: bool
    
    # 统计
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    
    # 耗时
    start_time: float = 0.0
    end_time: float = 0.0
    
    # 任务结果
    task_results: Dict[str, Any] = field(default_factory=dict)
    
    # 错误信息
    errors: List[str] = field(default_factory=list)
    
    @property
    def duration_ms(self) -> float:
        """总耗时（毫秒）"""
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "graph_id": self.graph_id,
            "success": self.success,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "skipped_tasks": self.skipped_tasks,
            "duration_ms": self.duration_ms,
            "task_results": self.task_results,
            "errors": self.errors,
        }


class Orchestrator:
    """
    多 Agent 编排器
    
    调度和执行多 Agent 协作任务。
    
    使用示例：
    ```python
    from aibridge.gateway.protocol_bridge import ProtocolBridge
    
    bridge = ProtocolBridge(mcp_registry, a2a_gateway)
    orchestrator = Orchestrator(bridge)
    
    # 创建任务图
    graph = TaskGraph(name="research-workflow")
    
    t1 = graph.add_task(
        name="search",
        agent_id="search-agent",
        capability="web_search",
        input_data={"query": "AI trends 2025"}
    )
    
    t2 = graph.add_task(
        name="analyze",
        agent_id="analyzer-agent",
        capability="analyze",
        depends_on={t1.task_id},
        input_data={"use_result_from": t1.task_id}
    )
    
    t3 = graph.add_task(
        name="report",
        agent_id="writer-agent",
        capability="generate_report",
        depends_on={t2.task_id}
    )
    
    # 执行
    result = await orchestrator.execute(graph)
    print(f"Completed: {result.completed_tasks}/{result.total_tasks}")
    ```
    """
    
    def __init__(
        self,
        bridge: "ProtocolBridge",
        tracer: Optional["Tracer"] = None,
        default_timeout: float = 60.0,
        max_retries: int = 3,
    ):
        self._bridge = bridge
        self._tracer = tracer
        self._default_timeout = default_timeout
        self._max_retries = max_retries
        
        # 运行中的图
        self._running_graphs: Dict[str, TaskGraph] = {}
        
        # 取消事件（用于实际取消异步任务）
        self._cancel_events: Dict[str, asyncio.Event] = {}
        
        # 统计
        self._stats = {
            "executions": 0,
            "successful": 0,
            "failed": 0,
            "total_tasks": 0,
        }
    
    async def execute(
        self,
        graph: TaskGraph,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """
        执行任务图
        
        Args:
            graph: 任务图
            context: 执行上下文（可在任务间共享）
            
        Returns:
            ExecutionResult
        """
        self._stats["executions"] += 1
        start_time = time.time()
        
        # 验证图
        valid, errors = graph.validate()
        if not valid:
            return ExecutionResult(
                graph_id=graph.graph_id,
                success=False,
                errors=errors,
                start_time=start_time,
                end_time=time.time(),
            )
        
        # 初始化上下文
        context = context or {}
        context["_results"] = {}  # 存储任务结果
        
        # 标记运行中
        self._running_graphs[graph.graph_id] = graph
        
        # 创建取消事件
        self._cancel_events[graph.graph_id] = asyncio.Event()
        
        try:
            # 按层执行
            layers = graph.get_execution_layers()
            
            for layer in layers:
                # 检查是否已取消
                if self._cancel_events[graph.graph_id].is_set():
                    logger.info(f"Graph {graph.graph_id} was cancelled")
                    break
                
                # 检查是否需要提前终止
                if graph.fail_fast:
                    failed = [t for t in graph.tasks.values() if t.state == TaskState.FAILED]
                    if failed:
                        # 将剩余任务标记为跳过
                        for task in graph.tasks.values():
                            if task.state == TaskState.PENDING:
                                task.state = TaskState.SKIPPED
                        break
                
                # 并行执行当前层
                await self._execute_layer(layer, context, graph.max_parallel)
            
            # 统计结果
            completed = sum(1 for t in graph.tasks.values() if t.state == TaskState.COMPLETED)
            failed = sum(1 for t in graph.tasks.values() if t.state == TaskState.FAILED)
            skipped = sum(1 for t in graph.tasks.values() if t.state == TaskState.SKIPPED)
            
            success = failed == 0 and skipped == 0
            
            if success:
                self._stats["successful"] += 1
            else:
                self._stats["failed"] += 1
            
            self._stats["total_tasks"] += len(graph.tasks)
            
            return ExecutionResult(
                graph_id=graph.graph_id,
                success=success,
                total_tasks=len(graph.tasks),
                completed_tasks=completed,
                failed_tasks=failed,
                skipped_tasks=skipped,
                start_time=start_time,
                end_time=time.time(),
                task_results=context["_results"],
                errors=[t.error for t in graph.tasks.values() if t.error],
            )
            
        finally:
            # 清理运行状态
            if graph.graph_id in self._running_graphs:
                del self._running_graphs[graph.graph_id]
            if graph.graph_id in self._cancel_events:
                del self._cancel_events[graph.graph_id]
    
    async def _execute_layer(
        self,
        tasks: List[TaskNode],
        context: Dict[str, Any],
        max_parallel: int,
    ) -> None:
        """执行一层任务"""
        # 限制并行数
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def run_with_semaphore(task: TaskNode):
            async with semaphore:
                await self._execute_task(task, context)
        
        await asyncio.gather(*[run_with_semaphore(t) for t in tasks])
    
    async def _execute_task(
        self,
        task: TaskNode,
        context: Dict[str, Any],
    ) -> None:
        """执行单个任务"""
        task.state = TaskState.RUNNING
        task.started_at = time.time()
        
        # 准备输入数据
        input_data = self._prepare_input(task, context)
        
        # 重试逻辑
        retries = 0
        max_retries = task.retry_count or self._max_retries
        
        while retries <= max_retries:
            try:
                # 执行任务
                result = await asyncio.wait_for(
                    self._call_agent(task.agent_id, task.capability, input_data),
                    timeout=task.timeout or self._default_timeout,
                )
                
                # 成功
                task.state = TaskState.COMPLETED
                task.result = result
                task.completed_at = time.time()
                
                # 存储结果到上下文
                context["_results"][task.task_id] = result
                
                logger.info(f"Task {task.task_id} ({task.name}) completed in {task.duration_ms:.2f}ms")
                return
                
            except asyncio.TimeoutError:
                task.error = f"Timeout after {task.timeout}s"
                retries += 1
                
            except Exception as e:
                task.error = str(e)
                retries += 1
                
                if retries <= max_retries:
                    logger.warning(f"Task {task.task_id} failed, retrying ({retries}/{max_retries}): {e}")
                    await asyncio.sleep(task.retry_delay)
        
        # 所有重试失败
        task.state = TaskState.FAILED
        task.completed_at = time.time()
        logger.error(f"Task {task.task_id} ({task.name}) failed: {task.error}")
    
    def _prepare_input(
        self,
        task: TaskNode,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        准备任务输入
        
        支持从上下文注入前置任务的结果。
        """
        input_data = dict(task.input_data)
        
        # 检查是否有结果引用
        if "use_result_from" in input_data:
            ref_task_id = input_data.pop("use_result_from")
            if ref_task_id in context["_results"]:
                input_data["previous_result"] = context["_results"][ref_task_id]
        
        # 注入所有依赖任务的结果
        for dep_id in task.depends_on:
            if dep_id in context["_results"]:
                input_data[f"dep_{dep_id}"] = context["_results"][dep_id]
        
        return input_data
    
    async def _call_agent(
        self,
        agent_id: str,
        capability: str,
        input_data: Dict[str, Any],
    ) -> Any:
        """调用 Agent"""
        from ..gateway.a2a_gateway import A2ATask
        
        task = A2ATask(
            from_agent="orchestrator",
            to_agent=agent_id,
            capability=capability,
            input_data=input_data,
        )
        
        return await self._bridge.execute_task(task)
    
    async def cancel(self, graph_id: str) -> bool:
        """
        取消执行中的图
        
        Args:
            graph_id: 图 ID
            
        Returns:
            是否成功取消
        """
        if graph_id not in self._running_graphs:
            return False
        
        graph = self._running_graphs[graph_id]
        
        # 设置取消事件，通知执行中的任务
        if graph_id in self._cancel_events:
            self._cancel_events[graph_id].set()
        
        # 将所有未完成任务标记为取消
        for task in graph.tasks.values():
            if task.state in (TaskState.PENDING, TaskState.READY, TaskState.RUNNING):
                task.state = TaskState.CANCELLED
                task.error = "任务已被取消"
        
        logger.info(f"Graph {graph_id} cancelled")
        return True
    
    def get_running_graphs(self) -> List[str]:
        """获取运行中的图 ID"""
        return list(self._running_graphs.keys())
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            **self._stats,
            "running_graphs": len(self._running_graphs),
        }


# ===== 便捷函数 =====

def create_sequential_graph(
    name: str,
    tasks: List[Dict[str, Any]],
) -> TaskGraph:
    """
    创建顺序执行的任务图
    
    Args:
        name: 图名称
        tasks: 任务列表 [{"name", "agent_id", "capability", "input_data"}, ...]
        
    Returns:
        TaskGraph
    """
    graph = TaskGraph(name=name)
    prev_id = None
    
    for task_def in tasks:
        depends = {prev_id} if prev_id else set()
        task = graph.add_task(
            name=task_def["name"],
            agent_id=task_def["agent_id"],
            capability=task_def["capability"],
            input_data=task_def.get("input_data", {}),
            depends_on=depends,
            timeout=task_def.get("timeout", 60.0),
        )
        prev_id = task.task_id
    
    return graph


def create_parallel_graph(
    name: str,
    tasks: List[Dict[str, Any]],
    aggregator: Optional[Dict[str, Any]] = None,
) -> TaskGraph:
    """
    创建并行执行的任务图
    
    Args:
        name: 图名称
        tasks: 并行任务列表
        aggregator: 可选的聚合任务
        
    Returns:
        TaskGraph
    """
    graph = TaskGraph(name=name)
    task_ids = []
    
    # 添加并行任务
    for task_def in tasks:
        task = graph.add_task(
            name=task_def["name"],
            agent_id=task_def["agent_id"],
            capability=task_def["capability"],
            input_data=task_def.get("input_data", {}),
            timeout=task_def.get("timeout", 60.0),
        )
        task_ids.append(task.task_id)
    
    # 添加聚合任务
    if aggregator:
        graph.add_task(
            name=aggregator["name"],
            agent_id=aggregator["agent_id"],
            capability=aggregator["capability"],
            input_data=aggregator.get("input_data", {}),
            depends_on=set(task_ids),
            timeout=aggregator.get("timeout", 60.0),
        )
    
    return graph


def create_fan_out_fan_in_graph(
    name: str,
    splitter: Dict[str, Any],
    workers: List[Dict[str, Any]],
    merger: Dict[str, Any],
) -> TaskGraph:
    """
    创建扇出-扇入模式的任务图
    
    ```
           ┌─> Worker1 ─┐
    Split ─┼─> Worker2 ─┼─> Merge
           └─> Worker3 ─┘
    ```
    
    Args:
        name: 图名称
        splitter: 分割任务
        workers: 工作任务列表
        merger: 合并任务
        
    Returns:
        TaskGraph
    """
    graph = TaskGraph(name=name)
    
    # 分割任务
    split_task = graph.add_task(
        name=splitter["name"],
        agent_id=splitter["agent_id"],
        capability=splitter["capability"],
        input_data=splitter.get("input_data", {}),
    )
    
    # 工作任务
    worker_ids = []
    for worker_def in workers:
        worker = graph.add_task(
            name=worker_def["name"],
            agent_id=worker_def["agent_id"],
            capability=worker_def["capability"],
            input_data=worker_def.get("input_data", {}),
            depends_on={split_task.task_id},
        )
        worker_ids.append(worker.task_id)
    
    # 合并任务
    graph.add_task(
        name=merger["name"],
        agent_id=merger["agent_id"],
        capability=merger["capability"],
        input_data=merger.get("input_data", {}),
        depends_on=set(worker_ids),
    )
    
    return graph


# ===== 向后兼容别名 =====

# v3.x 兼容：TaskStatus -> TaskState
TaskStatus = TaskState

# v3.x 兼容：TaskResult -> ExecutionResult
TaskResult = ExecutionResult
