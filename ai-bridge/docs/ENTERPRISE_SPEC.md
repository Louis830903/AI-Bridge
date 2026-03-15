# AI-Bridge 企业级能力提升 & 协议桥接增强 开发规范

> **版本**: v4.0 规划  
> **创建日期**: 2026-03-15  
> **战略定位**: 聚焦企业级管理层 + 协议桥接，构建差异化壁垒

---

## 一、战略背景

### 1.1 第一性原理分析

**问题本质**：MCP 生态快速发展，单独的 MCP Server 谁都能写。AI-Bridge 的价值不在于"又一个连接器"，而在于：

```
┌─────────────────────────────────────────────────────────────┐
│                    AI-Bridge 核心价值                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. 企业级管理层（市场空白）                                  │
│     - 多 MCP Server 统一管控                                 │
│     - 工具级权限控制                                         │
│     - 调用成本计量                                           │
│     - 分布式链路追踪                                         │
│                                                             │
│  2. 协议互通能力（MCP ↔ A2A）                                │
│     - 双向协议转换                                           │
│     - 多 Agent 编排                                          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 当前状态

| 模块 | 成熟度 | 缺口 |
|------|--------|------|
| Auth 认证 | 70% | 仅角色级权限，缺工具级 |
| Audit 审计 | 70% | 单次审计，缺链路追踪 |
| RateLimit 限流 | 75% | 完善 |
| Protocol Bridge | 40% | 仅 MCP→A2A 单向 |
| 成本计量 | 0% | 完全缺失 |

---

## 二、架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI Assistant Layer                            │
│                   (Claude, GPT, Qwen, Gemini)                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │ MCP / A2A Protocol
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     AI-Bridge v4.0 Protocol Gateway                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Enterprise Layer (新增)                    │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │   │
│  │  │ Policy  │  │Metering │  │ Tracing │  │ Quota   │        │   │
│  │  │ Engine  │  │Collector│  │  (OTel) │  │ Manager │        │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Gateway Layer (增强)                       │   │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐          │   │
│  │  │   Protocol  │  │   Multi-    │  │   Service   │          │   │
│  │  │   Bridge    │  │   Agent     │  │  Discovery  │          │   │
│  │  │  (双向增强)  │  │ Orchestrator│  │             │          │   │
│  │  └─────────────┘  └─────────────┘  └─────────────┘          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Existing Layer (现有)                      │   │
│  │  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐     │   │
│  │  │ Auth  │  │ Audit │  │ Rate  │  │Health │  │  MCP  │     │   │
│  │  │       │  │       │  │ Limit │  │ Check │  │Registry│     │   │
│  │  └───────┘  └───────┘  └───────┘  └───────┘  └───────┘     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 模块依赖关系

```
Policy Engine ──────┐
                    ├──→ Auth Middleware (增强)
Metering Collector ─┤
                    ├──→ Audit Logger (增强)
Tracing (OTel) ─────┤
                    └──→ Protocol Bridge (增强)
Quota Manager ──────────→ Rate Limiter (增强)
```

---

## 三、Phase 1: 工具级权限控制

### 3.1 需求分析

**用户场景**：
- 管理员：可以使用所有工具
- 开发者：可以使用 browser、database，但不能用 filesystem
- 只读用户：只能读取资源，不能执行工具

**现状**：
```python
# 当前：角色级权限
class Permission(Enum):
    READ = "read"
    EXECUTE = "execute"
    ADMIN = "admin"

# 问题：无法控制"用户A可以用browser，但不能用filesystem"
```

### 3.2 设计方案

#### 3.2.1 数据模型

```python
# enterprise/policy.py

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Pattern
import re

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
    ALL = "*"                         # 所有操作

@dataclass
class PolicyStatement:
    """策略声明"""
    sid: str                                    # 声明ID
    effect: PolicyEffect                        # 允许/拒绝
    actions: Set[PolicyAction]                  # 动作列表
    resources: List[str]                        # 资源模式 (支持通配符)
    conditions: Optional[Dict[str, Any]] = None # 条件约束
    
    def matches_action(self, action: PolicyAction) -> bool:
        """检查动作是否匹配"""
        if PolicyAction.ALL in self.actions:
            return True
        return action in self.actions
    
    def matches_resource(self, resource: str) -> bool:
        """检查资源是否匹配 (支持通配符)"""
        for pattern in self.resources:
            if pattern == "*":
                return True
            # 转换通配符为正则
            regex = pattern.replace(".", r"\.").replace("*", ".*")
            if re.match(f"^{regex}$", resource):
                return True
        return False

@dataclass
class ToolPolicy:
    """工具访问策略"""
    policy_id: str
    name: str
    description: str = ""
    statements: List[PolicyStatement] = field(default_factory=list)
    priority: int = 0  # 优先级，数字越大优先级越高
    
    def evaluate(self, action: PolicyAction, resource: str) -> Optional[PolicyEffect]:
        """
        评估策略
        
        Returns:
            PolicyEffect 或 None（无匹配）
        """
        for stmt in self.statements:
            if stmt.matches_action(action) and stmt.matches_resource(resource):
                return stmt.effect
        return None
```

#### 3.2.2 策略引擎

```python
# enterprise/policy.py (续)

