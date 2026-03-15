"""
操作审计日志

记录所有关键操作，支持多种输出目标：
- 控制台
- 文件
- 数据库
- 外部系统（如 Elasticsearch）
"""

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """审计级别"""
    DEBUG = "debug"      # 调试信息
    INFO = "info"        # 一般操作
    WARNING = "warning"  # 警告
    ERROR = "error"      # 错误
    CRITICAL = "critical"  # 严重事件


class AuditAction(Enum):
    """审计操作类型"""
    # 认证相关
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    
    # 工具调用
    TOOL_CALL = "tool.call"
    TOOL_SUCCESS = "tool.success"
    TOOL_FAILED = "tool.failed"
    
    # 资源访问
    RESOURCE_READ = "resource.read"
    RESOURCE_WRITE = "resource.write"
    RESOURCE_DELETE = "resource.delete"
    
    # 管理操作
    SERVER_START = "server.start"
    SERVER_STOP = "server.stop"
    SERVER_REGISTER = "server.register"
    SERVER_UNREGISTER = "server.unregister"
    
    # Agent 相关
    AGENT_REGISTER = "agent.register"
    AGENT_UNREGISTER = "agent.unregister"
    TASK_CREATE = "task.create"
    TASK_COMPLETE = "task.complete"
    TASK_FAILED = "task.failed"
    
    # 安全相关
    PERMISSION_DENIED = "security.permission_denied"
    RATE_LIMITED = "security.rate_limited"
    SUSPICIOUS_ACTIVITY = "security.suspicious"


@dataclass
class AuditEvent:
    """审计事件"""
    # 事件标识
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    
    # 事件信息
    action: str = ""
    level: AuditLevel = AuditLevel.INFO
    
    # 用户信息
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    
    # 请求信息
    request_id: Optional[str] = None
    source_ip: Optional[str] = None
    
    # 操作详情
    resource: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    
    # 结果
    success: bool = True
    result: Optional[Any] = None
    error: Optional[str] = None
    
    # 耗时（毫秒）
    duration_ms: Optional[float] = None
    
    # 额外元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        d = asdict(self)
        d["level"] = self.level.value
        d["timestamp_iso"] = datetime.fromtimestamp(self.timestamp).isoformat()
        return d
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)


@dataclass
class AuditConfig:
    """审计配置"""
    # 是否启用
    enabled: bool = True
    
    # 最小记录级别
    min_level: AuditLevel = AuditLevel.INFO
    
    # 输出目标
    console_output: bool = True
    file_output: bool = True
    file_path: str = "./logs/audit.log"
    
    # 文件轮转
    max_file_size_mb: int = 100
    max_files: int = 10
    
    # 敏感数据处理
    mask_sensitive_fields: List[str] = field(
        default_factory=lambda: ["password", "token", "api_key", "secret"]
    )
    
    # 异步写入
    async_write: bool = True
    buffer_size: int = 100
    flush_interval: float = 5.0  # 秒


