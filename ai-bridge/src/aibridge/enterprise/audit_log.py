"""
Audit Log 持久化

提供审计日志的持久化存储与检索：
- 多存储后端支持（内存、文件、SQLite）
- 结构化日志记录
- 日志查询与过滤
- 日志轮转与清理
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Protocol, AsyncIterator
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
import asyncio
import json
import logging
import hashlib

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """获取当前 UTC 时间"""
    return datetime.now(timezone.utc)


class AuditAction(str, Enum):
    """审计动作类型"""
    # 认证相关
    LOGIN = "auth.login"
    LOGOUT = "auth.logout"
    TOKEN_REFRESH = "auth.token_refresh"
    AUTH_FAILED = "auth.failed"
    
    # 访问相关
    RESOURCE_ACCESS = "access.resource"
    TOOL_CALL = "access.tool_call"
    API_CALL = "access.api_call"
    
    # 管理相关
    CONFIG_CHANGE = "admin.config_change"
    USER_CREATE = "admin.user_create"
    USER_UPDATE = "admin.user_update"
    USER_DELETE = "admin.user_delete"
    POLICY_CHANGE = "admin.policy_change"
    
    # Agent 相关
    AGENT_REGISTER = "agent.register"
    AGENT_UNREGISTER = "agent.unregister"
    TASK_START = "agent.task_start"
    TASK_COMPLETE = "agent.task_complete"
    TASK_FAIL = "agent.task_fail"
    
    # 安全相关
    PERMISSION_DENIED = "security.permission_denied"
    RATE_LIMITED = "security.rate_limited"
    SUSPICIOUS_ACTIVITY = "security.suspicious"


class AuditLevel(str, Enum):
    """审计级别"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEntry:
    """审计日志条目"""
    # 必填字段
    action: AuditAction
    actor: str  # 执行者（用户ID、Agent ID 等）
    
    # 可选字段
    resource: Optional[str] = None  # 被操作资源
    level: AuditLevel = AuditLevel.INFO
    success: bool = True
    message: str = ""
    
    # 上下文
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    request_id: Optional[str] = None
    
    # 详细数据
    details: Dict[str, Any] = field(default_factory=dict)
    
    # 自动生成
    entry_id: str = ""
    timestamp: datetime = field(default_factory=_utcnow)
    
    def __post_init__(self):
        if not self.entry_id:
            # 生成唯一 ID
            content = f"{self.timestamp.isoformat()}-{self.action}-{self.actor}"
            self.entry_id = hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "entry_id": self.entry_id,
            "action": self.action.value,
            "actor": self.actor,
            "resource": self.resource,
            "level": self.level.value,
            "success": self.success,
            "message": self.message,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
            "request_id": self.request_id,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """从字典创建"""
        return cls(
            entry_id=data.get("entry_id", ""),
            action=AuditAction(data["action"]),
            actor=data["actor"],
            resource=data.get("resource"),
            level=AuditLevel(data.get("level", "info")),
            success=data.get("success", True),
            message=data.get("message", ""),
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            session_id=data.get("session_id"),
            request_id=data.get("request_id"),
            details=data.get("details", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]),
        )
    
    def to_json(self) -> str:
        """转换为 JSON"""
        return json.dumps(self.to_dict())


@dataclass
class AuditQuery:
    """审计查询条件"""
    # 时间范围
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # 过滤条件
    actions: Optional[List[AuditAction]] = None
    actors: Optional[List[str]] = None
    resources: Optional[List[str]] = None
    levels: Optional[List[AuditLevel]] = None
    success: Optional[bool] = None
    
    # 分页
    limit: int = 100
    offset: int = 0
    
    # 排序
    order_desc: bool = True  # 默认时间倒序


@dataclass
class AuditQueryResult:
    """审计查询结果"""
    entries: List[AuditEntry]
    total_count: int
    has_more: bool