@dataclass
class PolicyEvaluationResult:
    """策略评估结果"""
    allowed: bool
    matched_policy: Optional[str] = None
    matched_statement: Optional[str] = None
    reason: str = ""

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
    result = engine.evaluate("user:dev1", PolicyAction.CALL_TOOL, "browser/navigate")
    # result.allowed = True
    
    result = engine.evaluate("user:dev1", PolicyAction.CALL_TOOL, "filesystem/read")
    # result.allowed = False
    ```
    """
    
    def __init__(self):
        self._policies: Dict[str, ToolPolicy] = {}
        self._user_policies: Dict[str, Set[str]] = {}  # user_id -> policy_ids
        self._role_policies: Dict[str, Set[str]] = {}  # role -> policy_ids
    
    def register_policy(self, policy: ToolPolicy) -> None:
        """注册策略"""
        self._policies[policy.policy_id] = policy
    
    def unregister_policy(self, policy_id: str) -> None:
        """注销策略"""
        if policy_id in self._policies:
            del self._policies[policy_id]
    
    def attach_policy(self, principal: str, policy_id: str) -> None:
        """
        绑定策略到主体
        
        Args:
            principal: 主体标识 (user:xxx 或 role:xxx)
            policy_id: 策略ID
        """
        if principal.startswith("user:"):
            if principal not in self._user_policies:
                self._user_policies[principal] = set()
            self._user_policies[principal].add(policy_id)
        elif principal.startswith("role:"):
            if principal not in self._role_policies:
                self._role_policies[principal] = set()
            self._role_policies[principal].add(policy_id)
    
    def detach_policy(self, principal: str, policy_id: str) -> None:
        """解绑策略"""
        if principal.startswith("user:") and principal in self._user_policies:
            self._user_policies[principal].discard(policy_id)
        elif principal.startswith("role:") and principal in self._role_policies:
            self._role_policies[principal].discard(policy_id)
    
    def get_policies_for_user(self, user_id: str, role: Optional[str] = None) -> List[ToolPolicy]:
        """获取用户关联的所有策略"""
        policy_ids = set()
        
        # 用户直接绑定的策略
        user_key = f"user:{user_id}"
        if user_key in self._user_policies:
            policy_ids.update(self._user_policies[user_key])
        
        # 角色关联的策略
        if role:
            role_key = f"role:{role}"
            if role_key in self._role_policies:
                policy_ids.update(self._role_policies[role_key])
        
        # 按优先级排序
        policies = [self._policies[pid] for pid in policy_ids if pid in self._policies]
        return sorted(policies, key=lambda p: p.priority, reverse=True)
    
    def evaluate(
        self,
        user_id: str,
        action: PolicyAction,
        resource: str,
        role: Optional[str] = None,
    ) -> PolicyEvaluationResult:
        """
        评估访问请求
        
        Args:
            user_id: 用户ID
            action: 请求的动作
            resource: 请求的资源
            role: 用户角色（可选）
            
        Returns:
            PolicyEvaluationResult
        """
        policies = self.get_policies_for_user(user_id, role)
        
        if not policies:
            # 无策略，默认拒绝
            return PolicyEvaluationResult(
                allowed=False,
                reason="No policy attached"
            )
        
        # 评估所有策略
        allow_matched = None
        
        for policy in policies:
            effect = policy.evaluate(action, resource)
            
            if effect == PolicyEffect.DENY:
                # 显式拒绝，立即返回
                return PolicyEvaluationResult(
                    allowed=False,
                    matched_policy=policy.policy_id,
                    reason="Explicit DENY"
                )
            
            if effect == PolicyEffect.ALLOW and allow_matched is None:
                allow_matched = policy.policy_id
        
        if allow_matched:
            return PolicyEvaluationResult(
                allowed=True,
                matched_policy=allow_matched,
                reason="Explicit ALLOW"
            )
        
        # 无匹配，默认拒绝
        return PolicyEvaluationResult(
            allowed=False,
            reason="No matching statement"
        )
```

#### 3.2.3 策略中间件

```python
# enterprise/policy.py (续)

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
    
    def __init__(self, engine: PolicyEngine, audit_logger: Optional[AuditLogger] = None):
        self._engine = engine
        self._audit = audit_logger
    
    def check_tool_access(
        self,
        auth_context: AuthContext,
        tool_name: str,
    ) -> PolicyEvaluationResult:
        """
        检查工具访问权限
        
        Args:
            auth_context: 认证上下文
            tool_name: 工具名称 (如 "browser/navigate")
            
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
        )
        
        # 审计记录
        if self._audit:
            asyncio.create_task(self._audit.log(
                action="policy.evaluate",
                level=AuditLevel.INFO if result.allowed else AuditLevel.WARNING,
                user_id=auth_context.user_id,
                resource=tool_name,
                success=result.allowed,
                metadata={
                    "matched_policy": result.matched_policy,
                    "reason": result.reason,
                }
            ))
        
        if not result.allowed:
            raise PermissionError(
                f"Access denied to tool '{tool_name}': {result.reason}"
            )
        
        return result
    
    def check_resource_access(
        self,
        auth_context: AuthContext,
        resource: str,
        action: PolicyAction = PolicyAction.READ_RESOURCE,
    ) -> PolicyEvaluationResult:
        """检查资源访问权限"""
        result = self._engine.evaluate(
            user_id=auth_context.user_id or "anonymous",
            action=action,
            resource=resource,
            role=auth_context.role.name if auth_context.role else None,
        )
        
        if not result.allowed:
            raise PermissionError(
                f"Access denied to resource '{resource}': {result.reason}"
            )
        
        return result
```

#### 3.2.4 预定义策略模板

