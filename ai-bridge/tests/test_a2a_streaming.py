"""
A2A Streaming 测试
"""

import pytest
import asyncio
import json

from aibridge.registry import (
    StreamEventType,
    StreamEvent,
    TaskProgress,
    StreamSubscription,
    StreamManager,
    TaskStreamHandler,
    SSEHandler,
    WebSocketHandler,
)


class TestStreamEvent:
    """StreamEvent 测试"""
    
    def test_create_event(self):
        """测试创建事件"""
        event = StreamEvent(
            event_type=StreamEventType.TASK_STARTED,
            data={"message": "Task started"},
            task_id="task-1",
            agent_id="agent-1",
            sequence=1,
        )
        
        assert event.event_type == StreamEventType.TASK_STARTED
        assert event.data["message"] == "Task started"
        assert event.task_id == "task-1"
        assert event.sequence == 1
    
    def test_to_sse(self):
        """测试 SSE 格式转换"""
        event = StreamEvent(
            event_type=StreamEventType.TASK_PROGRESS,
            data={"percentage": 50},
            task_id="task-1",
            sequence=1,
        )
        
        sse = event.to_sse()
        
        assert "event: task.progress" in sse
        assert "data:" in sse
        assert "percentage" in sse
    
    def test_to_websocket(self):
        """测试 WebSocket 格式转换"""
        event = StreamEvent(
            event_type=StreamEventType.TASK_COMPLETED,
            data={"result": "success"},
            task_id="task-1",
            sequence=1,
        )
        
        ws_msg = event.to_websocket()
        parsed = json.loads(ws_msg)
        
        assert parsed["type"] == "task.completed"
        assert parsed["task_id"] == "task-1"
        assert parsed["data"]["result"] == "success"
    
    def test_to_dict(self):
        """测试字典转换"""
        event = StreamEvent(
            event_type=StreamEventType.AGENT_THINKING,
            data={"thought": "Analyzing..."},
            task_id="task-1",
            agent_id="agent-1",
            sequence=5,
        )
        
        d = event.to_dict()
        
        assert d["event_type"] == "agent.thinking"
        assert d["task_id"] == "task-1"
        assert d["agent_id"] == "agent-1"
        assert d["data"]["thought"] == "Analyzing..."


class TestTaskProgress:
    """TaskProgress 测试"""
    
    def test_create_progress(self):
        """测试创建进度"""
        progress = TaskProgress(
            total_steps=10,
            completed_steps=5,
            current_step="Processing",
            percentage=50.0,
        )
        
        assert progress.percentage == 50.0
        assert progress.current_step == "Processing"
    
    def test_to_dict(self):
        """测试字典转换"""
        progress = TaskProgress(
            total_steps=4,
            completed_steps=2,
            percentage=50.0,
            estimated_remaining_ms=5000,
        )
        
        d = progress.to_dict()
        
        assert d["total_steps"] == 4
        assert d["completed_steps"] == 2
        assert d["percentage"] == 50.0
        assert d["estimated_remaining_ms"] == 5000


