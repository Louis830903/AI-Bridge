"""
测试 policy.py - 工具级权限策略引擎
"""

import pytest
from dataclasses import dataclass
from typing import Optional

from aibridge.enterprise.policy import (
    PolicyEngine,
    PolicyMiddleware,
    PolicyStatement,
    PolicyEffect,
    PolicyAction,
    PolicyCondition,
    PolicyEvaluationResult,
    ToolPolicy,
    BUILTIN_POLICIES,
    get_builtin_policy,
    list_builtin_policies,
)


# ===== Mock AuthContext =====

@dataclass
class MockRole:
    name: str


@dataclass
class MockAuthContext:
    user_id: str
    role: Optional[MockRole] = None
    authenticated: bool = True


# ===== PolicyCondition Tests =====

class TestPolicyCondition:
    """测试策略条件"""
    
    def test_eq_operator(self):
        """测试等于操作符"""
        cond = PolicyCondition(key="user.level", operator="eq", value="admin")
        assert cond.evaluate({"user": {"level": "admin"}}) is True
        assert cond.evaluate({"user": {"level": "user"}}) is False
    
    def test_ne_operator(self):
        """测试不等于操作符"""
        cond = PolicyCondition(key="env", operator="ne", value="prod")
        assert cond.evaluate({"env": "dev"}) is True
        assert cond.evaluate({"env": "prod"}) is False
    
    def test_gt_lt_operators(self):
        """测试大于/小于操作符"""
        cond_gt = PolicyCondition(key="count", operator="gt", value=10)
        assert cond_gt.evaluate({"count": 15}) is True
        assert cond_gt.evaluate({"count": 5}) is False
        
        cond_lt = PolicyCondition(key="count", operator="lt", value=10)
        assert cond_lt.evaluate({"count": 5}) is True
        assert cond_lt.evaluate({"count": 15}) is False
    
    def test_in_operator(self):
        """测试 in 操作符"""
        cond = PolicyCondition(key="region", operator="in", value=["us", "eu", "cn"])
        assert cond.evaluate({"region": "us"}) is True
        assert cond.evaluate({"region": "jp"}) is False
    
    def test_contains_operator(self):
        """测试 contains 操作符"""
        cond = PolicyCondition(key="tags", operator="contains", value="premium")
        assert cond.evaluate({"tags": ["free", "premium", "basic"]}) is True
        assert cond.evaluate({"tags": ["free", "basic"]}) is False
    
    def test_startswith_operator(self):
        """测试 startswith 操作符"""
        cond = PolicyCondition(key="tool", operator="startswith", value="browser/")
        assert cond.evaluate({"tool": "browser/navigate"}) is True
        assert cond.evaluate({"tool": "database/query"}) is False
    
    def test_regex_operator(self):
        """测试 regex 操作符"""
        cond = PolicyCondition(key="path", operator="regex", value=r"^/api/v\d+/.*")
        assert cond.evaluate({"path": "/api/v1/users"}) is True
        assert cond.evaluate({"path": "/static/file.js"}) is False
    
    def test_nested_key(self):
        """测试嵌套键访问"""
        cond = PolicyCondition(key="request.headers.auth", operator="eq", value="valid")
        context = {
            "request": {
                "headers": {
                    "auth": "valid"
                }
            }
        }
        assert cond.evaluate(context) is True
    
    def test_missing_key(self):
        """测试缺失键"""
        cond = PolicyCondition(key="missing.key", operator="eq", value="any")
        assert cond.evaluate({}) is False


# ===== PolicyStatement Tests =====

