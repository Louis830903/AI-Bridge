"""
Tests for adapter config module
适配器配置模块单元测试
"""

import os
import pytest
from aibridge.core.adapter_config import (
    BaseAdapterConfig, ChromeConfig, FeishuConfig, SlackConfig,
    TelegramConfig, WhatsAppConfig, OfficeConfig, DesktopConfig,
    create_config, CONFIG_CLASS_MAP
)


class TestBaseAdapterConfig:
    """Test BaseAdapterConfig."""
    
    def test_default_values(self):
        """Test default config values."""
        # 使用一个具体的子类来测试
        config = ChromeConfig()
        
        assert config.enabled is True
        assert config.timeout == 30
        assert config.retry_count == 3
        assert config.retry_delay == 1.0
    
    def test_to_dict(self):
        """Test converting config to dict."""
        config = ChromeConfig(cdp_url="http://test:9222")
        d = config.to_dict()
        
        assert d["enabled"] is True
        assert d["cdp_url"] == "http://test:9222"
        assert d["timeout"] == 30
    
    def test_from_dict(self):
        """Test creating config from dict."""
        data = {"cdp_url": "http://custom:9222", "timeout": 60}
        config = ChromeConfig.from_dict(data)
        
        assert config.cdp_url == "http://custom:9222"
        assert config.timeout == 60
    
    def test_from_dict_filters_invalid_fields(self):
        """Test that from_dict filters invalid fields."""
        data = {"cdp_url": "test", "invalid_field": "ignored"}
        config = ChromeConfig.from_dict(data)
        
        assert config.cdp_url == "test"
        assert not hasattr(config, "invalid_field")


class TestChromeConfig:
    """Test ChromeConfig."""
    
    def test_default_values(self):
        """Test Chrome config defaults."""
        config = ChromeConfig()
        
        assert config.cdp_url == "http://localhost:9222"
        assert config.headless is False
        assert config.user_data_dir is None
    
    def test_custom_values(self):
        """Test Chrome config with custom values."""
        config = ChromeConfig(
            cdp_url="http://remote:9222",
            headless=True,
            timeout=60
        )
        
        assert config.cdp_url == "http://remote:9222"
        assert config.headless is True
        assert config.timeout == 60


class TestFeishuConfig:
    """Test FeishuConfig."""
    
    def test_default_values(self):
        """Test Feishu config defaults."""
        config = FeishuConfig()
        
        assert config.app_id == ""
        assert config.app_secret == ""
        assert config.encrypt_key == ""
    
    def test_with_credentials(self):
        """Test Feishu config with credentials."""
        config = FeishuConfig(
            app_id="cli_xxx",
            app_secret="secret123"
        )
        
        assert config.app_id == "cli_xxx"
        assert config.app_secret == "secret123"


class TestSlackConfig:
    """Test SlackConfig."""
    
    def test_default_values(self):
        """Test Slack config defaults."""
        config = SlackConfig()
        
        assert config.bot_token == ""
        assert config.app_token == ""
        assert config.default_channel == ""
    
    def test_with_token(self):
        """Test Slack config with token."""
        config = SlackConfig(
            bot_token="xoxb-xxx",
            default_channel="#general"
        )
        
        assert config.bot_token == "xoxb-xxx"
        assert config.default_channel == "#general"


class TestTelegramConfig:
    """Test TelegramConfig."""
    
    def test_default_values(self):
        """Test Telegram config defaults."""
        config = TelegramConfig()
        
        assert config.bot_token == ""
        assert config.default_chat == ""
        assert config.parse_mode == "HTML"
    
    def test_parse_mode_options(self):
        """Test different parse modes."""
        config = TelegramConfig(parse_mode="Markdown")
        assert config.parse_mode == "Markdown"


class TestWhatsAppConfig:
    """Test WhatsAppConfig."""
    
    def test_default_values(self):
        """Test WhatsApp config defaults."""
        config = WhatsAppConfig()
        
        assert config.phone_number_id == ""
        assert config.access_token == ""
        assert config.api_version == "v18.0"
    
    def test_api_version(self):
        """Test custom API version."""
        config = WhatsAppConfig(api_version="v19.0")
        assert config.api_version == "v19.0"


class TestOfficeConfig:
    """Test OfficeConfig."""
    
    def test_default_values(self):
        """Test Office config defaults."""
        config = OfficeConfig()
        
        assert config.visible is True
        assert config.display_alerts is False
    
    def test_hidden_mode(self):
        """Test hidden mode configuration."""
        config = OfficeConfig(visible=False)
        assert config.visible is False


class TestDesktopConfig:
    """Test DesktopConfig."""
    
    def test_default_values(self):
        """Test Desktop config defaults."""
        config = DesktopConfig()
        
        assert config.backend == "uia"
    
    def test_win32_backend(self):
        """Test win32 backend configuration."""
        config = DesktopConfig(backend="win32")
        assert config.backend == "win32"


class TestConfigClassMap:
    """Test CONFIG_CLASS_MAP."""
    
    def test_all_adapters_mapped(self):
        """Test all adapters have config classes."""
        expected = [
            "chrome", "edge", "feishu", "dingtalk", "wecom",
            "slack", "teams", "discord", "google_chat",
            "telegram", "whatsapp", "messenger", "line", "viber", "kakaotalk",
            "office", "wps", "desktop"
        ]
        
        for adapter_id in expected:
            assert adapter_id in CONFIG_CLASS_MAP
    
    def test_config_classes_are_correct_type(self):
        """Test all mapped classes inherit from BaseAdapterConfig."""
        for adapter_id, config_class in CONFIG_CLASS_MAP.items():
            assert hasattr(config_class, "from_dict")
            assert hasattr(config_class, "to_dict")


class TestCreateConfig:
    """Test create_config function."""
    
    def test_create_chrome_config(self):
        """Test creating Chrome config."""
        config = create_config("chrome", {"cdp_url": "http://test:9222"})
        
        assert isinstance(config, ChromeConfig)
        assert config.cdp_url == "http://test:9222"
    
    def test_create_feishu_config(self):
        """Test creating Feishu config."""
        config = create_config("feishu", {"app_id": "test"})
        
        assert isinstance(config, FeishuConfig)
        assert config.app_id == "test"
    
    def test_create_unknown_adapter(self):
        """Test creating config for unknown adapter."""
        config = create_config("unknown", {})
        
        # Should return base config
        assert isinstance(config, BaseAdapterConfig)
    
    def test_create_with_empty_data(self):
        """Test creating config with empty data."""
        config = create_config("slack", {})
        
        assert isinstance(config, SlackConfig)
        assert config.bot_token == ""  # Default value


class TestFromEnv:
    """Test from_env class method."""
    
    def test_from_env_with_prefix(self, monkeypatch):
        """Test creating config from environment variables."""
        monkeypatch.setenv("FEISHU_APP_ID", "env_app_id")
        monkeypatch.setenv("FEISHU_APP_SECRET", "env_secret")
        
        config = FeishuConfig.from_env("FEISHU")
        
        assert config.app_id == "env_app_id"
        assert config.app_secret == "env_secret"
    
    def test_from_env_bool_conversion(self, monkeypatch):
        """Test boolean conversion from env."""
        monkeypatch.setenv("CHROME_HEADLESS", "true")
        
        config = ChromeConfig.from_env("CHROME")
        
        assert config.headless is True
    
    def test_from_env_int_conversion(self, monkeypatch):
        """Test integer conversion from env."""
        monkeypatch.setenv("SLACK_TIMEOUT", "60")
        
        config = SlackConfig.from_env("SLACK")
        
        assert config.timeout == 60
