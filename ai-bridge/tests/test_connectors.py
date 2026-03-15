"""
Connectors 模块单元测试

测试 MCPConnector 基类和 BrowserConnector
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aibridge.connectors.base import (
    MCPConnector,
    ConnectorConfig,
    ConnectorStatus,
    ConnectorError,
    ToolInfo,
)
from aibridge.connectors.mcp import BrowserConnector, BrowserConnectorConfig
from aibridge.connectors.mcp.browser import BrowserBackend


class TestConnectorConfig:
    """ConnectorConfig 测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = ConnectorConfig(name="test")
        
        assert config.name == "test"
        assert config.timeout == 30.0
        assert config.auto_connect is True
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = ConnectorConfig(
            name="custom",
            timeout=60.0,
            auto_connect=False,
        )
        
        assert config.name == "custom"
        assert config.timeout == 60.0
        assert config.auto_connect is False


class TestBrowserConnectorConfig:
    """BrowserConnectorConfig 测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = BrowserConnectorConfig(name="browser")
        
        assert config.backend == BrowserBackend.AUTO
        assert config.headless is True
        assert config.viewport_width == 1280
        assert config.viewport_height == 720
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = BrowserConnectorConfig(
            name="browser",
            backend=BrowserBackend.BROWSER_USE,
            headless=False,
            viewport_width=1920,
            viewport_height=1080,
        )
        
        assert config.backend == BrowserBackend.BROWSER_USE
        assert config.headless is False
        assert config.viewport_width == 1920
        assert config.viewport_height == 1080


class TestBrowserConnector:
    """BrowserConnector 测试"""
    
    @pytest.fixture
    def connector(self):
        config = BrowserConnectorConfig(
            name="test-browser",
            backend=BrowserBackend.AUTO,
        )
        return BrowserConnector(config)
    
    def test_initial_status(self, connector):
        """测试初始状态"""
        assert connector.status == ConnectorStatus.DISCONNECTED
        assert connector.active_backend is None
    
    def test_config_access(self, connector):
        """测试配置访问"""
        assert connector.name == "test-browser"
        assert connector._browser_config.backend == BrowserBackend.AUTO
    
    @pytest.mark.asyncio
    async def test_detect_backend_none_available(self, connector):
        """测试无可用后端时返回 None"""
        with patch.object(connector, '_is_backend_available', return_value=False):
            backend = await connector._detect_available_backend()
            assert backend is None
    
    @pytest.mark.asyncio
    async def test_detect_backend_browser_use(self, connector):
        """测试检测到 Browser Use 后端"""
        async def mock_available(backend):
            return backend == BrowserBackend.BROWSER_USE
        
        with patch.object(connector, '_is_backend_available', side_effect=mock_available):
            backend = await connector._detect_available_backend()
            assert backend == BrowserBackend.BROWSER_USE
    
    def test_get_standard_tools(self, connector):
        """测试获取标准工具列表"""
        tools = connector._get_standard_tools()
        
        assert len(tools) > 0
        tool_names = [t.name for t in tools]
        assert "navigate" in tool_names
        assert "click" in tool_names
        assert "type" in tool_names
        assert "screenshot" in tool_names


class TestToolInfo:
    """ToolInfo 测试"""
    
    def test_basic_tool(self):
        """测试基本工具信息"""
        tool = ToolInfo(
            name="test_tool",
            description="A test tool",
            input_schema={},
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "A test tool"
        assert tool.input_schema == {}
    
    def test_tool_with_schema(self):
        """测试带 schema 的工具"""
        tool = ToolInfo(
            name="navigate",
            description="Navigate to URL",
            input_schema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to navigate to"}
                },
                "required": ["url"]
            }
        )
        
        assert "url" in tool.input_schema["properties"]


class TestConnectorStatus:
    """ConnectorStatus 测试"""
    
    def test_status_values(self):
        """测试状态枚举值"""
        assert ConnectorStatus.DISCONNECTED.value == "disconnected"
        assert ConnectorStatus.CONNECTING.value == "connecting"
        assert ConnectorStatus.CONNECTED.value == "connected"
        assert ConnectorStatus.ERROR.value == "error"


class TestConnectorError:
    """ConnectorError 测试"""
    
    def test_basic_error(self):
        """测试基本错误"""
        error = ConnectorError("Something went wrong")
        
        assert str(error) == "Something went wrong"
        assert isinstance(error, Exception)
    
    def test_error_with_cause(self):
        """测试带原因的错误"""
        cause = ValueError("Invalid value")
        error = ConnectorError("Wrapper error")
        error.__cause__ = cause
        
        assert error.__cause__ == cause


class TestBrowserBackend:
    """BrowserBackend 枚举测试"""
    
    def test_backend_values(self):
        """测试后端枚举值"""
        assert BrowserBackend.BROWSER_USE.value == "browser-use"
        assert BrowserBackend.CHROME_DEVTOOLS.value == "chrome-devtools"
        assert BrowserBackend.PLAYWRIGHT.value == "playwright"
        assert BrowserBackend.AUTO.value == "auto"