class TestPolicyStatement:
    """测试策略声明"""
    
    def test_action_match(self):
        """测试动作匹配"""
        stmt = PolicyStatement(
            sid="test",
            effect=PolicyEffect.ALLOW,
            actions={PolicyAction.CALL_TOOL, PolicyAction.LIST_TOOLS},
            resources=["*"],
        )
        assert stmt.matches_action(PolicyAction.CALL_TOOL) is True
        assert stmt.matches_action(PolicyAction.LIST_TOOLS) is True
        assert stmt.matches_action(PolicyAction.MANAGE_SERVER) is False
    
    def test_action_wildcard(self):
        """测试动作通配符"""
        stmt = PolicyStatement(
            sid="test",
            effect=PolicyEffect.ALLOW,
            actions={PolicyAction.ALL},
            resources=["*"],
        )
        assert stmt.matches_action(PolicyAction.CALL_TOOL) is True
        assert stmt.matches_action(PolicyAction.MANAGE_SERVER) is True
    
    def test_resource_exact_match(self):
        """测试资源精确匹配"""
        stmt = PolicyStatement(
            sid="test",
            effect=PolicyEffect.ALLOW,
            actions={PolicyAction.CALL_TOOL},
            resources=["browser/navigate"],
        )
        assert stmt.matches_resource("browser/navigate") is True
        assert stmt.matches_resource("browser/click") is False
    
    def test_resource_wildcard(self):
        """测试资源通配符"""
        stmt = PolicyStatement(
            sid="test",
            effect=PolicyEffect.ALLOW,
            actions={PolicyAction.CALL_TOOL},
            resources=["browser/*"],
        )
        assert stmt.matches_resource("browser/navigate") is True
        assert stmt.matches_resource("browser/click") is True
        assert stmt.matches_resource("database/query") is False
    
    def test_resource_single_char_wildcard(self):
        """测试单字符通配符"""
        stmt = PolicyStatement(
            sid="test",
            effect=PolicyEffect.ALLOW,
            actions={PolicyAction.CALL_TOOL},
            resources=["browser/v?"],
        )
        assert stmt.matches_resource("browser/v1") is True
        assert stmt.matches_resource("browser/v2") is True
        assert stmt.matches_resource("browser/v10") is False
    
    def test_resource_universal_wildcard(self):
        """测试全局通配符"""
        stmt = PolicyStatement(
            sid="test",
            effect=PolicyEffect.ALLOW,
            actions={PolicyAction.CALL_TOOL},
            resources=["*"],
        )
        assert stmt.matches_resource("anything") is True
        assert stmt.matches_resource("browser/navigate") is True
    
    def test_full_match(self):
        """测试完整匹配"""
        stmt = PolicyStatement(
            sid="test",
            effect=PolicyEffect.ALLOW,
            actions={PolicyAction.CALL_TOOL},
            resources=["browser/*"],
            conditions=[
                PolicyCondition(key="env", operator="eq", value="prod")
            ]
        )
        # 满足所有条件
        assert stmt.matches(
            PolicyAction.CALL_TOOL,
            "browser/navigate",
            {"env": "prod"}
        ) is True
        
        # 动作不匹配
        assert stmt.matches(
            PolicyAction.LIST_TOOLS,
            "browser/navigate",
            {"env": "prod"}
        ) is False
        
        # 资源不匹配
        assert stmt.matches(
            PolicyAction.CALL_TOOL,
            "database/query",
            {"env": "prod"}
        ) is False
        
        # 条件不匹配
        assert stmt.matches(
            PolicyAction.CALL_TOOL,
            "browser/navigate",
            {"env": "dev"}
        ) is False


# ===== ToolPolicy Tests =====

class TestToolPolicy:
    """测试工具访问策略"""
    
    def test_evaluate_allow(self):
        """测试策略评估 - 允许"""
        policy = ToolPolicy(
            policy_id="test",
            name="Test Policy",
            statements=[
                PolicyStatement(
                    sid="allow-browser",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["browser/*"],
                )
            ]
        )
        
        result = policy.evaluate(PolicyAction.CALL_TOOL, "browser/navigate")
        assert result == PolicyEffect.ALLOW
    
    def test_evaluate_deny(self):
        """测试策略评估 - 拒绝"""
        policy = ToolPolicy(
            policy_id="test",
            name="Test Policy",
            statements=[
                PolicyStatement(
                    sid="deny-all",
                    effect=PolicyEffect.DENY,
                    actions={PolicyAction.ALL},
                    resources=["*"],
                )
            ]
        )
        
        result = policy.evaluate(PolicyAction.CALL_TOOL, "browser/navigate")
        assert result == PolicyEffect.DENY
    
    def test_evaluate_no_match(self):
        """测试策略评估 - 无匹配"""
        policy = ToolPolicy(
            policy_id="test",
            name="Test Policy",
            statements=[
                PolicyStatement(
                    sid="allow-browser",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["browser/*"],
                )
            ]
        )
        
        result = policy.evaluate(PolicyAction.CALL_TOOL, "database/query")
        assert result is None
    
    def test_add_remove_statement(self):
        """测试添加/移除策略声明"""
        policy = ToolPolicy(policy_id="test", name="Test")
        
        stmt = PolicyStatement(
            sid="stmt1",
            effect=PolicyEffect.ALLOW,
            actions={PolicyAction.CALL_TOOL},
            resources=["*"],
        )
        
        policy.add_statement(stmt)
        assert len(policy.statements) == 1
        
        result = policy.remove_statement("stmt1")
        assert result is True
        assert len(policy.statements) == 0
        
        result = policy.remove_statement("nonexistent")
        assert result is False


