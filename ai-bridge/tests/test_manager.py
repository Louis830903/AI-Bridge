"""
Tests for AdapterManager module
适配器管理器模块测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio

from aibridge.core.manager import AdapterManager
from aibridge.adapters.base import BaseAdapter, SyncBaseAdapter, AdapterInfo, AdapterType


# ============ Mock Adapters for Testing ============

class MockAsyncAdapter(BaseAdapter):
    """模拟异步适配器"""
    
    info = AdapterInfo(
        id="mock_async",
        name="Mock Async Adapter",
        type=AdapterType.BROWSER,
        actions=["click", "type"]
    )
    
    async def connect(self) -> bool:
        self._connected = True
        return True
    
    async def disconnect(self) -> bool:
        self._connected = False
        return True
    
    def is_available(self) -> bool:
        return True
    
    async def execute(self, action, target=None, value=None, options=None):
        return {"success": True, "action": action}


class MockSyncAdapter(SyncBaseAdapter):
    """模拟同步适配器"""
    
    info = AdapterInfo(
        id="mock_sync",
        name="Mock Sync Adapter",
        type=AdapterType.OFFICE,
        actions=["read", "write"]
    )
    
    def connect(self) -> bool:
        self._connected = True
        return True
    
    def disconnect(self) -> bool:
        self._connected = False
        return True
    
    def is_available(self) -> bool:
        return True
    
    def execute(self, action, target=None, value=None, options=None):
        return {"success": True, "action": action}


class FailingAsyncAdapter(BaseAdapter):
    """连接失败的异步适配器"""
    
    info = AdapterInfo(
        id="failing_async",
        name="Failing Adapter",
        type=AdapterType.IM,
        actions=[]
    )
    
    async def connect(self) -> bool:
        raise ConnectionError("Connection failed")
    
    async def disconnect(self) -> bool:
        return True
    
    def is_available(self) -> bool:
        return False
    
    async def execute(self, action, target=None, value=None, options=None):
        return {"success": False, "error": "Not connected"}


# ============ Tests ============

class TestAdapterManager:
    """测试 AdapterManager"""
    
    def test_create_manager(self):
        """测试创建管理器"""
        manager = AdapterManager()
        
        assert manager._adapters == {}
        assert manager._sync_adapters == {}
    
    def test_register_async_adapter(self):
        """测试注册异步适配器"""
        manager = AdapterManager()
        adapter = MockAsyncAdapter()
        
        manager.register(adapter)
        
        assert "mock_async" in manager._adapters
        assert manager.get_adapter("mock_async") is adapter
    
    def test_register_sync_adapter(self):
        """测试注册同步适配器"""
        manager = AdapterManager()
        adapter = MockSyncAdapter()
        
        manager.register_sync(adapter)
        
        assert "mock_sync" in manager._sync_adapters
        assert manager.get_sync_adapter("mock_sync") is adapter
    
    def test_unregister_async_adapter(self):
        """测试注销异步适配器"""
        manager = AdapterManager()
        adapter = MockAsyncAdapter()
        
        manager.register(adapter)
        result = manager.unregister("mock_async")
        
        assert result is True
        assert "mock_async" not in manager._adapters
    
    def test_unregister_sync_adapter(self):
        """测试注销同步适配器"""
        manager = AdapterManager()
        adapter = MockSyncAdapter()
        
        manager.register_sync(adapter)
        result = manager.unregister("mock_sync")
        
        assert result is True
        assert "mock_sync" not in manager._sync_adapters
    
    def test_unregister_nonexistent(self):
        """测试注销不存在的适配器"""
        manager = AdapterManager()
        
        result = manager.unregister("nonexistent")
        
        assert result is False
    
    def test_get_any_adapter_async(self):
        """测试获取任意适配器（异步）"""
        manager = AdapterManager()
        adapter = MockAsyncAdapter()
        
        manager.register(adapter)
        
        result = manager.get_any_adapter("mock_async")
        
        assert result is adapter
    
    def test_get_any_adapter_sync(self):
        """测试获取任意适配器（同步）"""
        manager = AdapterManager()
        adapter = MockSyncAdapter()
        
        manager.register_sync(adapter)
        
        result = manager.get_any_adapter("mock_sync")
        
        assert result is adapter
    
    def test_get_any_adapter_not_found(self):
        """测试获取不存在的适配器"""
        manager = AdapterManager()
        
        result = manager.get_any_adapter("nonexistent")
        
        assert result is None
    
    def test_list_adapters(self):
        """测试列出适配器"""
        manager = AdapterManager()
        manager.register(MockAsyncAdapter())
        manager.register_sync(MockSyncAdapter())
        
        adapters = manager.list_adapters()
        
        assert len(adapters) == 2
        ids = [a["id"] for a in adapters]
        assert "mock_async" in ids
        assert "mock_sync" in ids
    
    def test_list_adapters_includes_async_flag(self):
        """测试列出适配器包含异步标志"""
        manager = AdapterManager()
        manager.register(MockAsyncAdapter())
        manager.register_sync(MockSyncAdapter())
        
        adapters = manager.list_adapters()
        
        async_adapter = next(a for a in adapters if a["id"] == "mock_async")
        sync_adapter = next(a for a in adapters if a["id"] == "mock_sync")
        
        assert async_adapter["async"] is True
        assert sync_adapter["async"] is False
    
    def test_list_adapter_ids(self):
        """测试列出适配器 ID"""
        manager = AdapterManager()
        manager.register(MockAsyncAdapter())
        manager.register_sync(MockSyncAdapter())
        
        ids = manager.list_adapter_ids()
        
        assert "mock_async" in ids
        assert "mock_sync" in ids
    
    @pytest.mark.asyncio
    async def test_connect_all(self):
        """测试连接所有适配器"""
        manager = AdapterManager()
        manager.register(MockAsyncAdapter())
        manager.register_sync(MockSyncAdapter())
        
        results = await manager.connect_all()
        
        assert results["mock_async"] is True
        assert results["mock_sync"] is True
    
    @pytest.mark.asyncio
    async def test_connect_all_with_failure(self):
        """测试连接失败的情况"""
        manager = AdapterManager()
        manager.register(MockAsyncAdapter())
        manager.register(FailingAsyncAdapter())
        
        results = await manager.connect_all()
        
        assert results["mock_async"] is True
        assert results["failing_async"] is False
    
    @pytest.mark.asyncio
    async def test_disconnect_all(self):
        """测试断开所有连接"""
        manager = AdapterManager()
        async_adapter = MockAsyncAdapter()
        sync_adapter = MockSyncAdapter()
        
        manager.register(async_adapter)
        manager.register_sync(sync_adapter)
        
        # 先连接
        await manager.connect_all()
        
        # 再断开
        results = await manager.disconnect_all()
        
        assert results["mock_async"] is True
        assert results["mock_sync"] is True
    
    @pytest.mark.asyncio
    async def test_execute_async_adapter(self):
        """测试执行异步适配器操作"""
        manager = AdapterManager()
        adapter = MockAsyncAdapter()
        manager.register(adapter)
        
        result = await manager.execute(
            app="mock_async",
            action="click",
            target={"name": "button"}
        )
        
        assert result["success"] is True
        assert result["action"] == "click"
    
    @pytest.mark.asyncio
    async def test_execute_sync_adapter(self):
        """测试执行同步适配器操作"""
        manager = AdapterManager()
        adapter = MockSyncAdapter()
        manager.register_sync(adapter)
        
        result = await manager.execute(
            app="mock_sync",
            action="write",
            value="test"
        )
        
        assert result["success"] is True
        assert result["action"] == "write"
    
    @pytest.mark.asyncio
    async def test_execute_unknown_app(self):
        """测试执行未知应用"""
        manager = AdapterManager()
        
        result = await manager.execute(
            app="unknown",
            action="click"
        )
        
        assert result["success"] is False
        assert "Unknown application" in result["error"]
    
    @pytest.mark.asyncio
    async def test_execute_auto_connects(self):
        """测试执行时自动连接"""
        manager = AdapterManager()
        adapter = MockAsyncAdapter()
        manager.register(adapter)
        
        assert adapter.is_connected is False
        
        await manager.execute(app="mock_async", action="click")
        
        assert adapter.is_connected is True
    
    @pytest.mark.asyncio
    async def test_execute_connection_failure(self):
        """测试执行时连接失败"""
        manager = AdapterManager()
        adapter = FailingAsyncAdapter()
        manager.register(adapter)
        
        result = await manager.execute(app="failing_async", action="test")
        
        assert result["success"] is False
        assert "Failed to connect" in result["error"]
    
    @pytest.mark.asyncio
    async def test_health_check_all(self):
        """测试健康检查所有适配器"""
        manager = AdapterManager()
        manager.register(MockAsyncAdapter())
        manager.register_sync(MockSyncAdapter())
        
        # 连接适配器
        await manager.connect_all()
        
        results = await manager.health_check_all()
        
        assert "mock_async" in results
        assert "mock_sync" in results


class TestAdapterManagerWithRealAdapters:
    """测试与真实适配器类的集成"""
    
    def test_list_adapters_returns_correct_format(self):
        """测试列出适配器返回正确格式"""
        manager = AdapterManager()
        manager.register(MockAsyncAdapter())
        
        adapters = manager.list_adapters()
        
        assert len(adapters) == 1
        adapter = adapters[0]
        
        assert "id" in adapter
        assert "name" in adapter
        assert "type" in adapter
        assert "actions" in adapter
        assert "async" in adapter
        assert "connected" in adapter
