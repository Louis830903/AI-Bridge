"""安全相关的工具函数 — 跨模块共享的验证逻辑。

提供输入验证、URL验证、文件路径验证、密钥管理、速率限制和CSS选择器验证。

Usage:
    from aibridge.utils.security import (
        InputValidator, URLValidator, FilePathValidator,
        SecretManager, RateLimiter, validate_css_selector,
    )
"""

import hashlib
import hmac
import re
import secrets
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from urllib.parse import urlparse

# ============ CSS 选择器验证 ============

# 危险字符列表（共享）
DANGEROUS_CHARS = ['<', '>', '{', '}', ';', '`', '\x00', '\n', '\r']

# 危险模式列表（不区分大小写，共享）
DANGEROUS_PATTERNS = [
    'javascript:', 'expression(', 'eval(', '@import',
    'behavior:', 'binding:', 'moz-binding:'
]

# 合法的 CSS 选择器字符
VALID_SELECTOR_RE = re.compile(r'^[\w\s\[\]\.#:\-\*,>+~="\'()@\^\$\|]+$')


def validate_css_selector(selector: str, allow_empty: bool = True) -> Tuple[bool, str]:
    """通用的 CSS 选择器安全验证。

    检查：长度限制、危险字符、危险模式、格式有效性。

    Args:
        selector: CSS 选择器字符串。
        allow_empty: True 则空字符串通过验证（返回成功），
                     False 则空字符串视为无效。

    Returns:
        (is_valid, error_message) — is_valid 为 True 表示通过验证，
        error_message 为错误描述（验证通过时为空字符串）。
    """
    # 空选择器处理
    if not selector:
        if allow_empty:
            return True, ""
        return False, "选择器不能为空"

    if not isinstance(selector, str):
        return False, "选择器必须是字符串"

    # 长度限制（防止 DoS）
    if len(selector) > 500:
        return False, "选择器过长（最大500字符）"

    # 检查危险字符
    for char in DANGEROUS_CHARS:
        if char in selector:
            return False, f"选择器包含不允许的字符: {repr(char)}"

    # 检查危险模式（不区分大小写）
    selector_lower = selector.lower()
    for pattern in DANGEROUS_PATTERNS:
        if pattern in selector_lower:
            return False, f"选择器包含不允许的模式: {pattern}"

    # 格式有效性验证
    if not VALID_SELECTOR_RE.match(selector):
        return False, "选择器格式无效"

    return True, ""


# ============ URL 相关安全常量 ============

# URL 最大长度
MAX_URL_LENGTH = 2048

# 允许的 URL 协议
ALLOWED_URL_SCHEMES = ('http', 'https')


# ============ InputValidator ============

class InputValidator:
    """输入验证器 — 提供通用输入的格式与安全验证。"""

    DANGEROUS_SCRIPT_PATTERNS = [
        re.compile(r'\beval\s*\('),
        re.compile(r'__import__'),
        re.compile(r'\bos\.'),
        re.compile(r'\bsubprocess\.'),
    ]

    IDENTIFIER_RE = re.compile(r'^[\w@#][\w\-@#]*$')

    PHONE_RE = re.compile(r'^\+?[\d\s\-\(\)]+$')

    EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')

    @staticmethod
    def validate_string(
        value, allow_empty: bool = False,
        max_length: Optional[int] = None, pattern: Optional[str] = None,
    ) -> str:
        """验证并返回字符串。

        Args:
            value: 待验证的值。
            allow_empty: 是否允许空字符串。
            max_length: 最大长度限制。
            pattern: 正则表达式模式。

        Returns:
            str: 通过验证的字符串。

        Raises:
            ValueError: 验证失败时抛出。
        """
        if not isinstance(value, str):
            raise ValueError("Expected string, got " + type(value).__name__)
        if not allow_empty and not value:
            raise ValueError("Empty string not allowed")
        if max_length is not None and len(value) > max_length:
            raise ValueError(f"String exceeds max length of {max_length}")
        if pattern is not None:
            if not re.match(pattern, value):
                raise ValueError(f"String does not match required pattern")
        return value

    @staticmethod
    def sanitize_script(script: str, allow_dangerous: bool = False) -> str:
        """检查脚本中是否包含危险模式。

        Args:
            script: 脚本内容。
            allow_dangerous: 是否允许危险模式。

        Returns:
            str: 通过检查的脚本。

        Raises:
            ValueError: 检测到危险模式时抛出。
        """
        if not isinstance(script, str):
            raise ValueError("Expected string, got " + type(script).__name__)
        if not allow_dangerous:
            for pat in InputValidator.DANGEROUS_SCRIPT_PATTERNS:
                if pat.search(script):
                    raise ValueError("Dangerous script pattern detected")
        return script

    @staticmethod
    def validate_identifier(identifier: str) -> str:
        """验证标识符格式（字母、数字、_、-、@、#）。

        Args:
            identifier: 标识符字符串。

        Returns:
            str: 通过验证的标识符。

        Raises:
            ValueError: 格式无效时抛出。
        """
        if not isinstance(identifier, str):
            raise ValueError("Expected string, got " + type(identifier).__name__)
        if not InputValidator.IDENTIFIER_RE.match(identifier):
            raise ValueError("Invalid identifier")
        return identifier

    @staticmethod
    def validate_phone(phone: str) -> str:
        """验证并清理电话号码。

        Args:
            phone: 电话号码字符串。

        Returns:
            str: 清理后的电话号码。

        Raises:
            ValueError: 格式无效时抛出。
        """
        if not isinstance(phone, str):
            raise ValueError("Expected string, got " + type(phone).__name__)
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        if not InputValidator.PHONE_RE.match(cleaned):
            raise ValueError("Invalid phone number")
        digits = re.sub(r'\D', '', cleaned)
        if len(digits) < 7:
            raise ValueError("Invalid phone number")
        return cleaned

    @staticmethod
    def validate_email(email: str) -> str:
        """验证电子邮件地址格式。

        Args:
            email: 电子邮件地址。

        Returns:
            str: 通过验证的电子邮件。

        Raises:
            ValueError: 格式无效时抛出。
        """
        if not isinstance(email, str):
            raise ValueError("Expected string, got " + type(email).__name__)
        if not InputValidator.EMAIL_RE.match(email):
            raise ValueError("Invalid email address")
        return email