class AuditStorageBackend(Protocol):
    """审计存储后端协议"""
    
    async def write(self, entry: AuditEntry) -> bool:
        """写入日志"""
        ...
    
    async def query(self, query: AuditQuery) -> AuditQueryResult:
        """查询日志"""
        ...
    
    async def count(self, query: AuditQuery) -> int:
        """统计数量"""
        ...
    
    async def delete_before(self, before: datetime) -> int:
        """删除指定时间之前的日志"""
        ...
    
    async def close(self) -> None:
        """关闭存储"""
        ...


class MemoryAuditStorage:
    """内存审计存储（适合测试和开发）"""
    
    def __init__(self, max_entries: int = 10000):
        self._entries: List[AuditEntry] = []
        self._max_entries = max_entries
        self._lock = asyncio.Lock()
    
    async def write(self, entry: AuditEntry) -> bool:
        async with self._lock:
            self._entries.append(entry)
            # 超过最大条数时删除旧的
            if len(self._entries) > self._max_entries:
                self._entries = self._entries[-self._max_entries:]
        return True
    
    async def query(self, query: AuditQuery) -> AuditQueryResult:
        async with self._lock:
            filtered = self._filter_entries(query)
            
            # 排序
            sorted_entries = sorted(
                filtered,
                key=lambda e: e.timestamp,
                reverse=query.order_desc
            )
            
            # 分页
            total = len(sorted_entries)
            start = query.offset
            end = query.offset + query.limit
            paged = sorted_entries[start:end]
            
            return AuditQueryResult(
                entries=paged,
                total_count=total,
                has_more=end < total,
            )
    
    async def count(self, query: AuditQuery) -> int:
        async with self._lock:
            return len(self._filter_entries(query))
    
    async def delete_before(self, before: datetime) -> int:
        async with self._lock:
            original_count = len(self._entries)
            self._entries = [e for e in self._entries if e.timestamp >= before]
            return original_count - len(self._entries)
    
    async def close(self) -> None:
        pass
    
    def _filter_entries(self, query: AuditQuery) -> List[AuditEntry]:
        """应用过滤条件"""
        entries = self._entries
        
        if query.start_time:
            entries = [e for e in entries if e.timestamp >= query.start_time]
        if query.end_time:
            entries = [e for e in entries if e.timestamp <= query.end_time]
        if query.actions:
            entries = [e for e in entries if e.action in query.actions]
        if query.actors:
            entries = [e for e in entries if e.actor in query.actors]
        if query.resources:
            entries = [e for e in entries if e.resource in query.resources]
        if query.levels:
            entries = [e for e in entries if e.level in query.levels]
        if query.success is not None:
            entries = [e for e in entries if e.success == query.success]
        
        return entries