```python
# enterprise/policy.py (续)

# 预定义策略模板
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
            ),
            PolicyStatement(
                sid="allow-read",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.READ_RESOURCE},
                resources=["*"],
            ),
            PolicyStatement(
                sid="deny-write",
                effect=PolicyEffect.DENY,
                actions={PolicyAction.WRITE_RESOURCE},
                resources=["*"],
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
            ),
            PolicyStatement(
                sid="allow-read",
                effect=PolicyEffect.ALLOW,
                actions={PolicyAction.READ_RESOURCE},
                resources=["*"],
            ),
            PolicyStatement(
                sid="deny-execute",
                effect=PolicyEffect.DENY,
                actions={PolicyAction.CALL_TOOL},
                resources=["*"],
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
            ),
            PolicyStatement(
                sid="deny-others",
                effect=PolicyEffect.DENY,
                actions={PolicyAction.CALL_TOOL},
                resources=["*"],
            ),
        ]
    ),
}
```

---

## 四、Phase 1: 调用成本计量

### 4.1 需求分析

**用户场景**：
- 按用户统计调用次数
- 按工具统计使用量
- 生成使用报告（日/周/月）
- 配额管理（超限告警/限制）

### 4.2 设计方案

#### 4.2.1 数据模型

```python
# enterprise/metering.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
import asyncio
import time

class MeteringDimension(Enum):
    """计量维度"""
    USER = "user"
    TOOL = "tool"
    SERVER = "server"
    HOUR = "hour"
    DAY = "day"

@dataclass
class UsageRecord:
    """使用记录"""
    record_id: str
    timestamp: float = field(default_factory=time.time)
    
    # 调用信息
    user_id: str = ""
    tool_name: str = ""
    server_name: str = ""
    
    # 计量数据
    call_count: int = 1
    success_count: int = 0
    error_count: int = 0
    
    # 资源消耗
    duration_ms: float = 0
    input_tokens: int = 0   # 输入 token 数（如适用）
    output_tokens: int = 0  # 输出 token 数（如适用）
    
    # 成本估算（可配置单价）
    estimated_cost: float = 0.0
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class UsageAggregation:
    """使用量聚合"""
    dimension: MeteringDimension
    key: str  # 聚合键（如 user:xxx 或 tool:browser）
    period_start: datetime
    period_end: datetime
    
    # 聚合统计
    total_calls: int = 0
    success_calls: int = 0
    error_calls: int = 0
    total_duration_ms: float = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost: float = 0.0
    
    # 衍生指标
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.success_calls / self.total_calls
    
    @property
    def avg_duration_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_duration_ms / self.total_calls

@dataclass  
class QuotaConfig:
    """配额配置"""
    quota_id: str
    name: str
    
    # 限制
    max_calls_per_hour: Optional[int] = None
    max_calls_per_day: Optional[int] = None
    max_calls_per_month: Optional[int] = None
    max_cost_per_day: Optional[float] = None
    max_cost_per_month: Optional[float] = None
    
    # 告警阈值（百分比）
    warning_threshold: float = 0.8  # 80% 时告警
    
    # 超限行为
    block_on_exceed: bool = True  # 超限时阻止
```

#### 4.2.2 计量采集器

