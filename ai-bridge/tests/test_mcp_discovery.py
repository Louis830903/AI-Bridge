"""
MCP Server 动态发现测试
"""

import pytest
import asyncio
import json
import os
from pathlib import Path

from aibridge.enterprise.mcp_discovery import (
    ServerStatus,
    TransportType,
    MCPServerConfig,
    DiscoverySource,
    MCPServerDiscovery,
)


class TestServerStatus:
    """ServerStatus 测试"""
    
    def test_status_values(self):
        """测试状态值"""
        assert ServerStatus.UNKNOWN.value == "unknown"
        assert ServerStatus.HEALTHY.value == "healthy"
        assert ServerStatus.UNHEALTHY.value == "unhealthy"
        assert ServerStatus.CONNECTING.value == "connecting"
        assert ServerStatus.DISCONNECTED.value == "disconnected"


class TestTransportType:
    """TransportType 测试"""
    
    def test_transport_values(self):
        """测试传输类型值"""
        assert TransportType.STDIO.value == "stdio"
        assert TransportType.SSE.value == "sse"
        assert TransportType.WEBSOCKET.value == "websocket"
        assert TransportType.HTTP.value == "http"


class TestMCPServerConfig:
    """MCPServerConfig 测试"""
    
    def test_create_stdio_config(self):
        """测试创建 STDIO 配置"""
        config = MCPServerConfig(
            name="test-server",
            command="python",
            args=["-m", "mcp_server"],
            env={"DEBUG": "1"},
        )
        
        assert config.name == "test-server"
        assert config.command == "python"
        assert config.transport == TransportType.STDIO
        assert config.status == ServerStatus.UNKNOWN
    
    def test_create_http_config(self):
        """测试创建 HTTP 配置"""
        config = MCPServerConfig(
            name="http-server",
            url="http://localhost:8080",
            transport=TransportType.HTTP,
        )
        
        assert config.name == "http-server"
        assert config.url == "http://localhost:8080"
        assert config.transport == TransportType.HTTP
    
    def test_to_dict(self):
        """测试字典转换"""
        config = MCPServerConfig(
            name="test",
            command="python",
            args=["--arg"],
            tags=["prod"],
        )
        
        d = config.to_dict()
        
        assert d["name"] == "test"
        assert d["command"] == "python"
        assert d["args"] == ["--arg"]
        assert d["tags"] == ["prod"]
        assert d["transport"] == "stdio"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "name": "server-1",
            "command": "node",
            "args": ["server.js"],
            "transport": "stdio",
            "timeout_seconds": 60.0,
        }
        
        config = MCPServerConfig.from_dict(data)
        
        assert config.name == "server-1"
        assert config.command == "node"
        assert config.timeout_seconds == 60.0


class TestDiscoverySource:
    """DiscoverySource 测试"""
    
    def test_create_source(self):
        """测试创建发现源"""
        source = DiscoverySource(
            name="config-file",
            source_type="file",
            priority=10,
        )
        
        assert source.name == "config-file"
        assert source.source_type == "file"
        assert source.priority == 10
        assert source.last_update is None