class TestStreamSubscription:
    """StreamSubscription 测试"""
    
    def test_create_subscription(self):
        """测试创建订阅"""
        sub = StreamSubscription(
            subscription_id="sub-1",
            task_ids=["task-1", "task-2"],
            event_types=[StreamEventType.TASK_PROGRESS],
        )
        
        assert sub.subscription_id == "sub-1"
        assert "task-1" in sub.task_ids
        assert StreamEventType.TASK_PROGRESS in sub.event_types
    
    def test_matches_event_type(self):
        """测试事件类型匹配"""
        sub = StreamSubscription(
            subscription_id="sub-1",
            event_types=[StreamEventType.TASK_PROGRESS, StreamEventType.TASK_COMPLETED],
        )
        
        event1 = StreamEvent(
            event_type=StreamEventType.TASK_PROGRESS,
            data={},
        )
        event2 = StreamEvent(
            event_type=StreamEventType.TASK_FAILED,
            data={},
        )
        
        assert sub.matches(event1) is True
        assert sub.matches(event2) is False
    
    def test_matches_task_id(self):
        """测试任务 ID 匹配"""
        sub = StreamSubscription(
            subscription_id="sub-1",
            task_ids=["task-1"],
        )
        
        event1 = StreamEvent(
            event_type=StreamEventType.TASK_PROGRESS,
            data={},
            task_id="task-1",
        )
        event2 = StreamEvent(
            event_type=StreamEventType.TASK_PROGRESS,
            data={},
            task_id="task-2",
        )
        event3 = StreamEvent(
            event_type=StreamEventType.HEARTBEAT,
            data={},
        )
        
        assert sub.matches(event1) is True
        assert sub.matches(event2) is False
        # 无 task_id 的事件（如心跳）应该通过
        assert sub.matches(event3) is True
    
    def test_matches_agent_id(self):
        """测试 Agent ID 匹配"""
        sub = StreamSubscription(
            subscription_id="sub-1",
            agent_ids=["agent-1"],
        )
        
        event1 = StreamEvent(
            event_type=StreamEventType.AGENT_STATUS,
            data={},
            agent_id="agent-1",
        )
        event2 = StreamEvent(
            event_type=StreamEventType.AGENT_STATUS,
            data={},
            agent_id="agent-2",
        )
        
        assert sub.matches(event1) is True
        assert sub.matches(event2) is False
    
    @pytest.mark.asyncio
    async def test_send_receive(self):
        """测试发送接收"""
        sub = StreamSubscription(subscription_id="sub-1")
        
        event = StreamEvent(
            event_type=StreamEventType.TASK_STARTED,
            data={"message": "Started"},
            task_id="task-1",
        )
        
        await sub.send(event)
        received = await sub.receive(timeout=1.0)
        
        assert received is not None
        assert received.task_id == "task-1"
    
    @pytest.mark.asyncio
    async def test_receive_timeout(self):
        """测试接收超时"""
        sub = StreamSubscription(subscription_id="sub-1")
        
        received = await sub.receive(timeout=0.1)
        assert received is None
    
    def test_close(self):
        """测试关闭"""
        sub = StreamSubscription(subscription_id="sub-1")
        
        assert sub.is_closed is False
        sub.close()
        assert sub.is_closed is True
    
    @pytest.mark.asyncio
    async def test_send_to_closed(self):
        """测试发送到已关闭的订阅"""
        sub = StreamSubscription(subscription_id="sub-1")
        sub.close()
        
        event = StreamEvent(
            event_type=StreamEventType.TASK_STARTED,
            data={},
        )
        
        result = await sub.send(event)
        assert result is False


class TestStreamManager:
    """StreamManager 测试"""
    
    @pytest.fixture
    def manager(self):
        """创建 StreamManager"""
        return StreamManager(heartbeat_interval=60.0)  # 长间隔避免干扰
    
    @pytest.mark.asyncio
    async def test_subscribe_unsubscribe(self, manager):
        """测试订阅和取消订阅"""
        sub = await manager.subscribe(subscription_id="sub-1")
        
        assert sub.subscription_id == "sub-1"
        assert manager.active_subscriptions == 1
        
        result = await manager.unsubscribe("sub-1")
        assert result is True
        assert manager.active_subscriptions == 0
    
    @pytest.mark.asyncio
    async def test_subscribe_auto_id(self, manager):
        """测试自动生成订阅 ID"""
        sub = await manager.subscribe()
        
        assert sub.subscription_id is not None
        assert len(sub.subscription_id) > 0
    
    @pytest.mark.asyncio
    async def test_publish_to_subscribers(self, manager):
        """测试发布到订阅者"""
        sub1 = await manager.subscribe(task_ids=["task-1"])
        sub2 = await manager.subscribe(task_ids=["task-2"])
        
        event = await manager.publish(
            StreamEventType.TASK_PROGRESS,
            {"percentage": 50},
            task_id="task-1",
        )
        
        # sub1 应该收到
        received1 = await sub1.receive(timeout=1.0)
        assert received1 is not None
        assert received1.task_id == "task-1"
        
        # sub2 不应该收到（task_id 不匹配）
        received2 = await sub2.receive(timeout=0.1)
        assert received2 is None
    
    @pytest.mark.asyncio
    async def test_publish_sequence(self, manager):
        """测试发布序列号"""
        await manager.publish(StreamEventType.TASK_STARTED, {})
        event2 = await manager.publish(StreamEventType.TASK_PROGRESS, {})
        event3 = await manager.publish(StreamEventType.TASK_COMPLETED, {})
        
        assert event2.sequence == 2
        assert event3.sequence == 3
    
    @pytest.mark.asyncio
    async def test_start_stop(self, manager):
        """测试启动停止"""
        await manager.start()
        assert manager._running is True
        
        await manager.stop()
        assert manager._running is False


