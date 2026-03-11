"""
Tests for security module
安全模块单元测试
"""

import pytest
from pathlib import Path
from aibridge.utils.security import (
    InputValidator, URLValidator, FilePathValidator,
    SecretManager, RateLimiter,
    validate_url, validate_file_path, sanitize_input
)


class TestInputValidator:
    """Test InputValidator class."""
    
    def test_validate_string_success(self):
        """Test valid string passes validation."""
        result = InputValidator.validate_string("hello world")
        assert result == "hello world"
    
    def test_validate_string_empty_not_allowed(self):
        """Test empty string fails when not allowed."""
        with pytest.raises(ValueError, match="Empty string"):
            InputValidator.validate_string("")
    
    def test_validate_string_empty_allowed(self):
        """Test empty string passes when allowed."""
        result = InputValidator.validate_string("", allow_empty=True)
        assert result == ""
    
    def test_validate_string_max_length(self):
        """Test string exceeding max length fails."""
        with pytest.raises(ValueError, match="max length"):
            InputValidator.validate_string("a" * 100, max_length=50)
    
    def test_validate_string_pattern(self):
        """Test pattern validation."""
        result = InputValidator.validate_string("abc123", pattern=r"^[a-z0-9]+$")
        assert result == "abc123"
        
        with pytest.raises(ValueError, match="pattern"):
            InputValidator.validate_string("ABC!", pattern=r"^[a-z0-9]+$")
    
    def test_validate_string_non_string(self):
        """Test non-string input fails."""
        with pytest.raises(ValueError, match="Expected string"):
            InputValidator.validate_string(123)
    
    def test_sanitize_script_safe(self):
        """Test safe script passes."""
        script = "return document.title"
        result = InputValidator.sanitize_script(script)
        assert result == script
    
    def test_sanitize_script_dangerous(self):
        """Test dangerous script is detected."""
        # These scripts match the DANGEROUS_PATTERNS in InputValidator
        dangerous_scripts = [
            "eval('code')",       # matches \beval\s*\(
            "__import__('os')",   # matches __import__
            "os.system('rm -rf /')",  # matches \bos\.
            "subprocess.call(['ls'])",  # matches \bsubprocess\.
        ]
        
        for script in dangerous_scripts:
            with pytest.raises(ValueError, match="Dangerous"):
                InputValidator.sanitize_script(script)
    
    def test_sanitize_script_allow_dangerous(self):
        """Test allowing dangerous patterns."""
        script = "eval('code')"
        result = InputValidator.sanitize_script(script, allow_dangerous=True)
        assert result == script
    
    def test_validate_identifier_valid(self):
        """Test valid identifiers pass."""
        valid_ids = ["test", "test-123", "test_name", "@channel", "#general"]
        
        for id in valid_ids:
            result = InputValidator.validate_identifier(id)
            assert result == id
    
    def test_validate_identifier_invalid(self):
        """Test invalid identifiers fail."""
        with pytest.raises(ValueError, match="Invalid identifier"):
            InputValidator.validate_identifier("test<script>")
    
    def test_validate_phone_valid(self):
        """Test valid phone numbers pass."""
        valid_phones = ["+1234567890", "+86 138 1234 5678", "1234567890"]
        
        for phone in valid_phones:
            result = InputValidator.validate_phone(phone)
            assert result  # Should return cleaned phone
    
    def test_validate_phone_invalid(self):
        """Test invalid phone numbers fail."""
        with pytest.raises(ValueError, match="Invalid phone"):
            InputValidator.validate_phone("abc123")
    
    def test_validate_email_valid(self):
        """Test valid emails pass."""
        result = InputValidator.validate_email("test@example.com")
        assert result == "test@example.com"
    
    def test_validate_email_invalid(self):
        """Test invalid emails fail."""
        invalid_emails = ["not-an-email", "@domain.com", "user@", "user@.com"]
        
        for email in invalid_emails:
            with pytest.raises(ValueError, match="Invalid email"):
                InputValidator.validate_email(email)


