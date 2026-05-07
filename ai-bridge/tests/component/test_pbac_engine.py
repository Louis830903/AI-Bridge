"""
Component Tests — PBAC 策略引擎 (L1)

Phase IV v1.0.0 — PolicyEngine 规则注册、评估和优先级逻辑。
"""

from __future__ import annotations

import pytest

from aibridge.enterprise.policy import (
    PolicyEngine,
    ToolPolicy,
    PolicyStatement,
    PolicyEffect,
    PolicyAction,
    PolicyEvaluationResult,
)


class TestPBACEngine:
    """PolicyEngine 组件测试"""

    @pytest.fixture
    def engine(self):
        return PolicyEngine(default_deny=True)

    @pytest.fixture
    def allow_policy(self):
        return ToolPolicy(
            policy_id="dev-allow",
            name="Developer Allow",
            statements=[
                PolicyStatement(
                    sid="allow-browser",
                    effect=PolicyEffect.ALLOW,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["browser/*", "database/*"],
                ),
            ],
        )

    @pytest.fixture
    def deny_policy(self):
        return ToolPolicy(
            policy_id="prod-deny",
            name="Production Deny",
            statements=[
                PolicyStatement(
                    sid="deny-filesystem",
                    effect=PolicyEffect.DENY,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["filesystem/*"],
                ),
            ],
        )

    # ── 允许场景 ──────────────────────────────────────────────

    def test_allow_matching_resource(self, engine, allow_policy):
        """资源匹配时 ALLOW 策略放行"""
        engine.register_policy(allow_policy)
        engine.attach_policy("user:dev1", "dev-allow")
        result = engine.evaluate("dev1", PolicyAction.CALL_TOOL, "browser/navigate")
        assert isinstance(result, PolicyEvaluationResult)
        assert result.allowed is True

    def test_allow_with_wildcard(self, engine, allow_policy):
        """通配符资源匹配"""
        engine.register_policy(allow_policy)
        engine.attach_policy("user:dev1", "dev-allow")
        result = engine.evaluate("dev1", PolicyAction.CALL_TOOL, "database/query")
        assert result.allowed is True

    # ── 拒绝场景 ──────────────────────────────────────────────

    def test_deny_matching_resource(self, engine, deny_policy):
        """资源匹配时 DENY 策略拒绝"""
        engine.register_policy(deny_policy)
        engine.attach_policy("user:ops1", "prod-deny")
        result = engine.evaluate("ops1", PolicyAction.CALL_TOOL, "filesystem/read")
        assert isinstance(result, PolicyEvaluationResult)
        assert result.allowed is False

    def test_default_deny_no_policy(self, engine):
        """无匹配策略时 default_deny 生效"""
        result = engine.evaluate("unknown", PolicyAction.CALL_TOOL, "some/tool")
        assert isinstance(result, PolicyEvaluationResult)
        assert result.allowed is False

    # ── 优先级覆盖 ────────────────────────────────────────────

    def test_deny_overrides_allow(self, engine, allow_policy):
        """DENY 优先级高于 ALLOW — filesystem 被明确拒绝"""
        engine.register_policy(allow_policy)
        engine.attach_policy("user:dev1", "dev-allow")

        override_deny = ToolPolicy(
            policy_id="override-deny",
            name="Override Deny",
            priority=100,
            statements=[
                PolicyStatement(
                    sid="deny-all-filesystem",
                    effect=PolicyEffect.DENY,
                    actions={PolicyAction.CALL_TOOL},
                    resources=["filesystem/*"],
                ),
            ],
        )
        engine.register_policy(override_deny)
        engine.attach_policy("user:dev1", "override-deny")

        result = engine.evaluate("dev1", PolicyAction.CALL_TOOL, "filesystem/read")
        assert result.allowed is False
