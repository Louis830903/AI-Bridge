"""Tests for error migration — legacy dict → structured exceptions.

错误迁移回归测试：确保旧字典模式在 v0.9.x 仍可用但发出警告，
新结构化异常正确传播。
"""

import pytest

from aibridge.core.exceptions import (
    AIBridgeError,
    AdapterError,
    AdapterConnectionError,
    AdapterTimeoutError,
    AdapterExecutionError,
    AdapterNotFoundError,
    AdapterConfigError,
    ProtocolError,
    MCPProtocolError,
    A2AProtocolError,
    ProtocolBridgeError,
    IntentError,
    IntentParseError,
    IntentRouteError,
    IntentRegistrationError,
    EnterpriseError,
    PolicyDeniedError,
    RateLimitExceededError,
    AuditWriteError,
    SecurityError,
    SSRFBlockedError,
    InputValidationError,
)
from aibridge.core.legacy_error_wrapper import (
    migrate_dict_error,
    bridge_legacy,
)


class TestExceptionHierarchy:
    """测试异常层次结构完整性。"""

    def test_root_exception_stores_code(self):
        exc = AIBridgeError("test error", code="TEST_CODE")
        assert exc.code == "TEST_CODE"
        assert str(exc) == "test error"

    def test_root_exception_uses_class_code_default(self):
        exc = AdapterExecutionError("test")
        assert exc.code == "ADAPTER_EXECUTION_ERROR"

    def test_root_exception_stores_details(self):
        exc = AIBridgeError("msg", details={"key": "value"})
        assert exc.details == {"key": "value"}

    def test_root_exception_stores_cause(self):
        cause = ValueError("original")
        exc = AIBridgeError("wrapped", cause=cause)
        assert exc.cause is cause

    def test_to_dict_includes_all_fields(self):
        cause = RuntimeError("boom")
        exc = AdapterExecutionError("failed", adapter_id="chrome", cause=cause)
        d = exc.to_dict()
        assert d["success"] is False
        assert d["error"] == "failed"
        assert d["error_code"] == "ADAPTER_EXECUTION_ERROR"
        assert d["details"]["adapter_id"] == "chrome"
        assert "RuntimeError" in d["cause"]

    def test_to_dict_without_cause(self):
        exc = AdapterTimeoutError("timeout", timeout_seconds=30)
        d = exc.to_dict()
        assert "cause" not in d

    @pytest.mark.parametrize("exc_class,expected_code", [
        (AdapterConnectionError, "ADAPTER_CONNECTION_ERROR"),
        (AdapterTimeoutError, "ADAPTER_TIMEOUT"),
        (AdapterExecutionError, "ADAPTER_EXECUTION_ERROR"),
        (AdapterNotFoundError, "ADAPTER_NOT_FOUND"),
        (AdapterConfigError, "ADAPTER_CONFIG_ERROR"),
        (MCPProtocolError, "MCP_PROTOCOL_ERROR"),
        (A2AProtocolError, "A2A_PROTOCOL_ERROR"),
        (ProtocolBridgeError, "PROTOCOL_BRIDGE_ERROR"),
        (IntentParseError, "INTENT_PARSE_ERROR"),
        (IntentRouteError, "INTENT_ROUTE_ERROR"),
        (IntentRegistrationError, "INTENT_REGISTRATION_ERROR"),
        (PolicyDeniedError, "POLICY_DENIED"),
        (RateLimitExceededError, "RATE_LIMIT_EXCEEDED"),
        (AuditWriteError, "AUDIT_WRITE_ERROR"),
        (SSRFBlockedError, "SSRF_BLOCKED"),
        (InputValidationError, "INPUT_VALIDATION_ERROR"),
    ])
    def test_all_subclasses_have_correct_code(self, exc_class, expected_code):
        exc = exc_class("test")
        assert exc.code == expected_code

    def test_inheritance_chain_adapter(self):
        exc = AdapterExecutionError("test")
        assert isinstance(exc, AdapterError)
        assert isinstance(exc, AIBridgeError)
        assert isinstance(exc, Exception)

    def test_inheritance_chain_protocol(self):
        exc = MCPProtocolError("test")
        assert isinstance(exc, ProtocolError)
        assert isinstance(exc, AIBridgeError)

    def test_inheritance_chain_intent(self):
        exc = IntentParseError("test")
        assert isinstance(exc, IntentError)
        assert isinstance(exc, AIBridgeError)

    def test_inheritance_chain_enterprise(self):
        exc = PolicyDeniedError("test")
        assert isinstance(exc, EnterpriseError)
        assert isinstance(exc, AIBridgeError)

    def test_inheritance_chain_security(self):
        exc = SSRFBlockedError("test")
        assert isinstance(exc, SecurityError)
        assert isinstance(exc, AIBridgeError)

    def test_catch_by_parent_exception(self):
        """确保子类异常可被父类捕获。"""
        with pytest.raises(AdapterError):
            raise AdapterTimeoutError("timeout")

        with pytest.raises(ProtocolError):
            raise MCPProtocolError("bad protocol")

        with pytest.raises(AIBridgeError):
            raise PolicyDeniedError("denied")

    def test_adapter_config_error_stores_key(self):
        exc = AdapterConfigError("bad config", key="timeout")
        assert exc.details["key"] == "timeout"

    def test_intent_error_stores_intent_text(self):
        exc = IntentError("parse failed", intent_text="open browser")
        assert exc.details["intent_text"] == "open browser"

    def test_input_validation_error_stores_field(self):
        exc = InputValidationError("invalid", field="email")
        assert exc.details["field"] == "email"

    # --- backward compatibility aliases ---

    def test_validation_error_alias(self):
        # ValidationError = InputValidationError
        from aibridge.core.exceptions import ValidationError
        exc = ValidationError("bad", field="name")
        assert exc.code == "INPUT_VALIDATION_ERROR"

    def test_configuration_error_alias(self):
        # ConfigurationError = AdapterConfigError
        from aibridge.core.exceptions import ConfigurationError
        exc = ConfigurationError("bad", key="port")
        assert exc.code == "ADAPTER_CONFIG_ERROR"

    def test_timeout_error_alias(self):
        # TimeoutError = AdapterTimeoutError
        from aibridge.core.exceptions import TimeoutError
        exc = TimeoutError("timeout", timeout_seconds=5)
        assert exc.code == "ADAPTER_TIMEOUT"


