"""
Agent Registry 注册中心

提供 Agent 的注册、发现和生命周期管理：
- Agent 注册与注销
- 心跳检测与健康状态
- 服务发现与负载均衡
- 自动清理不健康的 Agent
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Awaitable, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
import asyncio
import logging

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """获取当前 UTC 时间（timezone-aware）"""
    return datetime.now(timezone.utc)


class AgentHealth(str, Enum):
    """Agent 健康状态"""
    HEALTHY = "healthy"       # 健康
    DEGRADED = "degraded"     # 降级（部分功能异常）
    UNHEALTHY = "unhealthy"   # 不健康
    UNKNOWN = "unknown"       # 未知（刚注册或未检测）


class LoadBalanceStrategy(str, Enum):
    """负载均衡策略"""
    ROUND_ROBIN = "round_robin"       # 轮询
    LEAST_CONNECTIONS = "least_conn"  # 最少连接
    LATENCY = "latency"               # 最低延迟
    SUCCESS_RATE = "success_rate"     # 最高成功率
    RANDOM = "random"                 # 随机


@dataclass
class RegistryConfig:
    """Registry 配置"""
    heartbeat_interval: float = 30.0       # 心跳间隔（秒）
    heartbeat_timeout: float = 90.0        # 心跳超时（秒）
    health_check_interval: float = 60.0    # 健康检查间隔
    health_check_timeout: float = 5.0      # 健康检查超时
    max_consecutive_failures: int = 3      # 最大连续失败次数
    cleanup_interval: float = 300.0        # 清理间隔（秒）
    cleanup_threshold: int = 10            # 清理阈值（失败次数）
    enable_health_check: bool = True       # 是否启用健康检查


@dataclass
class RegisteredAgent:
    """注册的 Agent"""
    # 基础信息
    agent_id: str
    name: str
    endpoint: str
    capabilities: List[str] = field(default_factory=list)
    
    # 状态信息
    health: AgentHealth = AgentHealth.UNKNOWN
    last_heartbeat: datetime = field(default_factory=_utcnow)
    registered_at: datetime = field(default_factory=_utcnow)
    
    # 统计信息
    consecutive_failures: int = 0
    total_requests: int = 0
    active_connections: int = 0
    
    # 性能指标
    avg_latency_ms: Optional[float] = None
    success_rate: Optional[float] = None
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    
    def is_available(self) -> bool:
        """是否可用"""
        return self.health in (AgentHealth.HEALTHY, AgentHealth.DEGRADED)
    
    def update_heartbeat(self) -> None:
        """更新心跳时间"""
        self.last_heartbeat = _utcnow()
        self.consecutive_failures = 0
        if self.health == AgentHealth.UNHEALTHY:
            self.health = AgentHealth.HEALTHY
    
    def record_failure(self) -> None:
        """记录失败"""
        self.consecutive_failures += 1
    
    def record_request(self, latency_ms: float, success: bool) -> None:
        """记录请求
        
        Args:
            latency_ms: 延迟（毫秒）
            success: 是否成功
        """
        self.total_requests += 1
        
        # 更新平均延迟（指数移动平均）
        alpha = 0.1
        if self.avg_latency_ms is None:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = alpha * latency_ms + (1 - alpha) * self.avg_latency_ms
        
        # 更新成功率
        if self.success_rate is None:
            self.success_rate = 1.0 if success else 0.0
        else:
            alpha = 0.05
            self.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * self.success_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "endpoint": self.endpoint,
            "capabilities": self.capabilities,
            "health": self.health.value,
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "registered_at": self.registered_at.isoformat(),
            "consecutive_failures": self.consecutive_failures,
            "total_requests": self.total_requests,
            "active_connections": self.active_connections,
            "avg_latency_ms": self.avg_latency_ms,
            "success_rate": self.success_rate,
            "metadata": self.metadata,
            "tags": self.tags,
        }


class AgentRegistry:
    """Agent 注册中心
    
    管理 Agent 的注册、发现和生命周期
    """
    
    def __init__(self, config: RegistryConfig = None):
        """
        Args:
            config: Registry 配置
        """
        self._config = config or RegistryConfig()
        self._agents: Dict[str, RegisteredAgent] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # 回调
        self._on_register_callbacks: List[Callable[[RegisteredAgent], Awaitable[None]]] = []
        self._on_unregister_callbacks: List[Callable[[str], Awaitable[None]]] = []
        self._on_health_change_callbacks: List[Callable[[str, AgentHealth, AgentHealth], Awaitable[None]]] = []
        
        # 负载均衡状态
        self._round_robin_index: Dict[str, int] = {}  # capability -> index
    
    # ========== 生命周期管理 ==========
    
    async def start(self) -> None:
        """启动 Registry"""
        if self._running:
            return
        
        self._running = True
        self._tasks = [
            asyncio.create_task(self._heartbeat_checker()),
            asyncio.create_task(self._cleanup_task()),
        ]
        
        if self._config.enable_health_check:
            self._tasks.append(asyncio.create_task(self._health_checker()))
        
        logger.info("Agent Registry started")
    
    async def stop(self) -> None:
        """停止 Registry"""
        self._running = False
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        logger.info("Agent Registry stopped")
    
    # ========== 注册管理 ==========
    
    async def register(
        self,
        agent_id: str,
        name: str,
        endpoint: str,
        capabilities: List[str] = None,
        metadata: Dict[str, Any] = None,
        tags: List[str] = None,
    ) -> RegisteredAgent:
        """注册 Agent
        
        Args:
            agent_id: Agent ID
            name: Agent 名称
            endpoint: Agent 端点
            capabilities: 能力列表
            metadata: 元数据
            tags: 标签
            
        Returns:
            注册的 Agent
        """
        async with self._lock:
            agent = RegisteredAgent(
                agent_id=agent_id,
                name=name,
                endpoint=endpoint,
                capabilities=capabilities or [],
                metadata=metadata or {},
                tags=tags or [],
            )
            self._agents[agent_id] = agent
        
        logger.info(f"Agent registered: {agent_id} ({name})")
        
        # 触发回调
        for callback in self._on_register_callbacks:
            try:
                await callback(agent)
            except Exception as e:
                logger.warning(f"Register callback error: {e}")
        
        return agent
    
    async def unregister(self, agent_id: str) -> bool:
        """注销 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            if agent_id not in self._agents:
                return False
            del self._agents[agent_id]
        
        logger.info(f"Agent unregistered: {agent_id}")
        
        # 触发回调
        for callback in self._on_unregister_callbacks:
            try:
                await callback(agent_id)
            except Exception as e:
                logger.warning(f"Unregister callback error: {e}")
        
        return True
    
    async def heartbeat(self, agent_id: str) -> bool:
        """接收心跳
        
        Args:
            agent_id: Agent ID
            
        Returns:
            是否成功
        """
        async with self._lock:
            if agent_id not in self._agents:
                return False
            self._agents[agent_id].update_heartbeat()
        
        return True
    
    # ========== 查询接口 ==========
    
    async def get(self, agent_id: str) -> Optional[RegisteredAgent]:
        """获取 Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent 或 None
        """
        return self._agents.get(agent_id)
    
    async def list_agents(
        self,
        health: Optional[AgentHealth] = None,
        capabilities: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        available_only: bool = False,
    ) -> List[RegisteredAgent]:
        """列出 Agents
        
        Args:
            health: 健康状态过滤
            capabilities: 能力过滤（任一匹配）
            tags: 标签过滤（任一匹配）
            available_only: 仅返回可用的
            
        Returns:
            Agent 列表
        """
        agents = list(self._agents.values())
        
        if available_only:
            agents = [a for a in agents if a.is_available()]
        
        if health:
            agents = [a for a in agents if a.health == health]
        
        if capabilities:
            def has_capability(agent: RegisteredAgent) -> bool:
                return any(cap in agent.capabilities for cap in capabilities)
            agents = [a for a in agents if has_capability(a)]
        
        if tags:
            def has_tag(agent: RegisteredAgent) -> bool:
                return any(tag in agent.tags for tag in tags)
            agents = [a for a in agents if has_tag(a)]
        
        return agents
    
    async def count(
        self,
        health: Optional[AgentHealth] = None,
        available_only: bool = False,
    ) -> int:
        """统计 Agent 数量"""
        agents = await self.list_agents(health=health, available_only=available_only)
        return len(agents)
    
    # ========== 负载均衡 ==========
    
    async def select(
        self,
        capability: str,
        strategy: LoadBalanceStrategy = LoadBalanceStrategy.ROUND_ROBIN,
        exclude: List[str] = None,
    ) -> Optional[RegisteredAgent]:
        """选择 Agent（负载均衡）
        
        Args:
            capability: 能力名称
            strategy: 负载均衡策略
            exclude: 排除的 Agent ID 列表
            
        Returns:
            选中的 Agent 或 None
        """
        candidates = await self.list_agents(
            capabilities=[capability],
            available_only=True,
        )
        
        if exclude:
            candidates = [a for a in candidates if a.agent_id not in exclude]
        
        if not candidates:
            # 降级：尝试 DEGRADED 状态的
            candidates = await self.list_agents(
                capabilities=[capability],
                health=AgentHealth.DEGRADED,
            )
            if exclude:
                candidates = [a for a in candidates if a.agent_id not in exclude]
        
        if not candidates:
            return None
        
        # 根据策略选择
        if strategy == LoadBalanceStrategy.ROUND_ROBIN:
            return self._select_round_robin(capability, candidates)
        elif strategy == LoadBalanceStrategy.LEAST_CONNECTIONS:
            return self._select_least_connections(candidates)
        elif strategy == LoadBalanceStrategy.LATENCY:
            return self._select_by_latency(candidates)
        elif strategy == LoadBalanceStrategy.SUCCESS_RATE:
            return self._select_by_success_rate(candidates)
        elif strategy == LoadBalanceStrategy.RANDOM:
            return self._select_random(candidates)
        else:
            return candidates[0]
    
    def _select_round_robin(
        self,
        capability: str,
        candidates: List[RegisteredAgent]
    ) -> RegisteredAgent:
        """轮询选择"""
        if capability not in self._round_robin_index:
            self._round_robin_index[capability] = 0
        
        index = self._round_robin_index[capability] % len(candidates)
        self._round_robin_index[capability] = index + 1
        
        return candidates[index]
    
    def _select_least_connections(
        self,
        candidates: List[RegisteredAgent]
    ) -> RegisteredAgent:
        """最少连接选择"""
        return min(candidates, key=lambda a: a.active_connections)
    
    def _select_by_latency(
        self,
        candidates: List[RegisteredAgent]
    ) -> RegisteredAgent:
        """最低延迟选择"""
        return min(
            candidates,
            key=lambda a: a.avg_latency_ms if a.avg_latency_ms is not None else float('inf')
        )
    
    def _select_by_success_rate(
        self,
        candidates: List[RegisteredAgent]
    ) -> RegisteredAgent:
        """最高成功率选择"""
        return max(
            candidates,
            key=lambda a: a.success_rate if a.success_rate is not None else 0
        )
    
    def _select_random(
        self,
        candidates: List[RegisteredAgent]
    ) -> RegisteredAgent:
        """随机选择"""
        import random
        return random.choice(candidates)
    
    # ========== 回调注册 ==========
    
    def on_register(self, callback: Callable[[RegisteredAgent], Awaitable[None]]) -> None:
        """注册回调：Agent 注册时"""
        self._on_register_callbacks.append(callback)
    
    def on_unregister(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """注册回调：Agent 注销时"""
        self._on_unregister_callbacks.append(callback)
    
    def on_health_change(
        self,
        callback: Callable[[str, AgentHealth, AgentHealth], Awaitable[None]]
    ) -> None:
        """注册回调：健康状态变化时
        
        callback(agent_id, old_health, new_health)
        """
        self._on_health_change_callbacks.append(callback)
    
    # ========== 内部任务 ==========
    
    async def _heartbeat_checker(self) -> None:
        """心跳检查任务"""
        while self._running:
            await asyncio.sleep(self._config.heartbeat_interval)
            
            now = _utcnow()
            timeout = timedelta(seconds=self._config.heartbeat_timeout)
            
            async with self._lock:
                for agent in self._agents.values():
                    if now - agent.last_heartbeat > timeout:
                        old_health = agent.health
                        agent.health = AgentHealth.UNHEALTHY
                        
                        if old_health != AgentHealth.UNHEALTHY:
                            await self._notify_health_change(
                                agent.agent_id, old_health, AgentHealth.UNHEALTHY
                            )
    
    async def _health_checker(self) -> None:
        """健康检查任务"""
        while self._running:
            await asyncio.sleep(self._config.health_check_interval)
            
            for agent_id, agent in list(self._agents.items()):
                old_health = agent.health
                healthy = await self._check_agent_health(agent)
                
                async with self._lock:
                    if agent_id not in self._agents:
                        continue
                    
                    if healthy:
                        self._agents[agent_id].health = AgentHealth.HEALTHY
                        self._agents[agent_id].consecutive_failures = 0
                    else:
                        self._agents[agent_id].consecutive_failures += 1
                        if self._agents[agent_id].consecutive_failures >= self._config.max_consecutive_failures:
                            self._agents[agent_id].health = AgentHealth.UNHEALTHY
                        else:
                            self._agents[agent_id].health = AgentHealth.DEGRADED
                    
                    new_health = self._agents[agent_id].health
                
                if old_health != new_health:
                    await self._notify_health_change(agent_id, old_health, new_health)
    
    async def _check_agent_health(self, agent: RegisteredAgent) -> bool:
        """检查单个 Agent 健康"""
        if not HAS_AIOHTTP:
            return True  # 没有 aiohttp，假设健康
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"{agent.endpoint.rstrip('/')}/health"
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self._config.health_check_timeout)
                ) as resp:
                    return resp.status == 200
        except Exception:
            return False
    
    async def _cleanup_task(self) -> None:
        """清理不健康的 Agent"""
        while self._running:
            await asyncio.sleep(self._config.cleanup_interval)
            
            to_remove = []
            async with self._lock:
                for agent_id, agent in self._agents.items():
                    if (agent.health == AgentHealth.UNHEALTHY and
                        agent.consecutive_failures > self._config.cleanup_threshold):
                        to_remove.append(agent_id)
            
            for agent_id in to_remove:
                logger.warning(f"Cleaning up unhealthy agent: {agent_id}")
                await self.unregister(agent_id)
    
    async def _notify_health_change(
        self,
        agent_id: str,
        old_health: AgentHealth,
        new_health: AgentHealth
    ) -> None:
        """通知健康状态变化"""
        logger.info(f"Agent {agent_id} health changed: {old_health.value} -> {new_health.value}")
        
        for callback in self._on_health_change_callbacks:
            try:
                await callback(agent_id, old_health, new_health)
            except Exception as e:
                logger.warning(f"Health change callback error: {e}")


