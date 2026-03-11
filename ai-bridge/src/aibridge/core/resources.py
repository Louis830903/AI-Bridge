"""
MCP Resources - Resources support for MCP protocol
MCP 资源模块 - 提供资源管理和访问功能
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Callable
from enum import Enum
import mimetypes


class ResourceType(str, Enum):
    """资源类型"""
    TEXT = "text"
    BLOB = "blob"
    JSON = "json"


@dataclass
class Resource:
    """
    MCP 资源定义
    
    资源是 AI 可以访问的数据源，如文件、数据库记录等。
    """
    uri: str  # 资源 URI，格式: scheme://path
    name: str  # 显示名称
    description: str = ""
    mime_type: str = "text/plain"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uri": self.uri,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


@dataclass
class ResourceContent:
    """资源内容"""
    uri: str
    mime_type: str = "text/plain"
    text: Optional[str] = None
    blob: Optional[bytes] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "uri": self.uri,
            "mimeType": self.mime_type,
        }
        if self.text is not None:
            result["text"] = self.text
        if self.blob is not None:
            import base64
            result["blob"] = base64.b64encode(self.blob).decode()
        return result


@dataclass
class ResourceTemplate:
    """
    资源模板
    
    用于动态生成资源，支持参数化 URI。
    """
    uri_template: str  # URI 模板，如 "file:///{path}"
    name: str
    description: str = ""
    mime_type: str = "text/plain"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "uriTemplate": self.uri_template,
            "name": self.name,
            "description": self.description,
            "mimeType": self.mime_type,
        }


class ResourceProvider(ABC):
    """
    资源提供者抽象基类
    
    每种类型的资源应实现此接口。
    """
    
    @property
    @abstractmethod
    def scheme(self) -> str:
        """资源 URI 的 scheme，如 'file', 'adapter', 'config'"""
        pass
    
    @abstractmethod
    async def list_resources(self) -> List[Resource]:
        """列出可用资源"""
        pass
    
    @abstractmethod
    async def read_resource(self, uri: str) -> ResourceContent:
        """读取资源内容"""
        pass
    
    def get_templates(self) -> List[ResourceTemplate]:
        """获取资源模板（可选）"""
        return []


class AdapterResourceProvider(ResourceProvider):
    """
    适配器资源提供者
    
    将已注册的适配器暴露为资源。
    """
    
    def __init__(self, manager):
        self._manager = manager
    
    @property
    def scheme(self) -> str:
        return "adapter"
    
    async def list_resources(self) -> List[Resource]:
        """列出所有适配器作为资源"""
        resources = []
        for adapter_info in self._manager.list_adapters():
            resources.append(Resource(
                uri=f"adapter://{adapter_info['id']}",
                name=adapter_info['name'],
                description=f"Adapter: {adapter_info.get('description', '')}",
                mime_type="application/json",
            ))
        return resources
    
    async def read_resource(self, uri: str) -> ResourceContent:
        """读取适配器信息"""
        import json
        
        # 解析 URI: adapter://adapter_id
        adapter_id = uri.replace("adapter://", "")
        adapter = self._manager.get_any_adapter(adapter_id)
        
        if not adapter:
            raise ValueError(f"Adapter not found: {adapter_id}")
        
        # 获取适配器信息
        info = adapter.info.to_dict()
        health = {}
        
        if hasattr(adapter, 'health_check'):
            try:
                import inspect
                if inspect.iscoroutinefunction(adapter.health_check):
                    health = await adapter.health_check()
                else:
                    health = adapter.health_check()
            except Exception:
                pass
        
        content = {
            "adapter": info,
            "health": health,
            "connected": adapter.is_connected,
        }
        
        return ResourceContent(
            uri=uri,
            mime_type="application/json",
            text=json.dumps(content, ensure_ascii=False, indent=2),
        )
    
    def get_templates(self) -> List[ResourceTemplate]:
        return [
            ResourceTemplate(
                uri_template="adapter://{adapter_id}",
                name="Adapter Info",
                description="Get information about a specific adapter",
                mime_type="application/json",
            )
        ]


class ConfigResourceProvider(ResourceProvider):
    """
    配置资源提供者
    
    将系统配置暴露为资源。
    """
    
    def __init__(self, config):
        self._config = config
    
    @property
    def scheme(self) -> str:
        return "config"
    
    async def list_resources(self) -> List[Resource]:
        """列出配置资源"""
        return [
            Resource(
                uri="config://server",
                name="Server Configuration",
                description="AI-Bridge server configuration",
                mime_type="application/json",
            ),
            Resource(
                uri="config://adapters",
                name="Adapters Configuration",
                description="Enabled adapters and their settings",
                mime_type="application/json",
            ),
        ]
    
    async def read_resource(self, uri: str) -> ResourceContent:
        """读取配置"""
        import json
        
        path = uri.replace("config://", "")
        
        if path == "server":
            content = {
                "transport": self._config.server.transport,
                "host": self._config.server.host,
                "port": self._config.server.port,
                "log_level": self._config.server.log_level,
            }
        elif path == "adapters":
            content = {
                name: {"enabled": adapter.enabled}
                for name, adapter in self._config.adapters.items()
            }
        else:
            raise ValueError(f"Unknown config resource: {path}")
        
        return ResourceContent(
            uri=uri,
            mime_type="application/json",
            text=json.dumps(content, ensure_ascii=False, indent=2),
        )


class ResourceManager:
    """
    资源管理器
    
    管理所有资源提供者，处理资源请求。
    """
    
    def __init__(self):
        self._providers: Dict[str, ResourceProvider] = {}
    
    def register_provider(self, provider: ResourceProvider):
        """注册资源提供者"""
        self._providers[provider.scheme] = provider
    
    def unregister_provider(self, scheme: str):
        """注销资源提供者"""
        if scheme in self._providers:
            del self._providers[scheme]
    
    async def list_resources(self) -> List[Dict[str, Any]]:
        """列出所有资源"""
        resources = []
        for provider in self._providers.values():
            try:
                provider_resources = await provider.list_resources()
                resources.extend([r.to_dict() for r in provider_resources])
            except Exception:
                pass
        return resources
    
    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """读取资源"""
        # 解析 scheme
        if "://" not in uri:
            raise ValueError(f"Invalid resource URI: {uri}")
        
        scheme = uri.split("://")[0]
        provider = self._providers.get(scheme)
        
        if not provider:
            raise ValueError(f"No provider for scheme: {scheme}")
        
        content = await provider.read_resource(uri)
        return content.to_dict()
    
    def list_templates(self) -> List[Dict[str, Any]]:
        """列出所有资源模板"""
        templates = []
        for provider in self._providers.values():
            templates.extend([t.to_dict() for t in provider.get_templates()])
        return templates