class FileAuditStorage:
    """文件审计存储（JSON Lines 格式）"""
    
    def __init__(
        self,
        log_dir: str,
        file_prefix: str = "audit",
        max_file_size_mb: int = 100,
        max_files: int = 10,
    ):
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._file_prefix = file_prefix
        self._max_file_size = max_file_size_mb * 1024 * 1024
        self._max_files = max_files
        self._current_file: Optional[Path] = None
        self._lock = asyncio.Lock()
    
    async def write(self, entry: AuditEntry) -> bool:
        async with self._lock:
            file_path = self._get_current_file()
            try:
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(entry.to_json() + "\n")
                
                # 检查是否需要轮转
                await self._rotate_if_needed()
                return True
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
                return False
    
    async def query(self, query: AuditQuery) -> AuditQueryResult:
        entries = []
        async for entry in self._read_all_entries():
            if self._matches_query(entry, query):
                entries.append(entry)
        
        # 排序
        entries.sort(key=lambda e: e.timestamp, reverse=query.order_desc)
        
        # 分页
        total = len(entries)
        start = query.offset
        end = query.offset + query.limit
        paged = entries[start:end]
        
        return AuditQueryResult(
            entries=paged,
            total_count=total,
            has_more=end < total,
        )
    
    async def count(self, query: AuditQuery) -> int:
        count = 0
        async for entry in self._read_all_entries():
            if self._matches_query(entry, query):
                count += 1
        return count
    
    async def delete_before(self, before: datetime) -> int:
        # 对于文件存储，只删除整个旧文件
        deleted = 0
        for file_path in self._get_log_files():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    first_line = f.readline()
                    if first_line:
                        entry = AuditEntry.from_dict(json.loads(first_line))
                        if entry.timestamp < before:
                            file_path.unlink()
                            deleted += 1
            except Exception:
                pass
        return deleted
    
    async def close(self) -> None:
        pass
    
    def _get_current_file(self) -> Path:
        """获取当前写入文件"""
        if self._current_file and self._current_file.exists():
            return self._current_file
        
        timestamp = _utcnow().strftime("%Y%m%d_%H%M%S")
        self._current_file = self._log_dir / f"{self._file_prefix}_{timestamp}.jsonl"
        return self._current_file
    
    async def _rotate_if_needed(self) -> None:
        """检查并执行日志轮转"""
        if not self._current_file or not self._current_file.exists():
            return
        
        if self._current_file.stat().st_size >= self._max_file_size:
            self._current_file = None
            await self._cleanup_old_files()
    
    async def _cleanup_old_files(self) -> None:
        """清理旧文件"""
        files = sorted(self._get_log_files(), key=lambda f: f.stat().st_mtime)
        while len(files) > self._max_files:
            oldest = files.pop(0)
            oldest.unlink()
    
    def _get_log_files(self) -> List[Path]:
        """获取所有日志文件"""
        return list(self._log_dir.glob(f"{self._file_prefix}_*.jsonl"))
    
    async def _read_all_entries(self) -> AsyncIterator[AuditEntry]:
        """读取所有条目"""
        for file_path in self._get_log_files():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                yield AuditEntry.from_dict(json.loads(line))
                            except Exception:
                                pass
            except Exception:
                pass
    
    def _matches_query(self, entry: AuditEntry, query: AuditQuery) -> bool:
        """检查条目是否匹配查询"""
        if query.start_time and entry.timestamp < query.start_time:
            return False
        if query.end_time and entry.timestamp > query.end_time:
            return False
        if query.actions and entry.action not in query.actions:
            return False
        if query.actors and entry.actor not in query.actors:
            return False
        if query.resources and entry.resource not in query.resources:
            return False
        if query.levels and entry.level not in query.levels:
            return False
        if query.success is not None and entry.success != query.success:
            return False
        return True


