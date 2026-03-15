"""
Audit Log 持久化测试
"""

import pytest
import asyncio
import tempfile
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

from aibridge.enterprise.audit_log import (
    AuditAction,
    AuditLevel,
    AuditEntry,
    AuditQuery,
    MemoryAuditStorage,
    FileAuditStorage,
    AuditLogger,
    create_memory_audit_logger,
    create_file_audit_logger,
)


class TestAuditEntry:
    """AuditEntry 测试"""
    
    def test_create_entry(self):
        """测试创建条目"""
        entry = AuditEntry(
            action=AuditAction.LOGIN,
            actor="user-1",
            resource="auth-service",
            message="User logged in",
        )
        
        assert entry.action == AuditAction.LOGIN
        assert entry.actor == "user-1"
        assert entry.success is True
        assert entry.level == AuditLevel.INFO
        assert entry.entry_id  # 自动生成
    
    def test_to_dict(self):
        """测试字典转换"""
        entry = AuditEntry(
            action=AuditAction.TOOL_CALL,
            actor="agent-1",
            resource="calculator",
            details={"input": "2+2"},
        )
        
        d = entry.to_dict()
        
        assert d["action"] == "access.tool_call"
        assert d["actor"] == "agent-1"
        assert d["details"]["input"] == "2+2"
        assert "timestamp" in d
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "entry_id": "test-123",
            "action": "auth.login",
            "actor": "user-1",
            "level": "info",
            "success": True,
            "message": "OK",
            "timestamp": "2024-01-01T00:00:00+00:00",
        }
        
        entry = AuditEntry.from_dict(data)
        
        assert entry.entry_id == "test-123"
        assert entry.action == AuditAction.LOGIN
        assert entry.actor == "user-1"
    
    def test_to_json(self):
        """测试 JSON 序列化"""
        entry = AuditEntry(
            action=AuditAction.CONFIG_CHANGE,
            actor="admin",
        )
        
        json_str = entry.to_json()
        assert "admin.config_change" in json_str
        assert "admin" in json_str


class TestAuditActions:
    """审计动作类型测试"""
    
    def test_action_values(self):
        """测试动作值"""
        assert AuditAction.LOGIN.value == "auth.login"
        assert AuditAction.LOGOUT.value == "auth.logout"
        assert AuditAction.TOOL_CALL.value == "access.tool_call"
        assert AuditAction.PERMISSION_DENIED.value == "security.permission_denied"
        assert AuditAction.AGENT_REGISTER.value == "agent.register"


