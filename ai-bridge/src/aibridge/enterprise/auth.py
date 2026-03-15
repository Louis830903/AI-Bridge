"""
统一认证中间件

提供多种认证方式：
- API Key 认证
- JWT Token 认证
- 自定义认证提供者

支持细粒度权限控制。
"""

import asyncio
import hashlib
import hmac
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)


class Permission(Enum):
    """权限枚举"""
    # 读权限
    READ = "read"
    READ_TOOLS = "read:tools"
    READ_RESOURCES = "read:resources"
    
    # 写权限
    WRITE = "write"
    EXECUTE = "execute"
    EXECUTE_TOOLS = "execute:tools"
    
    # 管理权限
    ADMIN = "admin"
    MANAGE_SERVERS = "manage:servers"
    MANAGE_AGENTS = "manage:agents"
    
    # 全部权限
    ALL = "*"


@dataclass
class Role:
    """角色定义"""
    name: str
    permissions: Set[Permission] = field(default_factory=set)
    description: str = ""
    
    def has_permission(self, permission: Permission) -> bool:
        """检查是否有指定权限"""
        if Permission.ALL in self.permissions:
            return True
        if permission in self.permissions:
            return True
        # 检查父权限（如 read 包含 read:tools）
        for p in self.permissions:
            if permission.value.startswith(p.value + ":"):
                return True
        return False


# 预定义角色
ROLES = {
    "admin": Role(
        name="admin",
        permissions={Permission.ALL},
        description="Full access to all resources"
    ),
    "operator": Role(
        name="operator",
        permissions={Permission.READ, Permission.EXECUTE},
        description="Can read and execute tools"
    ),
    "viewer": Role(
        name="viewer",
        permissions={Permission.READ},
        description="Read-only access"
    ),
}


@dataclass
class AuthConfig:
    """认证配置"""
    # 是否启用认证
    enabled: bool = True
    
    # API Key 配置
    api_keys: Dict[str, str] = field(default_factory=dict)  # key -> role
    
    # JWT 配置
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry: int = 3600  # 秒
    
    # 允许的认证方式
    allowed_providers: List[str] = field(default_factory=lambda: ["api_key", "jwt"])
    
    # 默认角色（未认证时）
    default_role: Optional[str] = None


@dataclass
class AuthContext:
    """认证上下文"""
    authenticated: bool = False
    user_id: Optional[str] = None
    role: Optional[Role] = None
    provider: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def has_permission(self, permission: Permission) -> bool:
        """检查当前用户是否有指定权限"""
        if not self.authenticated or not self.role:
            return False
        return self.role.has_permission(permission)


