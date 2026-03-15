"""
企业级特性单元测试

测试认证、审计、限流、健康检查等企业级特性。
"""

import asyncio
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch

# 认证模块测试
from aibridge.enterprise.auth import (
    AuthMiddleware,
    AuthConfig,
    AuthContext,
    Permission,
    Role,
    ROLES,
    APIKeyAuth,
    JWTAuth,
)


class TestPermission:
    """权限测试"""
    
    def test_role_has_permission(self):
        """测试角色权限检查"""
        admin_role = ROLES["admin"]
        assert admin_role.has_permission(Permission.ALL)
        assert admin_role.has_permission(Permission.READ)
        assert admin_role.has_permission(Permission.EXECUTE_TOOLS)
    
    def test_role_parent_permission(self):
        """测试父权限包含子权限"""
        role = Role(
            name="test",
            permissions={Permission.READ}
        )
        # READ 包含 READ_TOOLS
        assert role.has_permission(Permission.READ)
    
    def test_viewer_role_limited(self):
        """测试 viewer 角色权限有限"""
        viewer_role = ROLES["viewer"]
        assert viewer_role.has_permission(Permission.READ)
        assert not viewer_role.has_permission(Permission.EXECUTE)
        assert not viewer_role.has_permission(Permission.ADMIN)


class TestAPIKeyAuth:
    """API Key 认证测试"""
    
    @pytest.fixture
    def config(self):
        return AuthConfig(
            enabled=True,
            api_keys={
                "sk-admin-key": "admin",
                "sk-viewer-key": "viewer",
            }
        )
    
    @pytest.mark.asyncio
    async def test_valid_api_key(self, config):
        """测试有效 API Key"""
        auth = APIKeyAuth(config)
        context = await auth.authenticate({"api_key": "sk-admin-key"})
        
        assert context is not None
        assert context.authenticated
        assert context.role.name == "admin"
    
    @pytest.mark.asyncio
    async def test_invalid_api_key(self, config):
        """测试无效 API Key"""
        auth = APIKeyAuth(config)
        context = await auth.authenticate({"api_key": "invalid-key"})
        
        assert context is None
    
    @pytest.mark.asyncio
    async def test_x_api_key_header(self, config):
        """测试 x-api-key 头"""
        auth = APIKeyAuth(config)
        context = await auth.authenticate({"x-api-key": "sk-viewer-key"})
        
        assert context is not None
        assert context.role.name == "viewer"


class TestJWTAuth:
    """JWT 认证测试"""
    
    @pytest.fixture
    def config(self):
        return AuthConfig(
            enabled=True,
            jwt_secret="test-secret",
            jwt_expiry=3600,
        )
    
    @pytest.mark.asyncio
    async def test_create_and_verify_token(self, config):
        """测试创建和验证 Token"""
        auth = JWTAuth(config)
        
        # 创建 Token
        token = auth.create_token(user_id="user123", role="operator")
        assert token
        
        # 验证 Token
        context = await auth.authenticate({"token": token})
        
        assert context is not None
        assert context.authenticated
        assert context.user_id == "user123"
        assert context.role.name == "operator"
    
    @pytest.mark.asyncio
    async def test_bearer_prefix(self, config):
        """测试 Bearer 前缀"""
        auth = JWTAuth(config)
        token = auth.create_token(user_id="user123")
        
        context = await auth.authenticate({"authorization": f"Bearer {token}"})
        assert context.authenticated
    
    @pytest.mark.asyncio
    async def test_expired_token(self, config):
        """测试过期 Token"""
        auth = JWTAuth(config)
        token = auth.create_token(user_id="user123", expiry=-100)  # 已过期
        
        context = await auth.authenticate({"token": token})
        assert context is None


class TestAuthMiddleware:
    """认证中间件测试"""
    
    @pytest.fixture
    def config(self):
        return AuthConfig(
            enabled=True,
            api_keys={"sk-test": "admin"},
            jwt_secret="secret",
        )
    
    @pytest.mark.asyncio
    async def test_middleware_api_key(self, config):
        """测试中间件 API Key 认证"""
        middleware = AuthMiddleware(config)
        context = await middleware.authenticate({"api_key": "sk-test"})
        
        assert context.authenticated
        assert middleware.authorize(context, Permission.ADMIN)
    
    @pytest.mark.asyncio
    async def test_middleware_disabled(self, config):
        """测试禁用认证"""
        config.enabled = False
        middleware = AuthMiddleware(config)
        
        context = await middleware.authenticate({})
        assert context.authenticated
    
    @pytest.mark.asyncio
    async def test_authorization_denied(self, config):
        """测试授权拒绝"""
        config.api_keys = {"sk-viewer": "viewer"}
        middleware = AuthMiddleware(config)
        
        context = await middleware.authenticate({"api_key": "sk-viewer"})
        assert context.authenticated
        assert not middleware.authorize(context, Permission.ADMIN)