class RegistryClient:
    """Registry 客户端
    
    用于 Agent 向 Registry 注册自己
    """
    
    def __init__(
        self,
        registry_url: str,
        agent_id: str,
        name: str,
        endpoint: str,
        capabilities: List[str] = None,
        heartbeat_interval: float = 30.0,
    ):
        """
        Args:
            registry_url: Registry 服务地址
            agent_id: Agent ID
            name: Agent 名称
            endpoint: 自身服务端点
            capabilities: 能力列表
            heartbeat_interval: 心跳间隔
        """
        if not HAS_AIOHTTP:
            raise ImportError("aiohttp is required for RegistryClient")
        
        self._registry_url = registry_url.rstrip("/")
        self._agent_id = agent_id
        self._name = name
        self._endpoint = endpoint
        self._capabilities = capabilities or []
        self._heartbeat_interval = heartbeat_interval
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None
    
    async def register(self, metadata: Dict[str, Any] = None, tags: List[str] = None) -> bool:
        """注册到 Registry"""
        url = f"{self._registry_url}/agents"
        payload = {
            "agent_id": self._agent_id,
            "name": self._name,
            "endpoint": self._endpoint,
            "capabilities": self._capabilities,
            "metadata": metadata or {},
            "tags": tags or [],
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status in (200, 201):
                        logger.info(f"Registered to registry: {self._agent_id}")
                        return True
                    else:
                        logger.warning(f"Failed to register: HTTP {resp.status}")
                        return False
        except Exception as e:
            logger.warning(f"Failed to register: {e}")
            return False
    
    async def unregister(self) -> bool:
        """从 Registry 注销"""
        url = f"{self._registry_url}/agents/{self._agent_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status in (200, 204):
                        logger.info(f"Unregistered from registry: {self._agent_id}")
                        return True
                    else:
                        return False
        except Exception as e:
            logger.warning(f"Failed to unregister: {e}")
            return False
    
    async def start_heartbeat(self) -> None:
        """启动心跳"""
        if self._running:
            return
        
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def stop_heartbeat(self) -> None:
        """停止心跳"""
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
    
    async def _heartbeat_loop(self) -> None:
        """心跳循环"""
        while self._running:
            await asyncio.sleep(self._heartbeat_interval)
            await self._send_heartbeat()
    
    async def _send_heartbeat(self) -> bool:
        """发送心跳"""
        url = f"{self._registry_url}/agents/{self._agent_id}/heartbeat"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                    return resp.status == 200
        except Exception:
            return False