```python
# enterprise/metering.py (续)

class MeteringCollector:
    """
    计量采集器
    
    收集和聚合使用量数据。
    
    使用示例：
    ```python
    collector = MeteringCollector()
    await collector.start()
    
    # 记录调用
    await collector.record(
        user_id="user123",
        tool_name="browser/navigate",
        server_name="browser-use",
        duration_ms=150.5,
        success=True,
    )
    
    # 获取统计
    stats = await collector.get_user_stats("user123", period="day")
    print(f"Today's calls: {stats.total_calls}")
    
    await collector.stop()
    ```
    """
    
    def __init__(self, config: Optional[MeteringConfig] = None):
        self._config = config or MeteringConfig()
        self._records: List[UsageRecord] = []
        self._aggregations: Dict[str, UsageAggregation] = {}
        self._lock = asyncio.Lock()
        self._running = False
        self._flush_task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动采集器"""
        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_aggregate())
    
    async def stop(self) -> None:
        """停止采集器"""
        self._running = False
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._aggregate_all()
    
    async def record(
        self,
        user_id: str,
        tool_name: str,
        server_name: str = "",
        duration_ms: float = 0,
        success: bool = True,
        input_tokens: int = 0,
        output_tokens: int = 0,
        **metadata
    ) -> UsageRecord:
        """
        记录一次调用
        
        Args:
            user_id: 用户ID
            tool_name: 工具名称
            server_name: 服务器名称
            duration_ms: 耗时（毫秒）
            success: 是否成功
            input_tokens: 输入 token 数
            output_tokens: 输出 token 数
            **metadata: 额外元数据
            
        Returns:
            UsageRecord
        """
        record = UsageRecord(
            record_id=str(uuid.uuid4()),
            user_id=user_id,
            tool_name=tool_name,
            server_name=server_name,
            success_count=1 if success else 0,
            error_count=0 if success else 1,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost=self._calculate_cost(input_tokens, output_tokens, duration_ms),
            metadata=metadata,
        )
        
        async with self._lock:
            self._records.append(record)
            
            # 实时更新聚合
            self._update_aggregation(record)
        
        return record
    
    def _calculate_cost(
        self, 
        input_tokens: int, 
        output_tokens: int, 
        duration_ms: float
    ) -> float:
        """计算成本"""
        cost = 0.0
        cost += input_tokens * self._config.cost_per_input_token
        cost += output_tokens * self._config.cost_per_output_token
        cost += (duration_ms / 1000) * self._config.cost_per_second
        return cost
    
    def _update_aggregation(self, record: UsageRecord) -> None:
        """更新聚合数据"""
        now = datetime.now()
        
        # 按用户聚合（当天）
        user_key = f"user:{record.user_id}:day:{now.strftime('%Y-%m-%d')}"
        if user_key not in self._aggregations:
            self._aggregations[user_key] = UsageAggregation(
                dimension=MeteringDimension.USER,
                key=record.user_id,
                period_start=now.replace(hour=0, minute=0, second=0),
                period_end=now.replace(hour=23, minute=59, second=59),
            )
        agg = self._aggregations[user_key]
        agg.total_calls += 1
        agg.success_calls += record.success_count
        agg.error_calls += record.error_count
        agg.total_duration_ms += record.duration_ms
        agg.total_input_tokens += record.input_tokens
        agg.total_output_tokens += record.output_tokens
        agg.total_cost += record.estimated_cost
        
        # 按工具聚合（当天）
        tool_key = f"tool:{record.tool_name}:day:{now.strftime('%Y-%m-%d')}"
        if tool_key not in self._aggregations:
            self._aggregations[tool_key] = UsageAggregation(
                dimension=MeteringDimension.TOOL,
                key=record.tool_name,
                period_start=now.replace(hour=0, minute=0, second=0),
                period_end=now.replace(hour=23, minute=59, second=59),
            )
        agg = self._aggregations[tool_key]
        agg.total_calls += 1
        agg.success_calls += record.success_count
        agg.error_calls += record.error_count
        agg.total_duration_ms += record.duration_ms
        agg.total_cost += record.estimated_cost
    
    async def get_user_stats(
        self, 
        user_id: str, 
        period: str = "day"
    ) -> Optional[UsageAggregation]:
        """获取用户统计"""
        now = datetime.now()
        if period == "day":
            key = f"user:{user_id}:day:{now.strftime('%Y-%m-%d')}"
        elif period == "hour":
            key = f"user:{user_id}:hour:{now.strftime('%Y-%m-%d-%H')}"
        else:
            return None
        
        return self._aggregations.get(key)
    
    async def get_tool_stats(
        self, 
        tool_name: str, 
        period: str = "day"
    ) -> Optional[UsageAggregation]:
        """获取工具统计"""
        now = datetime.now()
        key = f"tool:{tool_name}:day:{now.strftime('%Y-%m-%d')}"
        return self._aggregations.get(key)
    
    async def generate_report(
        self,
        period_start: datetime,
        period_end: datetime,
        group_by: MeteringDimension = MeteringDimension.USER,
    ) -> List[UsageAggregation]:
        """生成使用报告"""
        results = []
        prefix = f"{group_by.value}:"
        
        for key, agg in self._aggregations.items():
            if key.startswith(prefix):
                if agg.period_start >= period_start and agg.period_end <= period_end:
                    results.append(agg)
        
        return sorted(results, key=lambda x: x.total_calls, reverse=True)
```

#### 4.2.3 配额管理器

```python
# enterprise/metering.py (续)

class QuotaExceeded(Exception):
    """配额超限异常"""
    def __init__(
        self,
        message: str,
        quota_type: str,
        current: float,
        limit: float,
    ):
        super().__init__(message)
        self.quota_type = quota_type
        self.current = current
        self.limit = limit

class QuotaManager:
    """
    配额管理器
    
    管理用户的使用配额。
    
    使用示例：
    ```python
    collector = MeteringCollector()
    quota_mgr = QuotaManager(collector)
    
    # 设置配额
    quota_mgr.set_user_quota("user123", QuotaConfig(
        quota_id="user123-quota",
        name="User 123 Quota",
        max_calls_per_day=1000,
        max_cost_per_month=100.0,
    ))
    
    # 检查配额
    try:
        await quota_mgr.check_quota("user123")
        # 执行调用...
    except QuotaExceeded as e:
        print(f"Quota exceeded: {e.quota_type}")
    ```
    """
    
    def __init__(self, collector: MeteringCollector):
        self._collector = collector
        self._user_quotas: Dict[str, QuotaConfig] = {}
        self._default_quota: Optional[QuotaConfig] = None
    
    def set_default_quota(self, quota: QuotaConfig) -> None:
        """设置默认配额"""
        self._default_quota = quota
    
    def set_user_quota(self, user_id: str, quota: QuotaConfig) -> None:
        """设置用户配额"""
        self._user_quotas[user_id] = quota
    
    def get_user_quota(self, user_id: str) -> Optional[QuotaConfig]:
        """获取用户配额"""
        return self._user_quotas.get(user_id, self._default_quota)
    
    async def check_quota(self, user_id: str) -> Dict[str, Any]:
        """
        检查配额
        
        Args:
            user_id: 用户ID
            
        Returns:
            配额状态信息
            
        Raises:
            QuotaExceeded: 配额超限
        """
        quota = self.get_user_quota(user_id)
        if not quota:
            return {"status": "no_quota"}
        
        stats = await self._collector.get_user_stats(user_id, "day")
        if not stats:
            return {"status": "ok", "usage": 0}
        
        result = {
            "status": "ok",
            "checks": [],
        }
        
        # 检查每日调用限制
        if quota.max_calls_per_day:
            usage_pct = stats.total_calls / quota.max_calls_per_day
            result["checks"].append({
                "type": "calls_per_day",
                "current": stats.total_calls,
                "limit": quota.max_calls_per_day,
                "usage_pct": usage_pct,
            })
            
            if stats.total_calls >= quota.max_calls_per_day:
                if quota.block_on_exceed:
                    raise QuotaExceeded(
                        f"Daily call quota exceeded",
                        quota_type="calls_per_day",
                        current=stats.total_calls,
                        limit=quota.max_calls_per_day,
                    )
                result["status"] = "exceeded"
            elif usage_pct >= quota.warning_threshold:
                result["status"] = "warning"
        
        # 检查每日成本限制
        if quota.max_cost_per_day:
            usage_pct = stats.total_cost / quota.max_cost_per_day
            result["checks"].append({
                "type": "cost_per_day",
                "current": stats.total_cost,
                "limit": quota.max_cost_per_day,
                "usage_pct": usage_pct,
            })
            
            if stats.total_cost >= quota.max_cost_per_day:
                if quota.block_on_exceed:
                    raise QuotaExceeded(
                        f"Daily cost quota exceeded",
                        quota_type="cost_per_day",
                        current=stats.total_cost,
                        limit=quota.max_cost_per_day,
                    )
                result["status"] = "exceeded"
            elif usage_pct >= quota.warning_threshold:
                result["status"] = "warning"
        
        return result
```