class TestMemoryAuditStorage:
    """MemoryAuditStorage 测试"""
    
    @pytest.fixture
    def storage(self):
        """创建存储"""
        return MemoryAuditStorage(max_entries=100)
    
    @pytest.mark.asyncio
    async def test_write(self, storage):
        """测试写入"""
        entry = AuditEntry(
            action=AuditAction.LOGIN,
            actor="user-1",
        )
        
        result = await storage.write(entry)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_query_all(self, storage):
        """测试查询所有"""
        # 写入多条
        for i in range(5):
            await storage.write(AuditEntry(
                action=AuditAction.TOOL_CALL,
                actor=f"user-{i}",
            ))
        
        result = await storage.query(AuditQuery())
        assert result.total_count == 5
        assert len(result.entries) == 5
    
    @pytest.mark.asyncio
    async def test_query_filter_action(self, storage):
        """测试按动作过滤"""
        await storage.write(AuditEntry(action=AuditAction.LOGIN, actor="u1"))
        await storage.write(AuditEntry(action=AuditAction.LOGOUT, actor="u2"))
        await storage.write(AuditEntry(action=AuditAction.LOGIN, actor="u3"))
        
        result = await storage.query(AuditQuery(actions=[AuditAction.LOGIN]))
        assert result.total_count == 2
    
    @pytest.mark.asyncio
    async def test_query_filter_actor(self, storage):
        """测试按执行者过滤"""
        await storage.write(AuditEntry(action=AuditAction.LOGIN, actor="user-1"))
        await storage.write(AuditEntry(action=AuditAction.LOGIN, actor="user-2"))
        await storage.write(AuditEntry(action=AuditAction.LOGIN, actor="user-1"))
        
        result = await storage.query(AuditQuery(actors=["user-1"]))
        assert result.total_count == 2
    
    @pytest.mark.asyncio
    async def test_query_filter_success(self, storage):
        """测试按成功过滤"""
        await storage.write(AuditEntry(action=AuditAction.LOGIN, actor="u1", success=True))
        await storage.write(AuditEntry(action=AuditAction.LOGIN, actor="u2", success=False))
        
        result = await storage.query(AuditQuery(success=False))
        assert result.total_count == 1
        assert result.entries[0].actor == "u2"
    
    @pytest.mark.asyncio
    async def test_query_pagination(self, storage):
        """测试分页"""
        for i in range(10):
            await storage.write(AuditEntry(action=AuditAction.LOGIN, actor=f"u{i}"))
        
        result = await storage.query(AuditQuery(limit=3, offset=0))
        assert len(result.entries) == 3
        assert result.total_count == 10
        assert result.has_more is True
        
        result = await storage.query(AuditQuery(limit=3, offset=9))
        assert len(result.entries) == 1
        assert result.has_more is False
    
    @pytest.mark.asyncio
    async def test_count(self, storage):
        """测试计数"""
        for i in range(5):
            await storage.write(AuditEntry(action=AuditAction.LOGIN, actor=f"u{i}"))
        
        count = await storage.count(AuditQuery())
        assert count == 5
    
    @pytest.mark.asyncio
    async def test_delete_before(self, storage):
        """测试删除旧记录"""
        now = datetime.now(timezone.utc)
        
        # 写入一些条目
        for i in range(5):
            entry = AuditEntry(action=AuditAction.LOGIN, actor=f"u{i}")
            entry.timestamp = now - timedelta(days=i+1)  # 1, 2, 3, 4, 5 天前
            await storage.write(entry)
        
        # 删除 3 天前的（即 4, 5 天前的）
        cutoff = now - timedelta(days=3)
        deleted = await storage.delete_before(cutoff)
        
        assert deleted == 2  # 4, 5 天前的被删除
        
        remaining = await storage.count(AuditQuery())
        assert remaining == 3
    
    @pytest.mark.asyncio
    async def test_max_entries(self):
        """测试最大条目限制"""
        storage = MemoryAuditStorage(max_entries=5)
        
        for i in range(10):
            await storage.write(AuditEntry(action=AuditAction.LOGIN, actor=f"u{i}"))
        
        count = await storage.count(AuditQuery())
        assert count == 5  # 只保留最后 5 条


class TestFileAuditStorage:
    """FileAuditStorage 测试"""
    
    @pytest.fixture
    def storage(self, tmp_path):
        """创建存储"""
        return FileAuditStorage(str(tmp_path), file_prefix="test_audit")
    
    @pytest.mark.asyncio
    async def test_write_and_query(self, storage):
        """测试写入和查询"""
        entry = AuditEntry(
            action=AuditAction.LOGIN,
            actor="user-1",
            message="Test",
        )
        
        result = await storage.write(entry)
        assert result is True
        
        query_result = await storage.query(AuditQuery())
        assert query_result.total_count == 1
        assert query_result.entries[0].actor == "user-1"
    
    @pytest.mark.asyncio
    async def test_query_filter(self, storage):
        """测试查询过滤"""
        await storage.write(AuditEntry(action=AuditAction.LOGIN, actor="u1"))
        await storage.write(AuditEntry(action=AuditAction.LOGOUT, actor="u2"))
        
        result = await storage.query(AuditQuery(actions=[AuditAction.LOGIN]))
        assert result.total_count == 1
        assert result.entries[0].actor == "u1"


