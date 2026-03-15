"""
工具级权限策略引擎

基于策略的访问控制 (PBAC - Policy-Based Access Control)：
- 细粒度工具级权限控制
- 支持通配符资源匹配
- 显式 DENY 优先

核心概念：
- PolicyStatement: 单条策略声明
- ToolPolicy: 策略集合
- PolicyEngine: 策略评估引擎
- PolicyMiddleware: 与认证集成的中间件
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from .auth import AuthContext
    from .audit import AuditLogger, AuditLevel

logger = logging.getLogger(__name__)


class PolicyEffect(Enum):
    """策略效果"""
    ALLOW = "allow"
    DENY = "deny"


class PolicyAction(Enum):
    """策略动作"""
    CALL_TOOL = "tool:call"           # 调用工具
    LIST_TOOLS = "tool:list"          # 列出工具
    READ_RESOURCE = "resource:read"   # 读取资源
    WRITE_RESOURCE = "resource:write" # 写入资源
    MANAGE_SERVER = "server:manage"   # 管理服务器
    ALL = "*"                         # 所有操作


@dataclass
class PolicyCondition:
    """策略条件"""
    key: str                    # 条件键 (如 "time.hour", "source.ip")
    operator: str               # 操作符 (eq, ne, gt, lt, in, contains)
    value: Any                  # 期望值
    
    def evaluate(self, context: Dict[str, Any]) -> bool:
        """评估条件"""
        # 获取实际值
        actual = self._get_value(context, self.key)
        if actual is None:
            return False
        
        # 根据操作符比较
        if self.operator == "eq":
            return actual == self.value
        elif self.operator == "ne":
            return actual != self.value
        elif self.operator == "gt":
            return actual > self.value
        elif self.operator == "lt":
            return actual < self.value
        elif self.operator == "gte":
            return actual >= self.value
        elif self.operator == "lte":
            return actual <= self.value
        elif self.operator == "in":
            return actual in self.value
        elif self.operator == "contains":
            return self.value in actual
        elif self.operator == "startswith":
            return str(actual).startswith(str(self.value))
        elif self.operator == "endswith":
            return str(actual).endswith(str(self.value))
        elif self.operator == "regex":
            return bool(re.match(self.value, str(actual)))
        
        return False
    
    def _get_value(self, context: Dict[str, Any], key: str) -> Any:
        """从上下文获取值"""
        parts = key.split(".")
        value = context
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value


@dataclass
class PolicyStatement:
    """
    策略声明
    
    定义一条访问控制规则。
    """
    sid: str                                    # 声明ID
    effect: PolicyEffect                        # 允许/拒绝
    actions: Set[PolicyAction]                  # 动作列表
    resources: List[str]                        # 资源模式 (支持通配符)
    conditions: List[PolicyCondition] = field(default_factory=list)  # 条件约束
    description: str = ""                       # 描述
    
    def matches_action(self, action: PolicyAction) -> bool:
        """检查动作是否匹配"""
        if PolicyAction.ALL in self.actions:
            return True
        return action in self.actions
    
    def matches_resource(self, resource: str) -> bool:
        """
        检查资源是否匹配 (支持通配符)
        
        通配符规则：
        - * 匹配任意字符序列
        - ? 匹配单个字符
        - browser/* 匹配 browser/ 下所有
        """
        for pattern in self.resources:
            if pattern == "*":
                return True
            
            # 转换通配符为正则
            regex = self._pattern_to_regex(pattern)
            if re.match(f"^{regex}$", resource, re.IGNORECASE):
                return True
        
        return False
    
    def _pattern_to_regex(self, pattern: str) -> str:
        """将通配符模式转换为正则表达式"""
        # 转义特殊字符
        regex = re.escape(pattern)
        # 将通配符转换为正则
        regex = regex.replace(r"\*", ".*")
        regex = regex.replace(r"\?", ".")
        return regex
    
    def evaluate_conditions(self, context: Dict[str, Any]) -> bool:
        """评估所有条件（AND 逻辑）"""
        if not self.conditions:
            return True
        return all(cond.evaluate(context) for cond in self.conditions)
    
    def matches(
        self,
        action: PolicyAction,
        resource: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """完整匹配检查"""
        if not self.matches_action(action):
            return False
        if not self.matches_resource(resource):
            return False
        if context and not self.evaluate_conditions(context):
            return False
        return True


@dataclass
class ToolPolicy:
    """
    工具访问策略
    
    包含多条策略声明的策略集合。
    """
    policy_id: str
    name: str
    description: str = ""
    statements: List[PolicyStatement] = field(default_factory=list)
    priority: int = 0  # 优先级，数字越大优先级越高
    version: str = "1.0"
    
    def evaluate(
        self,
        action: PolicyAction,
        resource: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Optional[PolicyEffect]:
        """
        评估策略
        
        Returns:
            PolicyEffect 或 None（无匹配）
        """
        for stmt in self.statements:
            if stmt.matches(action, resource, context):
                return stmt.effect
        return None
    
    def add_statement(self, statement: PolicyStatement) -> None:
        """添加策略声明"""
        self.statements.append(statement)
    
    def remove_statement(self, sid: str) -> bool:
        """移除策略声明"""
        for i, stmt in enumerate(self.statements):
            if stmt.sid == sid:
                self.statements.pop(i)
                return True
        return False


@dataclass
class PolicyEvaluationResult:
    """策略评估结果"""
    allowed: bool
    matched_policy: Optional[str] = None
    matched_statement: Optional[str] = None
    reason: str = ""
    evaluation_time_ms: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "allowed": self.allowed,
            "matched_policy": self.matched_policy,
            "matched_statement": self.matched_statement,
            "reason": self.reason,
            "evaluation_time_ms": self.evaluation_time_ms,
        }


class PolicyEngine:
    """
    策略引擎
    
    实现基于策略的访问控制 (PBAC)。
    
    策略评估逻辑：
    1. 收集用户关联的所有策略
    2. 按优先级排序
    3. 显式 DENY 优先（任何 DENY 即拒绝）
    4. 需要显式 ALLOW 才放行
    
    使用示例：
    ```python
    engine = PolicyEngine()
    
    # 创建策略
    dev_policy = ToolPolicy(
        policy_id="dev-policy",
        name="Developer Policy",
        statements=[
            PolicyStatement(
                sid="allow-browser",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.CALL_TOOL},
                resources=["browser/*", "database/*"],
            ),
            PolicyStatement(
                sid="deny-filesystem",
                effect=PolicyEffect.DENY,
                actions={PolicyAction.CALL_TOOL},
                resources=["filesystem/*"],
            ),
        ]
    )
    
    # 注册策略
    engine.register_policy(dev_policy)
    
    # 绑定用户
    engine.attach_policy("user:dev1", "dev-policy")
    
    # 评估
    result = engine.evaluate("dev1", PolicyAction.CALL_TOOL, "browser/navigate")
    # result.allowed = True
    
    result = engine.evaluate("dev1", PolicyAction.CALL_TOOL, "filesystem/read")
    # result.allowed = False
    ```
    """
    
    def __init__(self, default_deny: bool = True):
        """
        初始化策略引擎
        
        Args:
            default_deny: 无策略匹配时是否默认拒绝
        """
        self._policies: Dict[str, ToolPolicy] = {}
        self._user_policies: Dict[str, Set[str]] = {}  # user_id -> policy_ids
        self._role_policies: Dict[str, Set[str]] = {}  # role -> policy_ids
        self._default_deny = default_deny
        self._cache: Dict[str, PolicyEvaluationResult] = {}
        self._cache_enabled = True
        self._cache_ttl = 60.0  # 缓存 TTL（秒）
    
    def register_policy(self, policy: ToolPolicy) -> None:
        """注册策略"""
        self._policies[policy.policy_id] = policy
        self._invalidate_cache()
        logger.info(f"Registered policy: {policy.policy_id}")
    
    def unregister_policy(self, policy_id: str) -> bool:
        """注销策略"""
        if policy_id in self._policies:
            del self._policies[policy_id]
            self._invalidate_cache()
            logger.info(f"Unregistered policy: {policy_id}")
            return True
        return False
    
    def get_policy(self, policy_id: str) -> Optional[ToolPolicy]:
        """获取策略"""
        return self._policies.get(policy_id)
    
    def list_policies(self) -> List[ToolPolicy]:
        """列出所有策略"""
        return list(self._policies.values())
    
    def attach_policy(self, principal: str, policy_id: str) -> bool:
        """
        绑定策略到主体
        
        Args:
            principal: 主体标识 (user:xxx 或 role:xxx)
            policy_id: 策略ID
            
        Returns:
            是否成功
        """
        if policy_id not in self._policies:
            logger.warning(f"Policy not found: {policy_id}")
            return False
        
        if principal.startswith("user:"):
            user_id = principal[5:]
            if user_id not in self._user_policies:
                self._user_policies[user_id] = set()
            self._user_policies[user_id].add(policy_id)
        elif principal.startswith("role:"):
            role = principal[5:]
            if role not in self._role_policies:
                self._role_policies[role] = set()
            self._role_policies[role].add(policy_id)
        else:
            logger.warning(f"Invalid principal format: {principal}")
            return False
        
        self._invalidate_cache()
        logger.info(f"Attached policy {policy_id} to {principal}")
        return True
    
    def detach_policy(self, principal: str, policy_id: str) -> bool:
        """解绑策略"""
        if principal.startswith("user:"):
            user_id = principal[5:]
            if user_id in self._user_policies:
                self._user_policies[user_id].discard(policy_id)
                self._invalidate_cache()
                return True
        elif principal.startswith("role:"):
            role = principal[5:]
            if role in self._role_policies:
                self._role_policies[role].discard(policy_id)
                self._invalidate_cache()
                return True
        return False
    
    def get_policies_for_user(
        self,
        user_id: str,
        role: Optional[str] = None
    ) -> List[ToolPolicy]:
        """获取用户关联的所有策略"""
        policy_ids: Set[str] = set()
        
        # 用户直接绑定的策略
        if user_id in self._user_policies:
            policy_ids.update(self._user_policies[user_id])
        
        # 角色关联的策略
        if role and role in self._role_policies:
            policy_ids.update(self._role_policies[role])
        
        # 按优先级排序
        policies = [
            self._policies[pid] 
            for pid in policy_ids 
            if pid in self._policies
        ]
        return sorted(policies, key=lambda p: p.priority, reverse=True)
    
    def evaluate(
        self,
        user_id: str,
        action: PolicyAction,
        resource: str,
        role: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluationResult:
        """
        评估访问请求
        
        Args:
            user_id: 用户ID
            action: 请求的动作
            resource: 请求的资源
            role: 用户角色（可选）
            context: 评估上下文（可选）
            
        Returns:
            PolicyEvaluationResult
        """
        import time
        start_time = time.perf_counter()
        
        # 检查缓存（有条件评估时不使用缓存，因为结果取决于动态上下文）
        cache_key = f"{user_id}:{role}:{action.value}:{resource}"
        use_cache = self._cache_enabled and context is None
        if use_cache and cache_key in self._cache:
            cached = self._cache[cache_key]
            return cached
        
        # 获取用户策略
        policies = self.get_policies_for_user(user_id, role)
        
        if not policies:
            # 无策略
            result = PolicyEvaluationResult(
                allowed=not self._default_deny,
                reason="No policy attached" if self._default_deny else "Default allow (no policy)",
                evaluation_time_ms=(time.perf_counter() - start_time) * 1000,
            )
            if use_cache:
                self._cache[cache_key] = result
            return result
        
        # 评估所有策略
        allow_matched: Optional[tuple] = None  # (policy_id, statement_id)
        
        for policy in policies:
            for stmt in policy.statements:
                if stmt.matches(action, resource, context):
                    if stmt.effect == PolicyEffect.DENY:
                        # 显式拒绝，立即返回
                        result = PolicyEvaluationResult(
                            allowed=False,
                            matched_policy=policy.policy_id,
                            matched_statement=stmt.sid,
                            reason=f"Explicit DENY: {stmt.description or stmt.sid}",
                            evaluation_time_ms=(time.perf_counter() - start_time) * 1000,
                        )
                        if use_cache:
                            self._cache[cache_key] = result
                        return result
                    
                    if stmt.effect == PolicyEffect.ALLOW and allow_matched is None:
                        allow_matched = (policy.policy_id, stmt.sid)
        
        if allow_matched:
            result = PolicyEvaluationResult(
                allowed=True,
                matched_policy=allow_matched[0],
                matched_statement=allow_matched[1],
                reason="Explicit ALLOW",
                evaluation_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        else:
            # 无匹配
            result = PolicyEvaluationResult(
                allowed=not self._default_deny,
                reason="No matching statement" + (" (default deny)" if self._default_deny else ""),
                evaluation_time_ms=(time.perf_counter() - start_time) * 1000,
            )
        
        if use_cache:
            self._cache[cache_key] = result
        return result
    
    def _invalidate_cache(self) -> None:
        """清除缓存"""
        self._cache.clear()
    
    def set_cache_enabled(self, enabled: bool) -> None:
        """设置缓存开关"""
        self._cache_enabled = enabled
        if not enabled:
            self._invalidate_cache()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取引擎统计"""
        return {
            "policies_count": len(self._policies),
            "user_bindings": len(self._user_policies),
            "role_bindings": len(self._role_policies),
            "cache_size": len(self._cache),
            "cache_enabled": self._cache_enabled,
            "default_deny": self._default_deny,
        }


class PolicyMiddleware:
    """
    策略中间件
    
    与 AuthMiddleware 集成，在认证后执行策略检查。
    
    使用示例：
    ```python
    auth_middleware = AuthMiddleware(auth_config)
    policy_engine = PolicyEngine()
    policy_middleware = PolicyMiddleware(policy_engine)
    
    # 请求处理流程
    async def handle_tool_call(request):
        # 1. 认证
        auth_ctx = await auth_middleware.authenticate(request.credentials)
        if not auth_ctx.authenticated:
            raise AuthenticationError()
        
        # 2. 策略检查
        policy_middleware.check_tool_access(
            auth_ctx,
            tool_name="browser/navigate",
        )
        
        # 3. 执行工具
        ...
    ```
    """
    
    def __init__(
        self,
        engine: PolicyEngine,
        audit_logger: Optional["AuditLogger"] = None
    ):
        self._engine = engine
        self._audit = audit_logger
    
    def check_tool_access(
        self,
        auth_context: "AuthContext",
        tool_name: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluationResult:
        """
        检查工具访问权限
        
        Args:
            auth_context: 认证上下文
            tool_name: 工具名称 (如 "browser/navigate")
            context: 额外上下文
            
        Returns:
            PolicyEvaluationResult
            
        Raises:
            PermissionError: 访问被拒绝
        """
        result = self._engine.evaluate(
            user_id=auth_context.user_id or "anonymous",
            action=PolicyAction.CALL_TOOL,
            resource=tool_name,
            role=auth_context.role.name if auth_context.role else None,
            context=context,
        )
        
        # 审计记录
        if self._audit:
            self._log_audit(auth_context, tool_name, result)
        
        if not result.allowed:
            raise PermissionError(
                f"Access denied to tool '{tool_name}': {result.reason}"
            )
        
        return result
    
    def check_resource_access(
        self,
        auth_context: "AuthContext",
        resource: str,
        action: PolicyAction = PolicyAction.READ_RESOURCE,
        context: Optional[Dict[str, Any]] = None,
    ) -> PolicyEvaluationResult:
        """检查资源访问权限"""
        result = self._engine.evaluate(
            user_id=auth_context.user_id or "anonymous",
            action=action,
            resource=resource,
            role=auth_context.role.name if auth_context.role else None,
            context=context,
        )
        
        if not result.allowed:
            raise PermissionError(
                f"Access denied to resource '{resource}': {result.reason}"
            )
        
        return result
    
    def _log_audit(
        self,
        auth_context: "AuthContext",
        resource: str,
        result: PolicyEvaluationResult
    ) -> None:
        """记录审计日志"""
        try:
            # 动态导入避免循环依赖
            from .audit import AuditLevel
            
            asyncio.create_task(self._audit.log(
                action="policy.evaluate",
                level=AuditLevel.INFO if result.allowed else AuditLevel.WARNING,
                user_id=auth_context.user_id,
                user_role=auth_context.role.name if auth_context.role else None,
                resource=resource,
                success=result.allowed,
                metadata={
                    "matched_policy": result.matched_policy,
                    "matched_statement": result.matched_statement,
                    "reason": result.reason,
                    "evaluation_time_ms": result.evaluation_time_ms,
                }
            ))
        except Exception as e:
            logger.warning(f"Failed to log audit: {e}")
    
    def require_permission(
        self,
        action: PolicyAction = PolicyAction.CALL_TOOL,
        resource_extractor: Optional[Callable] = None
    ):
        """
        装饰器：要求指定权限
        
        ```python
        @middleware.require_permission(
            PolicyAction.CALL_TOOL,
            resource_extractor=lambda tool_name, **_: tool_name
        )
        async def execute_tool(auth_ctx, tool_name, params):
            ...
        ```
        """
        def decorator(func: Callable):
            async def wrapper(auth_context: "AuthContext", *args, **kwargs):
                # 提取资源
                if resource_extractor:
                    resource = resource_extractor(*args, **kwargs)
                else:
                    resource = func.__name__
                
                # 检查权限
                self._engine.evaluate(
                    user_id=auth_context.user_id or "anonymous",
                    action=action,
                    resource=resource,
                    role=auth_context.role.name if auth_context.role else None,
                )
                
                return await func(auth_context, *args, **kwargs)
            
            return wrapper
        return decorator


# ===== 预定义策略模板 =====

BUILTIN_POLICIES = {
    "admin-full-access": ToolPolicy(
        policy_id="admin-full-access",
        name="Admin Full Access",
        description="Full access to all tools and resources",
        priority=100,
        statements=[
            PolicyStatement(
                sid="allow-all",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.ALL},
                resources=["*"],
                description="Allow all actions on all resources",
            )
        ]
    ),
    
    "operator-execute": ToolPolicy(
        policy_id="operator-execute",
        name="Operator Execute",
        description="Can execute tools but not manage servers",
        priority=50,
        statements=[
            PolicyStatement(
                sid="allow-tools",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.CALL_TOOL, PolicyAction.LIST_TOOLS},
                resources=["*"],
                description="Allow calling and listing tools",
            ),
            PolicyStatement(
                sid="allow-read",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.READ_RESOURCE},
                resources=["*"],
                description="Allow reading resources",
            ),
            PolicyStatement(
                sid="deny-manage",
                effect=PolicyEffect.DENY,
                actions={PolicyAction.MANAGE_SERVER},
                resources=["*"],
                description="Deny server management",
            ),
        ]
    ),
    
    "viewer-readonly": ToolPolicy(
        policy_id="viewer-readonly",
        name="Viewer Read-Only",
        description="Read-only access to resources",
        priority=10,
        statements=[
            PolicyStatement(
                sid="allow-list",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.LIST_TOOLS},
                resources=["*"],
                description="Allow listing tools",
            ),
            PolicyStatement(
                sid="allow-read",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.READ_RESOURCE},
                resources=["*"],
                description="Allow reading resources",
            ),
            PolicyStatement(
                sid="deny-execute",
                effect=PolicyEffect.DENY,
                actions={PolicyAction.CALL_TOOL, PolicyAction.WRITE_RESOURCE},
                resources=["*"],
                description="Deny tool execution and writing",
            ),
        ]
    ),
    
    "browser-only": ToolPolicy(
        policy_id="browser-only",
        name="Browser Only",
        description="Only browser tools allowed",
        priority=30,
        statements=[
            PolicyStatement(
                sid="allow-browser",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.CALL_TOOL},
                resources=["browser/*", "mcp-browser-*/*"],
                description="Allow browser-related tools",
            ),
            PolicyStatement(
                sid="allow-list",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.LIST_TOOLS, PolicyAction.READ_RESOURCE},
                resources=["*"],
                description="Allow listing and reading",
            ),
        ]
    ),
    
    "database-readonly": ToolPolicy(
        policy_id="database-readonly",
        name="Database Read-Only",
        description="Read-only access to database tools",
        priority=30,
        statements=[
            PolicyStatement(
                sid="allow-read-ops",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.CALL_TOOL},
                resources=["database/query", "database/list*", "sqlite/query", "sqlite/list*"],
                description="Allow read operations on database",
            ),
            PolicyStatement(
                sid="deny-write-ops",
                effect=PolicyEffect.DENY,
                actions={PolicyAction.CALL_TOOL},
                resources=["database/execute", "database/create*", "database/drop*", 
                          "sqlite/execute", "sqlite/create*"],
                description="Deny write operations on database",
            ),
        ]
    ),
}


def get_builtin_policy(policy_id: str) -> Optional[ToolPolicy]:
    """获取内置策略"""
    return BUILTIN_POLICIES.get(policy_id)


def list_builtin_policies() -> List[str]:
    """列出所有内置策略ID"""
    return list(BUILTIN_POLICIES.keys())