---

## 五、Phase 2: 分布式链路追踪

### 5.1 设计方案

```python
# enterprise/tracing.py

"""
分布式链路追踪

兼容 OpenTelemetry 标准，支持：
- Trace: 完整调用链
- Span: 单次调用
- Context Propagation: 上下文传递
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import time
import uuid
from contextvars import ContextVar
from enum import Enum

# 当前追踪上下文
_current_span: ContextVar[Optional["Span"]] = ContextVar("current_span", default=None)

class SpanKind(Enum):
    """Span 类型"""
    INTERNAL = "internal"
    CLIENT = "client"    # 发起调用
    SERVER = "server"    # 接收调用
    PRODUCER = "producer"
    CONSUMER = "consumer"

class SpanStatus(Enum):
    """Span 状态"""
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"

@dataclass
class SpanContext:
    """Span 上下文（用于跨进程传递）"""
    trace_id: str
    span_id: str
    trace_flags: int = 1  # 采样标志
    trace_state: str = ""
    
    def to_headers(self) -> Dict[str, str]:
        """转换为 HTTP 头"""
        return {
            "traceparent": f"00-{self.trace_id}-{self.span_id}-{self.trace_flags:02x}",
            "tracestate": self.trace_state,
        }
    
    @classmethod
    def from_headers(cls, headers: Dict[str, str]) -> Optional["SpanContext"]:
        """从 HTTP 头解析"""
        traceparent = headers.get("traceparent")
        if not traceparent:
            return None
        
        parts = traceparent.split("-")
        if len(parts) != 4:
            return None
        
        return cls(
            trace_id=parts[1],
            span_id=parts[2],
            trace_flags=int(parts[3], 16),
            trace_state=headers.get("tracestate", ""),
        )

@dataclass
class Span:
    """调用跨度"""
    name: str
    context: SpanContext
    parent_id: Optional[str] = None
    kind: SpanKind = SpanKind.INTERNAL
    
    # 时间
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    
    # 状态
    status: SpanStatus = SpanStatus.UNSET
    status_message: str = ""
    
    # 属性和事件
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    
    # 资源信息
    service_name: str = ""
    
    def set_attribute(self, key: str, value: Any) -> None:
        """设置属性"""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
        """添加事件"""
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {},
        })
    
    def set_status(self, status: SpanStatus, message: str = "") -> None:
        """设置状态"""
        self.status = status
        self.status_message = message
    
    def end(self, end_time: Optional[float] = None) -> None:
        """结束 Span"""
        self.end_time = end_time or time.time()
    
    @property
    def duration_ms(self) -> float:
        """持续时间（毫秒）"""
        if self.end_time is None:
            return 0
        return (self.end_time - self.start_time) * 1000
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "trace_id": self.context.trace_id,
            "span_id": self.context.span_id,
            "parent_id": self.parent_id,
            "kind": self.kind.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "status": self.status.value,
            "status_message": self.status_message,
            "attributes": self.attributes,
            "events": self.events,
            "service_name": self.service_name,
        }

class Tracer:
    """
    追踪器
    
    创建和管理 Span。
    
    使用示例：
    ```python
    tracer = Tracer(service_name="ai-bridge")
    
    # 手动创建 Span
    with tracer.start_span("tool_call") as span:
        span.set_attribute("tool.name", "browser/navigate")
        span.set_attribute("user.id", "user123")
        
        # 嵌套 Span
        with tracer.start_span("mcp_call") as child:
            child.set_attribute("mcp.server", "browser-use")
            result = await mcp_server.call_tool(...)
        
        span.set_status(SpanStatus.OK)
    
    # 使用装饰器
    @tracer.trace("my_function")
    async def my_function():
        ...
    ```
    """
    
    def __init__(self, service_name: str = "ai-bridge", exporter: Optional["SpanExporter"] = None):
        self._service_name = service_name
        self._exporter = exporter
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        parent: Optional[SpanContext] = None,
        attributes: Optional[Dict[str, Any]] = None,
    ) -> "SpanContextManager":
        """
        创建新 Span
        
        Args:
            name: Span 名称
            kind: Span 类型
            parent: 父 Span 上下文（可选，默认使用当前上下文）
            attributes: 初始属性
            
        Returns:
            SpanContextManager
        """
        # 确定父 Span
        parent_span = _current_span.get()
        if parent:
            parent_context = parent
        elif parent_span:
            parent_context = parent_span.context
        else:
            parent_context = None
        
        # 生成 Span ID
        span_id = uuid.uuid4().hex[:16]
        
        # 确定 Trace ID
        if parent_context:
            trace_id = parent_context.trace_id
            parent_id = parent_context.span_id
        else:
            trace_id = uuid.uuid4().hex
            parent_id = None
        
        # 创建 Span
        span = Span(
            name=name,
            context=SpanContext(trace_id=trace_id, span_id=span_id),
            parent_id=parent_id,
            kind=kind,
            service_name=self._service_name,
        )
        
        if attributes:
            span.attributes.update(attributes)
        
        return SpanContextManager(span, self._exporter)
    
    def trace(
        self,
        name: Optional[str] = None,
        kind: SpanKind = SpanKind.INTERNAL,
    ):
        """
        装饰器：自动追踪函数调用
        """
        def decorator(func):
            span_name = name or func.__name__
            
            async def async_wrapper(*args, **kwargs):
                with self.start_span(span_name, kind) as span:
                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(SpanStatus.OK)
                        return result
                    except Exception as e:
                        span.set_status(SpanStatus.ERROR, str(e))
                        span.add_event("exception", {"message": str(e)})
                        raise
            
            def sync_wrapper(*args, **kwargs):
                with self.start_span(span_name, kind) as span:
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(SpanStatus.OK)
                        return result
                    except Exception as e:
                        span.set_status(SpanStatus.ERROR, str(e))
                        span.add_event("exception", {"message": str(e)})
                        raise
            
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper
        
        return decorator
    
    def get_current_span(self) -> Optional[Span]:
        """获取当前 Span"""
        return _current_span.get()
    
    def get_current_context(self) -> Optional[SpanContext]:
        """获取当前追踪上下文"""
        span = _current_span.get()
        return span.context if span else None

class SpanContextManager:
    """Span 上下文管理器"""
    
    def __init__(self, span: Span, exporter: Optional["SpanExporter"]):
        self._span = span
        self._exporter = exporter
        self._token = None
    
    def __enter__(self) -> Span:
        self._token = _current_span.set(self._span)
        return self._span
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self._span.end()
        _current_span.reset(self._token)
        
        # 导出 Span
        if self._exporter:
            self._exporter.export(self._span)
        
        return False

class SpanExporter:
    """Span 导出器基类"""
    
    def export(self, span: Span) -> None:
        """导出 Span"""
        raise NotImplementedError

class ConsoleSpanExporter(SpanExporter):
    """控制台导出器"""
    
    def export(self, span: Span) -> None:
        import json
        print(f"[TRACE] {json.dumps(span.to_dict(), default=str)}")

class AuditSpanExporter(SpanExporter):
    """审计日志导出器"""
    
    def __init__(self, audit_logger: AuditLogger):
        self._audit = audit_logger
    
    def export(self, span: Span) -> None:
        asyncio.create_task(self._audit.log(
            action="trace.span",
            level=AuditLevel.DEBUG,
            resource=span.name,
            duration_ms=span.duration_ms,
            success=span.status != SpanStatus.ERROR,
            metadata=span.to_dict(),
        ))
```