class TestTaskStreamHandler:
    """TaskStreamHandler 测试"""
    
    @pytest.fixture
    def manager(self):
        """创建 StreamManager"""
        return StreamManager(heartbeat_interval=60.0)
    
    @pytest.fixture
    def handler(self, manager):
        """创建 TaskStreamHandler"""
        return TaskStreamHandler(
            task_id="task-1",
            stream_manager=manager,
            agent_id="agent-1",
        )
    
    @pytest.mark.asyncio
    async def test_start(self, manager, handler):
        """测试任务开始"""
        sub = await manager.subscribe(task_ids=["task-1"])
        
        await handler.start(metadata={"user": "test"})
        
        event = await sub.receive(timeout=1.0)
        assert event is not None
        assert event.event_type == StreamEventType.TASK_STARTED
        assert event.task_id == "task-1"
        assert event.data["metadata"]["user"] == "test"
    
    @pytest.mark.asyncio
    async def test_progress(self, manager, handler):
        """测试进度更新"""
        sub = await manager.subscribe(task_ids=["task-1"])
        
        await handler.progress(
            completed_steps=2,
            total_steps=10,
            current_step="Processing",
        )
        
        event = await sub.receive(timeout=1.0)
        assert event is not None
        assert event.event_type == StreamEventType.TASK_PROGRESS
        assert event.data["completed_steps"] == 2
        assert event.data["percentage"] == 20.0
    
    @pytest.mark.asyncio
    async def test_partial(self, manager, handler):
        """测试中间结果"""
        sub = await manager.subscribe(task_ids=["task-1"])
        
        await handler.partial(
            partial_result={"items": [1, 2, 3]},
            message="First batch",
        )
        
        event = await sub.receive(timeout=1.0)
        assert event is not None
        assert event.event_type == StreamEventType.TASK_PARTIAL
        assert event.data["partial_result"]["items"] == [1, 2, 3]
    
    @pytest.mark.asyncio
    async def test_thinking(self, manager, handler):
        """测试思考过程"""
        sub = await manager.subscribe(task_ids=["task-1"])
        
        await handler.thinking("Analyzing the problem...")
        
        event = await sub.receive(timeout=1.0)
        assert event is not None
        assert event.event_type == StreamEventType.AGENT_THINKING
        assert event.data["thought"] == "Analyzing the problem..."
    
    @pytest.mark.asyncio
    async def test_artifact(self, manager, handler):
        """测试 Artifact"""
        sub = await manager.subscribe(task_ids=["task-1"])
        
        await handler.artifact(
            artifact_type="code",
            content="print('hello')",
            name="main.py",
        )
        
        event = await sub.receive(timeout=1.0)
        assert event is not None
        assert event.event_type == StreamEventType.AGENT_ARTIFACT
        assert event.data["artifact_type"] == "code"
        assert event.data["name"] == "main.py"
    
    @pytest.mark.asyncio
    async def test_complete(self, manager, handler):
        """测试任务完成"""
        sub = await manager.subscribe(task_ids=["task-1"])
        
        await handler.complete(
            result={"status": "success"},
            message="Done!",
        )
        
        event = await sub.receive(timeout=1.0)
        assert event is not None
        assert event.event_type == StreamEventType.TASK_COMPLETED
        assert event.data["result"]["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_fail(self, manager, handler):
        """测试任务失败"""
        sub = await manager.subscribe(task_ids=["task-1"])
        
        await handler.fail(
            error="Something went wrong",
            error_code="ERR_001",
        )
        
        event = await sub.receive(timeout=1.0)
        assert event is not None
        assert event.event_type == StreamEventType.TASK_FAILED
        assert event.data["error"] == "Something went wrong"
        assert event.data["error_code"] == "ERR_001"
    
    @pytest.mark.asyncio
    async def test_cancel(self, manager, handler):
        """测试任务取消"""
        sub = await manager.subscribe(task_ids=["task-1"])
        
        await handler.cancel(reason="User cancelled")
        
        event = await sub.receive(timeout=1.0)
        assert event is not None
        assert event.event_type == StreamEventType.TASK_CANCELLED
        assert event.data["reason"] == "User cancelled"
    
    @pytest.mark.asyncio
    async def test_complete_only_once(self, manager, handler):
        """测试只能完成一次"""
        sub = await manager.subscribe(task_ids=["task-1"])
        
        await handler.complete(result="first")
        await handler.complete(result="second")  # 应该被忽略
        
        event1 = await sub.receive(timeout=1.0)
        event2 = await sub.receive(timeout=0.1)
        
        assert event1 is not None
        assert event2 is None  # 第二次 complete 不应该发送事件


class TestSSEHandler:
    """SSEHandler 测试"""
    
    @pytest.mark.asyncio
    async def test_stream(self):
        """测试 SSE 流"""
        sub = StreamSubscription(subscription_id="sub-1")
        handler = SSEHandler(sub)
        
        # 发送一个事件
        event = StreamEvent(
            event_type=StreamEventType.TASK_PROGRESS,
            data={"percentage": 75},
        )
        await sub.send(event)
        
        # 接收
        async for sse_data in handler.stream(timeout=0.5):
            assert "task.progress" in sse_data
            assert "75" in sse_data
            break
        
        handler.close()
    
    @pytest.mark.asyncio
    async def test_keepalive(self):
        """测试保活"""
        sub = StreamSubscription(subscription_id="sub-1")
        handler = SSEHandler(sub)
        
        # 不发送事件，等待超时
        async for sse_data in handler.stream(timeout=0.1):
            # 应该收到 keepalive
            assert "keepalive" in sse_data
            break
        
        handler.close()


class TestWebSocketHandler:
    """WebSocketHandler 测试"""
    
    @pytest.mark.asyncio
    async def test_receive_events(self):
        """测试接收事件"""
        sub = StreamSubscription(subscription_id="sub-1")
        handler = WebSocketHandler(sub)
        
        event = StreamEvent(
            event_type=StreamEventType.TASK_COMPLETED,
            data={"result": "ok"},
            task_id="task-1",
        )
        await sub.send(event)
        
        async for ws_msg in handler.receive_events(timeout=0.5):
            parsed = json.loads(ws_msg)
            assert parsed["type"] == "task.completed"
            assert parsed["task_id"] == "task-1"
            break
        
        handler.close()
    
    @pytest.mark.asyncio
    async def test_handle_message(self):
        """测试处理消息"""
        received = []
        
        async def on_message(data):
            received.append(data)
        
        sub = StreamSubscription(subscription_id="sub-1")
        handler = WebSocketHandler(sub, on_message=on_message)
        
        await handler.handle_message('{"action": "ping"}')
        
        assert len(received) == 1
        assert received[0]["action"] == "ping"
    
    @pytest.mark.asyncio
    async def test_handle_invalid_message(self):
        """测试处理无效消息"""
        received = []
        
        async def on_message(data):
            received.append(data)
        
        sub = StreamSubscription(subscription_id="sub-1")
        handler = WebSocketHandler(sub, on_message=on_message)
        
        # 无效 JSON 不应该崩溃
        await handler.handle_message('invalid json')
        
        assert len(received) == 0


class TestStreamEventTypes:
    """事件类型测试"""
    
    def test_event_type_values(self):
        """测试事件类型值"""
        assert StreamEventType.TASK_STARTED.value == "task.started"
        assert StreamEventType.TASK_PROGRESS.value == "task.progress"
        assert StreamEventType.TASK_PARTIAL.value == "task.partial"
        assert StreamEventType.TASK_COMPLETED.value == "task.completed"
        assert StreamEventType.TASK_FAILED.value == "task.failed"
        assert StreamEventType.TASK_CANCELLED.value == "task.cancelled"
        assert StreamEventType.AGENT_STATUS.value == "agent.status"
        assert StreamEventType.AGENT_THINKING.value == "agent.thinking"
        assert StreamEventType.AGENT_ARTIFACT.value == "agent.artifact"
        assert StreamEventType.HEARTBEAT.value == "heartbeat"
        assert StreamEventType.ERROR.value == "error"