# 审计日志测试
from aibridge.enterprise.audit import (
    AuditLogger,
    AuditConfig,
    AuditEvent,
    AuditLevel,
    AuditAction,
)


class TestAuditEvent:
    """审计事件测试"""
    
    def test_event_creation(self):
        """测试事件创建"""
        event = AuditEvent(
            action="test.action",
            user_id="user123",
        )
        
        assert event.event_id
        assert event.timestamp > 0
        assert event.action == "test.action"
    
    def test_event_to_dict(self):
        """测试转换为字典"""
        event = AuditEvent(
            action=AuditAction.TOOL_CALL.value,
            level=AuditLevel.INFO,
            user_id="user123",
        )
        
        d = event.to_dict()
        assert d["action"] == "tool.call"
        assert d["level"] == "info"
        assert "timestamp_iso" in d
    
    def test_event_to_json(self):
        """测试转换为 JSON"""
        event = AuditEvent(action="test")
        json_str = event.to_json()
        
        assert "test" in json_str
        assert "event_id" in json_str


class TestAuditLogger:
    """审计日志记录器测试"""
    
    @pytest.fixture
    def config(self):
        return AuditConfig(
            enabled=True,
            console_output=False,
            file_output=False,
            async_write=False,
        )
    
    @pytest.mark.asyncio
    async def test_log_event(self, config):
        """测试记录事件"""
        logger = AuditLogger(config)
        
        event = await logger.log(
            action=AuditAction.TOOL_CALL,
            user_id="user123",
            resource="browser/navigate",
            success=True,
        )
        
        assert event.action == "tool.call"
        assert event.user_id == "user123"
    
    @pytest.mark.asyncio
    async def test_mask_sensitive_data(self, config):
        """测试敏感数据遮蔽"""
        logger = AuditLogger(config)
        
        event = await logger.log(
            action="test",
            params={
                "username": "admin",
                "password": "secret123",
                "api_key": "sk-1234567890",
            }
        )
        
        assert event.params["username"] == "admin"
        assert "****" in event.params["password"]
        assert "****" in event.params["api_key"]
    
    @pytest.mark.asyncio
    async def test_min_level_filtering(self, config):
        """测试最小级别过滤"""
        config.min_level = AuditLevel.WARNING
        logger = AuditLogger(config)
        
        # INFO 级别应被过滤
        event = await logger.log(action="test", level=AuditLevel.INFO)
        assert event.event_id  # 返回空事件
        
        # WARNING 级别应记录
        event = await logger.log(action="test", level=AuditLevel.WARNING)
        assert event.action == "test"
    
    @pytest.mark.asyncio
    async def test_disabled_logger(self, config):
        """测试禁用日志"""
        config.enabled = False
        logger = AuditLogger(config)
        
        event = await logger.log(action="test")
        # 应返回空事件
        assert not event.action


# 限流测试
from aibridge.enterprise.rate_limit import (
    RateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    RateLimitStrategy,
)


class TestRateLimiter:
    """限流器测试"""
    
    @pytest.fixture
    def config(self):
        return RateLimitConfig(
            enabled=True,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            requests_per_minute=10,
        )
    
    @pytest.mark.asyncio
    async def test_allow_within_limit(self, config):
        """测试限制内允许"""
        limiter = RateLimiter(config)
        
        for _ in range(5):
            info = await limiter.check("user:123")
            assert info.allowed
    
    @pytest.mark.asyncio
    async def test_exceed_limit(self, config):
        """测试超出限制"""
        config.requests_per_minute = 3
        limiter = RateLimiter(config)
        
        # 前 3 个请求应允许
        for _ in range(3):
            await limiter.check("user:123")
        
        # 第 4 个应被拒绝
        with pytest.raises(RateLimitExceeded) as exc_info:
            await limiter.check("user:123")
        
        assert exc_info.value.limit == 3
        assert exc_info.value.retry_after is not None
    
    @pytest.mark.asyncio
    async def test_whitelist(self, config):
        """测试白名单"""
        config.requests_per_minute = 1
        config.whitelist = ["vip:admin"]
        limiter = RateLimiter(config)
        
        # 白名单用户不受限
        for _ in range(10):
            info = await limiter.check("vip:admin")
            assert info.allowed
    
    @pytest.mark.asyncio
    async def test_disabled(self, config):
        """测试禁用限流"""
        config.enabled = False
        limiter = RateLimiter(config)
        
        for _ in range(100):
            info = await limiter.check("user:123")
            assert info.allowed
    
    @pytest.mark.asyncio
    async def test_reset(self, config):
        """测试重置计数"""
        config.requests_per_minute = 2
        limiter = RateLimiter(config)
        
        # 用完限制
        await limiter.check("user:123")
        await limiter.check("user:123")
        
        # 重置
        await limiter.reset("user:123")
        
        # 应可以继续
        info = await limiter.check("user:123")
        assert info.allowed
    
    @pytest.mark.asyncio
    async def test_token_bucket(self, config):
        """测试令牌桶策略"""
        config.strategy = RateLimitStrategy.TOKEN_BUCKET
        config.bucket_capacity = 5
        config.refill_rate = 1.0
        limiter = RateLimiter(config)
        
        # 快速消耗 5 个令牌
        for _ in range(5):
            info = await limiter.check("user:123")
            assert info.allowed
        
        # 第 6 个应被拒绝
        with pytest.raises(RateLimitExceeded):
            await limiter.check("user:123")