---

## 六、Phase 2: 协议桥接增强

### 6.1 双向协议转换

```python
# gateway/protocol_bridge.py (增强)

class ProtocolBridge:
    """
    协议桥接器（增强版）
    
    支持 MCP ↔ A2A 双向转换。
    """
    
    # ... 现有代码 ...
    
    # ===== 新增：A2A → MCP 方向 =====
    
    def a2a_capability_to_mcp_tool(self, capability: AgentCapability) -> ToolSchema:
        """
        将 A2A 能力转换为 MCP Tool
        
        Args:
            capability: A2A 能力描述
            
        Returns:
            ToolSchema: MCP Tool Schema
        """
        return ToolSchema(
            name=capability.name,
            description=capability.description,
            input_schema=capability.input_schema or {},
        )
    
    def a2a_agent_to_mcp_server(self, agent: AgentCard) -> MCPServerConfig:
        """
        将 A2A Agent 转换为虚拟 MCP Server
        
        Args:
            agent: A2A Agent 名片
            
        Returns:
            MCPServerConfig
        """
        return MCPServerConfig(
            name=f"a2a-{agent.agent_id}",
            description=f"MCP Server bridged from A2A Agent '{agent.name}'",
            tools=[
                self.a2a_capability_to_mcp_tool(cap) 
                for cap in agent.capabilities
            ],
            metadata={
                "bridge_type": "a2a_to_mcp",
                "a2a_agent": agent.agent_id,
            }
        )
    
    async def expose_a2a_as_mcp(self, agent_id: str) -> Optional[MCPServerConfig]:
        """
        将 A2A Agent 暴露为 MCP Server
        """
        agent = await self._a2a.get_agent(agent_id)
        if not agent:
            logger.warning(f"A2A Agent {agent_id} not found")
            return None
        
        # 创建虚拟 MCP Server
        server_config = self.a2a_agent_to_mcp_server(agent)
        
        # 注册到 MCP Registry
        await self._mcp.register_virtual_server(
            server_config,
            handler=lambda tool, params: self._route_mcp_to_a2a(agent_id, tool, params)
        )
        
        self._a2a_servers[agent_id] = server_config.name
        
        logger.info(f"Exposed A2A Agent {agent_id} as MCP Server {server_config.name}")
        return server_config
    
    async def _route_mcp_to_a2a(
        self, 
        agent_id: str, 
        tool_name: str, 
        params: Dict[str, Any]
    ) -> Any:
        """
        将 MCP 调用路由到 A2A Agent
        """
        task = A2ATask(
            from_agent="mcp-bridge",
            to_agent=agent_id,
            capability=tool_name,
            input_data=params,
        )
        
        handle = await self._a2a.send_task(task)
        return await handle.wait_for_completion()
```

