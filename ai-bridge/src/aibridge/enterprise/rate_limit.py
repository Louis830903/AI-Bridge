"""
请求限流器

支持多种限流策略：
- 固定窗口
- 滑动窗口
- 令牌桶
- 漏桶

支持多维度限流（用户、IP、资源等）。
"""

import asyncio
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """限流策略"""
    FIXED_WINDOW = "fixed_window"      # 固定窗口
    SLIDING_WINDOW = "sliding_window"  # 滑动窗口
    TOKEN_BUCKET = "token_bucket"      # 令牌桶
    LEAKY_BUCKET = "leaky_bucket"      # 漏桶


class RateLimitExceeded(Exception):
    """限流异常"""
    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: Optional[float] = None,
        limit: Optional[int] = None,
        remaining: int = 0,
    ):
        super().__init__(message)
        self.retry_after = retry_after
        self.limit = limit
        self.remaining = remaining


@dataclass
class RateLimitConfig:
    """限流配置"""
    # 是否启用
    enabled: bool = True
    
    # 限流策略
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    
    # 默认限制
    requests_per_second: float = 10.0  # 每秒请求数
    requests_per_minute: int = 100     # 每分钟请求数
    requests_per_hour: int = 1000      # 每小时请求数
    
    # 令牌桶配置
    bucket_capacity: int = 100         # 桶容量
    refill_rate: float = 10.0          # 每秒补充速率
    
    # 针对不同资源的限制
    resource_limits: Dict[str, int] = field(default_factory=dict)
    
    # 针对不同用户的限制
    user_limits: Dict[str, int] = field(default_factory=dict)
    
    # 白名单（不限流）
    whitelist: List[str] = field(default_factory=list)
    
    # 惩罚配置
    penalty_enabled: bool = False
    penalty_duration: float = 60.0     # 惩罚时长（秒）
    penalty_threshold: int = 10        # 触发惩罚的连续超限次数


@dataclass
class RateLimitInfo:
    """限流信息"""
    allowed: bool
    limit: int
    remaining: int
    reset_at: float  # Unix 时间戳
    retry_after: Optional[float] = None


class RateLimitBackend(ABC):
    """限流后端基类"""
    
    @abstractmethod
    async def check(self, key: str, limit: int, window: float) -> RateLimitInfo:
        """
        检查是否限流
        
        Args:
            key: 限流键（如 user:123 或 ip:1.2.3.4）
            limit: 限制数量
            window: 时间窗口（秒）
            
        Returns:
            RateLimitInfo
        """
        pass
    
    @abstractmethod
    async def reset(self, key: str) -> None:
        """重置限流计数"""
        pass


class InMemoryBackend(RateLimitBackend):
    """内存限流后端"""
    
    def __init__(self):
        self._counters: Dict[str, List[float]] = defaultdict(list)
        self._tokens: Dict[str, Tuple[float, float]] = {}  # key -> (tokens, last_refill)
        self._lock = asyncio.Lock()
    
    async def check(self, key: str, limit: int, window: float) -> RateLimitInfo:
        """滑动窗口检查"""
        async with self._lock:
            now = time.time()
            window_start = now - window
            
            # 清理过期记录
            self._counters[key] = [
                ts for ts in self._counters[key] if ts > window_start
            ]
            
            current_count = len(self._counters[key])
            remaining = max(0, limit - current_count)
            reset_at = now + window
            
            if current_count >= limit:
                # 计算需要等待的时间
                if self._counters[key]:
                    oldest = min(self._counters[key])
                    retry_after = oldest + window - now
                else:
                    retry_after = window
                
                return RateLimitInfo(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=max(0, retry_after),
                )
            
            # 记录本次请求
            self._counters[key].append(now)
            
            return RateLimitInfo(
                allowed=True,
                limit=limit,
                remaining=remaining - 1,
                reset_at=reset_at,
            )
    
    async def check_token_bucket(
        self,
        key: str,
        capacity: int,
        refill_rate: float
    ) -> RateLimitInfo:
        """令牌桶检查"""
        async with self._lock:
            now = time.time()
            
            # 获取或初始化令牌
            if key not in self._tokens:
                self._tokens[key] = (float(capacity), now)
            
            tokens, last_refill = self._tokens[key]
            
            # 补充令牌
            elapsed = now - last_refill
            tokens = min(capacity, tokens + elapsed * refill_rate)
            
            if tokens < 1:
                # 计算等待时间
                wait_time = (1 - tokens) / refill_rate
                return RateLimitInfo(
                    allowed=False,
                    limit=capacity,
                    remaining=0,
                    reset_at=now + wait_time,
                    retry_after=wait_time,
                )
            
            # 消耗一个令牌
            tokens -= 1
            self._tokens[key] = (tokens, now)
            
            return RateLimitInfo(
                allowed=True,
                limit=capacity,
                remaining=int(tokens),
                reset_at=now + (capacity - tokens) / refill_rate,
            )
    
    async def reset(self, key: str) -> None:
        """重置限流计数"""
        async with self._lock:
            if key in self._counters:
                del self._counters[key]
            if key in self._tokens:
                del self._tokens[key]