# ============ URLValidator ============

class URLValidator:
    """URL 验证器 — 检查协议、域名白名单/黑名单及内网地址。"""

    INTERNAL_SUBNETS = [
        re.compile(r'^10\.'),
        re.compile(r'^172\.(1[6-9]|2\d|3[01])\.'),
        re.compile(r'^192\.168\.'),
        re.compile(r'^169\.254\.'),
        re.compile(r'^127\.'),
        re.compile(r'^0\.'),
    ]

    def __init__(
        self,
        allowed_schemes: Optional[Tuple[str, ...]] = None,
        allow_internal: bool = False,
        allowed_domains: Optional[Set[str]] = None,
        max_length: Optional[int] = None,
    ):
        self.allowed_schemes = allowed_schemes or ('http', 'https')
        self.allow_internal = allow_internal
        self.allowed_domains = allowed_domains
        self.max_length = max_length or 2048
        self.blocked_domains = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}

    def validate(self, url: str) -> str:
        """验证 URL 的安全性。

        Args:
            url: 待验证的 URL。

        Returns:
            str: 通过验证的 URL。

        Raises:
            ValueError: 验证失败时抛出。
        """
        if not isinstance(url, str):
            raise ValueError("Expected string, got " + type(url).__name__)

        if len(url) > self.max_length:
            raise ValueError(f"URL exceeds max length of {self.max_length}")

        try:
            parsed = urlparse(url)
        except Exception:
            raise ValueError("Invalid URL format")

        if parsed.scheme not in self.allowed_schemes:
            raise ValueError(f"URL scheme not allowed: {parsed.scheme}")

        hostname = parsed.hostname or ""

        if hostname in self.blocked_domains:
            raise ValueError(f"Domain is blocked: {hostname}")

        if not self.allow_internal and self._is_internal_ip(hostname):
            raise ValueError(f"Internal address not allowed: {hostname}")

        if self.allowed_domains is not None:
            if not self._match_domain(hostname, self.allowed_domains):
                raise ValueError(f"Domain not in whitelist: {hostname}")

        return url

    def _is_internal_ip(self, hostname: str) -> bool:
        """检查主机名是否为内网地址。"""
        for subnet in self.INTERNAL_SUBNETS:
            if subnet.match(hostname):
                return True
        return False

    def _match_domain(self, hostname: str, allowed: Set[str]) -> bool:
        """通配符域名匹配（如 *.google.com）。"""
        for pattern in allowed:
            if pattern.startswith('*.'):
                suffix = pattern[2:]
                if hostname == suffix or hostname.endswith('.' + suffix):
                    return True
            elif hostname == pattern:
                return True
        return False


# ============ FilePathValidator ============