class TestURLValidator:
    """Test URLValidator class."""
    
    def test_validate_valid_url(self):
        """Test valid URL passes."""
        validator = URLValidator()
        result = validator.validate("https://example.com")
        assert result == "https://example.com"
    
    def test_validate_blocked_scheme(self):
        """Test blocked scheme fails."""
        validator = URLValidator()
        
        with pytest.raises(ValueError, match="scheme not allowed"):
            validator.validate("ftp://example.com")
    
    def test_validate_blocked_domain(self):
        """Test blocked domain fails."""
        validator = URLValidator()
        
        with pytest.raises(ValueError, match="blocked"):
            validator.validate("http://localhost")
        
        with pytest.raises(ValueError, match="blocked"):
            validator.validate("http://127.0.0.1")
    
    def test_validate_internal_address(self):
        """Test internal addresses are blocked."""
        validator = URLValidator()
        
        with pytest.raises(ValueError, match="Internal"):
            validator.validate("http://192.168.1.1")
        
        with pytest.raises(ValueError, match="Internal"):
            validator.validate("http://10.0.0.1")
    
    def test_validate_internal_allowed(self):
        """Test internal addresses allowed when configured."""
        validator = URLValidator(allow_internal=True)
        result = validator.validate("http://192.168.1.1")
        assert "192.168.1.1" in result
    
    def test_validate_whitelist(self):
        """Test whitelist filtering."""
        validator = URLValidator(allowed_domains={"example.com", "*.google.com"})
        
        result = validator.validate("https://example.com/path")
        assert result == "https://example.com/path"
        
        result = validator.validate("https://api.google.com/v1")
        assert "google.com" in result
        
        with pytest.raises(ValueError, match="whitelist"):
            validator.validate("https://other.com")
    
    def test_validate_max_length(self):
        """Test URL length limit."""
        validator = URLValidator(max_length=50)
        
        with pytest.raises(ValueError, match="max length"):
            validator.validate("https://example.com/" + "a" * 100)


class TestFilePathValidator:
    """Test FilePathValidator class."""
    
    def test_validate_allowed_directory(self, tmp_path):
        """Test path in allowed directory passes."""
        validator = FilePathValidator(allowed_directories=[str(tmp_path)])
        
        test_file = tmp_path / "test.txt"
        result = validator.validate(str(test_file))
        
        assert result == test_file.resolve()
    
    def test_validate_blocked_directory(self, tmp_path):
        """Test path outside allowed directories fails."""
        validator = FilePathValidator(allowed_directories=[str(tmp_path)])
        
        with pytest.raises(ValueError, match="allowed directories"):
            validator.validate("/etc/passwd")
    
    def test_validate_blocked_patterns(self):
        """Test blocked patterns are detected."""
        validator = FilePathValidator(allowed_directories=["/"])
        
        with pytest.raises(ValueError, match="blocked pattern"):
            validator.validate("../../../etc/passwd")
    
    def test_validate_allowed_extensions(self, tmp_path):
        """Test extension filtering."""
        validator = FilePathValidator(
            allowed_directories=[str(tmp_path)],
            allowed_extensions={".txt", ".json"}
        )
        
        # Valid extension
        result = validator.validate(str(tmp_path / "file.txt"))
        assert result.suffix == ".txt"
        
        # Invalid extension
        with pytest.raises(ValueError, match="extension"):
            validator.validate(str(tmp_path / "file.exe"))
    
    def test_validate_for_read(self, tmp_path):
        """Test validate_for_read requires existing file."""
        validator = FilePathValidator(allowed_directories=[str(tmp_path)])
        
        # Non-existing file
        with pytest.raises(ValueError, match="does not exist"):
            validator.validate_for_read(str(tmp_path / "nonexistent.txt"))
        
        # Existing file
        test_file = tmp_path / "exists.txt"
        test_file.write_text("test")
        
        result = validator.validate_for_read(str(test_file))
        assert result.exists()
    
    def test_validate_for_write(self, tmp_path):
        """Test validate_for_write checks parent directory."""
        validator = FilePathValidator(allowed_directories=[str(tmp_path)])
        
        # Valid - parent exists
        result = validator.validate_for_write(str(tmp_path / "new_file.txt"))
        assert result.parent.exists()
        
        # Invalid - parent doesn't exist
        with pytest.raises(ValueError, match="Parent directory"):
            validator.validate_for_write(str(tmp_path / "nonexistent" / "file.txt"))


