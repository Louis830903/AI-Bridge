"""AI-Bridge 统一异常体系

提供结构化的异常类型，6 类 17 子类，便于上层统一处理不同错误场景。

异常层次：
    AIBridgeError (root, code="UNKNOWN")
    ├── AdapterError (2xx) — 适配器层异常
    │   ├── AdapterConnectionError (201)
    │   ├── AdapterTimeoutError (202)
    │   ├── AdapterExecutionError (203)
    │   ├── AdapterNotFoundError (204)
    │   └── AdapterConfigError (205)
    ├── ProtocolError (3xx) — 协议层异常
    │   ├── MCPProtocolError (301)
    │   ├── A2AProtocolError (302)
    │   └── ProtocolBridgeError (303)
    ├── IntentError (4xx) — 意图引擎异常
    │   ├── IntentParseError (401)
    │   ├── IntentRouteError (402)
    │   └── IntentRegistrationError (403)
    ├── EnterpriseError (5xx) — 企业级异常
    │   ├── PolicyDeniedError (501)
    │   ├── RateLimitExceededError (502)
    │   └── AuditWriteError (503)
    └── SecurityError (6xx) — 安全异常
        ├── SSRFBlockedError (601)
        └── InputValidationError (602)

向后兼容别名:
    ValidationError  → InputValidationError
    ConfigurationError → AdapterConfigError
    TimeoutError     → AdapterTimeoutError

Usage:
    raise AdapterTimeoutError("操作超时", adapter_id="chrome", timeout_seconds=30)
    try: ...
    except AIBridgeError as e:
        print(e.code, e.details, e.cause)
"""

from typing import Any, Dict, Optional