# ===== PolicyEngine Tests =====

class TestPolicyEngine:
    """测试策略引擎"""
    
    def test_register_unregister_policy(self):
        """测试注册/注销策略"""
        engine = PolicyEngine()
        
        policy = ToolPolicy(
            policy_id="test-policy",
            name="Test Policy",
            statements=[
                PolicyStatement(
                    sid="allow-all",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.ALL},
                    resources=["*"],
                )
            ]
        )
        
        engine.register_policy(policy)
        assert engine.get_policy("test-policy") is not None
        
        engine.unregister_policy("test-policy")
        assert engine.get_policy("test-policy") is None
    
    def test_attach_detach_policy(self):
        """测试绑定/解绑策略"""
        engine = PolicyEngine()
        
        policy = ToolPolicy(policy_id="test", name="Test")
        engine.register_policy(policy)
        
        # 绑定到用户
        result = engine.attach_policy("user:alice", "test")
        assert result is True
        
        # 绑定到角色
        result = engine.attach_policy("role:admin", "test")
        assert result is True
        
        # 绑定不存在的策略
        result = engine.attach_policy("user:bob", "nonexistent")
        assert result is False
        
        # 解绑
        result = engine.detach_policy("user:alice", "test")
        assert result is True
    
    def test_get_policies_for_user(self):
        """测试获取用户策略"""
        engine = PolicyEngine()
        
        policy1 = ToolPolicy(policy_id="user-policy", name="User Policy", priority=10)
        policy2 = ToolPolicy(policy_id="role-policy", name="Role Policy", priority=20)
        
        engine.register_policy(policy1)
        engine.register_policy(policy2)
        
        engine.attach_policy("user:alice", "user-policy")
        engine.attach_policy("role:admin", "role-policy")
        
        # 仅用户策略
        policies = engine.get_policies_for_user("alice")
        assert len(policies) == 1
        assert policies[0].policy_id == "user-policy"
        
        # 用户 + 角色策略（按优先级排序）
        policies = engine.get_policies_for_user("alice", role="admin")
        assert len(policies) == 2
        assert policies[0].policy_id == "role-policy"  # 优先级更高
        assert policies[1].policy_id == "user-policy"
    
    def test_evaluate_explicit_deny(self):
        """测试评估 - 显式拒绝优先"""
        engine = PolicyEngine()
        
        policy = ToolPolicy(
            policy_id="mixed",
            name="Mixed Policy",
            statements=[
                PolicyStatement(
                    sid="allow-browser",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["browser/*"],
                ),
                PolicyStatement(
                    sid="deny-sensitive",
                    effect=PolicyEffect.DENY,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["browser/execute_script"],
                ),
            ]
        )
        
        engine.register_policy(policy)
        engine.attach_policy("user:alice", "mixed")
        
        # 允许普通浏览器操作
        result = engine.evaluate("alice", PolicyAction.CALL_TOOL, "browser/navigate")
        assert result.allowed is True
        
        # 拒绝敏感操作
        result = engine.evaluate("alice", PolicyAction.CALL_TOOL, "browser/execute_script")
        assert result.allowed is False
        assert result.matched_statement == "deny-sensitive"
    
    def test_evaluate_no_policy(self):
        """测试评估 - 无策略"""
        engine = PolicyEngine(default_deny=True)
        
        result = engine.evaluate("unknown_user", PolicyAction.CALL_TOOL, "any/tool")
        assert result.allowed is False
        assert "No policy attached" in result.reason
        
        # 默认允许模式
        engine_allow = PolicyEngine(default_deny=False)
        result = engine_allow.evaluate("unknown_user", PolicyAction.CALL_TOOL, "any/tool")
        assert result.allowed is True
    
    def test_evaluate_with_context(self):
        """测试带上下文的评估"""
        engine = PolicyEngine()
        
        policy = ToolPolicy(
            policy_id="conditional",
            name="Conditional Policy",
            statements=[
                PolicyStatement(
                    sid="allow-in-working-hours",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["*"],
                    conditions=[
                        PolicyCondition(key="time.hour", operator="gte", value=9),
                        PolicyCondition(key="time.hour", operator="lte", value=17),
                    ]
                ),
            ]
        )
        
        engine.register_policy(policy)
        engine.attach_policy("user:alice", "conditional")
        
        # 工作时间内
        result = engine.evaluate(
            "alice",
            PolicyAction.CALL_TOOL,
            "any/tool",
            context={"time": {"hour": 10}}
        )
        assert result.allowed is True
        
        # 工作时间外
        result = engine.evaluate(
            "alice",
            PolicyAction.CALL_TOOL,
            "any/tool",
            context={"time": {"hour": 22}}
        )
        assert result.allowed is False
    
    def test_cache_functionality(self):
        """测试缓存功能"""
        engine = PolicyEngine()
        
        policy = ToolPolicy(
            policy_id="test",
            name="Test",
            statements=[
                PolicyStatement(
                    sid="allow-all",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.ALL},
                    resources=["*"],
                )
            ]
        )
        
        engine.register_policy(policy)
        engine.attach_policy("user:alice", "test")
        
        # 第一次评估
        result1 = engine.evaluate("alice", PolicyAction.CALL_TOOL, "browser/navigate")
        
        # 第二次评估应该命中缓存
        result2 = engine.evaluate("alice", PolicyAction.CALL_TOOL, "browser/navigate")
        
        assert result1.allowed == result2.allowed
        
        # 禁用缓存
        engine.set_cache_enabled(False)
        stats = engine.get_stats()
        assert stats["cache_enabled"] is False
        assert stats["cache_size"] == 0
    
    def test_stats(self):
        """测试统计信息"""
        engine = PolicyEngine()
        
        policy = ToolPolicy(policy_id="test", name="Test")
        engine.register_policy(policy)
        engine.attach_policy("user:alice", "test")
        engine.attach_policy("role:admin", "test")
        
        stats = engine.get_stats()
        assert stats["policies_count"] == 1
        assert stats["user_bindings"] == 1
        assert stats["role_bindings"] == 1