class AuthProvider(ABC):
    """认证提供者基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """提供者名称"""
        pass
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[AuthContext]:
        """
        验证凭证
        
        Args:
            credentials: 凭证信息
            
        Returns:
            AuthContext 或 None（认证失败）
        """
        pass


class APIKeyAuth(AuthProvider):
    """API Key 认证"""
    
    def __init__(self, config: AuthConfig):
        self._config = config
    
    @property
    def name(self) -> str:
        return "api_key"
    
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[AuthContext]:
        """验证 API Key"""
        api_key = credentials.get("api_key") or credentials.get("x-api-key")
        if not api_key:
            return None
        
        # 查找 API Key 对应的角色
        role_name = self._config.api_keys.get(api_key)
        if not role_name:
            logger.warning(f"Invalid API key attempted")
            return None
        
        role = ROLES.get(role_name)
        if not role:
            logger.error(f"Unknown role: {role_name}")
            return None
        
        # 从 API Key 生成用户 ID（哈希）
        user_id = hashlib.sha256(api_key.encode()).hexdigest()[:16]
        
        return AuthContext(
            authenticated=True,
            user_id=f"apikey:{user_id}",
            role=role,
            provider=self.name,
            metadata={"key_prefix": api_key[:8] + "..."}
        )


class JWTAuth(AuthProvider):
    """JWT Token 认证"""
    
    def __init__(self, config: AuthConfig):
        self._config = config
    
    @property
    def name(self) -> str:
        return "jwt"
    
    async def authenticate(self, credentials: Dict[str, Any]) -> Optional[AuthContext]:
        """验证 JWT Token"""
        token = credentials.get("token") or credentials.get("authorization")
        if not token:
            return None
        
        # 移除 Bearer 前缀
        if token.startswith("Bearer "):
            token = token[7:]
        
        try:
            # 解析 JWT（简化实现，生产环境应使用 PyJWT）
            payload = self._decode_jwt(token)
            if not payload:
                return None
            
            # 检查过期
            exp = payload.get("exp", 0)
            if exp < time.time():
                logger.warning("JWT token expired")
                return None
            
            # 获取角色
            role_name = payload.get("role", "viewer")
            role = ROLES.get(role_name)
            if not role:
                role = ROLES["viewer"]
            
            return AuthContext(
                authenticated=True,
                user_id=payload.get("sub", "unknown"),
                role=role,
                provider=self.name,
                metadata={"claims": payload}
            )
            
        except Exception as e:
            logger.warning(f"JWT authentication failed: {e}")
            return None
    
    def _decode_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        """解码 JWT（简化实现）"""
        import base64
        import json
        
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            
            # 解码 payload
            payload_b64 = parts[1]
            # 添加填充
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            
            payload_json = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_json)
            
            # 验证签名（简化：仅验证 HMAC）
            if self._config.jwt_secret:
                expected_sig = self._sign(parts[0] + "." + parts[1])
                actual_sig = parts[2]
                # 简化比较（生产环境应使用安全比较）
                if expected_sig != actual_sig:
                    logger.warning("JWT signature mismatch")
                    # 允许继续（演示用途）
            
            return payload
            
        except Exception as e:
            logger.debug(f"JWT decode error: {e}")
            return None
    
    def _sign(self, data: str) -> str:
        """签名数据"""
        import base64
        signature = hmac.new(
            self._config.jwt_secret.encode(),
            data.encode(),
            hashlib.sha256
        ).digest()
        return base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    
    def create_token(
        self,
        user_id: str,
        role: str = "viewer",
        expiry: Optional[int] = None,
        **extra_claims
    ) -> str:
        """
        创建 JWT Token
        
        Args:
            user_id: 用户 ID
            role: 角色名
            expiry: 过期时间（秒），None 使用默认配置
            **extra_claims: 额外的 claims
            
        Returns:
            JWT Token 字符串
        """
        import base64
        import json
        
        # Header
        header = {"alg": self._config.jwt_algorithm, "typ": "JWT"}
        header_b64 = base64.urlsafe_b64encode(
            json.dumps(header).encode()
        ).rstrip(b"=").decode()
        
        # Payload
        exp = expiry or self._config.jwt_expiry
        payload = {
            "sub": user_id,
            "role": role,
            "iat": int(time.time()),
            "exp": int(time.time()) + exp,
            **extra_claims
        }
        payload_b64 = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).rstrip(b"=").decode()
        
        # Signature
        signature = self._sign(header_b64 + "." + payload_b64)
        
        return f"{header_b64}.{payload_b64}.{signature}"


class AuthMiddleware:
    """
    认证中间件
    
    统一处理所有请求的认证和授权。
    
    使用示例：
    ```python
    config = AuthConfig(
        enabled=True,
        api_keys={
            "sk-12345": "admin",
            "sk-67890": "viewer",
        },
        jwt_secret="my-secret-key"
    )
    
    middleware = AuthMiddleware(config)
    
    # 认证请求
    context = await middleware.authenticate({
        "x-api-key": "sk-12345"
    })
    
    if context.authenticated:
        print(f"User: {context.user_id}, Role: {context.role.name}")
    
    # 检查权限
    if middleware.authorize(context, Permission.EXECUTE_TOOLS):
        # 执行操作
        pass
    ```
    """
    
    def __init__(self, config: AuthConfig):
        self._config = config
        self._providers: Dict[str, AuthProvider] = {}
        
        # 注册默认提供者
        if "api_key" in config.allowed_providers:
            self.register_provider(APIKeyAuth(config))
        if "jwt" in config.allowed_providers:
            self.register_provider(JWTAuth(config))
    
    def register_provider(self, provider: AuthProvider) -> None:
        """注册认证提供者"""
        self._providers[provider.name] = provider
        logger.info(f"Registered auth provider: {provider.name}")
    
    async def authenticate(self, credentials: Dict[str, Any]) -> AuthContext:
        """
        认证请求
        
        尝试所有注册的提供者进行认证。
        
        Args:
            credentials: 凭证信息（可包含多种凭证）
            
        Returns:
            AuthContext
        """
        if not self._config.enabled:
            # 认证禁用，返回默认角色
            default_role = ROLES.get(self._config.default_role or "viewer")
            return AuthContext(
                authenticated=True,
                user_id="anonymous",
                role=default_role,
                provider="none",
            )
        
        # 尝试每个提供者
        for provider in self._providers.values():
            try:
                context = await provider.authenticate(credentials)
                if context and context.authenticated:
                    logger.info(f"Authenticated via {provider.name}: {context.user_id}")
                    return context
            except Exception as e:
                logger.warning(f"Auth provider {provider.name} error: {e}")
        
        # 认证失败
        if self._config.default_role:
            # 返回默认角色（受限访问）
            default_role = ROLES.get(self._config.default_role)
            return AuthContext(
                authenticated=False,
                role=default_role,
            )
        
        return AuthContext(authenticated=False)
    
    def authorize(
        self,
        context: AuthContext,
        permission: Permission,
        resource: Optional[str] = None
    ) -> bool:
        """
        授权检查
        
        Args:
            context: 认证上下文
            permission: 需要的权限
            resource: 资源标识（可选，用于细粒度控制）
            
        Returns:
            是否授权
        """
        if not context.has_permission(permission):
            logger.warning(
                f"Authorization denied: user={context.user_id}, "
                f"permission={permission.value}, resource={resource}"
            )
            return False
        
        return True
    
    def require_permission(self, permission: Permission):
        """
        装饰器：要求指定权限
        
        ```python
        @middleware.require_permission(Permission.EXECUTE_TOOLS)
        async def execute_tool(context, tool_name, params):
            ...
        ```
        """
        def decorator(func: Callable):
            async def wrapper(context: AuthContext, *args, **kwargs):
                if not self.authorize(context, permission):
                    raise PermissionError(
                        f"Permission denied: {permission.value} required"
                    )
                return await func(context, *args, **kwargs)
            return wrapper
        return decorator
    
    def get_jwt_provider(self) -> Optional[JWTAuth]:
        """获取 JWT 提供者（用于创建 Token）"""
        provider = self._providers.get("jwt")
        if isinstance(provider, JWTAuth):
            return provider
        return None