class SQLiteAuditStorage:
    """SQLite 审计存储"""
    
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn = None
        self._lock = asyncio.Lock()
    
    async def _ensure_connection(self):
        """确保数据库连接"""
        if self._conn is None:
            import aiosqlite
            self._conn = await aiosqlite.connect(self._db_path)
            await self._create_tables()
    
    async def _create_tables(self):
        """创建表"""
        await self._conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                entry_id TEXT PRIMARY KEY,
                action TEXT NOT NULL,
                actor TEXT NOT NULL,
                resource TEXT,
                level TEXT NOT NULL,
                success INTEGER NOT NULL,
                message TEXT,
                ip_address TEXT,
                user_agent TEXT,
                session_id TEXT,
                request_id TEXT,
                details TEXT,
                timestamp TEXT NOT NULL
            )
        """)
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)"
        )
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_logs(actor)"
        )
        await self._conn.commit()
    
    async def write(self, entry: AuditEntry) -> bool:
        async with self._lock:
            await self._ensure_connection()
            try:
                await self._conn.execute("""
                    INSERT INTO audit_logs 
                    (entry_id, action, actor, resource, level, success, message,
                     ip_address, user_agent, session_id, request_id, details, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.entry_id,
                    entry.action.value,
                    entry.actor,
                    entry.resource,
                    entry.level.value,
                    1 if entry.success else 0,
                    entry.message,
                    entry.ip_address,
                    entry.user_agent,
                    entry.session_id,
                    entry.request_id,
                    json.dumps(entry.details),
                    entry.timestamp.isoformat(),
                ))
                await self._conn.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to write audit log: {e}")
                return False
    
    async def query(self, query: AuditQuery) -> AuditQueryResult:
        async with self._lock:
            await self._ensure_connection()
            
            where_clauses = []
            params = []
            
            if query.start_time:
                where_clauses.append("timestamp >= ?")
                params.append(query.start_time.isoformat())
            if query.end_time:
                where_clauses.append("timestamp <= ?")
                params.append(query.end_time.isoformat())
            if query.actions:
                placeholders = ",".join("?" * len(query.actions))
                where_clauses.append(f"action IN ({placeholders})")
                params.extend(a.value for a in query.actions)
            if query.actors:
                placeholders = ",".join("?" * len(query.actors))
                where_clauses.append(f"actor IN ({placeholders})")
                params.extend(query.actors)
            if query.resources:
                placeholders = ",".join("?" * len(query.resources))
                where_clauses.append(f"resource IN ({placeholders})")
                params.extend(query.resources)
            if query.levels:
                placeholders = ",".join("?" * len(query.levels))
                where_clauses.append(f"level IN ({placeholders})")
                params.extend(l.value for l in query.levels)
            if query.success is not None:
                where_clauses.append("success = ?")
                params.append(1 if query.success else 0)
            
            where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
            order = "DESC" if query.order_desc else "ASC"
            
            # 获取总数
            count_sql = f"SELECT COUNT(*) FROM audit_logs WHERE {where_sql}"
            cursor = await self._conn.execute(count_sql, params)
            total_count = (await cursor.fetchone())[0]
            
            # 获取数据
            data_sql = f"""
                SELECT * FROM audit_logs 
                WHERE {where_sql} 
                ORDER BY timestamp {order}
                LIMIT ? OFFSET ?
            """
            cursor = await self._conn.execute(
                data_sql, params + [query.limit, query.offset]
            )
            rows = await cursor.fetchall()
            
            entries = [self._row_to_entry(row) for row in rows]
            
            return AuditQueryResult(
                entries=entries,
                total_count=total_count,
                has_more=query.offset + len(entries) < total_count,
            )
    
    async def count(self, query: AuditQuery) -> int:
        result = await self.query(AuditQuery(
            start_time=query.start_time,
            end_time=query.end_time,
            actions=query.actions,
            actors=query.actors,
            resources=query.resources,
            levels=query.levels,
            success=query.success,
            limit=1,
        ))
        return result.total_count
    
    async def delete_before(self, before: datetime) -> int:
        async with self._lock:
            await self._ensure_connection()
            cursor = await self._conn.execute(
                "DELETE FROM audit_logs WHERE timestamp < ?",
                (before.isoformat(),)
            )
            await self._conn.commit()
            return cursor.rowcount
    
    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
    
    def _row_to_entry(self, row) -> AuditEntry:
        """将数据库行转换为 AuditEntry"""
        return AuditEntry(
            entry_id=row[0],
            action=AuditAction(row[1]),
            actor=row[2],
            resource=row[3],
            level=AuditLevel(row[4]),
            success=bool(row[5]),
            message=row[6] or "",
            ip_address=row[7],
            user_agent=row[8],
            session_id=row[9],
            request_id=row[10],
            details=json.loads(row[11]) if row[11] else {},
            timestamp=datetime.fromisoformat(row[12]),
        )


