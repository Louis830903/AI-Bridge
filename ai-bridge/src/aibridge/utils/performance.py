"""
Performance Utilities - Connection pooling and caching
性能工具模块 - 连接池和缓存机制
"""

import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generic, Optional, TypeVar
from functools import wraps
import httpx


# ============ HTTP Connection Pool ============

class HTTPClientPool:
    """
    HTTP 客户端连接池
    
    为所有适配器提供共享的 httpx.AsyncClient 实例，
    减少连接创建开销，支持连接复用。
    """
    
    _instance: Optional["HTTPClientPool"] = None
    _lock = asyncio.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._clients: Dict[str, httpx.AsyncClient] = {}
        self._default_timeout = 30.0
        self._default_limits = httpx.Limits(
            max_connections=100,
            max_keepalive_connections=20,
            keepalive_expiry=30.0,
        )
        self._initialized = True
    
    async def get_client(
        self,
        name: str = "default",
        base_url: str = "",
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[float] = None,
        **kwargs
    ) -> httpx.AsyncClient:
        """
        获取或创建 HTTP 客户端
        
        Args:
            name: 客户端名称（用于缓存）
            base_url: 基础 URL
            headers: 请求头
            timeout: 超时时间
            
        Returns:
            httpx.AsyncClient 实例
        """
        async with self._lock:
            if name not in self._clients:
                self._clients[name] = httpx.AsyncClient(
                    base_url=base_url,
                    headers=headers or {},
                    timeout=timeout or self._default_timeout,
                    limits=self._default_limits,
                    **kwargs
                )
            return self._clients[name]
    
    async def close_client(self, name: str) -> bool:
        """
        关闭指定的客户端
        
        Args:
            name: 客户端名称
            
        Returns:
            是否成功关闭
        """
        async with self._lock:
            if name in self._clients:
                await self._clients[name].aclose()
                del self._clients[name]
                return True
            return False
    
    async def close_all(self):
        """关闭所有客户端"""
        async with self._lock:
            for client in self._clients.values():
                await client.aclose()
            self._clients.clear()
    
    def update_client_headers(self, name: str, headers: Dict[str, str]):
        """
        更新客户端的请求头
        
        Args:
            name: 客户端名称
            headers: 新的请求头
        """
        if name in self._clients:
            self._clients[name].headers.update(headers)


# 全局连接池实例
http_pool = HTTPClientPool()


# ============ Token Cache ============

@dataclass
class CachedToken:
    """缓存的 Token"""
    token: str
    expires_at: float  # Unix 时间戳
    refresh_token: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """检查 Token 是否过期（提前 60 秒）"""
        return time.time() >= self.expires_at - 60
    
    @property
    def remaining_seconds(self) -> float:
        """剩余有效时间（秒）"""
        return max(0, self.expires_at - time.time())


class TokenCache:
    """
    Token 缓存管理器
    
    支持自动刷新、过期检测、并发安全。
    """
    
    def __init__(self):
        self._cache: Dict[str, CachedToken] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._refresh_callbacks: Dict[str, Callable] = {}
    
    def _get_lock(self, key: str) -> asyncio.Lock:
        """获取指定 key 的锁"""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
    
    async def get(
        self,
        key: str,
        refresh_callback: Optional[Callable] = None
    ) -> Optional[str]:
        """
        获取 Token，如果过期则尝试刷新
        
        Args:
            key: Token 标识
            refresh_callback: 刷新回调函数
            
        Returns:
            Token 字符串，如果不存在或刷新失败则返回 None
        """
        async with self._get_lock(key):
            cached = self._cache.get(key)
            
            if cached is None:
                return None
            
            if not cached.is_expired:
                return cached.token
            
            # Token 过期，尝试刷新
            callback = refresh_callback or self._refresh_callbacks.get(key)
            if callback:
                try:
                    new_token = await callback(cached)
                    if new_token:
                        return new_token.token
                except Exception:
                    pass
            
            # 刷新失败，删除缓存
            del self._cache[key]
            return None
    
    def set(
        self,
        key: str,
        token: str,
        expires_in: float,
        refresh_token: Optional[str] = None,
        refresh_callback: Optional[Callable] = None,
        **metadata
    ) -> CachedToken:
        """
        设置 Token
        
        Args:
            key: Token 标识
            token: Token 值
            expires_in: 过期时间（秒）
            refresh_token: 刷新令牌
            refresh_callback: 刷新回调函数
            
        Returns:
            CachedToken 实例
        """
        cached = CachedToken(
            token=token,
            expires_at=time.time() + expires_in,
            refresh_token=refresh_token,
            metadata=metadata
        )
        self._cache[key] = cached
        
        if refresh_callback:
            self._refresh_callbacks[key] = refresh_callback
        
        return cached
    
    def invalidate(self, key: str) -> bool:
        """
        使 Token 失效
        
        Args:
            key: Token 标识
            
        Returns:
            是否成功删除
        """
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def invalidate_all(self):
        """清除所有缓存"""
        self._cache.clear()
    
    def get_info(self, key: str) -> Optional[Dict[str, Any]]:
        """获取 Token 信息（不含实际 Token）"""
        cached = self._cache.get(key)
        if cached:
            return {
                "key": key,
                "expires_at": cached.expires_at,
                "remaining_seconds": cached.remaining_seconds,
                "is_expired": cached.is_expired,
                "has_refresh_token": bool(cached.refresh_token),
                "metadata": cached.metadata,
            }
        return None


# 全局 Token 缓存实例
token_cache = TokenCache()


# ============ Generic Cache ============

T = TypeVar('T')