class TestMigrateDictError:
    """测试 migrate_dict_error 转换逻辑。"""

    def test_error_dict_converts_to_exception(self):
        result = {"success": False, "error": "something broke"}
        with pytest.warns(DeprecationWarning, match="字典错误模式已弃用"):
            exc = migrate_dict_error(result)
        assert exc is not None
        assert isinstance(exc, AdapterExecutionError)
        assert str(exc) == "something broke"
        assert exc.details["legacy_result"] == result

    def test_success_dict_returns_none(self):
        result = {"success": True, "data": "ok"}
        exc = migrate_dict_error(result)
        assert exc is None

    def test_no_success_key_returns_none(self):
        result = {"data": "no success field"}
        exc = migrate_dict_error(result)
        assert exc is None

    def test_non_dict_returns_none(self):
        exc = migrate_dict_error("not a dict")  # type: ignore[arg-type]
        assert exc is None

    def test_empty_dict_returns_none(self):
        exc = migrate_dict_error({})
        assert exc is None

    def test_success_false_without_error_message(self):
        result = {"success": False}
        with pytest.warns(DeprecationWarning):
            exc = migrate_dict_error(result)
        assert exc is not None
        assert str(exc) == "Unknown error"


class TestBridgeLegacyDecorator:
    """测试 bridge_legacy 装饰器。"""

    @pytest.mark.asyncio
    async def test_async_raises_on_error_dict(self):
        @bridge_legacy
        async def old_style():
            return {"success": False, "error": "async boom"}

        with pytest.raises(AdapterExecutionError, match="async boom"):
            await old_style()

    @pytest.mark.asyncio
    async def test_async_passes_through_success(self):
        @bridge_legacy
        async def old_style():
            return {"success": True, "data": 42}

        result = await old_style()
        assert result == {"success": True, "data": 42}

    def test_sync_raises_on_error_dict(self):
        @bridge_legacy
        def old_style():
            return {"success": False, "error": "sync boom"}

        with pytest.raises(AdapterExecutionError, match="sync boom"):
            old_style()

    def test_sync_passes_through_success(self):
        @bridge_legacy
        def old_style():
            return {"success": True, "data": "ok"}

        result = old_style()
        assert result == {"success": True, "data": "ok"}

    def test_sync_passes_through_non_dict(self):
        @bridge_legacy
        def old_style():
            return 42

        result = old_style()
        assert result == 42

    def test_preserves_function_name(self):
        @bridge_legacy
        def my_func():
            return {"success": True}

        assert my_func.__name__ == "my_func"

    @pytest.mark.asyncio
    async def test_preserves_async_function_name(self):
        @bridge_legacy
        async def my_async_func():
            return {"success": True}

        assert my_async_func.__name__ == "my_async_func"

    def test_deprecation_warning_emitted(self):
        @bridge_legacy
        def old_style():
            return {"success": False, "error": "warning test"}

        with pytest.warns(DeprecationWarning, match="字典错误模式已弃用"):
            try:
                old_style()
            except AdapterExecutionError:
                pass  # expected
