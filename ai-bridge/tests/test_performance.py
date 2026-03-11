"""
Performance Utilities Tests
性能工具模块测试
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aibridge.utils.performance import (
    HTTPClientPool,
    http_pool,
    CachedToken,
    TokenCache,
    token_cache,
    CacheEntry,
    AsyncCache,
    with_retry,
    BatchExecutor,
    HealthMonitor,
    health_monitor,
)


# ============ HTTPClientPool Tests ============

class TestHTTPClientPool:
    """HTTP 客户端连接池测试"""
    
    def setup_method(self):
        """每个测试前重置单例"""
        HTTPClientPool._instance = None
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        pool1 = HTTPClientPool()
        pool2 = HTTPClientPool()
        assert pool1 is pool2
    
    @pytest.mark.asyncio
    async def test_get_client_creates_new(self):
        """测试获取客户端会创建新实例"""
        pool = HTTPClientPool()
        client = await pool.get_client("test_client")
        
        assert client is not None
        assert "test_client" in pool._clients
        
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_get_client_returns_cached(self):
        """测试获取已存在的客户端返回缓存"""
        pool = HTTPClientPool()
        
        client1 = await pool.get_client("cached_client")
        client2 = await pool.get_client("cached_client")
        
        assert client1 is client2
        
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_get_client_with_config(self):
        """测试使用配置创建客户端"""
        pool = HTTPClientPool()
        
        client = await pool.get_client(
            "configured_client",
            base_url="https://api.example.com",
            headers={"Authorization": "Bearer token"},
            timeout=60.0
        )
        
        assert client.base_url == "https://api.example.com"
        assert "Authorization" in client.headers
        
        await pool.close_all()
    
    @pytest.mark.asyncio
    async def test_close_client(self):
        """测试关闭指定客户端"""
        pool = HTTPClientPool()
        
        await pool.get_client("to_close")
        assert "to_close" in pool._clients
        
        result = await pool.close_client("to_close")
        assert result is True
        assert "to_close" not in pool._clients
        
        # 关闭不存在的客户端
        result = await pool.close_client("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_close_all(self):
        """测试关闭所有客户端"""
        pool = HTTPClientPool()
        
        await pool.get_client("client1")
        await pool.get_client("client2")
        assert len(pool._clients) == 2
        
        await pool.close_all()
        assert len(pool._clients) == 0
    
    @pytest.mark.asyncio
    async def test_update_client_headers(self):
        """测试更新客户端请求头"""
        pool = HTTPClientPool()
        
        await pool.get_client("header_client", headers={"X-Old": "old"})
        pool.update_client_headers("header_client", {"X-New": "new"})
        
        assert "X-New" in pool._clients["header_client"].headers
        
        await pool.close_all()


# ============ CachedToken Tests ============

class TestCachedToken:
    """Token 缓存条目测试"""
    
    def test_not_expired(self):
        """测试未过期 Token"""
        token = CachedToken(
            token="abc123",
            expires_at=time.time() + 3600  # 1 小时后过期
        )
        
        assert not token.is_expired
        assert token.remaining_seconds > 3500
    
    def test_expired(self):
        """测试已过期 Token"""
        token = CachedToken(
            token="abc123",
            expires_at=time.time() - 100  # 100 秒前过期
        )
        
        assert token.is_expired
        assert token.remaining_seconds == 0
    
    def test_about_to_expire(self):
        """测试即将过期 Token（提前 60 秒视为过期）"""
        token = CachedToken(
            token="abc123",
            expires_at=time.time() + 30  # 30 秒后过期，但提前 60 秒判定
        )
        
        assert token.is_expired  # 应该被视为过期
    
    def test_with_refresh_token(self):
        """测试带刷新令牌"""
        token = CachedToken(
            token="access",
            expires_at=time.time() + 3600,
            refresh_token="refresh_abc"
        )
        
        assert token.refresh_token == "refresh_abc"
    
    def test_with_metadata(self):
        """测试带元数据"""
        token = CachedToken(
            token="abc",
            expires_at=time.time() + 3600,
            metadata={"scope": "read write", "user_id": "123"}
        )
        
        assert token.metadata["scope"] == "read write"


# ============ TokenCache Tests ============

class TestTokenCache:
    """Token 缓存管理器测试"""
    
    def setup_method(self):
        """每个测试前创建新缓存"""
        self.cache = TokenCache()
    
    def test_set_and_get_sync(self):
        """测试设置 Token"""
        cached = self.cache.set(
            key="test_key",
            token="test_token",
            expires_in=3600
        )
        
        assert cached.token == "test_token"
        assert not cached.is_expired
    
    @pytest.mark.asyncio
    async def test_get_valid_token(self):
        """测试获取有效 Token"""
        self.cache.set("valid", "my_token", expires_in=3600)
        
        token = await self.cache.get("valid")
        assert token == "my_token"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """测试获取不存在的 Token"""
        token = await self.cache.get("nonexistent")
        assert token is None
    
    @pytest.mark.asyncio
    async def test_get_expired_without_refresh(self):
        """测试获取过期 Token（无刷新回调）"""
        self.cache.set("expired", "old_token", expires_in=-100)
        
        token = await self.cache.get("expired")
        assert token is None
    
    @pytest.mark.asyncio
    async def test_get_expired_with_refresh(self):
        """测试获取过期 Token（有刷新回调）"""
        self.cache.set("to_refresh", "old_token", expires_in=-100)
        
        async def refresh_callback(cached_token):
            return CachedToken(
                token="new_token",
                expires_at=time.time() + 3600
            )
        
        token = await self.cache.get("to_refresh", refresh_callback=refresh_callback)
        assert token == "new_token"
    
    @pytest.mark.asyncio
    async def test_refresh_callback_failure(self):
        """测试刷新回调失败"""
        self.cache.set("fail_refresh", "old", expires_in=-100)
        
        async def failing_callback(cached):
            raise Exception("Refresh failed")
        
        token = await self.cache.get("fail_refresh", refresh_callback=failing_callback)
        assert token is None
    
    def test_invalidate(self):
        """测试使 Token 失效"""
        self.cache.set("to_invalidate", "token", expires_in=3600)
        
        result = self.cache.invalidate("to_invalidate")
        assert result is True
        
        result = self.cache.invalidate("nonexistent")
        assert result is False
    
    def test_invalidate_all(self):
        """测试清除所有缓存"""
        self.cache.set("key1", "token1", expires_in=3600)
        self.cache.set("key2", "token2", expires_in=3600)
        
        self.cache.invalidate_all()
        assert len(self.cache._cache) == 0
    
    def test_get_info(self):
        """测试获取 Token 信息"""
        self.cache.set(
            "info_key",
            "token",
            expires_in=3600,
            refresh_token="refresh",
            user="test_user"
        )
        
        info = self.cache.get_info("info_key")
        
        assert info is not None
        assert info["key"] == "info_key"
        assert info["has_refresh_token"] is True
        assert info["metadata"]["user"] == "test_user"
        assert not info["is_expired"]
    
    def test_get_info_nonexistent(self):
        """测试获取不存在 Token 的信息"""
        info = self.cache.get_info("nonexistent")
        assert info is None


# ============ CacheEntry Tests ============

class TestCacheEntry:
    """缓存条目测试"""
    
    def test_not_expired(self):
        """测试未过期"""
        entry = CacheEntry(
            value="data",
            expires_at=time.time() + 100
        )
        assert not entry.is_expired
    
    def test_expired(self):
        """测试已过期"""
        entry = CacheEntry(
            value="data",
            expires_at=time.time() - 100
        )
        assert entry.is_expired


# ============ AsyncCache Tests ============

class TestAsyncCache:
    """异步缓存测试"""
    
    @pytest.mark.asyncio
    async def test_set_and_get(self):
        """测试设置和获取"""
        cache = AsyncCache[str](default_ttl=300)
        
        await cache.set("key1", "value1")
        value = await cache.get("key1")
        
        assert value == "value1"
    
    @pytest.mark.asyncio
    async def test_get_nonexistent(self):
        """测试获取不存在的键"""
        cache = AsyncCache[str]()
        
        value = await cache.get("nonexistent")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_get_with_loader(self):
        """测试带加载器获取"""
        cache = AsyncCache[str]()
        
        value = await cache.get("loaded", loader=lambda: "loaded_value")
        assert value == "loaded_value"
        
        # 再次获取应该返回缓存值
        value = await cache.get("loaded")
        assert value == "loaded_value"
    
    @pytest.mark.asyncio
    async def test_get_with_async_loader(self):
        """测试带异步加载器获取"""
        cache = AsyncCache[str]()
        
        async def async_loader():
            return "async_value"
        
        value = await cache.get("async_key", loader=async_loader)
        assert value == "async_value"
    
    @pytest.mark.asyncio
    async def test_expired_entry(self):
        """测试过期条目"""
        cache = AsyncCache[str](default_ttl=0.01)  # 10ms TTL
        
        await cache.set("short_lived", "value")
        await asyncio.sleep(0.02)  # 等待过期
        
        value = await cache.get("short_lived")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_lru_eviction(self):
        """测试 LRU 淘汰"""
        cache = AsyncCache[int](default_ttl=300, max_size=3)
        
        await cache.set("a", 1)
        await cache.set("b", 2)
        await cache.set("c", 3)
        
        # 访问 a 使其最近使用
        await cache.get("a")
        
        # 添加第 4 个元素，应该淘汰 b
        await cache.set("d", 4)
        
        assert await cache.get("a") == 1
        assert await cache.get("b") is None  # 被淘汰
        assert await cache.get("c") == 3
        assert await cache.get("d") == 4
    
    @pytest.mark.asyncio
    async def test_delete(self):
        """测试删除"""
        cache = AsyncCache[str]()
        
        await cache.set("to_delete", "value")
        result = await cache.delete("to_delete")
        
        assert result is True
        assert await cache.get("to_delete") is None
        
        # 删除不存在的键
        result = await cache.delete("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_clear(self):
        """测试清空"""
        cache = AsyncCache[str]()
        
        await cache.set("k1", "v1")
        await cache.set("k2", "v2")
        
        await cache.clear()
        
        assert cache.size == 0
    
    @pytest.mark.asyncio
    async def test_size(self):
        """测试大小"""
        cache = AsyncCache[str]()
        
        assert cache.size == 0
        
        await cache.set("k1", "v1")
        assert cache.size == 1
        
        await cache.set("k2", "v2")
        assert cache.size == 2


# ============ with_retry Tests ============

class TestWithRetry:
    """重试装饰器测试"""
    
    @pytest.mark.asyncio
    async def test_success_first_try(self):
        """测试首次成功"""
        call_count = 0
        
        @with_retry(max_retries=3)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await successful_func()
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        """测试重试后成功"""
        call_count = 0
        
        @with_retry(max_retries=3, delay=0.01)
        async def retry_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary error")
            return "success"
        
        result = await retry_func()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        call_count = 0
        
        @with_retry(max_retries=2, delay=0.01)
        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError, match="Permanent error"):
            await failing_func()
        
        assert call_count == 3  # 1 initial + 2 retries
    
    @pytest.mark.asyncio
    async def test_specific_exceptions(self):
        """测试只重试特定异常"""
        call_count = 0
        
        @with_retry(max_retries=3, delay=0.01, exceptions=(ValueError,))
        async def specific_error_func():
            nonlocal call_count
            call_count += 1
            raise TypeError("Wrong type")
        
        # TypeError 不在重试列表中，应该立即抛出
        with pytest.raises(TypeError):
            await specific_error_func()
        
        assert call_count == 1


# ============ BatchExecutor Tests ============

class TestBatchExecutor:
    """批量执行器测试"""
    
    @pytest.mark.asyncio
    async def test_batch_execution(self):
        """测试批量执行"""
        executor = BatchExecutor(batch_size=3, max_wait=0.1)
        
        async def batch_handler(items):
            return [f"processed_{item}" for item in items]
        
        # 提交多个项目
        results = await asyncio.gather(
            executor.submit("a", batch_handler),
            executor.submit("b", batch_handler),
            executor.submit("c", batch_handler),
        )
        
        assert "processed_a" in results
        assert "processed_b" in results
        assert "processed_c" in results


# ============ HealthMonitor Tests ============

class TestHealthMonitor:
    """健康监控器测试"""
    
    def setup_method(self):
        """每个测试前创建新监控器"""
        self.monitor = HealthMonitor(failure_threshold=3, recovery_time=1.0)
    
    def test_initial_healthy(self):
        """测试初始状态健康"""
        assert self.monitor.is_healthy("new_service")
    
    def test_record_success_resets_count(self):
        """测试记录成功重置失败计数"""
        self.monitor.record_failure("service")
        self.monitor.record_failure("service")
        self.monitor.record_success("service")
        
        assert self.monitor._failure_count["service"] == 0
    
    def test_threshold_not_reached(self):
        """测试未达到阈值仍健康"""
        self.monitor.record_failure("service")
        self.monitor.record_failure("service")
        
        assert self.monitor.is_healthy("service")  # 2 < 3
    
    def test_threshold_reached_unhealthy(self):
        """测试达到阈值不健康"""
        for _ in range(3):
            self.monitor.record_failure("service")
        
        assert not self.monitor.is_healthy("service")
    
    def test_recovery_after_time(self):
        """测试恢复期后恢复健康"""
        for _ in range(3):
            self.monitor.record_failure("service")
        
        assert not self.monitor.is_healthy("service")
        
        # 模拟时间流逝
        self.monitor._last_failure["service"] = time.time() - 2.0
        
        assert self.monitor.is_healthy("service")
    
    def test_get_status(self):
        """测试获取状态"""
        self.monitor.record_failure("status_service")
        
        status = self.monitor.get_status("status_service")
        
        assert status["key"] == "status_service"
        assert status["failure_count"] == 1
        assert status["is_healthy"] is True
        assert status["threshold"] == 3


# ============ Global Instance Tests ============

class TestGlobalInstances:
    """全局实例测试"""
    
    def test_http_pool_is_singleton(self):
        """测试 HTTPClientPool 是单例"""
        # 单例模式测试：连续创建两个实例应该是同一个对象
        pool1 = HTTPClientPool()
        pool2 = HTTPClientPool()
        assert pool1 is pool2
    
    def test_token_cache_exists(self):
        """测试 token_cache 存在"""
        assert token_cache is not None
        assert isinstance(token_cache, TokenCache)
    
    def test_health_monitor_exists(self):
        """测试 health_monitor 存在"""
        assert health_monitor is not None
        assert isinstance(health_monitor, HealthMonitor)
