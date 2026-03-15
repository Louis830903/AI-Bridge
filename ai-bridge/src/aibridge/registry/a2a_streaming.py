"""
A2A Streaming 支持

提供 A2A 协议的流式通信能力：
- Server-Sent Events (SSE) 支持
- WebSocket 支持
- 任务状态实时推送
- 中间结果流式返回
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Awaitable, Any, AsyncIterator
from datetime import datetime, timezone
from enum import Enum
import asyncio
import json
import logging

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc)


class StreamEventType(str, Enum):
    """流事件类型"""
    TASK_STARTED = "task.started"
    TASK_PROGRESS = "task.progress"
    TASK_PARTIAL = "task.partial"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_CANCELLED = "task.cancelled"
    
    # Agent 状态
    AGENT_STATUS = "agent.status"
    AGENT_THINKING = "agent.thinking"
    AGENT_ARTIFACT = "agent.artifact"
    
    # 系统事件
    HEARTBEAT = "heartbeat"
    ERROR = "error"


@dataclass
class StreamEvent:
    """流事件"""
    event_type: StreamEventType
    data: Dict[str, Any]
    task_id: Optional[str] = None
    agent_id: Optional[str] = None
    timestamp: datetime = field(default_factory=_utcnow)
    sequence: int = 0
    
    def to_sse(self) -> str:
        """转换为 SSE 格式"""
        lines = []
        lines.append(f"event: {self.event_type.value}")
        
        payload = {
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
        }
        if self.task_id:
            payload["task_id"] = self.task_id
        if self.agent_id:
            payload["agent_id"] = self.agent_id
        
        lines.append(f"data: {json.dumps(payload)}")
        lines.append("")  # SSE 事件之间需要空行
        
        return "\n".join(lines)
    
    def to_websocket(self) -> str:
        """转换为 WebSocket 消息格式"""
        return json.dumps({
            "type": self.event_type.value,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type.value,
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "data": self.data,
            "timestamp": self.timestamp.isoformat(),
            "sequence": self.sequence,
        }


@dataclass
class TaskProgress:
    """任务进度"""
    total_steps: int = 0
    completed_steps: int = 0
    current_step: str = ""
    percentage: float = 0.0
    estimated_remaining_ms: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "current_step": self.current_step,
            "percentage": self.percentage,
            "estimated_remaining_ms": self.estimated_remaining_ms,
        }


class StreamSubscription:
    """流订阅"""
    
    def __init__(
        self,
        subscription_id: str,
        task_ids: List[str] = None,
        agent_ids: List[str] = None,
        event_types: List[StreamEventType] = None,
    ):
        self.subscription_id = subscription_id
        self.task_ids = set(task_ids) if task_ids else None
        self.agent_ids = set(agent_ids) if agent_ids else None
        self.event_types = set(event_types) if event_types else None
        self._queue: asyncio.Queue[StreamEvent] = asyncio.Queue()
        self._closed = False
    
    def matches(self, event: StreamEvent) -> bool:
        """检查事件是否匹配订阅"""
        # 事件类型过滤
        if self.event_types and event.event_type not in self.event_types:
            return False
        
        # 任务 ID 过滤
        if self.task_ids and event.task_id and event.task_id not in self.task_ids:
            return False
        
        # Agent ID 过滤
        if self.agent_ids and event.agent_id and event.agent_id not in self.agent_ids:
            return False
        
        return True
    
    async def send(self, event: StreamEvent) -> bool:
        """发送事件到订阅者"""
        if self._closed:
            return False
        
        if self.matches(event):
            await self._queue.put(event)
            return True
        return False
    
    async def receive(self, timeout: float = None) -> Optional[StreamEvent]:
        """接收事件"""
        if self._closed:
            return None
        
        try:
            if timeout:
                return await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                return await self._queue.get()
        except asyncio.TimeoutError:
            return None
    
    def close(self) -> None:
        """关闭订阅"""
        self._closed = True
    
    @property
    def is_closed(self) -> bool:
        return self._closed


class StreamManager:
    """流管理器
    
    管理所有活跃的流订阅，分发事件
    """
    
    def __init__(self, heartbeat_interval: float = 30.0):
        """
        Args:
            heartbeat_interval: 心跳间隔（秒）
        """
        self._subscriptions: Dict[str, StreamSubscription] = {}
        self._sequence = 0
        self._lock = asyncio.Lock()
        self._running = False
        self._heartbeat_interval = heartbeat_interval
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动流管理器"""
        if self._running:
            return
        
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("StreamManager started")
    
    async def stop(self) -> None:
        """停止流管理器"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # 关闭所有订阅
        for sub in self._subscriptions.values():
            sub.close()
        
        logger.info("StreamManager stopped")
    
    async def subscribe(
        self,
        subscription_id: str = None,
        task_ids: List[str] = None,
        agent_ids: List[str] = None,
        event_types: List[StreamEventType] = None,
    ) -> StreamSubscription:
        """创建订阅
        
        Args:
            subscription_id: 订阅 ID（可选，自动生成）
            task_ids: 过滤的任务 ID
            agent_ids: 过滤的 Agent ID
            event_types: 过滤的事件类型
            
        Returns:
            流订阅对象
        """
        if not subscription_id:
            import uuid
            subscription_id = str(uuid.uuid4())
        
        subscription = StreamSubscription(
            subscription_id=subscription_id,
            task_ids=task_ids,
            agent_ids=agent_ids,
            event_types=event_types,
        )
        
        async with self._lock:
            self._subscriptions[subscription_id] = subscription
        
        logger.debug(f"New subscription: {subscription_id}")
        return subscription
    
    async def unsubscribe(self, subscription_id: str) -> bool:
        """取消订阅
        
        Args:
            subscription_id: 订阅 ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            if subscription_id in self._subscriptions:
                self._subscriptions[subscription_id].close()
                del self._subscriptions[subscription_id]
                logger.debug(f"Unsubscribed: {subscription_id}")
                return True
        return False
    
    async def publish(
        self,
        event_type: StreamEventType,
        data: Dict[str, Any],
        task_id: str = None,
        agent_id: str = None,
    ) -> StreamEvent:
        """发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            task_id: 任务 ID
            agent_id: Agent ID
            
        Returns:
            发布的事件
        """
        async with self._lock:
            self._sequence += 1
            sequence = self._sequence
        
        event = StreamEvent(
            event_type=event_type,
            data=data,
            task_id=task_id,
            agent_id=agent_id,
            sequence=sequence,
        )
        
        # 分发到所有匹配的订阅
        for sub in list(self._subscriptions.values()):
            if not sub.is_closed:
                await sub.send(event)
        
        return event
    
    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running:
            await asyncio.sleep(self._heartbeat_interval)
            await self.publish(
                StreamEventType.HEARTBEAT,
                {"message": "ping"},
            )
    
    @property
    def active_subscriptions(self) -> int:
        """活跃订阅数"""
        return len([s for s in self._subscriptions.values() if not s.is_closed])