class AuditLogger:
    """审计日志记录器
    
    提供便捷的审计日志记录接口
    """
    
    def __init__(
        self,
        storage: AuditStorageBackend,
        retention_days: int = 90,
        cleanup_interval_hours: int = 24,
    ):
        self._storage = storage
        self._retention_days = retention_days
        self._cleanup_interval = cleanup_interval_hours * 3600
        self._running = False
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动日志记录器"""
        if self._running:
            return
        
        self._running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        logger.info("AuditLogger started")
    
    async def stop(self) -> None:
        """停止日志记录器"""
        self._running = False
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        await self._storage.close()
        logger.info("AuditLogger stopped")
    
    async def log(self, entry: AuditEntry) -> bool:
        """记录审计日志"""
        return await self._storage.write(entry)
    
    async def log_action(
        self,
        action: AuditAction,
        actor: str,
        resource: str = None,
        success: bool = True,
        message: str = "",
        level: AuditLevel = None,
        **kwargs,
    ) -> bool:
        """便捷的日志记录方法"""
        if level is None:
            level = AuditLevel.INFO if success else AuditLevel.WARNING
        
        entry = AuditEntry(
            action=action,
            actor=actor,
            resource=resource,
            success=success,
            message=message,
            level=level,
            ip_address=kwargs.get("ip_address"),
            user_agent=kwargs.get("user_agent"),
            session_id=kwargs.get("session_id"),
            request_id=kwargs.get("request_id"),
            details=kwargs.get("details", {}),
        )
        return await self.log(entry)
    
    async def query(self, query: AuditQuery) -> AuditQueryResult:
        """查询审计日志"""
        return await self._storage.query(query)
    
    async def count(self, query: AuditQuery) -> int:
        """统计数量"""
        return await self._storage.count(query)
    
    async def get_recent(
        self,
        limit: int = 100,
        actions: List[AuditAction] = None,
    ) -> List[AuditEntry]:
        """获取最近的日志"""
        result = await self.query(AuditQuery(
            actions=actions,
            limit=limit,
            order_desc=True,
        ))
        return result.entries
    
    async def get_by_actor(
        self,
        actor: str,
        limit: int = 100,
        start_time: datetime = None,
    ) -> List[AuditEntry]:
        """获取指定执行者的日志"""
        result = await self.query(AuditQuery(
            actors=[actor],
            start_time=start_time,
            limit=limit,
            order_desc=True,
        ))
        return result.entries
    
    async def get_failures(
        self,
        limit: int = 100,
        start_time: datetime = None,
    ) -> List[AuditEntry]:
        """获取失败的日志"""
        result = await self.query(AuditQuery(
            success=False,
            start_time=start_time,
            limit=limit,
            order_desc=True,
        ))
        return result.entries
    
    async def get_security_events(
        self,
        limit: int = 100,
        start_time: datetime = None,
    ) -> List[AuditEntry]:
        """获取安全相关事件"""
        security_actions = [
            AuditAction.PERMISSION_DENIED,
            AuditAction.RATE_LIMITED,
            AuditAction.SUSPICIOUS_ACTIVITY,
            AuditAction.AUTH_FAILED,
        ]
        result = await self.query(AuditQuery(
            actions=security_actions,
            start_time=start_time,
            limit=limit,
            order_desc=True,
        ))
        return result.entries
    
    async def _cleanup_loop(self) -> None:
        """清理循环"""
        while self._running:
            await asyncio.sleep(self._cleanup_interval)
            await self._cleanup_old_logs()
    
    async def _cleanup_old_logs(self) -> None:
        """清理旧日志"""
        cutoff = _utcnow() - timedelta(days=self._retention_days)
        deleted = await self._storage.delete_before(cutoff)
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old audit logs")


# ========== 便捷工厂函数 ==========

def create_memory_audit_logger(max_entries: int = 10000) -> AuditLogger:
    """创建内存审计日志记录器"""
    storage = MemoryAuditStorage(max_entries)
    return AuditLogger(storage)


def create_file_audit_logger(
    log_dir: str,
    file_prefix: str = "audit",
    max_file_size_mb: int = 100,
    retention_days: int = 90,
) -> AuditLogger:
    """创建文件审计日志记录器"""
    storage = FileAuditStorage(log_dir, file_prefix, max_file_size_mb)
    return AuditLogger(storage, retention_days)


def create_sqlite_audit_logger(
    db_path: str,
    retention_days: int = 90,
) -> AuditLogger:
    """创建 SQLite 审计日志记录器"""
    storage = SQLiteAuditStorage(db_path)
    return AuditLogger(storage, retention_days)