class FilePathValidator:
    """文件路径验证器 — 限制访问目录、扩展名，检测路径穿越。"""

    BLOCKED_PATTERNS = [
        re.compile(r'\.\.'),
    ]

    def __init__(
        self,
        allowed_directories: Optional[List[str]] = None,
        blocked_patterns: Optional[List[re.Pattern]] = None,
        allowed_extensions: Optional[Set[str]] = None,
    ):
        self.allowed_directories = [
            Path(d).resolve() for d in (allowed_directories or [])
        ]
        self.blocked_patterns = blocked_patterns or self.BLOCKED_PATTERNS
        self.allowed_extensions = allowed_extensions

    def validate(self, path: str) -> Path:
        """验证文件路径。

        Args:
            path: 待验证的路径。

        Returns:
            Path: 解析后的绝对路径。

        Raises:
            ValueError: 验证失败时抛出。
        """
        resolved = Path(path).resolve()

        if self.allowed_directories:
            in_allowed = False
            for d in self.allowed_directories:
                try:
                    resolved.relative_to(d)
                    in_allowed = True
                    break
                except ValueError:
                    pass
            if not in_allowed:
                raise ValueError(f"Path not in allowed directories: {path}")

        path_str = str(path)
        for pattern in self.blocked_patterns:
            if pattern.search(path_str):
                raise ValueError(f"Path contains blocked pattern: {path}")

        if self.allowed_extensions is not None:
            if resolved.suffix not in self.allowed_extensions:
                raise ValueError(
                    f"File extension not allowed: {resolved.suffix}"
                )

        return resolved

    def validate_for_read(self, path: str) -> Path:
        """验证读取路径（要求文件存在）。

        Args:
            path: 待验证的路径。

        Returns:
            Path: 解析后的绝对路径。

        Raises:
            ValueError: 文件不存在时抛出。
        """
        resolved = self.validate(path)
        if not resolved.exists():
            raise ValueError(f"File does not exist: {resolved}")
        return resolved

    def validate_for_write(self, path: str) -> Path:
        """验证写入路径（要求父目录存在）。

        Args:
            path: 待验证的路径。

        Returns:
            Path: 解析后的绝对路径。

        Raises:
            ValueError: 父目录不存在时抛出。
        """
        resolved = self.validate(path)
        if not resolved.parent.exists():
            raise ValueError(
                f"Parent directory does not exist: {resolved.parent}"
            )
        return resolved


# ============ SecretManager ============

class SecretManager:
    """密钥管理器 — 生成令牌、哈希验证、密钥脱敏。"""

    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成安全的随机令牌。

        Args:
            length: 令牌的随机字节数。

        Returns:
            str: URL 安全的 Base64 编码令牌。
        """
        return secrets.token_urlsafe(length)

    @staticmethod
    def hash_secret(secret: str) -> str:
        """对密钥进行加盐哈希。

        Args:
            secret: 原始密钥。

        Returns:
            str: "salt:hash" 格式的哈希串。
        """
        salt = secrets.token_hex(16)
        h = hashlib.sha256((salt + secret).encode()).hexdigest()
        return f"{salt}:{h}"

    @staticmethod
    def verify_secret(secret: str, hashed: str) -> bool:
        """验证密钥是否匹配哈希值。

        Args:
            secret: 原始密钥。
            hashed: "salt:hash" 格式的哈希串。

        Returns:
            bool: 是否匹配。
        """
        try:
            salt, h = hashed.split(':', 1)
            expected = hashlib.sha256((salt + secret).encode()).hexdigest()
            return hmac.compare_digest(expected, h)
        except Exception:
            return False

    @staticmethod
    def mask_secret(secret: str) -> str:
        """脱敏显示密钥。

        Args:
            secret: 原始密钥。

        Returns:
            str: 脱敏后的字符串（前4后4可见，中间*）。
        """
        if len(secret) <= 8:
            return '*' * 5
        return secret[:4] + '*' * (len(secret) - 8) + secret[-4:]


# ============ RateLimiter ============

class RateLimiter:
    """速率限制器 — 基于滑动窗口的请求频率控制。"""

    def __init__(self, max_requests: int, window_seconds: float):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._windows: Dict[str, List[float]] = {}

    def is_allowed(self, key: str) -> bool:
        """检查指定 key 的请求是否允许。

        Args:
            key: 标识符（如用户 ID）。

        Returns:
            bool: 是否允许此次请求。
        """
        now = time.time()
        if key not in self._windows:
            self._windows[key] = []

        # 清理过期记录
        cutoff = now - self.window_seconds
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]

        if len(self._windows[key]) >= self.max_requests:
            return False

        self._windows[key].append(now)
        return True

    def get_remaining(self, key: str) -> int:
        """获取指定 key 的剩余可用请求数。

        Args:
            key: 标识符。

        Returns:
            int: 剩余请求数。
        """
        now = time.time()
        if key not in self._windows:
            return self.max_requests

        cutoff = now - self.window_seconds
        self._windows[key] = [t for t in self._windows[key] if t > cutoff]
        return max(0, self.max_requests - len(self._windows[key]))


# ============ 便捷函数 ============

def validate_url(url: str, **kwargs) -> str:
    """便捷的 URL 验证函数。

    Args:
        url: 待验证的 URL。
        **kwargs: 传递给 URLValidator 的参数。

    Returns:
        str: 通过验证的 URL。
    """
    validator = URLValidator(**kwargs)
    return validator.validate(url)


def validate_file_path(path: str, allowed_directories: List[str], **kwargs) -> Path:
    """便捷的文件路径验证函数。

    Args:
        path: 待验证的路径。
        allowed_directories: 允许的目录列表。
        **kwargs: 传递给 FilePathValidator 的参数。

    Returns:
        Path: 解析后的路径。
    """
    validator = FilePathValidator(
        allowed_directories=allowed_directories, **kwargs,
    )
    return validator.validate(path)


def sanitize_input(text: str) -> str:
    """便捷的输入清理函数。

    Args:
        text: 待清理的文本。

    Returns:
        str: 通过验证的文本。

    Raises:
        ValueError: 输入无效时抛出。
    """
    return InputValidator.validate_string(text)
