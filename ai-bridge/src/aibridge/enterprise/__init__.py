"""企业级特性 - 安全与治理模块

提供统一的认证、授权、审计、限流等企业级能力。

模块列表：
- auth: 认证中间件 (API Key, JWT)
- audit: 操作审计日志
- rate_limit: 请求限流
- health: 健康检查
- policy: 工具级权限策略 (PBAC)
- metering: 调用成本计量
- tracing: 分布式链路追踪

v5.0 新增：
- prometheus: Prometheus 指标导出
- metering_prometheus: Metering-Prometheus 适配
- audit_log: 审计日志持久化 (多后端支持)
- mcp_discovery: MCP Server 动态发现
"""

from .auth import (
    AuthMiddleware,
    AuthConfig,
    AuthProvider,
    AuthContext,
    Permission,
    Role,
    APIKeyAuth,
    JWTAuth,
)
from .audit import (
    AuditLogger,
    AuditConfig,
    AuditEvent,
    AuditLevel,
    AuditAction,
)
from .rate_limit import (
    RateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    RateLimitStrategy,
)
from .health import (
    HealthChecker,
    HealthStatus,
    HealthCheck,
)
from .policy import (
    PolicyEngine,
    PolicyMiddleware,
    ToolPolicy,
    PolicyStatement,
    PolicyEffect,
    PolicyAction,
    PolicyCondition,
    PolicyEvaluationResult,
    BUILTIN_POLICIES,
    get_builtin_policy,
    list_builtin_policies,
)
from .metering import (
    MeteringCollector,
    MeteringConfig,
    UsageRecord,
    UsageAggregation,
    MeteringDimension,
    QuotaManager,
    QuotaConfig,
    QuotaExceeded,
    BUILTIN_QUOTAS,
    get_builtin_quota,
    list_builtin_quotas,
)
from .tracing import (
    Tracer,
    TracerConfig,
    Span,
    SpanContext,
    SpanKind,
    SpanStatus,
    SpanEvent,
    SpanLink,
    SpanExporter,
    ConsoleExporter,
    InMemoryExporter,
    OTLPExporter,
    TracingMiddleware,
    get_tracer,
    set_tracer,
)

# v5.0: Prometheus 指标
from .prometheus import (
    PrometheusRegistry,
    CounterMetric,
    GaugeMetric,
    HistogramMetric,
    MetricLabels,
    MetricType,
    AIBridgeMetrics,
    MetricsMiddleware,
    MetricsExporter,
    get_registry,
    set_registry,
)
from .metering_prometheus import (
    MeteringPrometheusAdapter,
    MeteringHook,
    create_metering_prometheus_adapter,
)

# v5.0: Audit Log 持久化
from .audit_log import (
    AuditAction as AuditActionV2,
    AuditLevel as AuditLevelV2,
    AuditEntry,
    AuditQuery,
    AuditQueryResult,
    AuditStorageBackend,
    MemoryAuditStorage,
    FileAuditStorage,
    SQLiteAuditStorage,
    AuditLogger as AuditLoggerV2,
    create_memory_audit_logger,
    create_file_audit_logger,
    create_sqlite_audit_logger,
)

# v5.0: MCP Server 动态发现
from .mcp_discovery import (
    ServerStatus,
    TransportType,
    MCPServerConfig,
    DiscoverySource,
    ConfigFileWatcher,
    MCPServerDiscovery,
    MCPConnectionPool,
    discover_from_claude_desktop,
    discover_from_env,
)

__all__ = [
    # Auth
    "AuthMiddleware",
    "AuthConfig",
    "AuthProvider",
    "AuthContext",
    "Permission",
    "Role",
    "APIKeyAuth",
    "JWTAuth",
    # Audit
    "AuditLogger",
    "AuditConfig",
    "AuditEvent",
    "AuditLevel",
    "AuditAction",
    # Rate Limit
    "RateLimiter",
    "RateLimitConfig",
    "RateLimitExceeded",
    "RateLimitStrategy",
    # Health
    "HealthChecker",
    "HealthStatus",
    "HealthCheck",
    # Policy (v4.0)
    "PolicyEngine",
    "PolicyMiddleware",
    "ToolPolicy",
    "PolicyStatement",
    "PolicyEffect",
    "PolicyAction",
    "PolicyCondition",
    "PolicyEvaluationResult",
    "BUILTIN_POLICIES",
    "get_builtin_policy",
    "list_builtin_policies",
    # Metering (v4.0)
    "MeteringCollector",
    "MeteringConfig",
    "UsageRecord",
    "UsageAggregation",
    "MeteringDimension",
    "QuotaManager",
    "QuotaConfig",
    "QuotaExceeded",
    "BUILTIN_QUOTAS",
    "get_builtin_quota",
    "list_builtin_quotas",
    # Tracing (v4.0)
    "Tracer",
    "TracerConfig",
    "Span",
    "SpanContext",
    "SpanKind",
    "SpanStatus",
    "SpanEvent",
    "SpanLink",
    "SpanExporter",
    "ConsoleExporter",
    "InMemoryExporter",
    "OTLPExporter",
    "TracingMiddleware",
    "get_tracer",
    "set_tracer",
    # Prometheus (v5.0)
    "PrometheusRegistry",
    "CounterMetric",
    "GaugeMetric",
    "HistogramMetric",
    "MetricLabels",
    "MetricType",
    "AIBridgeMetrics",
    "MetricsMiddleware",
    "MetricsExporter",
    "get_registry",
    "set_registry",
    # Metering-Prometheus (v5.0)
    "MeteringPrometheusAdapter",
    "MeteringHook",
    "create_metering_prometheus_adapter",
    # Audit Log Persistence (v5.0)
    "AuditActionV2",
    "AuditLevelV2",
    "AuditEntry",
    "AuditQuery",
    "AuditQueryResult",
    "AuditStorageBackend",
    "MemoryAuditStorage",
    "FileAuditStorage",
    "SQLiteAuditStorage",
    "AuditLoggerV2",
    "create_memory_audit_logger",
    "create_file_audit_logger",
    "create_sqlite_audit_logger",
    # MCP Server Discovery (v5.0)
    "ServerStatus",
    "TransportType",
    "MCPServerConfig",
    "DiscoverySource",
    "ConfigFileWatcher",
    "MCPServerDiscovery",
    "MCPConnectionPool",
    "discover_from_claude_desktop",
    "discover_from_env",
]
