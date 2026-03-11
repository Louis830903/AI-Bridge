"""
Tests for MCP Resources module
MCP 资源模块测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aibridge.core.resources import (
    Resource, ResourceContent, ResourceTemplate, ResourceType,
    ResourceProvider, AdapterResourceProvider, ConfigResourceProvider,
    ResourceManager,
)


class TestResource:
    """测试 Resource 数据类"""
    
    def test_create_resource(self):
        """测试创建资源"""
        resource = Resource(
            uri="adapter://chrome",
            name="Chrome Browser",
            description="Chrome adapter resource",
            mime_type="application/json"
        )
        
        assert resource.uri == "adapter://chrome"
        assert resource.name == "Chrome Browser"
        assert resource.mime_type == "application/json"
    
    def test_resource_to_dict(self):
        """测试资源转字典"""
        resource = Resource(
            uri="config://server",
            name="Server Config",
            description="Server configuration"
        )
        
        data = resource.to_dict()
        
        assert data["uri"] == "config://server"
        assert data["name"] == "Server Config"
        assert data["mimeType"] == "text/plain"  # default


class TestResourceContent:
    """测试 ResourceContent 数据类"""
    
    def test_text_content(self):
        """测试文本内容"""
        content = ResourceContent(
            uri="test://doc",
            text="Hello World"
        )
        
        data = content.to_dict()
        
        assert data["uri"] == "test://doc"
        assert data["text"] == "Hello World"
        assert "blob" not in data
    
    def test_blob_content(self):
        """测试二进制内容"""
        content = ResourceContent(
            uri="test://image",
            mime_type="image/png",
            blob=b"PNG DATA"
        )
        
        data = content.to_dict()
        
        assert data["mimeType"] == "image/png"
        assert "blob" in data  # base64 encoded


class TestResourceTemplate:
    """测试 ResourceTemplate 数据类"""
    
    def test_create_template(self):
        """测试创建模板"""
        template = ResourceTemplate(
            uri_template="adapter://{adapter_id}",
            name="Adapter Info",
            description="Get adapter information"
        )
        
        assert template.uri_template == "adapter://{adapter_id}"
    
    def test_template_to_dict(self):
        """测试模板转字典"""
        template = ResourceTemplate(
            uri_template="file:///{path}",
            name="File",
            mime_type="text/plain"
        )
        
        data = template.to_dict()
        
        assert data["uriTemplate"] == "file:///{path}"
        assert data["name"] == "File"


class TestResourceManager:
    """测试 ResourceManager"""
    
    def test_register_provider(self):
        """测试注册提供者"""
        manager = ResourceManager()
        
        mock_provider = MagicMock()
        mock_provider.scheme = "test"
        
        manager.register_provider(mock_provider)
        
        assert "test" in manager._providers
    
    def test_unregister_provider(self):
        """测试注销提供者"""
        manager = ResourceManager()
        
        mock_provider = MagicMock()
        mock_provider.scheme = "test"
        
        manager.register_provider(mock_provider)
        manager.unregister_provider("test")
        
        assert "test" not in manager._providers
    
    @pytest.mark.asyncio
    async def test_list_resources(self):
        """测试列出资源"""
        manager = ResourceManager()
        
        mock_provider = MagicMock()
        mock_provider.scheme = "test"
        mock_provider.list_resources = AsyncMock(return_value=[
            Resource(uri="test://one", name="One"),
            Resource(uri="test://two", name="Two"),
        ])
        
        manager.register_provider(mock_provider)
        
        resources = await manager.list_resources()
        
        assert len(resources) == 2
        assert resources[0]["uri"] == "test://one"
    
    @pytest.mark.asyncio
    async def test_read_resource(self):
        """测试读取资源"""
        manager = ResourceManager()
        
        mock_provider = MagicMock()
        mock_provider.scheme = "test"
        mock_provider.read_resource = AsyncMock(return_value=ResourceContent(
            uri="test://doc",
            text="Document content"
        ))
        
        manager.register_provider(mock_provider)
        
        content = await manager.read_resource("test://doc")
        
        assert content["text"] == "Document content"
    
    @pytest.mark.asyncio
    async def test_read_resource_invalid_uri(self):
        """测试读取无效 URI"""
        manager = ResourceManager()
        
        with pytest.raises(ValueError, match="Invalid resource URI"):
            await manager.read_resource("invalid-uri")
    
    @pytest.mark.asyncio
    async def test_read_resource_no_provider(self):
        """测试读取未注册 scheme 的资源"""
        manager = ResourceManager()
        
        with pytest.raises(ValueError, match="No provider for scheme"):
            await manager.read_resource("unknown://resource")
    
    def test_list_templates(self):
        """测试列出模板"""
        manager = ResourceManager()
        
        mock_provider = MagicMock()
        mock_provider.scheme = "test"
        mock_provider.get_templates.return_value = [
            ResourceTemplate(uri_template="test://{id}", name="Test")
        ]
        
        manager.register_provider(mock_provider)
        
        templates = manager.list_templates()
        
        assert len(templates) == 1
        assert templates[0]["name"] == "Test"


class TestAdapterResourceProvider:
    """测试 AdapterResourceProvider"""
    
    def test_scheme(self):
        """测试 scheme 属性"""
        mock_manager = MagicMock()
        provider = AdapterResourceProvider(mock_manager)
        
        assert provider.scheme == "adapter"
    
    @pytest.mark.asyncio
    async def test_list_resources(self):
        """测试列出适配器资源"""
        mock_manager = MagicMock()
        mock_manager.list_adapters.return_value = [
            {"id": "chrome", "name": "Chrome", "description": "Browser"},
            {"id": "slack", "name": "Slack", "description": "IM"},
        ]
        
        provider = AdapterResourceProvider(mock_manager)
        resources = await provider.list_resources()
        
        assert len(resources) == 2
        assert resources[0].uri == "adapter://chrome"
        assert resources[1].name == "Slack"
    
    def test_get_templates(self):
        """测试获取模板"""
        mock_manager = MagicMock()
        provider = AdapterResourceProvider(mock_manager)
        
        templates = provider.get_templates()
        
        assert len(templates) == 1
        assert "adapter_id" in templates[0].uri_template


class TestConfigResourceProvider:
    """测试 ConfigResourceProvider"""
    
    def test_scheme(self):
        """测试 scheme 属性"""
        mock_config = MagicMock()
        provider = ConfigResourceProvider(mock_config)
        
        assert provider.scheme == "config"
    
    @pytest.mark.asyncio
    async def test_list_resources(self):
        """测试列出配置资源"""
        mock_config = MagicMock()
        provider = ConfigResourceProvider(mock_config)
        
        resources = await provider.list_resources()
        
        assert len(resources) == 2
        uris = [r.uri for r in resources]
        assert "config://server" in uris
        assert "config://adapters" in uris