class AIBridgeError(Exception):
    """所有 AI-Bridge 异常的根类。

    Attributes:
        code: 机器可读错误码，如 "ADAPTER_TIMEOUT"。
        details: 额外的结构化上下文信息。
        cause: 原始异常（用于异常链）。
    """

    code: str = "UNKNOWN"

    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
    ):
        super().__init__(message)
        self.code = code if code is not None else self.__class__.code
        self.details = details or {}
        self.cause = cause

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典，便于序列化返回。"""
        result: Dict[str, Any] = {
            "success": False,
            "error": str(self),
            "error_code": self.code,
            "details": self.details,
        }
        if self.cause:
            result["cause"] = repr(self.cause)
        return result


# ============ 适配器层异常 (2xx) ============

class AdapterError(AIBridgeError):
    """适配器层异常基类 (2xx)。

    Attributes:
        adapter_id: 发生异常的适配器标识。
        action: 触发异常的操作名称。
    """

    code = "ADAPTER_ERROR"

    def __init__(
        self,
        message: str,
        adapter_id: Optional[str] = None,
        action: Optional[str] = None,
        cause: Optional[Exception] = None,
        **kwargs: Any,
    ):
        extra = kwargs.pop("details", {})
        merged = {"adapter_id": adapter_id, "action": action, **extra, **kwargs}
        super().__init__(message, cause=cause, details=merged)


class AdapterConnectionError(AdapterError):
    """适配器连接错误 (201)。

    注意：命名为 AdapterConnectionError 而非 ConnectionError，
    以避免与 Python 内置 ConnectionError 同名异常冲突。
    """
    code = "ADAPTER_CONNECTION_ERROR"


class AdapterTimeoutError(AdapterError):
    """适配器操作超时 (202)。

    Attributes:
        timeout_seconds: 超时秒数。
    """
    code = "ADAPTER_TIMEOUT"

    def __init__(self, message: str, timeout_seconds: Optional[float] = None, **kwargs: Any):
        super().__init__(message, timeout_seconds=timeout_seconds, **kwargs)


class AdapterExecutionError(AdapterError):
    """适配器执行错误 (203)。"""
    code = "ADAPTER_EXECUTION_ERROR"


class AdapterNotFoundError(AdapterError):
    """适配器未找到 (204)。"""
    code = "ADAPTER_NOT_FOUND"


class AdapterConfigError(AdapterError):
    """适配器配置错误 (205)。

    Attributes:
        key: 配置键名。
    """
    code = "ADAPTER_CONFIG_ERROR"

    def __init__(self, message: str, key: Optional[str] = None, **kwargs: Any):
        super().__init__(message, key=key, **kwargs)


# ============ 协议层异常 (3xx) ============

class ProtocolError(AIBridgeError):
    """协议层异常基类 (3xx)。"""
    code = "PROTOCOL_ERROR"

    def __init__(self, message: str, cause: Optional[Exception] = None, **kwargs: Any):
        super().__init__(message, cause=cause, details=kwargs)


class MCPProtocolError(ProtocolError):
    """MCP 协议错误 (301)。"""
    code = "MCP_PROTOCOL_ERROR"


class A2AProtocolError(ProtocolError):
    """A2A 协议错误 (302)。"""
    code = "A2A_PROTOCOL_ERROR"


class ProtocolBridgeError(ProtocolError):
    """协议桥接错误 (303)。"""
    code = "PROTOCOL_BRIDGE_ERROR"


# ============ 意图引擎异常 (4xx) ============

class IntentError(AIBridgeError):
    """意图引擎异常基类 (4xx)。

    Attributes:
        intent_text: 触发异常的意图文本。
    """
    code = "INTENT_ERROR"

    def __init__(self, message: str, intent_text: Optional[str] = None, cause: Optional[Exception] = None, **kwargs: Any):
        super().__init__(
            message,
            cause=cause,
            details={"intent_text": intent_text, **kwargs},
        )


class IntentParseError(IntentError):
    """意图解析错误 (401)。"""
    code = "INTENT_PARSE_ERROR"


class IntentRouteError(IntentError):
    """意图路由错误 (402)。"""
    code = "INTENT_ROUTE_ERROR"


class IntentRegistrationError(IntentError):
    """意图注册错误 (403)。"""
    code = "INTENT_REGISTRATION_ERROR"


# ============ 企业级异常 (5xx) ============

class EnterpriseError(AIBridgeError):
    """企业级异常基类 (5xx)。"""
    code = "ENTERPRISE_ERROR"

    def __init__(self, message: str, cause: Optional[Exception] = None, **kwargs: Any):
        super().__init__(message, cause=cause, details=kwargs)


class PolicyDeniedError(EnterpriseError):
    """策略拒绝 (501)。"""
    code = "POLICY_DENIED"


class RateLimitExceededError(EnterpriseError):
    """速率限制超限 (502)。"""
    code = "RATE_LIMIT_EXCEEDED"


class AuditWriteError(EnterpriseError):
    """审计写入错误 (503)。"""
    code = "AUDIT_WRITE_ERROR"


# ============ 安全异常 (6xx) ============

class SecurityError(AIBridgeError):
    """安全异常基类 (6xx)。"""
    code = "SECURITY_ERROR"

    def __init__(self, message: str, cause: Optional[Exception] = None, **kwargs: Any):
        super().__init__(message, cause=cause, details=kwargs)


class SSRFBlockedError(SecurityError):
    """SSRF 攻击被拦截 (601)。"""
    code = "SSRF_BLOCKED"


class InputValidationError(SecurityError):
    """输入验证失败 (602)。

    Attributes:
        field: 验证失败的字段名。
    """
    code = "INPUT_VALIDATION_ERROR"

    def __init__(self, message: str, field: Optional[str] = None, **kwargs: Any):
        super().__init__(message, field=field, **kwargs)


# ============ 向后兼容别名 ============
# 保留旧类名，避免破坏现有引用。将在 v1.0 正式版移除。

ValidationError = InputValidationError       # 旧名 → 新名
ConfigurationError = AdapterConfigError       # 旧名 → 新名
TimeoutError = AdapterTimeoutError            # 旧名 → 新名
# 注意: 不要使用 ConnectionError 别名，它遮蔽 Python 内置异常