### 6.2 多 Agent 编排

```python
# gateway/orchestrator.py

"""
多 Agent 编排器

支持复杂的 Agent 协作场景：
- 串行执行
- 并行执行
- 条件分支
- 循环
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union
import asyncio

class TaskNodeType(Enum):
    """任务节点类型"""
    CALL = "call"           # 调用 Agent
    PARALLEL = "parallel"   # 并行执行
    SEQUENCE = "sequence"   # 串行执行
    CONDITION = "condition" # 条件分支
    LOOP = "loop"           # 循环

@dataclass
class TaskNode:
    """任务节点"""
    node_id: str
    node_type: TaskNodeType
    
    # CALL 节点
    agent_id: Optional[str] = None
    capability: Optional[str] = None
    input_mapping: Optional[Dict[str, str]] = None  # 输入映射
    
    # PARALLEL/SEQUENCE 节点
    children: List["TaskNode"] = field(default_factory=list)
    
    # CONDITION 节点
    condition: Optional[str] = None  # 条件表达式
    if_branch: Optional["TaskNode"] = None
    else_branch: Optional["TaskNode"] = None
    
    # LOOP 节点
    loop_var: Optional[str] = None
    loop_items: Optional[str] = None  # 引用变量
    loop_body: Optional["TaskNode"] = None

@dataclass
class TaskGraph:
    """任务图"""
    graph_id: str
    name: str
    description: str = ""
    root: Optional[TaskNode] = None
    variables: Dict[str, Any] = field(default_factory=dict)

class Orchestrator:
    """
    编排器
    
    执行复杂的多 Agent 工作流。
    
    使用示例：
    ```python
    orchestrator = Orchestrator(a2a_gateway, protocol_bridge)
    
    # 定义工作流
    graph = TaskGraph(
        graph_id="web-research",
        name="Web Research Workflow",
        root=TaskNode(
            node_id="root",
            node_type=TaskNodeType.SEQUENCE,
            children=[
                TaskNode(
                    node_id="search",
                    node_type=TaskNodeType.CALL,
                    agent_id="mcp-browser-use",
                    capability="search",
                    input_mapping={"query": "$.input.query"},
                ),
                TaskNode(
                    node_id="analyze",
                    node_type=TaskNodeType.PARALLEL,
                    children=[
                        TaskNode(
                            node_id="summarize",
                            node_type=TaskNodeType.CALL,
                            agent_id="llm-agent",
                            capability="summarize",
                            input_mapping={"text": "$.search.result"},
                        ),
                        TaskNode(
                            node_id="extract",
                            node_type=TaskNodeType.CALL,
                            agent_id="llm-agent",
                            capability="extract_entities",
                            input_mapping={"text": "$.search.result"},
                        ),
                    ]
                ),
            ]
        )
    )
    
    # 执行工作流
    result = await orchestrator.execute(graph, {"query": "AI-Bridge"})
    ```
    """
    
    def __init__(
        self, 
        a2a_gateway: A2AGateway, 
        protocol_bridge: ProtocolBridge,
        tracer: Optional[Tracer] = None,
    ):
        self._a2a = a2a_gateway
        self._bridge = protocol_bridge
        self._tracer = tracer
    
    async def execute(
        self, 
        graph: TaskGraph, 
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行任务图
        
        Args:
            graph: 任务图
            input_data: 输入数据
            
        Returns:
            执行结果
        """
        context = {
            "input": input_data,
            "variables": graph.variables.copy(),
            "results": {},
        }
        
        if graph.root:
            await self._execute_node(graph.root, context)
        
        return context["results"]
    
    async def _execute_node(
        self, 
        node: TaskNode, 
        context: Dict[str, Any]
    ) -> Any:
        """执行单个节点"""
        
        if node.node_type == TaskNodeType.CALL:
            return await self._execute_call(node, context)
        
        elif node.node_type == TaskNodeType.SEQUENCE:
            return await self._execute_sequence(node, context)
        
        elif node.node_type == TaskNodeType.PARALLEL:
            return await self._execute_parallel(node, context)
        
        elif node.node_type == TaskNodeType.CONDITION:
            return await self._execute_condition(node, context)
        
        elif node.node_type == TaskNodeType.LOOP:
            return await self._execute_loop(node, context)
    
    async def _execute_call(
        self, 
        node: TaskNode, 
        context: Dict[str, Any]
    ) -> Any:
        """执行调用节点"""
        # 解析输入
        params = {}
        if node.input_mapping:
            for key, path in node.input_mapping.items():
                params[key] = self._resolve_path(path, context)
        
        # 创建任务
        task = A2ATask(
            from_agent="orchestrator",
            to_agent=node.agent_id,
            capability=node.capability,
            input_data=params,
        )
        
        # 执行（通过 Protocol Bridge 自动路由）
        result = await self._bridge.execute_task(task)
        
        # 保存结果
        context["results"][node.node_id] = result
        
        return result
    
    async def _execute_sequence(
        self, 
        node: TaskNode, 
        context: Dict[str, Any]
    ) -> List[Any]:
        """串行执行子节点"""
        results = []
        for child in node.children:
            result = await self._execute_node(child, context)
            results.append(result)
        return results
    
    async def _execute_parallel(
        self, 
        node: TaskNode, 
        context: Dict[str, Any]
    ) -> List[Any]:
        """并行执行子节点"""
        tasks = [
            self._execute_node(child, context) 
            for child in node.children
        ]
        return await asyncio.gather(*tasks)
    
    async def _execute_condition(
        self, 
        node: TaskNode, 
        context: Dict[str, Any]
    ) -> Any:
        """执行条件分支"""
        # 简单表达式求值
        condition_result = self._evaluate_condition(node.condition, context)
        
        if condition_result:
            if node.if_branch:
                return await self._execute_node(node.if_branch, context)
        else:
            if node.else_branch:
                return await self._execute_node(node.else_branch, context)
        
        return None
    
    async def _execute_loop(
        self, 
        node: TaskNode, 
        context: Dict[str, Any]
    ) -> List[Any]:
        """执行循环"""
        items = self._resolve_path(node.loop_items, context)
        results = []
        
        for item in items:
            # 设置循环变量
            context["variables"][node.loop_var] = item
            
            if node.loop_body:
                result = await self._execute_node(node.loop_body, context)
                results.append(result)
        
        return results
    
    def _resolve_path(self, path: str, context: Dict[str, Any]) -> Any:
        """解析路径引用 (如 $.input.query)"""
        if not path.startswith("$."):
            return path
        
        parts = path[2:].split(".")
        value = context
        
        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        
        return value
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件表达式"""
        # 简化实现，实际应使用安全的表达式引擎
        try:
            # 替换路径引用
            import re
            def replace_path(match):
                path = match.group(0)
                value = self._resolve_path(path, context)
                return repr(value)
            
            expr = re.sub(r'\$\.[a-zA-Z0-9_.]+', replace_path, condition)
            return bool(eval(expr))
        except Exception:
            return False
```

