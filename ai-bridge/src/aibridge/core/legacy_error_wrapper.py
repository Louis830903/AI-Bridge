"""旧字典错误模式兼容层。

将旧的 ``{"success": False, "error": "..."}`` 返回值自动转换为结构化异常。
v0.9.x 使用 DeprecationWarning 保持向后兼容，v1.0 移除。

Usage:
    from aibridge.core.legacy_error_wrapper import bridge_legacy, migrate_dict_error

    # 方式 1: 装饰器
    @bridge_legacy
    async def old_style_adapter():
        return {"success": False, "error": "something went wrong"}

    # 方式 2: 手动转换
    result = {"success": False, "error": "timeout"}
    error = migrate_dict_error(result)
    if error:
        raise error
"""

from __future__ import annotations

import warnings
from typing import Any, Callable, Dict, Optional, TypeVar, Union, overload

from aibridge.core.exceptions import (
    AIBridgeError,
    AdapterExecutionError,
)

F = TypeVar("F", bound=Callable[..., Any])


def migrate_dict_error(result: Dict[str, Any]) -> Optional[AdapterExecutionError]:
    """将旧字典错误转为结构化异常。

    如果 result 包含 ``"success": False``，则构造对应的
    :class:`AdapterExecutionError` 并发出 DeprecationWarning。

    Args:
        result: 旧字典格式的返回值。

    Returns:
        AdapterExecutionError 或 None（成功时不转换）。
    """
    if not isinstance(result, dict):
        return None

    success = result.get("success", True)
    if success is not False:
        return None

    error_msg = result.get("error", "Unknown error")

    warnings.warn(
        f"字典错误模式已弃用: {error_msg}。"
        f"请使用 raise AIBridgeError 替代 return {{'success': False}}。",
        DeprecationWarning,
        stacklevel=2,
    )

    return AdapterExecutionError(
        message=error_msg,
        details={"legacy_result": result},
    )


@overload
def bridge_legacy(func: F) -> F:
    ...


def bridge_legacy(func: Callable[..., Any]) -> Callable[..., Any]:
    """装饰器 — 自动将旧字典错误返回值转为异常抛出。

    包装一个返回旧字典格式的函数/协程。如果返回值是
    ``{"success": False, "error": ...}`` 的字典，则自动转为
    :class:`AdapterExecutionError` 异常；否则原样返回。

    Args:
        func: 被包装的函数或协程。

    Returns:
        包装后的函数或异步函数。

    Example:
        >>> @bridge_legacy
        ... async def old_adapter():
        ...     return {"success": False, "error": "boom"}
        ...
        >>> await old_adapter()  # raises AdapterExecutionError
    """
    import asyncio

    if asyncio.iscoroutinefunction(func):
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await func(*args, **kwargs)
            if isinstance(result, dict):
                error = migrate_dict_error(result)
                if error:
                    raise error
            return result
        # 保留原函数元信息
        async_wrapper.__name__ = func.__name__
        async_wrapper.__qualname__ = func.__qualname__
        async_wrapper.__doc__ = func.__doc__
        async_wrapper.__wrapped__ = func  # type: ignore[attr-defined]
        return async_wrapper

    def wrapper(*args: Any, **kwargs: Any) -> Any:
        result = func(*args, **kwargs)
        if isinstance(result, dict):
            error = migrate_dict_error(result)
            if error:
                raise error
        return result

    wrapper.__name__ = func.__name__
    wrapper.__qualname__ = func.__qualname__
    wrapper.__doc__ = func.__doc__
    wrapper.__wrapped__ = func  # type: ignore[attr-defined]
    return wrapper
