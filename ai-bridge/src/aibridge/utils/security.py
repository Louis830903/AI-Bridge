"""
Security Utilities - Input validation and security tools
安全工具模块 - 输入验证和安全防护
"""

import re
import os
import hmac
import hashlib
import secrets
from pathlib import Path
from typing import Any, List, Optional, Set, Pattern
from urllib.parse import urlparse
from dataclasses import dataclass, field


# ============ Input Validators ============

class InputValidator:
    """输入验证器"""
    
    # 危险脚本模式
    DANGEROUS_PATTERNS = [
        r'\beval\s*\(',
        r'\bexec\s*\(',
        r'__import__',
        r'__builtins__',
        r'\bos\.',
        r'\bsubprocess\.',
        r'\bsystem\s*\(',
        r'\bpopen\s*\(',
        r'<script',
        r'javascript:',
        r'on\w+\s*=',
    ]
    
    # 编译正则表达式
    _dangerous_regex: List[Pattern] = []
    
    @classmethod
    def _get_dangerous_patterns(cls) -> List[Pattern]:
        """获取编译后的危险模式"""
        if not cls._dangerous_regex:
            cls._dangerous_regex = [
                re.compile(p, re.IGNORECASE) for p in cls.DANGEROUS_PATTERNS
            ]
        return cls._dangerous_regex
    
    @classmethod
    def validate_string(
        cls,
        value: str,
        max_length: int = 10000,
        allow_empty: bool = False,
        pattern: Optional[str] = None,
    ) -> str:
        """
        验证字符串输入
        
        Args:
            value: 输入字符串
            max_length: 最大长度
            allow_empty: 是否允许空字符串
            pattern: 正则表达式模式
            
        Returns:
            验证后的字符串
            
        Raises:
            ValueError: 验证失败
        """
        if not isinstance(value, str):
            raise ValueError(f"Expected string, got {type(value).__name__}")
        
        if not allow_empty and not value.strip():
            raise ValueError("Empty string not allowed")
        
        if len(value) > max_length:
            raise ValueError(f"String exceeds max length {max_length}")
        
        if pattern and not re.match(pattern, value):
            raise ValueError(f"String does not match pattern: {pattern}")
        
        return value
    
    @classmethod
    def sanitize_script(cls, script: str, allow_dangerous: bool = False) -> str:
        """
        清理脚本内容，检测危险模式
        
        Args:
            script: 脚本内容
            allow_dangerous: 是否允许危险模式
            
        Returns:
            清理后的脚本
            
        Raises:
            ValueError: 检测到危险模式
        """
        if not allow_dangerous:
            for pattern in cls._get_dangerous_patterns():
                if pattern.search(script):
                    raise ValueError(f"Dangerous pattern detected in script")
        
        return script
    
    @classmethod
    def validate_identifier(cls, value: str, max_length: int = 100) -> str:
        """
        验证标识符（如适配器 ID、频道 ID 等）
        
        Args:
            value: 标识符
            max_length: 最大长度
            
        Returns:
            验证后的标识符
        """
        if not re.match(r'^[\w\-\.@#]+$', value):
            raise ValueError(f"Invalid identifier format: {value}")
        
        if len(value) > max_length:
            raise ValueError(f"Identifier exceeds max length {max_length}")
        
        return value
    
    @classmethod
    def validate_phone(cls, phone: str) -> str:
        """
        验证电话号码格式
        
        Args:
            phone: 电话号码
            
        Returns:
            验证后的电话号码
        """
        # 移除空格和连字符
        cleaned = re.sub(r'[\s\-\(\)]', '', phone)
        
        # 验证格式: +国家代码 + 号码
        if not re.match(r'^\+?[1-9]\d{6,14}$', cleaned):
            raise ValueError(f"Invalid phone number format: {phone}")
        
        return cleaned
    
    @classmethod
    def validate_email(cls, email: str) -> str:
        """
        验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            验证后的邮箱
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            raise ValueError(f"Invalid email format: {email}")
        
        return email.lower()


# ============ URL Validator ============

@dataclass
class URLValidator:
    """URL 验证器，支持白名单"""
    
    # 允许的协议
    allowed_schemes: Set[str] = field(default_factory=lambda: {"http", "https"})
    
    # 域名白名单（为空则允许所有）
    allowed_domains: Set[str] = field(default_factory=set)
    
    # 域名黑名单
    blocked_domains: Set[str] = field(default_factory=lambda: {
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
        "169.254.169.254",  # AWS metadata
        "metadata.google.internal",  # GCP metadata
    })
    
    # 是否允许内部地址
    allow_internal: bool = False
    
    # 最大 URL 长度
    max_length: int = 2048
    
    def validate(self, url: str) -> str:
        """
        验证 URL
        
        Args:
            url: URL 字符串
            
        Returns:
            验证后的 URL
            
        Raises:
            ValueError: 验证失败
        """
        if len(url) > self.max_length:
            raise ValueError(f"URL exceeds max length {self.max_length}")
        
        try:
            parsed = urlparse(url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")
        
        # 验证协议
        if parsed.scheme not in self.allowed_schemes:
            raise ValueError(f"URL scheme not allowed: {parsed.scheme}")
        
        # 获取域名（不含端口）
        domain = parsed.netloc.split(':')[0].lower()
        
        # 检查黑名单
        if not self.allow_internal and domain in self.blocked_domains:
            raise ValueError(f"URL domain is blocked: {domain}")
        
        # 检查是否为内部地址
        if not self.allow_internal:
            if self._is_internal_address(domain):
                raise ValueError(f"Internal addresses not allowed: {domain}")
        
        # 检查白名单（如果设置了）
        if self.allowed_domains:
            if not self._domain_matches_whitelist(domain):
                raise ValueError(f"URL domain not in whitelist: {domain}")
        
        return url
    
    def _is_internal_address(self, domain: str) -> bool:
        """检查是否为内部地址"""
        # 检查 IP 地址
        try:
            parts = domain.split('.')
            if len(parts) == 4:
                nums = [int(p) for p in parts]
                # 10.0.0.0/8
                if nums[0] == 10:
                    return True
                # 172.16.0.0/12
                if nums[0] == 172 and 16 <= nums[1] <= 31:
                    return True
                # 192.168.0.0/16
                if nums[0] == 192 and nums[1] == 168:
                    return True
                # 127.0.0.0/8
                if nums[0] == 127:
                    return True
        except (ValueError, IndexError):
            pass
        
        return False
    
    def _domain_matches_whitelist(self, domain: str) -> bool:
        """检查域名是否匹配白名单"""
        for allowed in self.allowed_domains:
            if allowed.startswith('*.'):
                # 通配符匹配
                suffix = allowed[2:]
                if domain.endswith(suffix) or domain == suffix:
                    return True
            else:
                if domain == allowed:
                    return True
        return False


# ============ File Path Validator ============

@dataclass
class FilePathValidator:
    """文件路径验证器"""
    
    # 允许的目录（必须设置）
    allowed_directories: List[str] = field(default_factory=list)
    
    # 允许的扩展名（为空则允许所有）
    allowed_extensions: Set[str] = field(default_factory=set)
    
    # 禁止的文件名模式
    blocked_patterns: Set[str] = field(default_factory=lambda: {
        r'\.\.', 
        r'\x00',
        r'~',
    })
    
    # 最大路径长度
    max_length: int = 260
    
    def validate(self, path: str) -> Path:
        """
        验证文件路径
        
        Args:
            path: 文件路径
            
        Returns:
            验证后的 Path 对象
            
        Raises:
            ValueError: 验证失败
        """
        if len(path) > self.max_length:
            raise ValueError(f"Path exceeds max length {self.max_length}")
        
        # 检查禁止的模式
        for pattern in self.blocked_patterns:
            if re.search(pattern, path):
                raise ValueError(f"Path contains blocked pattern")
        
        # 解析为绝对路径
        try:
            resolved = Path(path).resolve()
        except Exception as e:
            raise ValueError(f"Invalid path: {e}")
        
        # 检查扩展名
        if self.allowed_extensions:
            ext = resolved.suffix.lower()
            if ext not in self.allowed_extensions:
                raise ValueError(f"File extension not allowed: {ext}")
        
        # 检查是否在允许的目录内
        if self.allowed_directories:
            in_allowed = False
            for allowed_dir in self.allowed_directories:
                allowed_path = Path(allowed_dir).resolve()
                try:
                    resolved.relative_to(allowed_path)
                    in_allowed = True
                    break
                except ValueError:
                    continue
            
            if not in_allowed:
                raise ValueError(f"Path not in allowed directories")
        
        return resolved
    
    def validate_for_read(self, path: str) -> Path:
        """验证用于读取的文件路径"""
        resolved = self.validate(path)
        if not resolved.exists():
            raise ValueError(f"File does not exist: {path}")
        if not resolved.is_file():
            raise ValueError(f"Path is not a file: {path}")
        return resolved
    
    def validate_for_write(self, path: str) -> Path:
        """验证用于写入的文件路径"""
        resolved = self.validate(path)
        # 检查父目录是否存在
        if not resolved.parent.exists():
            raise ValueError(f"Parent directory does not exist: {resolved.parent}")
        return resolved


# ============ Token/Secret Security ============

class SecretManager:
    """密钥管理器"""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """生成安全的随机令牌"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_secret(secret: str, salt: Optional[str] = None) -> str:
        """
        对密钥进行哈希处理
        
        Args:
            secret: 密钥
            salt: 盐值（可选）
            
        Returns:
            哈希后的字符串
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        combined = f"{salt}:{secret}"
        hashed = hashlib.sha256(combined.encode()).hexdigest()
        return f"{salt}:{hashed}"
    
    @staticmethod
    def verify_secret(secret: str, hashed: str) -> bool:
        """
        验证密钥是否匹配
        
        Args:
            secret: 明文密钥
            hashed: 哈希后的密钥
            
        Returns:
            是否匹配
        """
        try:
            salt, expected_hash = hashed.split(':', 1)
            combined = f"{salt}:{secret}"
            actual_hash = hashlib.sha256(combined.encode()).hexdigest()
            return hmac.compare_digest(actual_hash, expected_hash)
        except Exception:
            return False
    
    @staticmethod
    def mask_secret(secret: str, visible_chars: int = 4) -> str:
        """
        遮蔽密钥，仅显示部分字符
        
        Args:
            secret: 密钥
            visible_chars: 显示的字符数
            
        Returns:
            遮蔽后的字符串
        """
        if len(secret) <= visible_chars * 2:
            return "*" * len(secret)
        
        return f"{secret[:visible_chars]}{'*' * (len(secret) - visible_chars * 2)}{secret[-visible_chars:]}"


# ============ Rate Limiter ============

class RateLimiter:
    """简单的速率限制器"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        """
        Args:
            max_requests: 时间窗口内最大请求数
            window_seconds: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict = {}
    
    def is_allowed(self, key: str) -> bool:
        """
        检查是否允许请求
        
        Args:
            key: 请求标识（如用户 ID、IP 等）
            
        Returns:
            是否允许
        """
        import time
        current_time = time.time()
        
        # 清理过期记录
        if key in self._requests:
            self._requests[key] = [
                t for t in self._requests[key]
                if current_time - t < self.window_seconds
            ]
        else:
            self._requests[key] = []
        
        # 检查是否超限
        if len(self._requests[key]) >= self.max_requests:
            return False
        
        # 记录请求
        self._requests[key].append(current_time)
        return True
    
    def get_remaining(self, key: str) -> int:
        """获取剩余请求数"""
        import time
        current_time = time.time()
        
        if key not in self._requests:
            return self.max_requests
        
        valid_requests = [
            t for t in self._requests[key]
            if current_time - t < self.window_seconds
        ]
        
        return max(0, self.max_requests - len(valid_requests))


# ============ Default Instances ============

# 默认 URL 验证器实例
default_url_validator = URLValidator()

# 默认文件路径验证器实例（需要在使用前设置 allowed_directories）
default_file_validator = FilePathValidator()

# 默认速率限制器
default_rate_limiter = RateLimiter()


# ============ Convenience Functions ============

def validate_url(url: str, **kwargs) -> str:
    """便捷函数：验证 URL"""
    validator = URLValidator(**kwargs) if kwargs else default_url_validator
    return validator.validate(url)


def validate_file_path(path: str, allowed_dirs: List[str], **kwargs) -> Path:
    """便捷函数：验证文件路径"""
    validator = FilePathValidator(allowed_directories=allowed_dirs, **kwargs)
    return validator.validate(path)


def sanitize_input(value: str, max_length: int = 10000) -> str:
    """便捷函数：清理输入"""
    return InputValidator.validate_string(value, max_length=max_length)