---

## 七、文件结构

```
ai-bridge/src/aibridge/
├── enterprise/
│   ├── __init__.py          # 导出所有企业级模块
│   ├── auth.py              # 认证 (现有)
│   ├── audit.py             # 审计 (现有)
│   ├── rate_limit.py        # 限流 (现有)
│   ├── health.py            # 健康检查 (现有)
│   ├── policy.py            # 🆕 工具级权限策略
│   ├── metering.py          # 🆕 调用成本计量
│   └── tracing.py           # 🆕 分布式链路追踪
│
├── gateway/
│   ├── __init__.py          # 导出所有网关模块
│   ├── mcp_registry.py      # MCP 注册中心 (现有)
│   ├── mcp_protocol.py      # MCP 协议 (现有)
│   ├── a2a_gateway.py       # A2A 网关 (现有)
│   ├── discovery.py         # 服务发现 (现有)
│   ├── protocol_bridge.py   # 协议桥接 (增强)
│   └── orchestrator.py      # 🆕 多 Agent 编排器
```

---

## 八、实施计划

### Phase 1 (P0 - 2周)

| 任务 | 工作量 | 交付物 |
|------|--------|--------|
| 工具级权限策略 | 3天 | enterprise/policy.py |
| 调用成本计量 | 3天 | enterprise/metering.py |
| 单元测试 | 2天 | tests/test_policy.py, tests/test_metering.py |
| 集成测试 | 1天 | tests/test_enterprise_integration.py |
| 文档更新 | 1天 | README 更新 |

### Phase 2 (P1 - 2周)

| 任务 | 工作量 | 交付物 |
|------|--------|--------|
| 分布式链路追踪 | 4天 | enterprise/tracing.py |
| 双向协议转换 | 2天 | gateway/protocol_bridge.py 增强 |
| 多 Agent 编排 | 3天 | gateway/orchestrator.py |
| 测试 & 文档 | 1天 | 测试 + README |

---

## 九、验收标准

### 功能验收

1. **工具级权限**
   - [ ] 可以配置用户只能使用特定工具
   - [ ] 显式 DENY 优先于 ALLOW
   - [ ] 策略变更实时生效

2. **调用成本计量**
   - [ ] 按用户/工具/时间维度统计
   - [ ] 配额超限自动阻止
   - [ ] 可导出使用报告

3. **链路追踪**
   - [ ] 跨 MCP Server 调用链完整
   - [ ] 兼容 OpenTelemetry
   - [ ] 可导出到审计日志

4. **协议桥接**
   - [ ] MCP → A2A 双向转换
   - [ ] A2A → MCP 双向转换
   - [ ] 多 Agent 工作流可执行

### 性能验收

- 策略评估延迟 < 1ms
- 计量采集不阻塞主流程
- 追踪 overhead < 5%

---

## 十、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 策略复杂度导致性能下降 | 中 | 策略预编译 + 缓存 |
| 计量数据量过大 | 中 | 分层聚合 + 定期清理 |
| 追踪影响主流程 | 低 | 异步采集 + 采样 |
| 编排器表达式注入 | 高 | 沙箱执行 + 白名单 |

---

## 附录：预定义策略示例

```yaml
# policies/browser-only.yaml
policy_id: browser-only
name: Browser Only Access
description: Only browser tools are allowed
priority: 30
statements:
  - sid: allow-browser
    effect: allow
    actions: [tool:call]
    resources:
      - browser/*
      - mcp-browser-*/*
  - sid: deny-others
    effect: deny
    actions: [tool:call]
    resources: ["*"]
```

```yaml
# policies/cost-limited.yaml
policy_id: cost-limited
name: Cost Limited User
description: Limited daily cost
quota:
  max_calls_per_day: 1000
  max_cost_per_day: 10.0
  warning_threshold: 0.8
  block_on_exceed: true
```

---

**文档维护者**: AI-Bridge Team  
**最后更新**: 2026-03-15
