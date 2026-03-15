"""
企业级特性 - 安全与治理模块

提供统一的认证、授权、审计、限流等企业级能力。

模块列表：
- auth: 认证中间件 (API Key, JWT)
- audit: 操作审计日志
- rate_limit: 请求限流
- health: 健康检查
- policy: 工具级权限策略 (PBAC)
- metering: 调用成本计量
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
]
