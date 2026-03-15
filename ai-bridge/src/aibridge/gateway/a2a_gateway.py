"""
A2A (Agent-to-Agent) 协议网关

实现 Google A2A 协议规范，支持 Agent 间通信与协作：
- Agent 注册与发现
- 任务委派与执行
- 状态同步与事件流
- 结果聚合

参考：https://github.com/a2aproject/A2A
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """A2A 任务状态"""
    PENDING = "pending"           # 等待执行
    SUBMITTED = "submitted"       # 已提交
    WORKING = "working"           # 执行中
    INPUT_REQUIRED = "input-required"  # 需要输入
    COMPLETED = "completed"       # 已完成
    FAILED = "failed"             # 失败
    CANCELLED = "cancelled"       # 已取消


class MessageRole(Enum):
    """消息角色"""
    USER = "user"
    AGENT = "agent"


@dataclass
class AgentCapability:
    """Agent 能力描述"""
    name: str
    description: str
    input_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Dict[str, Any]] = None


@dataclass
class AgentCard:
    """
    Agent 名片 - A2A 协议核心数据结构
    
    描述一个 Agent 的身份、能力和通信方式
    """
    agent_id: str                          # Agent 唯一标识
    name: str                              # Agent 名称
    description: str                       # Agent 描述
    version: str = "1.0.0"                 # Agent 版本
    capabilities: List[AgentCapability] = field(default_factory=list)  # 能力列表
    endpoint: Optional[str] = None         # Agent 通信端点
    protocols: List[str] = field(default_factory=lambda: ["a2a/1.0"])  # 支持的协议
    metadata: Dict[str, Any] = field(default_factory=dict)  # 元数据
    created_at: datetime = field(default_factory=datetime.now)
    
    def supports_capability(self, capability_name: str) -> bool:
        """检查是否支持指定能力"""
        return any(c.name == capability_name for c in self.capabilities)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "capabilities": [
                {
                    "name": c.name,
                    "description": c.description,
                    "input_schema": c.input_schema,
                    "output_schema": c.output_schema,
                }
                for c in self.capabilities
            ],
            "endpoint": self.endpoint,
            "protocols": self.protocols,
            "metadata": self.metadata,
        }


@dataclass
class A2AMessage:
    """A2A 消息"""
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class A2ATask:
    """
    A2A 任务
    
    表示一个 Agent 间的任务请求
    """
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""                   # 发起 Agent
    to_agent: str = ""                     # 目标 Agent
    capability: str = ""                   # 请求的能力
    input_data: Dict[str, Any] = field(default_factory=dict)  # 输入数据
    status: TaskStatus = TaskStatus.PENDING
    messages: List[A2AMessage] = field(default_factory=list)  # 消息历史
    result: Optional[Any] = None           # 执行结果
    error: Optional[str] = None            # 错误信息
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_message(self, role: MessageRole, content: str) -> None:
        """添加消息"""
        self.messages.append(A2AMessage(role=role, content=content))
        self.updated_at = datetime.now()
    
    def complete(self, result: Any) -> None:
        """标记完成"""
        self.status = TaskStatus.COMPLETED
        self.result = result
        self.updated_at = datetime.now()
    
    def fail(self, error: str) -> None:
        """标记失败"""
        self.status = TaskStatus.FAILED
        self.error = error
        self.updated_at = datetime.now()


@dataclass
class TaskEvent:
    """任务事件"""
    task_id: str
    event_type: str  # status_change, message, result
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)


class A2AGateway:
    """
    A2A 协议网关
    
    功能：
    - Agent 注册与发现
    - 任务委派与路由
    - 状态同步
    - 事件广播
    
    使用示例：
    ```python
    gateway = A2AGateway()
    
    # 注册 Agent
    card = AgentCard(
        agent_id="browser-agent",
        name="Browser Agent",
        description="Web automation agent",
        capabilities=[
            AgentCapability(name="navigate", description="Navigate to URL"),
            AgentCapability(name="click", description="Click element"),
        ]
    )
    await gateway.register_agent(card)
    
    # 发现 Agent
    agents = await gateway.discover_agents("navigate")
    
    # 发送任务
    task = A2ATask(
        from_agent="orchestrator",
        to_agent="browser-agent",
        capability="navigate",
        input_data={"url": "https://example.com"}
    )
    handle = await gateway.send_task(task)
    
    # 获取结果
    result = await handle.wait_for_completion()
    ```
    """
    
    def __init__(self):
        self._agents: Dict[str, AgentCard] = {}
        self._tasks: Dict[str, A2ATask] = {}
        self._event_queues: Dict[str, asyncio.Queue] = {}  # task_id -> event queue
        self._lock = asyncio.Lock()
    
    async def register_agent(self, card: AgentCard) -> None:
        """
        注册 Agent
        
        Args:
            card: Agent 名片
        """
        async with self._lock:
            if card.agent_id in self._agents:
                logger.warning(f"Agent {card.agent_id} already registered, updating")
            
            self._agents[card.agent_id] = card
            logger.info(f"Registered agent: {card.agent_id} ({card.name})")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """
        注销 Agent
        
        Args:
            agent_id: Agent ID
        """
        async with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                logger.info(f"Unregistered agent: {agent_id}")
    
    async def get_agent(self, agent_id: str) -> Optional[AgentCard]:
        """获取 Agent 信息"""
        return self._agents.get(agent_id)
    
    async def list_agents(self) -> List[AgentCard]:
        """列出所有已注册的 Agent"""
        return list(self._agents.values())
    
    async def discover_agents(self, capability: str) -> List[AgentCard]:
        """
        发现具备特定能力的 Agent
        
        Args:
            capability: 能力名称
            
        Returns:
            匹配的 Agent 列表
        """
        return [
            agent for agent in self._agents.values()
            if agent.supports_capability(capability)
        ]
    
    async def send_task(self, task: A2ATask) -> "TaskHandle":
        """
        发送任务到目标 Agent
        
        Args:
            task: A2A 任务
            
        Returns:
            TaskHandle: 任务句柄，用于跟踪任务状态
        """
        # 验证目标 Agent 存在
        if task.to_agent not in self._agents:
            raise ValueError(f"Target agent {task.to_agent} not found")
        
        # 验证能力支持
        target_agent = self._agents[task.to_agent]
        if not target_agent.supports_capability(task.capability):
            raise ValueError(
                f"Agent {task.to_agent} does not support capability {task.capability}"
            )
        
        # 保存任务
        task.status = TaskStatus.SUBMITTED
        self._tasks[task.task_id] = task
        
        # 创建事件队列
        self._event_queues[task.task_id] = asyncio.Queue()
        
        # 发布状态变更事件
        await self._emit_event(task.task_id, "status_change", {
            "old_status": TaskStatus.PENDING.value,
            "new_status": TaskStatus.SUBMITTED.value,
        })
        
        logger.info(f"Task {task.task_id} submitted to {task.to_agent}")
        
        return TaskHandle(gateway=self, task_id=task.task_id)
    
    async def get_task(self, task_id: str) -> Optional[A2ATask]:
        """获取任务信息"""
        return self._tasks.get(task_id)
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """获取任务状态"""
        task = self._tasks.get(task_id)
        return task.status if task else None
    
    async def update_task_status(self, task_id: str, status: TaskStatus) -> None:
        """更新任务状态"""
        task = self._tasks.get(task_id)
        if task:
            old_status = task.status
            task.status = status
            task.updated_at = datetime.now()
            
            await self._emit_event(task_id, "status_change", {
                "old_status": old_status.value,
                "new_status": status.value,
            })
    
    async def complete_task(self, task_id: str, result: Any) -> None:
        """完成任务"""
        task = self._tasks.get(task_id)
        if task:
            task.complete(result)
            await self._emit_event(task_id, "result", {"result": result})
            logger.info(f"Task {task_id} completed")
    
    async def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败"""
        task = self._tasks.get(task_id)
        if task:
            task.fail(error)
            await self._emit_event(task_id, "error", {"error": error})
            logger.error(f"Task {task_id} failed: {error}")
    
    async def _emit_event(self, task_id: str, event_type: str, data: Dict[str, Any]) -> None:
        """发布事件"""
        if task_id in self._event_queues:
            event = TaskEvent(task_id=task_id, event_type=event_type, data=data)
            await self._event_queues[task_id].put(event)
    
    async def subscribe_events(self, task_id: str) -> AsyncIterator[TaskEvent]:
        """
        订阅任务事件流
        
        Args:
            task_id: 任务 ID
            
        Yields:
            TaskEvent: 任务事件
        """
        if task_id not in self._event_queues:
            raise ValueError(f"Task {task_id} not found")
        
        queue = self._event_queues[task_id]
        while True:
            event = await queue.get()
            yield event
            
            # 如果任务已结束，停止订阅
            task = self._tasks.get(task_id)
            if task and task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                break