class TaskStreamHandler:
    """任务流处理器
    
    为单个任务提供流式事件发送能力
    """
    
    def __init__(
        self,
        task_id: str,
        stream_manager: StreamManager,
        agent_id: str = None,
    ):
        """
        Args:
            task_id: 任务 ID
            stream_manager: 流管理器
            agent_id: Agent ID
        """
        self._task_id = task_id
        self._agent_id = agent_id
        self._stream_manager = stream_manager
        self._started = False
        self._completed = False
        self._progress = TaskProgress()
    
    async def start(self, metadata: Dict[str, Any] = None) -> None:
        """任务开始"""
        if self._started:
            return
        
        self._started = True
        await self._stream_manager.publish(
            StreamEventType.TASK_STARTED,
            {
                "message": "Task started",
                "metadata": metadata or {},
            },
            task_id=self._task_id,
            agent_id=self._agent_id,
        )
    
    async def progress(
        self,
        completed_steps: int = None,
        total_steps: int = None,
        current_step: str = None,
        percentage: float = None,
        estimated_remaining_ms: int = None,
    ) -> None:
        """更新进度"""
        if completed_steps is not None:
            self._progress.completed_steps = completed_steps
        if total_steps is not None:
            self._progress.total_steps = total_steps
        if current_step is not None:
            self._progress.current_step = current_step
        if percentage is not None:
            self._progress.percentage = percentage
        elif self._progress.total_steps > 0:
            self._progress.percentage = (
                self._progress.completed_steps / self._progress.total_steps * 100
            )
        if estimated_remaining_ms is not None:
            self._progress.estimated_remaining_ms = estimated_remaining_ms
        
        await self._stream_manager.publish(
            StreamEventType.TASK_PROGRESS,
            self._progress.to_dict(),
            task_id=self._task_id,
            agent_id=self._agent_id,
        )
    
    async def partial(self, partial_result: Any, message: str = None) -> None:
        """发送中间结果"""
        await self._stream_manager.publish(
            StreamEventType.TASK_PARTIAL,
            {
                "partial_result": partial_result,
                "message": message,
            },
            task_id=self._task_id,
            agent_id=self._agent_id,
        )
    
    async def thinking(self, thought: str) -> None:
        """发送思考过程"""
        await self._stream_manager.publish(
            StreamEventType.AGENT_THINKING,
            {"thought": thought},
            task_id=self._task_id,
            agent_id=self._agent_id,
        )
    
    async def artifact(
        self,
        artifact_type: str,
        content: Any,
        name: str = None,
    ) -> None:
        """发送 Artifact"""
        await self._stream_manager.publish(
            StreamEventType.AGENT_ARTIFACT,
            {
                "artifact_type": artifact_type,
                "content": content,
                "name": name,
            },
            task_id=self._task_id,
            agent_id=self._agent_id,
        )
    
    async def complete(self, result: Any, message: str = None) -> None:
        """任务完成"""
        if self._completed:
            return
        
        self._completed = True
        await self._stream_manager.publish(
            StreamEventType.TASK_COMPLETED,
            {
                "result": result,
                "message": message or "Task completed",
            },
            task_id=self._task_id,
            agent_id=self._agent_id,
        )
    
    async def fail(self, error: str, error_code: str = None) -> None:
        """任务失败"""
        if self._completed:
            return
        
        self._completed = True
        await self._stream_manager.publish(
            StreamEventType.TASK_FAILED,
            {
                "error": error,
                "error_code": error_code,
            },
            task_id=self._task_id,
            agent_id=self._agent_id,
        )
    
    async def cancel(self, reason: str = None) -> None:
        """任务取消"""
        if self._completed:
            return
        
        self._completed = True
        await self._stream_manager.publish(
            StreamEventType.TASK_CANCELLED,
            {"reason": reason or "Cancelled"},
            task_id=self._task_id,
            agent_id=self._agent_id,
        )