@dataclass
class CacheEntry(Generic[T]):
    """缓存条目"""
    value: T
    expires_at: float
    
    @property
    def is_expired(self) -> bool:
        return time.time() >= self.expires_at


class AsyncCache(Generic[T]):
    """
    通用异步缓存
    
    支持 TTL、LRU 淘汰、异步加载。
    """
    
    def __init__(
        self,
        default_ttl: float = 300,  # 默认 5 分钟
        max_size: int = 1000,
    ):
        self._cache: Dict[str, CacheEntry[T]] = {}
        self._access_order: list = []
        self._default_ttl = default_ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()
    
    async def get(
        self,
        key: str,
        loader: Optional[Callable[[], T]] = None,
        ttl: Optional[float] = None
    ) -> Optional[T]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            loader: 加载函数（缓存未命中时调用）
            ttl: 缓存 TTL
            
        Returns:
            缓存值
        """
        async with self._lock:
            entry = self._cache.get(key)
            
            if entry and not entry.is_expired:
                # 更新访问顺序
                if key in self._access_order:
                    self._access_order.remove(key)
                self._access_order.append(key)
                return entry.value
            
            # 缓存未命中或已过期
            if entry:
                del self._cache[key]
            
            if loader:
                value = await loader() if inspect.iscoroutinefunction(loader) else loader()
                await self._set_internal(key, value, ttl)
                return value
            
            return None
    
    async def set(self, key: str, value: T, ttl: Optional[float] = None):
        """设置缓存值"""
        async with self._lock:
            await self._set_internal(key, value, ttl)
    
    async def _set_internal(self, key: str, value: T, ttl: Optional[float] = None):
        """内部设置方法（需要已持有锁）"""
        # 检查是否需要淘汰
        while len(self._cache) >= self._max_size and self._access_order:
            old_key = self._access_order.pop(0)
            if old_key in self._cache:
                del self._cache[old_key]
        
        expires_at = time.time() + (ttl or self._default_ttl)
        self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
        
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                if key in self._access_order:
                    self._access_order.remove(key)
                return True
            return False
    
    async def clear(self):
        """清空缓存"""
        async with self._lock:
            self._cache.clear()
            self._access_order.clear()
    
    @property
    def size(self) -> int:
        """当前缓存大小"""
        return len(self._cache)


# ============ Retry Decorator ============

def with_retry(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,)
):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟（秒）
        backoff: 退避因子
        exceptions: 需要重试的异常类型
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


# ============ Batch Executor ============

class BatchExecutor:
    """
    批量执行器
    
    将多个请求合并为批量请求执行，减少网络往返。
    """
    
    def __init__(
        self,
        batch_size: int = 10,
        max_wait: float = 0.1,  # 最大等待时间（秒）
    ):
        self._batch_size = batch_size
        self._max_wait = max_wait
        self._pending: list = []
        self._lock = asyncio.Lock()
        self._event = asyncio.Event()
    
    async def submit(
        self,
        item: Any,
        executor: Callable[[list], Any]
    ) -> Any:
        """
        提交项目等待批量执行
        
        Args:
            item: 要处理的项目
            executor: 批量执行函数
            
        Returns:
            执行结果
        """
        future = asyncio.get_event_loop().create_future()
        
        async with self._lock:
            self._pending.append((item, future))
            
            if len(self._pending) >= self._batch_size:
                await self._flush(executor)
        
        # 等待结果或超时
        try:
            return await asyncio.wait_for(future, timeout=self._max_wait * 2)
        except asyncio.TimeoutError:
            # 超时，尝试强制执行
            async with self._lock:
                if self._pending:
                    await self._flush(executor)
            return await future
    
    async def _flush(self, executor: Callable):
        """执行当前批次"""
        if not self._pending:
            return
        
        batch = self._pending[:]
        self._pending.clear()
        
        items = [item for item, _ in batch]
        futures = [future for _, future in batch]
        
        try:
            results = await executor(items)
            for future, result in zip(futures, results):
                if not future.done():
                    future.set_result(result)
        except Exception as e:
            for future in futures:
                if not future.done():
                    future.set_exception(e)


# ============ Connection Health Monitor ============

class HealthMonitor:
    """
    连接健康监控器
    
    跟踪连接健康状态，支持熔断模式。
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_time: float = 30.0,
    ):
        self._failure_count: Dict[str, int] = {}
        self._last_failure: Dict[str, float] = {}
        self._failure_threshold = failure_threshold
        self._recovery_time = recovery_time
    
    def record_success(self, key: str):
        """记录成功"""
        self._failure_count[key] = 0
    
    def record_failure(self, key: str):
        """记录失败"""
        self._failure_count[key] = self._failure_count.get(key, 0) + 1
        self._last_failure[key] = time.time()
    
    def is_healthy(self, key: str) -> bool:
        """检查是否健康"""
        failures = self._failure_count.get(key, 0)
        
        if failures < self._failure_threshold:
            return True
        
        # 检查是否已过恢复期
        last_failure = self._last_failure.get(key, 0)
        if time.time() - last_failure > self._recovery_time:
            # 重置计数，允许重试
            self._failure_count[key] = 0
            return True
        
        return False
    
    def get_status(self, key: str) -> Dict[str, Any]:
        """获取状态信息"""
        failures = self._failure_count.get(key, 0)
        last_failure = self._last_failure.get(key)
        
        return {
            "key": key,
            "failure_count": failures,
            "is_healthy": self.is_healthy(key),
            "last_failure": last_failure,
            "threshold": self._failure_threshold,
        }


# 全局健康监控实例
health_monitor = HealthMonitor()
