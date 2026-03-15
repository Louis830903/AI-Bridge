"""
健康检查端点

提供系统健康状态检查：
- 整体健康状态
- 各组件状态
- 依赖服务状态
- 性能指标
"""

import asyncio
import inspect
import logging
import os
import platform
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"       # 健康
    DEGRADED = "degraded"     # 降级（部分功能受影响）
    UNHEALTHY = "unhealthy"   # 不健康


@dataclass
class HealthCheck:
    """单个健康检查结果"""
    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        d["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return d


@dataclass
class HealthReport:
    """健康报告"""
    status: HealthStatus
    checks: List[HealthCheck] = field(default_factory=list)
    version: str = ""
    uptime_seconds: float = 0
    system_info: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "checks": [c.to_dict() for c in self.checks],
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "system_info": self.system_info,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
        }


class HealthChecker:
    """
    健康检查器
    
    提供系统健康状态检查和报告。
    
    使用示例：
    ```python
    checker = HealthChecker(version="3.0.0")
    
    # 注册检查项
    checker.register_check("database", db_health_check)
    checker.register_check("redis", redis_health_check)
    
    # 执行健康检查
    report = await checker.check()
    print(f"Status: {report.status.value}")
    
    # 作为 HTTP 端点
    @app.get("/health")
    async def health():
        report = await checker.check()
        return report.to_dict()
    
    # 简单存活检查
    @app.get("/health/live")
    async def liveness():
        return {"status": "ok"}
    
    # 就绪检查
    @app.get("/health/ready")
    async def readiness():
        report = await checker.check()
        if report.status == HealthStatus.UNHEALTHY:
            raise HTTPException(503)
        return {"status": "ready"}
    ```
    """
    
    def __init__(
        self,
        version: str = "",
        timeout: float = 10.0,
    ):
        self._version = version
        self._timeout = timeout
        self._start_time = time.time()
        self._checks: Dict[str, Callable] = {}
    
    @property
    def uptime(self) -> float:
        """运行时间（秒）"""
        return time.time() - self._start_time
    
    def register_check(
        self,
        name: str,
        check_func: Callable[[], HealthCheck],
    ) -> None:
        """
        注册健康检查项
        
        Args:
            name: 检查名称
            check_func: 检查函数，返回 HealthCheck 或异步返回
        """
        self._checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    def unregister_check(self, name: str) -> None:
        """注销健康检查项"""
        if name in self._checks:
            del self._checks[name]
            logger.info(f"Unregistered health check: {name}")
    
    async def check(self) -> HealthReport:
        """
        执行所有健康检查
        
        Returns:
            HealthReport
        """
        checks: List[HealthCheck] = []
        
        # 并行执行所有检查
        tasks = []
        for name, check_func in self._checks.items():
            tasks.append(self._run_check(name, check_func))
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, HealthCheck):
                    checks.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"Health check error: {result}")
        
        # 确定整体状态
        overall_status = self._determine_overall_status(checks)
        
        # 收集系统信息
        system_info = self._get_system_info()
        
        return HealthReport(
            status=overall_status,
            checks=checks,
            version=self._version,
            uptime_seconds=self.uptime,
            system_info=system_info,
        )
    
    async def _run_check(
        self,
        name: str,
        check_func: Callable,
    ) -> HealthCheck:
        """运行单个检查"""
        start_time = time.time()
        
        try:
            # 添加超时
            if inspect.iscoroutinefunction(check_func):
                result = await asyncio.wait_for(
                    check_func(),
                    timeout=self._timeout
                )
            else:
                result = check_func()
            
            latency_ms = (time.time() - start_time) * 1000
            
            if isinstance(result, HealthCheck):
                result.latency_ms = latency_ms
                return result
            else:
                return HealthCheck(
                    name=name,
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency_ms,
                )
                
        except asyncio.TimeoutError:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check timed out after {self._timeout}s",
                latency_ms=self._timeout * 1000,
            )
        except Exception as e:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=str(e),
                latency_ms=(time.time() - start_time) * 1000,
            )
    
    def _determine_overall_status(self, checks: List[HealthCheck]) -> HealthStatus:
        """确定整体健康状态"""
        if not checks:
            return HealthStatus.HEALTHY
        
        has_unhealthy = any(c.status == HealthStatus.UNHEALTHY for c in checks)
        has_degraded = any(c.status == HealthStatus.DEGRADED for c in checks)
        
        if has_unhealthy:
            return HealthStatus.UNHEALTHY
        elif has_degraded:
            return HealthStatus.DEGRADED
        else:
            return HealthStatus.HEALTHY
    
    def _get_system_info(self) -> Dict[str, Any]:
        """获取系统信息"""
        try:
            import psutil
            memory = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            
            return {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version(),
                "cpu_count": os.cpu_count(),
                "cpu_percent": cpu_percent,
                "memory_total_gb": round(memory.total / (1024**3), 2),
                "memory_used_gb": round(memory.used / (1024**3), 2),
                "memory_percent": memory.percent,
            }
        except ImportError:
            return {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "python_version": platform.python_version(),
                "cpu_count": os.cpu_count(),
            }
    
    # 预置的健康检查函数
    @staticmethod
    def check_mcp_registry(registry) -> Callable:
        """创建 MCP Registry 健康检查"""
        async def check() -> HealthCheck:
            try:
                servers = await registry.list_servers()
                status = registry.get_server_status()
                
                connected = sum(1 for s in status.values() if s.get("connected"))
                total = len(servers)
                
                if total == 0:
                    return HealthCheck(
                        name="mcp_registry",
                        status=HealthStatus.HEALTHY,
                        message="No servers registered",
                        details={"servers": 0},
                    )
                
                if connected == total:
                    health_status = HealthStatus.HEALTHY
                elif connected > 0:
                    health_status = HealthStatus.DEGRADED
                else:
                    health_status = HealthStatus.UNHEALTHY
                
                return HealthCheck(
                    name="mcp_registry",
                    status=health_status,
                    message=f"{connected}/{total} servers connected",
                    details={
                        "total_servers": total,
                        "connected": connected,
                        "servers": list(servers),
                    },
                )
            except Exception as e:
                return HealthCheck(
                    name="mcp_registry",
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                )
        
        return check
    
    @staticmethod
    def check_a2a_gateway(gateway) -> Callable:
        """创建 A2A Gateway 健康检查"""
        async def check() -> HealthCheck:
            try:
                agents = await gateway.list_agents()
                
                return HealthCheck(
                    name="a2a_gateway",
                    status=HealthStatus.HEALTHY,
                    message=f"{len(agents)} agents registered",
                    details={
                        "agents": [a.name for a in agents],
                    },
                )
            except Exception as e:
                return HealthCheck(
                    name="a2a_gateway",
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                )
        
        return check
    
    @staticmethod
    def check_connector(connector, name: str) -> Callable:
        """创建连接器健康检查"""
        async def check() -> HealthCheck:
            from aibridge.connectors.base import ConnectorStatus
            
            status = connector.status
            
            if status == ConnectorStatus.CONNECTED:
                health_status = HealthStatus.HEALTHY
            elif status == ConnectorStatus.CONNECTING:
                health_status = HealthStatus.DEGRADED
            else:
                health_status = HealthStatus.UNHEALTHY
            
            return HealthCheck(
                name=f"connector_{name}",
                status=health_status,
                message=f"Status: {status.value}",
                details={
                    "connector_name": connector.name,
                    "status": status.value,
                },
            )
        
        return check
