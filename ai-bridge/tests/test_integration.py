"""Adapter Integration Tests
适配器集成测试
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aibridge.core.protocol import Target, Request, Response
from aibridge.adapters.base import AdapterType, AdapterInfo
from aibridge.core.adapter_config import (
    ChromeConfig, SlackConfig, FeishuConfig,
    OfficeConfig, DesktopConfig, create_config,
)


# ============ Configuration Integration Tests ============

class TestConfigurationIntegration:
    """配置集成测试"""
    
    def test_create_config_for_chrome(self):
        """测试创建 Chrome 配置"""
        config = create_config("chrome", {
            "cdp_url": "http://localhost:9999",
            "headless": True
        })
        
        assert isinstance(config, ChromeConfig)
        assert config.cdp_url == "http://localhost:9999"
        assert config.headless is True
    
    def test_create_config_for_slack(self):
        """测试创建 Slack 配置"""
        config = create_config("slack", {
            "bot_token": "xoxb-test",
            "default_channel": "#general"
        })
        
        assert isinstance(config, SlackConfig)
        assert config.bot_token == "xoxb-test"
    
    def test_create_config_unknown_adapter(self):
        """测试创建未知适配器配置"""
        config = create_config("unknown", {"enabled": False})
        # 应返回基类配置
        assert config.enabled is False
    
    def test_config_to_dict(self):
        """测试配置转字典"""
        config = ChromeConfig(
            cdp_url="http://test:1234",
            headless=True
        )
        
        data = config.to_dict()
        
        assert data["cdp_url"] == "http://test:1234"
        assert data["headless"] is True
        assert "enabled" in data
    
    def test_config_from_dict_filters_unknown(self):
        """测试从字典创建配置过滤未知字段"""
        config = ChromeConfig.from_dict({
            "cdp_url": "http://test:5678",
            "unknown_field": "should be ignored"
        })
        
        assert config.cdp_url == "http://test:5678"
        assert not hasattr(config, "unknown_field")
    
    def test_config_from_env(self):
        """测试从环境变量创建配置"""
        import os
        
        os.environ["SLACK_BOT_TOKEN"] = "env-token"
        os.environ["SLACK_ENABLED"] = "false"
        
        try:
            config = SlackConfig.from_env("SLACK")
            assert config.bot_token == "env-token"
            assert config.enabled is False
        finally:
            del os.environ["SLACK_BOT_TOKEN"]
            del os.environ["SLACK_ENABLED"]


# ============ Protocol Integration Tests ============

class TestProtocolIntegration:
    """协议集成测试"""
    
    def test_target_with_locators(self):
        """测试带定位器的目标"""
        target = Target(
            name="Test Button",
            css="#btn",
            role="button"
        )
        
        assert target.name == "Test Button"
        assert target.css == "#btn"
    
    def test_request_creation(self):
        """测试请求创建"""
        request = Request(
            app="slack",
            action="send_message",
            target=Target(name="channel"),
            value="Hello"
        )
        
        assert request.app == "slack"
        assert request.action == "send_message"
    
    def test_response_success(self):
        """测试成功响应"""
        response = Response(
            success=True,
            data={"message_id": "msg-456"}
        )
        
        assert response.success is True
        assert response.data["message_id"] == "msg-456"
    
    def test_response_error(self):
        """测试错误响应"""
        response = Response(
            success=False,
            error="Connection failed"
        )
        
        assert response.success is False
        assert response.error == "Connection failed"
    
    def test_response_success_helper(self):
        """测试成功响应辅助方法"""
        response = Response.success_response(data={"id": "123"})
        
        assert response.success is True
        assert response.data["id"] == "123"
    
    def test_response_error_helper(self):
        """测试错误响应辅助方法"""
        response = Response.error_response("Something went wrong")
        
        assert response.success is False
        assert response.error == "Something went wrong"


# ============ AdapterInfo Tests ============

class TestAdapterInfo:
    """适配器信息测试"""
    
    def test_adapter_info_creation(self):
        """测试创建适配器信息"""
        info = AdapterInfo(
            id="chrome",
            name="Chrome Browser",
            type=AdapterType.BROWSER,
            actions=["click", "type", "screenshot"]
        )
        
        assert info.id == "chrome"
        assert info.name == "Chrome Browser"
        assert info.type == AdapterType.BROWSER
        assert len(info.actions) == 3
    
    def test_adapter_type_values(self):
        """测试适配器类型枚举值"""
        assert AdapterType.BROWSER.value == "browser"
        assert AdapterType.IM.value == "im"
        assert AdapterType.OFFICE.value == "office"
        assert AdapterType.DESKTOP.value == "desktop"


# ============ Target Tests ============

class TestTarget:
    """目标元素测试"""
    
    def test_target_to_dict(self):
        """测试目标转字典"""
        target = Target(
            name="Submit",
            css="#submit-btn",
            role="button"
        )
        
        data = target.to_dict()
        
        assert data["name"] == "Submit"
        assert data["css"] == "#submit-btn"
    
    def test_target_from_dict(self):
        """测试从字典创建目标"""
        data = {
            "name": "Login",
            "xpath": "//button[@type='submit']",
            "index": 0
        }
        
        target = Target.from_dict(data)
        
        assert target.name == "Login"
        assert target.xpath == "//button[@type='submit']"
    
    def test_nested_target(self):
        """测试嵌套目标"""
        container = Target(name="Form")
        button = Target(
            name="Submit",
            inside=container
        )
        
        assert button.inside.name == "Form"


# ============ Request Tests ============

class TestRequest:
    """请求测试"""
    
    def test_request_to_dict(self):
        """测试请求转字典"""
        request = Request(
            app="chrome",
            action="click",
            target=Target(css="#btn"),
            value=None
        )
        
        data = request.to_dict()
        
        assert data["app"] == "chrome"
        assert data["action"] == "click"
        assert "target" in data
    
    def test_request_from_dict(self):
        """测试从字典创建请求"""
        data = {
            "app": "excel",
            "action": "write",
            "target": {"name": "A1"},
            "value": "Hello"
        }
        
        request = Request.from_dict(data)
        
        assert request.app == "excel"
        assert request.value == "Hello"