class TestMCPServerDiscovery:
    """MCPServerDiscovery 测试"""
    
    @pytest.fixture
    def discovery(self):
        """创建发现服务"""
        return MCPServerDiscovery()
    
    @pytest.mark.asyncio
    async def test_register_server(self, discovery):
        """测试注册 Server"""
        config = MCPServerConfig(
            name="test-server",
            command="python",
            args=["-m", "test"],
        )
        
        await discovery.register(config)
        
        found = await discovery.get("test-server")
        assert found is not None
        assert found.name == "test-server"
    
    @pytest.mark.asyncio
    async def test_unregister_server(self, discovery):
        """测试注销 Server"""
        config = MCPServerConfig(name="test", command="python")
        await discovery.register(config)
        
        result = await discovery.unregister("test")
        assert result is True
        
        found = await discovery.get("test")
        assert found is None
    
    @pytest.mark.asyncio
    async def test_unregister_nonexistent(self, discovery):
        """测试注销不存在的 Server"""
        result = await discovery.unregister("nonexistent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_list_servers(self, discovery):
        """测试列出 Servers"""
        for i in range(3):
            await discovery.register(MCPServerConfig(
                name=f"server-{i}",
                command="python",
            ))
        
        servers = await discovery.list_servers()
        assert len(servers) == 3
    
    @pytest.mark.asyncio
    async def test_list_servers_filter_status(self, discovery):
        """测试按状态过滤"""
        config1 = MCPServerConfig(name="healthy", command="python")
        config2 = MCPServerConfig(name="unhealthy", command="python")
        
        config1.status = ServerStatus.HEALTHY
        config2.status = ServerStatus.UNHEALTHY
        
        await discovery.register(config1)
        await discovery.register(config2)
        
        healthy = await discovery.list_servers(status=ServerStatus.HEALTHY)
        assert len(healthy) == 1
        assert healthy[0].name == "healthy"
    
    @pytest.mark.asyncio
    async def test_list_servers_filter_tags(self, discovery):
        """测试按标签过滤"""
        await discovery.register(MCPServerConfig(
            name="prod-server",
            command="python",
            tags=["prod", "v2"],
        ))
        await discovery.register(MCPServerConfig(
            name="dev-server",
            command="python",
            tags=["dev"],
        ))
        
        prod = await discovery.list_servers(tags=["prod"])
        assert len(prod) == 1
        assert prod[0].name == "prod-server"
    
    @pytest.mark.asyncio
    async def test_list_servers_filter_transport(self, discovery):
        """测试按传输类型过滤"""
        await discovery.register(MCPServerConfig(
            name="stdio-server",
            command="python",
            transport=TransportType.STDIO,
        ))
        await discovery.register(MCPServerConfig(
            name="http-server",
            url="http://localhost:8080",
            transport=TransportType.HTTP,
        ))
        
        http = await discovery.list_servers(transport=TransportType.HTTP)
        assert len(http) == 1
        assert http[0].name == "http-server"
    
    @pytest.mark.asyncio
    async def test_get_healthy_servers(self, discovery):
        """测试获取健康 Servers"""
        config1 = MCPServerConfig(name="s1", command="python")
        config2 = MCPServerConfig(name="s2", command="python")
        
        config1.status = ServerStatus.HEALTHY
        config2.status = ServerStatus.UNHEALTHY
        
        await discovery.register(config1)
        await discovery.register(config2)
        
        healthy = await discovery.get_healthy_servers()
        assert len(healthy) == 1
    
    @pytest.mark.asyncio
    async def test_count(self, discovery):
        """测试计数"""
        for i in range(3):
            config = MCPServerConfig(name=f"s{i}", command="python")
            config.status = ServerStatus.HEALTHY if i < 2 else ServerStatus.UNHEALTHY
            await discovery.register(config)
        
        total = await discovery.count()
        assert total == 3
        
        healthy = await discovery.count(status=ServerStatus.HEALTHY)
        assert healthy == 2


class TestMCPServerDiscoveryCallbacks:
    """发现服务回调测试"""
    
    @pytest.fixture
    def discovery(self):
        """创建发现服务"""
        return MCPServerDiscovery()
    
    @pytest.mark.asyncio
    async def test_on_server_added_callback(self, discovery):
        """测试 Server 添加回调"""
        added = []
        
        async def callback(config):
            added.append(config.name)
        
        discovery.on_server_added(callback)
        
        await discovery.register(MCPServerConfig(name="test", command="python"))
        
        assert "test" in added
    
    @pytest.mark.asyncio
    async def test_on_server_removed_callback(self, discovery):
        """测试 Server 移除回调"""
        removed = []
        
        async def callback(name):
            removed.append(name)
        
        discovery.on_server_removed(callback)
        
        await discovery.register(MCPServerConfig(name="test", command="python"))
        await discovery.unregister("test")
        
        assert "test" in removed
    
    @pytest.mark.asyncio
    async def test_on_server_updated_callback(self, discovery):
        """测试 Server 更新回调"""
        updated = []
        
        async def callback(config):
            updated.append(config.name)
        
        discovery.on_server_updated(callback)
        
        # 第一次注册触发 added
        await discovery.register(MCPServerConfig(name="test", command="python"))
        
        # 第二次注册触发 updated
        await discovery.register(MCPServerConfig(name="test", command="node"))
        
        assert "test" in updated


class TestConfigFileLoading:
    """配置文件加载测试"""
    
    @pytest.mark.asyncio
    async def test_load_claude_desktop_config(self, tmp_path):
        """测试加载 Claude Desktop 格式配置"""
        config_data = {
            "mcpServers": {
                "server-1": {
                    "command": "python",
                    "args": ["-m", "server1"],
                    "env": {"KEY": "value"},
                },
                "server-2": {
                    "url": "http://localhost:8080",
                    "transport": "http",
                },
            }
        }
        
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(config_data))
        
        discovery = MCPServerDiscovery()
        await discovery.add_config_file(str(config_file), watch=False)
        
        servers = await discovery.list_servers()
        assert len(servers) == 2
        
        s1 = await discovery.get("server-1")
        assert s1.command == "python"
        assert s1.args == ["-m", "server1"]
        
        s2 = await discovery.get("server-2")
        assert s2.url == "http://localhost:8080"
        assert s2.transport == TransportType.HTTP
    
    @pytest.mark.asyncio
    async def test_load_nonexistent_file(self, tmp_path):
        """测试加载不存在的文件"""
        discovery = MCPServerDiscovery()
        await discovery.add_config_file(str(tmp_path / "nonexistent.json"), watch=False)
        
        servers = await discovery.list_servers()
        assert len(servers) == 0


class TestEnvLoading:
    """环境变量加载测试"""
    
    @pytest.mark.asyncio
    async def test_load_from_env(self, monkeypatch):
        """测试从环境变量加载"""
        monkeypatch.setenv("MCP_SERVER_TEST", "python|arg1,arg2|http://example.com")
        
        discovery = MCPServerDiscovery()
        await discovery.add_env_source("MCP_SERVER_")
        
        server = await discovery.get("test")
        assert server is not None
        assert server.command == "python"
        assert server.args == ["arg1", "arg2"]
        assert server.url == "http://example.com"
    
    @pytest.mark.asyncio
    async def test_load_json_from_env(self, monkeypatch):
        """测试从环境变量加载 JSON"""
        config_json = json.dumps({
            "command": "node",
            "args": ["server.js"],
            "transport": "stdio",
        })
        monkeypatch.setenv("MCP_SERVER_JSONTEST", config_json)
        
        discovery = MCPServerDiscovery()
        await discovery.add_env_source("MCP_SERVER_")
        
        server = await discovery.get("jsontest")
        assert server is not None
        assert server.command == "node"


class TestDiscoveryLifecycle:
    """发现服务生命周期测试"""
    
    @pytest.mark.asyncio
    async def test_start_stop(self):
        """测试启动停止"""
        discovery = MCPServerDiscovery()
        
        await discovery.start()
        assert discovery._running is True
        
        await discovery.stop()
        assert discovery._running is False