# 健康检查测试
from aibridge.enterprise.health import (
    HealthChecker,
    HealthStatus,
    HealthCheck,
)


class TestHealthCheck:
    """健康检查测试"""
    
    def test_check_creation(self):
        """测试检查结果创建"""
        check = HealthCheck(
            name="test",
            status=HealthStatus.HEALTHY,
            message="All good",
        )
        
        assert check.name == "test"
        assert check.status == HealthStatus.HEALTHY
    
    def test_check_to_dict(self):
        """测试转换为字典"""
        check = HealthCheck(
            name="test",
            status=HealthStatus.DEGRADED,
            latency_ms=150.5,
        )
        
        d = check.to_dict()
        assert d["status"] == "degraded"
        assert d["latency_ms"] == 150.5


class TestHealthChecker:
    """健康检查器测试"""
    
    @pytest.mark.asyncio
    async def test_empty_checker(self):
        """测试无检查项"""
        checker = HealthChecker(version="1.0.0")
        report = await checker.check()
        
        assert report.status == HealthStatus.HEALTHY
        assert report.version == "1.0.0"
        assert len(report.checks) == 0
    
    @pytest.mark.asyncio
    async def test_healthy_check(self):
        """测试健康检查"""
        checker = HealthChecker()
        
        def healthy_check():
            return HealthCheck(
                name="test",
                status=HealthStatus.HEALTHY,
            )
        
        checker.register_check("test", healthy_check)
        report = await checker.check()
        
        assert report.status == HealthStatus.HEALTHY
        assert len(report.checks) == 1
    
    @pytest.mark.asyncio
    async def test_unhealthy_check(self):
        """测试不健康检查"""
        checker = HealthChecker()
        
        def unhealthy_check():
            return HealthCheck(
                name="db",
                status=HealthStatus.UNHEALTHY,
                message="Connection failed",
            )
        
        checker.register_check("db", unhealthy_check)
        report = await checker.check()
        
        assert report.status == HealthStatus.UNHEALTHY
    
    @pytest.mark.asyncio
    async def test_mixed_status(self):
        """测试混合状态"""
        checker = HealthChecker()
        
        checker.register_check("healthy", lambda: HealthCheck(
            name="healthy", status=HealthStatus.HEALTHY
        ))
        checker.register_check("degraded", lambda: HealthCheck(
            name="degraded", status=HealthStatus.DEGRADED
        ))
        
        report = await checker.check()
        assert report.status == HealthStatus.DEGRADED
    
    @pytest.mark.asyncio
    async def test_async_check(self):
        """测试异步检查"""
        checker = HealthChecker()
        
        async def async_check():
            await asyncio.sleep(0.01)
            return HealthCheck(
                name="async",
                status=HealthStatus.HEALTHY,
            )
        
        checker.register_check("async", async_check)
        report = await checker.check()
        
        assert report.status == HealthStatus.HEALTHY
        assert report.checks[0].latency_ms is not None
    
    @pytest.mark.asyncio
    async def test_check_timeout(self):
        """测试检查超时"""
        checker = HealthChecker(timeout=0.1)
        
        async def slow_check():
            await asyncio.sleep(1.0)
            return HealthCheck(name="slow", status=HealthStatus.HEALTHY)
        
        checker.register_check("slow", slow_check)
        report = await checker.check()
        
        assert report.status == HealthStatus.UNHEALTHY
        assert "timed out" in report.checks[0].message
    
    @pytest.mark.asyncio
    async def test_check_exception(self):
        """测试检查异常"""
        checker = HealthChecker()
        
        def error_check():
            raise RuntimeError("Check failed")
        
        checker.register_check("error", error_check)
        report = await checker.check()
        
        assert report.status == HealthStatus.UNHEALTHY
        assert "Check failed" in report.checks[0].message
    
    @pytest.mark.asyncio
    async def test_uptime(self):
        """测试运行时间"""
        checker = HealthChecker()
        await asyncio.sleep(0.01)
        
        assert checker.uptime >= 0.01
    
    @pytest.mark.asyncio
    async def test_system_info(self):
        """测试系统信息"""
        checker = HealthChecker()
        report = await checker.check()
        
        assert "platform" in report.system_info
        assert "python_version" in report.system_info
    
    def test_unregister_check(self):
        """测试注销检查"""
        checker = HealthChecker()
        checker.register_check("test", lambda: None)
        
        assert "test" in checker._checks
        
        checker.unregister_check("test")
        assert "test" not in checker._checks