class SSEHandler:
    """SSE 处理器
    
    用于生成 SSE 响应
    """
    
    def __init__(self, subscription: StreamSubscription):
        """
        Args:
            subscription: 流订阅
        """
        self._subscription = subscription
    
    async def stream(self, timeout: float = 30.0) -> AsyncIterator[str]:
        """生成 SSE 流
        
        Args:
            timeout: 单次接收超时
            
        Yields:
            SSE 格式的事件字符串
        """
        while not self._subscription.is_closed:
            event = await self._subscription.receive(timeout=timeout)
            if event:
                yield event.to_sse()
            else:
                # 发送保活注释
                yield ": keepalive\n\n"
    
    def close(self) -> None:
        """关闭 SSE 连接"""
        self._subscription.close()


class WebSocketHandler:
    """WebSocket 处理器
    
    用于处理 WebSocket 连接
    """
    
    def __init__(
        self,
        subscription: StreamSubscription,
        on_message: Callable[[Dict[str, Any]], Awaitable[None]] = None,
    ):
        """
        Args:
            subscription: 流订阅
            on_message: 接收消息时的回调
        """
        self._subscription = subscription
        self._on_message = on_message
    
    async def receive_events(self, timeout: float = 30.0) -> AsyncIterator[str]:
        """接收事件（发送给客户端）
        
        Args:
            timeout: 单次接收超时
            
        Yields:
            JSON 格式的消息
        """
        while not self._subscription.is_closed:
            event = await self._subscription.receive(timeout=timeout)
            if event:
                yield event.to_websocket()
    
    async def handle_message(self, message: str) -> None:
        """处理客户端消息
        
        Args:
            message: JSON 格式消息
        """
        if self._on_message:
            try:
                data = json.loads(message)
                await self._on_message(data)
            except json.JSONDecodeError:
                logger.warning(f"Invalid WebSocket message: {message}")
    
    def close(self) -> None:
        """关闭连接"""
        self._subscription.close()