class TestSecretManager:
    """Test SecretManager class."""
    
    def test_generate_token(self):
        """Test token generation."""
        token1 = SecretManager.generate_token()
        token2 = SecretManager.generate_token()
        
        assert len(token1) > 0
        assert token1 != token2  # Should be unique
    
    def test_generate_token_length(self):
        """Test token length parameter."""
        token = SecretManager.generate_token(length=64)
        # URL-safe base64 encoding results in longer strings
        assert len(token) > 64
    
    def test_hash_secret(self):
        """Test secret hashing."""
        hashed = SecretManager.hash_secret("my_secret")
        
        assert ":" in hashed  # Should contain salt
        assert hashed != "my_secret"  # Should be hashed
    
    def test_verify_secret_valid(self):
        """Test verifying correct secret."""
        hashed = SecretManager.hash_secret("my_secret")
        
        assert SecretManager.verify_secret("my_secret", hashed) is True
    
    def test_verify_secret_invalid(self):
        """Test verifying incorrect secret."""
        hashed = SecretManager.hash_secret("my_secret")
        
        assert SecretManager.verify_secret("wrong_secret", hashed) is False
    
    def test_mask_secret(self):
        """Test secret masking."""
        result = SecretManager.mask_secret("0123456789abcdef")
        
        assert result.startswith("0123")
        assert result.endswith("cdef")
        assert "*" in result
    
    def test_mask_secret_short(self):
        """Test masking short secrets."""
        result = SecretManager.mask_secret("short")
        
        assert result == "*****"  # Fully masked


class TestRateLimiter:
    """Test RateLimiter class."""
    
    def test_is_allowed_within_limit(self):
        """Test requests within limit are allowed."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        for _ in range(5):
            assert limiter.is_allowed("user1") is True
    
    def test_is_allowed_exceeds_limit(self):
        """Test requests exceeding limit are blocked."""
        limiter = RateLimiter(max_requests=3, window_seconds=60)
        
        for _ in range(3):
            limiter.is_allowed("user1")
        
        assert limiter.is_allowed("user1") is False
    
    def test_is_allowed_different_keys(self):
        """Test different keys have separate limits."""
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        
        for _ in range(2):
            limiter.is_allowed("user1")
        
        assert limiter.is_allowed("user1") is False
        assert limiter.is_allowed("user2") is True  # Different key
    
    def test_get_remaining(self):
        """Test getting remaining requests."""
        limiter = RateLimiter(max_requests=5, window_seconds=60)
        
        assert limiter.get_remaining("user1") == 5
        
        limiter.is_allowed("user1")
        assert limiter.get_remaining("user1") == 4


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_validate_url(self):
        """Test validate_url function."""
        result = validate_url("https://example.com")
        assert result == "https://example.com"
    
    def test_validate_file_path(self, tmp_path):
        """Test validate_file_path function."""
        test_file = tmp_path / "test.txt"
        result = validate_file_path(str(test_file), [str(tmp_path)])
        
        assert result == test_file.resolve()
    
    def test_sanitize_input(self):
        """Test sanitize_input function."""
        result = sanitize_input("hello world")
        assert result == "hello world"
        
        with pytest.raises(ValueError):
            sanitize_input("")  # Empty not allowed by default