# ===== PolicyMiddleware Tests =====

class TestPolicyMiddleware:
    """测试策略中间件"""
    
    def test_check_tool_access_allowed(self):
        """测试工具访问检查 - 允许"""
        engine = PolicyEngine()
        
        policy = ToolPolicy(
            policy_id="allow-browser",
            name="Allow Browser",
            statements=[
                PolicyStatement(
                    sid="allow",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["browser/*"],
                )
            ]
        )
        
        engine.register_policy(policy)
        engine.attach_policy("user:alice", "allow-browser")
        
        middleware = PolicyMiddleware(engine)
        auth_ctx = MockAuthContext(user_id="alice")
        
        result = middleware.check_tool_access(auth_ctx, "browser/navigate")
        assert result.allowed is True
    
    def test_check_tool_access_denied(self):
        """测试工具访问检查 - 拒绝"""
        engine = PolicyEngine()
        
        policy = ToolPolicy(
            policy_id="deny-all",
            name="Deny All",
            statements=[
                PolicyStatement(
                    sid="deny",
                    effect=PolicyEffect.DENY,
                    actions={PolicyAction.ALL},
                    resources=["*"],
                )
            ]
        )
        
        engine.register_policy(policy)
        engine.attach_policy("user:alice", "deny-all")
        
        middleware = PolicyMiddleware(engine)
        auth_ctx = MockAuthContext(user_id="alice")
        
        with pytest.raises(PermissionError) as exc_info:
            middleware.check_tool_access(auth_ctx, "browser/navigate")
        
        assert "Access denied" in str(exc_info.value)
    
    def test_check_with_role(self):
        """测试带角色的访问检查"""
        engine = PolicyEngine()
        
        policy = ToolPolicy(
            policy_id="admin-only",
            name="Admin Only",
            statements=[
                PolicyStatement(
                    sid="allow-admin",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.ALL},
                    resources=["*"],
                )
            ]
        )
        
        engine.register_policy(policy)
        engine.attach_policy("role:admin", "admin-only")
        
        middleware = PolicyMiddleware(engine)
        
        # 非管理员被拒绝
        auth_ctx = MockAuthContext(user_id="alice", role=None)
        with pytest.raises(PermissionError):
            middleware.check_tool_access(auth_ctx, "sensitive/tool")
        
        # 管理员允许
        auth_ctx = MockAuthContext(user_id="bob", role=MockRole("admin"))
        result = middleware.check_tool_access(auth_ctx, "sensitive/tool")
        assert result.allowed is True