class TestAuditLogger:
    """AuditLogger 测试"""
    
    @pytest.fixture
    def audit_logger(self):
        """创建日志记录器"""
        return create_memory_audit_logger(max_entries=100)
    
    @pytest.mark.asyncio
    async def test_log_entry(self, audit_logger):
        """测试记录日志"""
        entry = AuditEntry(
            action=AuditAction.LOGIN,
            actor="user-1",
        )
        
        result = await audit_logger.log(entry)
        assert result is True
        
        entries = await audit_logger.get_recent(limit=10)
        assert len(entries) == 1
    
    @pytest.mark.asyncio
    async def test_log_action(self, audit_logger):
        """测试便捷记录方法"""
        result = await audit_logger.log_action(
            AuditAction.TOOL_CALL,
            actor="agent-1",
            resource="calculator",
            message="Called tool",
            details={"input": "1+1"},
        )
        
        assert result is True
        
        entries = await audit_logger.get_recent()
        assert len(entries) == 1
        assert entries[0].action == AuditAction.TOOL_CALL
        assert entries[0].details["input"] == "1+1"
    
    @pytest.mark.asyncio
    async def test_get_recent(self, audit_logger):
        """测试获取最近日志"""
        for i in range(10):
            await audit_logger.log_action(
                AuditAction.LOGIN,
                actor=f"user-{i}",
            )
        
        recent = await audit_logger.get_recent(limit=5)
        assert len(recent) == 5
    
    @pytest.mark.asyncio
    async def test_get_by_actor(self, audit_logger):
        """测试按执行者获取"""
        await audit_logger.log_action(AuditAction.LOGIN, actor="user-1")
        await audit_logger.log_action(AuditAction.LOGOUT, actor="user-2")
        await audit_logger.log_action(AuditAction.LOGIN, actor="user-1")
        
        entries = await audit_logger.get_by_actor("user-1")
        assert len(entries) == 2
    
    @pytest.mark.asyncio
    async def test_get_failures(self, audit_logger):
        """测试获取失败日志"""
        await audit_logger.log_action(AuditAction.LOGIN, actor="u1", success=True)
        await audit_logger.log_action(AuditAction.LOGIN, actor="u2", success=False)
        await audit_logger.log_action(AuditAction.LOGIN, actor="u3", success=False)
        
        failures = await audit_logger.get_failures()
        assert len(failures) == 2
    
    @pytest.mark.asyncio
    async def test_get_security_events(self, audit_logger):
        """测试获取安全事件"""
        await audit_logger.log_action(AuditAction.LOGIN, actor="u1")
        await audit_logger.log_action(AuditAction.PERMISSION_DENIED, actor="u2")
        await audit_logger.log_action(AuditAction.RATE_LIMITED, actor="u3")
        
        security = await audit_logger.get_security_events()
        assert len(security) == 2


class TestAuditQuery:
    """AuditQuery 测试"""
    
    def test_default_values(self):
        """测试默认值"""
        query = AuditQuery()
        
        assert query.limit == 100
        assert query.offset == 0
        assert query.order_desc is True
        assert query.success is None
    
    def test_custom_values(self):
        """测试自定义值"""
        query = AuditQuery(
            actions=[AuditAction.LOGIN],
            actors=["user-1"],
            success=True,
            limit=50,
        )
        
        assert query.actions == [AuditAction.LOGIN]
        assert query.actors == ["user-1"]
        assert query.success is True
        assert query.limit == 50


class TestFactoryFunctions:
    """工厂函数测试"""
    
    def test_create_memory_audit_logger(self):
        """测试创建内存日志记录器"""
        logger = create_memory_audit_logger(max_entries=500)
        assert logger is not None
    
    def test_create_file_audit_logger(self, tmp_path):
        """测试创建文件日志记录器"""
        logger = create_file_audit_logger(
            str(tmp_path),
            file_prefix="test",
            retention_days=30,
        )
        assert logger is not None