class A2AStreamingClient:
    """A2A 流式客户端
    
    用于连接 A2A Agent 的流式端点
    """
    
    def __init__(self, endpoint: str):
        """
        Args:
            endpoint: A2A Agent 端点
        """
        try:
            import aiohttp
            self._aiohttp = aiohttp
        except ImportError:
            raise ImportError("aiohttp is required for A2AStreamingClient")
        
        self._endpoint = endpoint.rstrip("/")
    
    async def subscribe_task(
        self,
        task_id: str,
        on_event: Callable[[StreamEvent], Awaitable[None]],
    ) -> None:
        """订阅任务事件（SSE）
        
        Args:
            task_id: 任务 ID
            on_event: 事件回调
        """
        url = f"{self._endpoint}/tasks/{task_id}/stream"
        
        async with self._aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                async for line in resp.content:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data:"):
                        try:
                            data = json.loads(line_str[5:].strip())
                            event = StreamEvent(
                                event_type=StreamEventType(data.get("type", "unknown")),
                                data=data.get("data", {}),
                                task_id=data.get("task_id"),
                                agent_id=data.get("agent_id"),
                            )
                            await on_event(event)
                        except (json.JSONDecodeError, ValueError):
                            pass
    
    async def execute_streaming(
        self,
        task_data: Dict[str, Any],
        on_event: Callable[[StreamEvent], Awaitable[None]],
    ) -> None:
        """执行流式任务
        
        Args:
            task_data: 任务数据
            on_event: 事件回调
        """
        url = f"{self._endpoint}/tasks/execute/stream"
        
        async with self._aiohttp.ClientSession() as session:
            async with session.post(url, json=task_data) as resp:
                async for line in resp.content:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data:"):
                        try:
                            payload = json.loads(line_str[5:].strip())
                            event = StreamEvent(
                                event_type=StreamEventType(payload.get("type", "unknown")),
                                data=payload.get("data", {}),
                                task_id=payload.get("task_id"),
                                agent_id=payload.get("agent_id"),
                                sequence=payload.get("sequence", 0),
                            )
                            await on_event(event)
                        except (json.JSONDecodeError, ValueError):
                            pass


# ========== 便捷函数 ==========

async def create_sse_response(
    stream_manager: StreamManager,
    task_id: str = None,
    agent_id: str = None,
) -> tuple:
    """创建 SSE 响应
    
    返回 (SSEHandler, content_type)
    用于 FastAPI/aiohttp 等框架
    """
    subscription = await stream_manager.subscribe(
        task_ids=[task_id] if task_id else None,
        agent_ids=[agent_id] if agent_id else None,
    )
    handler = SSEHandler(subscription)
    return handler, "text/event-stream"


async def create_websocket_handler(
    stream_manager: StreamManager,
    task_id: str = None,
    agent_id: str = None,
    on_message: Callable[[Dict[str, Any]], Awaitable[None]] = None,
) -> WebSocketHandler:
    """创建 WebSocket 处理器"""
    subscription = await stream_manager.subscribe(
        task_ids=[task_id] if task_id else None,
        agent_ids=[agent_id] if agent_id else None,
    )
    return WebSocketHandler(subscription, on_message)
