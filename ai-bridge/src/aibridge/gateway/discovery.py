"""
服务发现与健康检查

功能：
- 自动发现可用的 MCP Server
- 定期健康检查
- 服务状态监控
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态"""
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"


@dataclass
class HealthCheckResult:
    """健康检查结果"""
    service_name: str
    status: ServiceStatus
    latency_ms: float = 0.0
    message: str = ""
    checked_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServiceInfo:
    """服务信息"""
    name: str
    type: str  # "mcp", "a2a", "connector"
    status: ServiceStatus = ServiceStatus.UNKNOWN
    last_check: Optional[HealthCheckResult] = None
    check_interval: float = 60.0  # 健康检查间隔(秒)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ServiceDiscovery:
    """
    服务发现与健康检查
    
    功能：
    - 自动发现本地和远程服务
    - 定期健康检查
    - 服务状态订阅
    
    使用示例：
    ```python
    discovery = ServiceDiscovery()
    
    # 注册服务
    discovery.register_service(ServiceInfo(
        name="browser-use",
        type="mcp",
        check_interval=30.0,
    ))
    
    # 启动健康检查
    await discovery.start()
    
    # 获取健康的服务
    healthy = discovery.get_healthy_services()
    
    # 停止
    await discovery.stop()
    ```
    """
    
    def __init__(self):
        self._services: Dict[str, ServiceInfo] = {}
        self._health_checkers: Dict[str, Callable] = {}  # service_type -> checker
        self._check_tasks: Dict[str, asyncio.Task] = {}
        self._running = False
        self._lock = asyncio.Lock()
    
    def register_health_checker(
        self, 
        service_type: str, 
        checker: Callable[[ServiceInfo], HealthCheckResult]
    ) -> None:
        """
        注册健康检查器
        
        Args:
            service_type: 服务类型
            checker: 检查函数，接收 ServiceInfo，返回 HealthCheckResult
        """
        self._health_checkers[service_type] = checker
        logger.info(f"Registered health checker for type: {service_type}")
    
    def register_service(self, service: ServiceInfo) -> None:
        """
        注册服务
        
        Args:
            service: 服务信息
        """
        self._services[service.name] = service
        logger.info(f"Registered service: {service.name} (type: {service.type})")
        
        # 如果已经在运行，启动健康检查
        if self._running:
            self._start_check_task(service.name)
    
    def unregister_service(self, name: str) -> None:
        """
        注销服务
        
        Args:
            name: 服务名称
        """
        if name in self._check_tasks:
            self._check_tasks[name].cancel()
            del self._check_tasks[name]
        
        if name in self._services:
            del self._services[name]
            logger.info(f"Unregistered service: {name}")
    
    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """获取服务信息"""
        return self._services.get(name)
    
    def get_all_services(self) -> List[ServiceInfo]:
        """获取所有服务"""
        return list(self._services.values())
    
    def get_healthy_services(self, service_type: Optional[str] = None) -> List[ServiceInfo]:
        """
        获取健康的服务
        
        Args:
            service_type: 可选，筛选服务类型
            
        Returns:
            健康服务列表
        """
        services = self._services.values()
        if service_type:
            services = [s for s in services if s.type == service_type]
        return [s for s in services if s.status == ServiceStatus.HEALTHY]
    
    async def check_service(self, name: str) -> HealthCheckResult:
        """
        检查单个服务健康状态
        
        Args:
            name: 服务名称
            
        Returns:
            健康检查结果
        """
        service = self._services.get(name)
        if not service:
            return HealthCheckResult(
                service_name=name,
                status=ServiceStatus.UNKNOWN,
                message="Service not found",
            )
        
        # 查找对应的健康检查器
        checker = self._health_checkers.get(service.type)
        if not checker:
            # 没有检查器，默认返回未知状态
            return HealthCheckResult(
                service_name=name,
                status=ServiceStatus.UNKNOWN,
                message=f"No health checker for type: {service.type}",
            )
        
        try:
            start = asyncio.get_event_loop().time()
            
            # 执行健康检查
            if asyncio.iscoroutinefunction(checker):
                result = await checker(service)
            else:
                result = checker(service)
            
            latency = (asyncio.get_event_loop().time() - start) * 1000
            result.latency_ms = latency
            
        except Exception as e:
            result = HealthCheckResult(
                service_name=name,
                status=ServiceStatus.UNHEALTHY,
                message=str(e),
            )
        
        # 更新服务状态
        service.status = result.status
        service.last_check = result
        
        return result
    
    async def check_all(self) -> Dict[str, HealthCheckResult]:
        """
        检查所有服务
        
        Returns:
            服务名称 -> 健康检查结果
        """
        results = {}
        for name in self._services:
            results[name] = await self.check_service(name)
        return results
    
    def _start_check_task(self, name: str) -> None:
        """启动单个服务的健康检查任务"""
        if name in self._check_tasks:
            return
        
        service = self._services.get(name)
        if not service:
            return
        
        async def check_loop():
            while self._running:
                try:
                    await self.check_service(name)
                except Exception as e:
                    logger.error(f"Health check failed for {name}: {e}")
                
                await asyncio.sleep(service.check_interval)
        
        self._check_tasks[name] = asyncio.create_task(check_loop())
    
    async def start(self) -> None:
        """启动健康检查"""
        self._running = True
        
        # 为所有服务启动检查任务
        for name in self._services:
            self._start_check_task(name)
        
        logger.info("Service discovery started")
    
    async def stop(self) -> None:
        """停止健康检查"""
        self._running = False
        
        # 取消所有检查任务
        for task in self._check_tasks.values():
            task.cancel()
        
        # 等待任务结束
        if self._check_tasks:
            await asyncio.gather(*self._check_tasks.values(), return_exceptions=True)
        
        self._check_tasks.clear()
        logger.info("Service discovery stopped")
    
    def get_status_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        total = len(self._services)
        healthy = len([s for s in self._services.values() if s.status == ServiceStatus.HEALTHY])
        unhealthy = len([s for s in self._services.values() if s.status == ServiceStatus.UNHEALTHY])
        unknown = total - healthy - unhealthy
        
        return {
            "total": total,
            "healthy": healthy,
            "unhealthy": unhealthy,
            "unknown": unknown,
            "services": {
                name: {
                    "type": s.type,
                    "status": s.status.value,
                    "last_check": s.last_check.checked_at.isoformat() if s.last_check else None,
                }
                for name, s in self._services.items()
            }
        }
    
    async def __aenter__(self):
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