class TaskHandle:
    """
    任务句柄
    
    用于跟踪和操作已提交的任务
    """
    
    def __init__(self, gateway: A2AGateway, task_id: str):
        self._gateway = gateway
        self._task_id = task_id
    
    @property
    def task_id(self) -> str:
        return self._task_id
    
    async def get_status(self) -> Optional[TaskStatus]:
        """获取当前状态"""
        return await self._gateway.get_task_status(self._task_id)
    
    async def get_task(self) -> Optional[A2ATask]:
        """获取任务详情"""
        return await self._gateway.get_task(self._task_id)
    
    async def wait_for_completion(self, timeout: float = 300.0) -> Any:
        """
        等待任务完成
        
        Args:
            timeout: 超时时间(秒)
            
        Returns:
            任务结果
            
        Raises:
            TimeoutError: 超时
            RuntimeError: 任务失败
        """
        try:
            async with asyncio.timeout(timeout):
                async for event in self._gateway.subscribe_events(self._task_id):
                    if event.event_type == "result":
                        return event.data.get("result")
                    elif event.event_type == "error":
                        raise RuntimeError(event.data.get("error"))
        except asyncio.TimeoutError:
            raise TimeoutError(f"Task {self._task_id} timed out after {timeout}s")
        
        # 如果循环结束但没有结果，检查任务状态
        task = await self.get_task()
        if task and task.status == TaskStatus.COMPLETED:
            return task.result
        elif task and task.status == TaskStatus.FAILED:
            raise RuntimeError(task.error or "Task failed with unknown error")
        else:
            raise RuntimeError(f"Task {self._task_id} ended in unexpected state")
    
    async def cancel(self) -> None:
        """取消任务"""
        await self._gateway.update_task_status(self._task_id, TaskStatus.CANCELLED)
    
    def subscribe_events(self) -> AsyncIterator[TaskEvent]:
        """订阅事件流"""
        return self._gateway.subscribe_events(self._task_id)