# ===== Builtin Policies Tests =====

class TestBuiltinPolicies:
    """测试内置策略"""
    
    def test_list_builtin_policies(self):
        """测试列出内置策略"""
        policies = list_builtin_policies()
        assert len(policies) > 0
        assert "admin-full-access" in policies
        assert "viewer-readonly" in policies
    
    def test_get_admin_policy(self):
        """测试管理员策略"""
        policy = get_builtin_policy("admin-full-access")
        assert policy is not None
        assert policy.name == "Admin Full Access"
        
        # 管理员可以做任何事
        result = policy.evaluate(PolicyAction.CALL_TOOL, "any/tool")
        assert result == PolicyEffect.ALLOW
        
        result = policy.evaluate(PolicyAction.MANAGE_SERVER, "server/config")
        assert result == PolicyEffect.ALLOW
    
    def test_get_viewer_policy(self):
        """测试只读策略"""
        policy = get_builtin_policy("viewer-readonly")
        assert policy is not None
        
        # 可以列出工具
        result = policy.evaluate(PolicyAction.LIST_TOOLS, "any")
        assert result == PolicyEffect.ALLOW
        
        # 不能执行工具
        result = policy.evaluate(PolicyAction.CALL_TOOL, "browser/navigate")
        assert result == PolicyEffect.DENY
    
    def test_get_browser_only_policy(self):
        """测试仅浏览器策略"""
        policy = get_builtin_policy("browser-only")
        assert policy is not None
        
        # 可以用浏览器工具
        result = policy.evaluate(PolicyAction.CALL_TOOL, "browser/navigate")
        assert result == PolicyEffect.ALLOW
        
        # 不能用数据库工具（无匹配，返回 None）
        result = policy.evaluate(PolicyAction.CALL_TOOL, "database/query")
        assert result is None
    
    def test_get_nonexistent_policy(self):
        """测试获取不存在的策略"""
        policy = get_builtin_policy("nonexistent")
        assert policy is None


# ===== Integration Tests =====

class TestPolicyIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        # 1. 创建引擎
        engine = PolicyEngine(default_deny=True)
        
        # 2. 注册内置策略
        engine.register_policy(get_builtin_policy("admin-full-access"))
        engine.register_policy(get_builtin_policy("browser-only"))
        
        # 3. 创建自定义策略
        custom = ToolPolicy(
            policy_id="dev-policy",
            name="Developer Policy",
            priority=50,
            statements=[
                PolicyStatement(
                    sid="allow-dev-tools",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["database/*", "filesystem/read*"],
                ),
                PolicyStatement(
                    sid="deny-delete",
                    effect=PolicyEffect.DENY,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["*/delete*", "*/drop*"],
                ),
            ]
        )
        engine.register_policy(custom)
        
        # 4. 绑定策略
        engine.attach_policy("role:admin", "admin-full-access")
        engine.attach_policy("role:developer", "dev-policy")
        engine.attach_policy("role:viewer", "browser-only")
        
        # 5. 创建中间件
        middleware = PolicyMiddleware(engine)
        
        # 6. 测试管理员
        admin = MockAuthContext(user_id="admin1", role=MockRole("admin"))
        result = middleware.check_tool_access(admin, "anything/anywhere")
        assert result.allowed is True
        
        # 7. 测试开发者
        dev = MockAuthContext(user_id="dev1", role=MockRole("developer"))
        
        result = middleware.check_tool_access(dev, "database/query")
        assert result.allowed is True
        
        with pytest.raises(PermissionError):
            middleware.check_tool_access(dev, "database/drop_table")
        
        # 8. 测试查看者
        viewer = MockAuthContext(user_id="viewer1", role=MockRole("viewer"))
        
        result = middleware.check_tool_access(viewer, "browser/navigate")
        assert result.allowed is True
        
        with pytest.raises(PermissionError):
            middleware.check_tool_access(viewer, "database/query")
