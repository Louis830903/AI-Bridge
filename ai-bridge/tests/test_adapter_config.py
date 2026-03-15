"""
Tests for adapter config module
适配器配置模块单元测试
"""

import os
import pytest
from aibridge.core.adapter_config import (
    BaseAdapterConfig, ChromeConfig, EdgeConfig,
    OfficeConfig, WPSConfig,
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


class TestEdgeConfig:
    """Test EdgeConfig."""
    
    def test_default_values(self):
        """Test Edge config defaults."""
        config = EdgeConfig()
        
        assert config.cdp_url == "http://localhost:9223"
        assert config.headless is False
    
    def test_custom_values(self):
        """Test Edge config with custom values."""
        config = EdgeConfig(cdp_url="http://remote:9223", headless=True)
        
        assert config.cdp_url == "http://remote:9223"
        assert config.headless is True


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


class TestWPSConfig:
    """Test WPSConfig."""
    
    def test_default_values(self):
        """Test WPS config defaults."""
        config = WPSConfig()
        
        assert config.visible is True
    
    def test_hidden_mode(self):
        """Test hidden mode configuration."""
        config = WPSConfig(visible=False)
        assert config.visible is False


class TestConfigClassMap:
    """Test CONFIG_CLASS_MAP."""
    
    def test_all_adapters_mapped(self):
        """Test all adapters have config classes."""
        expected = ["chrome", "edge", "office", "wps"]
        
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
    
    def test_create_office_config(self):
        """Test creating Office config."""
        config = create_config("office", {"visible": False})
        
        assert isinstance(config, OfficeConfig)
        assert config.visible is False
    
    def test_create_unknown_adapter(self):
        """Test creating config for unknown adapter."""
        config = create_config("unknown", {})
        
        # Should return base config
        assert isinstance(config, BaseAdapterConfig)
    
    def test_create_with_empty_data(self):
        """Test creating config with empty data."""
        config = create_config("chrome", {})
        
        assert isinstance(config, ChromeConfig)
        assert config.cdp_url == "http://localhost:9222"  # Default value


class TestFromEnv:
    """Test from_env class method."""
    
    def test_from_env_bool_conversion(self, monkeypatch):
        """Test boolean conversion from env."""
        monkeypatch.setenv("CHROME_HEADLESS", "true")
        
        config = ChromeConfig.from_env("CHROME")
        
        assert config.headless is True
    
    def test_from_env_int_conversion(self, monkeypatch):
        """Test integer conversion from env."""
        monkeypatch.setenv("CHROME_TIMEOUT", "60")
        
        config = ChromeConfig.from_env("CHROME")
        
        assert config.timeout == 60
    
    def test_from_env_with_cdp_url(self, monkeypatch):
        """Test creating config from environment variables."""
        monkeypatch.setenv("CHROME_CDP_URL", "http://env:9222")
        
        config = ChromeConfig.from_env("CHROME")
        
        assert config.cdp_url == "http://env:9222"