class AuditLogger:
    """
    审计日志记录器
    
    记录所有关键操作的审计日志。
    
    使用示例：
    ```python
    config = AuditConfig(
        enabled=True,
        file_path="./logs/audit.log"
    )
    
    audit = AuditLogger(config)
    await audit.start()
    
    # 记录事件
    await audit.log(
        action=AuditAction.TOOL_CALL,
        user_id="user123",
        resource="browser/navigate",
        params={"url": "https://example.com"},
        success=True,
        duration_ms=150.5
    )
    
    # 使用装饰器
    @audit.audit_call(AuditAction.TOOL_CALL)
    async def my_tool_call(params):
        ...
    
    await audit.stop()
    ```
    """
    
    def __init__(self, config: AuditConfig):
        self._config = config
        self._buffer: List[AuditEvent] = []
        self._file_handle = None
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
    
    async def start(self) -> None:
        """启动审计日志"""
        if not self._config.enabled:
            return
        
        self._running = True
        
        # 打开日志文件
        if self._config.file_output:
            await self._open_file()
        
        # 启动异步刷新任务
        if self._config.async_write:
            self._flush_task = asyncio.create_task(self._flush_loop())
        
        logger.info("Audit logger started")
    
    async def stop(self) -> None:
        """停止审计日志"""
        self._running = False
        
        # 停止刷新任务
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
            self._flush_task = None
        
        # 刷新缓冲区
        await self._flush()
        
        # 关闭文件
        if self._file_handle:
            self._file_handle.close()
            self._file_handle = None
        
        logger.info("Audit logger stopped")
    
    async def _open_file(self) -> None:
        """打开日志文件"""
        try:
            path = Path(self._config.file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # 检查文件大小，必要时轮转
            if path.exists():
                size_mb = path.stat().st_size / (1024 * 1024)
                if size_mb >= self._config.max_file_size_mb:
                    await self._rotate_file()
            
            self._file_handle = open(path, "a", encoding="utf-8")
            
        except Exception as e:
            logger.error(f"Failed to open audit log file: {e}")
    
    async def _rotate_file(self) -> None:
        """轮转日志文件"""
        try:
            path = Path(self._config.file_path)
            
            # 重命名现有文件
            for i in range(self._config.max_files - 1, 0, -1):
                old_path = path.with_suffix(f".{i}.log")
                new_path = path.with_suffix(f".{i + 1}.log")
                if old_path.exists():
                    if i + 1 >= self._config.max_files:
                        old_path.unlink()
                    else:
                        old_path.rename(new_path)
            
            # 重命名当前文件
            if path.exists():
                path.rename(path.with_suffix(".1.log"))
                
        except Exception as e:
            logger.error(f"Failed to rotate audit log: {e}")
    
    async def _flush_loop(self) -> None:
        """定期刷新缓冲区"""
        while self._running:
            try:
                await asyncio.sleep(self._config.flush_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Audit flush error: {e}")
    
    async def _flush(self) -> None:
        """刷新缓冲区到输出"""
        async with self._lock:
            if not self._buffer:
                return
            
            events = self._buffer.copy()
            self._buffer.clear()
        
        for event in events:
            await self._write_event(event)
        
        # 刷新文件
        if self._file_handle:
            self._file_handle.flush()
    
    async def _write_event(self, event: AuditEvent) -> None:
        """写入单个事件"""
        json_line = event.to_json()
        
        # 控制台输出
        if self._config.console_output:
            level = getattr(logging, event.level.value.upper(), logging.INFO)
            logger.log(level, f"[AUDIT] {json_line}")
        
        # 文件输出
        if self._file_handle:
            try:
                self._file_handle.write(json_line + "\n")
            except Exception as e:
                logger.error(f"Failed to write audit event: {e}")
    
    def _mask_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """遮蔽敏感数据"""
        result = {}
        for key, value in data.items():
            if any(s in key.lower() for s in self._config.mask_sensitive_fields):
                if isinstance(value, str) and len(value) > 4:
                    result[key] = value[:4] + "****"
                else:
                    result[key] = "****"
            elif isinstance(value, dict):
                result[key] = self._mask_sensitive(value)
            else:
                result[key] = value
        return result
    
    async def log(
        self,
        action: Union[AuditAction, str],
        level: AuditLevel = AuditLevel.INFO,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        request_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        resource: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        success: bool = True,
        result: Optional[Any] = None,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
        **metadata
    ) -> AuditEvent:
        """
        记录审计事件
        
        Args:
            action: 操作类型
            level: 审计级别
            user_id: 用户 ID
            user_role: 用户角色
            request_id: 请求 ID
            source_ip: 来源 IP
            resource: 资源标识
            params: 操作参数
            success: 是否成功
            result: 操作结果
            error: 错误信息
            duration_ms: 耗时（毫秒）
            **metadata: 额外元数据
            
        Returns:
            AuditEvent
        """
        if not self._config.enabled:
            return AuditEvent()
        
        # 检查级别
        level_order = [AuditLevel.DEBUG, AuditLevel.INFO, AuditLevel.WARNING, 
                       AuditLevel.ERROR, AuditLevel.CRITICAL]
        if level_order.index(level) < level_order.index(self._config.min_level):
            return AuditEvent()
        
        # 处理敏感数据
        if params:
            params = self._mask_sensitive(params)
        
        # 创建事件
        event = AuditEvent(
            action=action.value if isinstance(action, AuditAction) else action,
            level=level,
            user_id=user_id,
            user_role=user_role,
            request_id=request_id,
            source_ip=source_ip,
            resource=resource,
            params=params or {},
            success=success,
            result=result if not self._config.mask_sensitive_fields else None,
            error=error,
            duration_ms=duration_ms,
            metadata=metadata,
        )
        
        # 添加到缓冲区或直接写入
        if self._config.async_write:
            async with self._lock:
                self._buffer.append(event)
                if len(self._buffer) >= self._config.buffer_size:
                    await self._flush()
        else:
            await self._write_event(event)
        
        return event
    
    def audit_call(
        self,
        action: Union[AuditAction, str],
        resource_extractor: Optional[Callable] = None
    ):
        """
        装饰器：自动记录函数调用审计
        
        Args:
            action: 操作类型
            resource_extractor: 从参数提取资源标识的函数
        """
        def decorator(func: Callable):
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                error_msg = None
                result = None
                success = True
                
                try:
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    error_msg = str(e)
                    success = False
                    raise
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # 提取资源标识
                    resource = None
                    if resource_extractor:
                        try:
                            resource = resource_extractor(*args, **kwargs)
                        except Exception:
                            pass
                    
                    await self.log(
                        action=action,
                        level=AuditLevel.INFO if success else AuditLevel.ERROR,
                        resource=resource,
                        params=kwargs,
                        success=success,
                        error=error_msg,
                        duration_ms=duration_ms,
                    )
            
            return wrapper
        return decorator