class RateLimiter:
    """
    请求限流器
    
    保护系统免受过载，支持多种限流策略。
    
    使用示例：
    ```python
    config = RateLimitConfig(
        enabled=True,
        strategy=RateLimitStrategy.SLIDING_WINDOW,
        requests_per_minute=100,
    )
    
    limiter = RateLimiter(config)
    
    # 检查是否允许请求
    try:
        await limiter.check("user:123")
        # 执行请求...
    except RateLimitExceeded as e:
        print(f"Rate limited, retry after {e.retry_after}s")
    
    # 使用装饰器
    @limiter.limit()
    async def my_api_handler(user_id: str):
        ...
    ```
    """
    
    def __init__(
        self,
        config: RateLimitConfig,
        backend: Optional[RateLimitBackend] = None
    ):
        self._config = config
        self._backend = backend or InMemoryBackend()
        self._penalty_counts: Dict[str, int] = defaultdict(int)
        self._penalty_until: Dict[str, float] = {}
    
    async def check(
        self,
        key: str,
        limit: Optional[int] = None,
        window: Optional[float] = None,
    ) -> RateLimitInfo:
        """
        检查是否限流
        
        Args:
            key: 限流键
            limit: 覆盖默认限制
            window: 覆盖默认窗口（秒）
            
        Returns:
            RateLimitInfo
            
        Raises:
            RateLimitExceeded: 触发限流时抛出
        """
        if not self._config.enabled:
            return RateLimitInfo(
                allowed=True,
                limit=0,
                remaining=0,
                reset_at=0,
            )
        
        # 检查白名单
        if key in self._config.whitelist:
            return RateLimitInfo(
                allowed=True,
                limit=0,
                remaining=0,
                reset_at=0,
            )
        
        # 检查惩罚期
        if self._config.penalty_enabled:
            now = time.time()
            if key in self._penalty_until and self._penalty_until[key] > now:
                retry_after = self._penalty_until[key] - now
                raise RateLimitExceeded(
                    message=f"Rate limit exceeded (in penalty period)",
                    retry_after=retry_after,
                    limit=0,
                    remaining=0,
                )
        
        # 确定限制参数
        actual_limit = limit or self._config.requests_per_minute
        actual_window = window or 60.0
        
        # 检查资源特定限制
        for resource, res_limit in self._config.resource_limits.items():
            if resource in key:
                actual_limit = res_limit
                break
        
        # 检查用户特定限制
        for user, user_limit in self._config.user_limits.items():
            if user in key:
                actual_limit = user_limit
                break
        
        # 执行限流检查
        if self._config.strategy == RateLimitStrategy.TOKEN_BUCKET:
            if isinstance(self._backend, InMemoryBackend):
                info = await self._backend.check_token_bucket(
                    key,
                    self._config.bucket_capacity,
                    self._config.refill_rate,
                )
            else:
                info = await self._backend.check(key, actual_limit, actual_window)
        else:
            info = await self._backend.check(key, actual_limit, actual_window)
        
        # 处理限流结果
        if not info.allowed:
            self._handle_rate_limit(key)
            raise RateLimitExceeded(
                message=f"Rate limit exceeded for {key}",
                retry_after=info.retry_after,
                limit=info.limit,
                remaining=info.remaining,
            )
        
        # 重置惩罚计数
        if key in self._penalty_counts:
            self._penalty_counts[key] = 0
        
        return info
    
    def _handle_rate_limit(self, key: str) -> None:
        """处理限流触发"""
        if not self._config.penalty_enabled:
            return
        
        self._penalty_counts[key] += 1
        
        if self._penalty_counts[key] >= self._config.penalty_threshold:
            # 进入惩罚期
            self._penalty_until[key] = time.time() + self._config.penalty_duration
            self._penalty_counts[key] = 0
            logger.warning(f"Rate limit penalty applied to {key}")
    
    async def reset(self, key: str) -> None:
        """重置限流计数"""
        await self._backend.reset(key)
        if key in self._penalty_counts:
            del self._penalty_counts[key]
        if key in self._penalty_until:
            del self._penalty_until[key]
    
    def limit(
        self,
        key_extractor: Optional[Callable] = None,
        limit: Optional[int] = None,
        window: Optional[float] = None,
    ):
        """
        装饰器：自动限流
        
        Args:
            key_extractor: 从参数提取限流键的函数
            limit: 覆盖默认限制
            window: 覆盖默认窗口
        """
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                # 提取限流键
                if key_extractor:
                    key = key_extractor(*args, **kwargs)
                else:
                    key = f"func:{func.__name__}"
                
                # 检查限流
                await self.check(key, limit, window)
                
                # 执行函数
                return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    def get_status(self, key: str) -> Dict[str, Any]:
        """获取限流状态"""
        now = time.time()
        penalty_remaining = 0
        if key in self._penalty_until:
            penalty_remaining = max(0, self._penalty_until[key] - now)
        
        return {
            "key": key,
            "in_whitelist": key in self._config.whitelist,
            "penalty_count": self._penalty_counts.get(key, 0),
            "penalty_remaining": penalty_remaining,
            "config": {
                "strategy": self._config.strategy.value,
                "requests_per_minute": self._config.requests_per_minute,
            }
        }
