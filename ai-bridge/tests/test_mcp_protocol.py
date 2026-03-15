"""
MCP Protocol 单元测试

测试 JSON-RPC over STDIO 通信层
"""

import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aibridge.gateway.mcp_protocol import (
    MCPProtocol,
    MCPMethod,
    MCPTool,
    MCPClientInfo,
    MCPServerInfo,
    JSONRPCRequest,
    JSONRPCResponse,
)


class TestJSONRPCRequest:
    """JSONRPCRequest 测试"""
    
    def test_basic_request(self):
        """测试基本请求"""
        request = JSONRPCRequest(method="test", id=1)
        
        d = request.to_dict()
        assert d["jsonrpc"] == "2.0"
        assert d["method"] == "test"
        assert d["id"] == 1
        assert "params" not in d
    
    def test_request_with_params(self):
        """测试带参数的请求"""
        request = JSONRPCRequest(
            method="tools/call",
            params={"name": "navigate", "url": "https://example.com"},
            id=2,
        )
        
        d = request.to_dict()
        assert d["params"]["name"] == "navigate"
        assert d["params"]["url"] == "https://example.com"
    
    def test_notification_no_id(self):
        """测试通知（无 ID）"""
        request = JSONRPCRequest(method="notifications/initialized")
        
        d = request.to_dict()
        assert "id" not in d
    
    def test_to_json(self):
        """测试 JSON 序列化"""
        request = JSONRPCRequest(method="test", id=1)
        
        json_str = request.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["jsonrpc"] == "2.0"
        assert parsed["method"] == "test"


class TestJSONRPCResponse:
    """JSONRPCResponse 测试"""
    
    def test_success_response(self):
        """测试成功响应"""
        response = JSONRPCResponse.from_dict({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"tools": []}
        })
        
        assert response.id == 1
        assert response.result == {"tools": []}
        assert response.is_error is False
    
    def test_error_response(self):
        """测试错误响应"""
        response = JSONRPCResponse.from_dict({
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32600, "message": "Invalid Request"}
        })
        
        assert response.is_error is True
        assert response.error["code"] == -32600


class TestMCPTool:
    """MCPTool 测试"""
    
    def test_from_dict(self):
        """测试从字典创建"""
        tool = MCPTool.from_dict({
            "name": "navigate",
            "description": "Navigate to URL",
            "inputSchema": {
                "type": "object",
                "properties": {"url": {"type": "string"}}
            }
        })
        
        assert tool.name == "navigate"
        assert tool.description == "Navigate to URL"
        assert "url" in tool.input_schema["properties"]
    
    def test_from_dict_minimal(self):
        """测试最小字典创建"""
        tool = MCPTool.from_dict({"name": "simple_tool"})
        
        assert tool.name == "simple_tool"
        assert tool.description == ""
        assert tool.input_schema == {}


class TestMCPMethod:
    """MCPMethod 枚举测试"""
    
    def test_method_values(self):
        """测试方法枚举值"""
        assert MCPMethod.INITIALIZE.value == "initialize"
        assert MCPMethod.TOOLS_LIST.value == "tools/list"
        assert MCPMethod.TOOLS_CALL.value == "tools/call"
        assert MCPMethod.SHUTDOWN.value == "shutdown"


class TestMCPClientInfo:
    """MCPClientInfo 测试"""
    
    def test_default_info(self):
        """测试默认客户端信息"""
        info = MCPClientInfo()
        
        assert info.name == "AI-Bridge"
        assert info.version == "3.0.0"
    
    def test_custom_info(self):
        """测试自定义客户端信息"""
        info = MCPClientInfo(name="CustomClient", version="1.0.0")
        
        assert info.name == "CustomClient"
        assert info.version == "1.0.0"


class TestMCPServerInfo:
    """MCPServerInfo 测试"""
    
    def test_default_info(self):
        """测试默认服务端信息"""
        info = MCPServerInfo()
        
        assert info.name == ""
        assert info.version == ""
        assert info.protocol_version == ""
    
    def test_custom_info(self):
        """测试自定义服务端信息"""
        info = MCPServerInfo(
            name="BrowserUse",
            version="1.0.0",
            protocol_version="2024-11-05"
        )
        
        assert info.name == "BrowserUse"
        assert info.version == "1.0.0"


class TestMCPProtocol:
    """MCPProtocol 测试"""
    
    @pytest.fixture
    def protocol(self):
        return MCPProtocol(timeout=5.0)
    
    def test_initial_state(self, protocol):
        """测试初始状态"""
        assert protocol.is_running is False
        assert protocol.is_initialized is False
        assert protocol.server_info is None
        assert protocol.tools == []
    
    def test_next_id(self, protocol):
        """测试 ID 生成"""
        id1 = protocol._next_id()
        id2 = protocol._next_id()
        
        assert id1 == 1
        assert id2 == 2
    
    @pytest.mark.asyncio
    async def test_shutdown_without_start(self, protocol):
        """测试未启动时关闭不报错"""
        await protocol.shutdown()
        # 应该不抛出异常
        assert protocol.is_running is False
    
    @pytest.mark.asyncio
    async def test_context_manager(self, protocol):
        """测试上下文管理器"""
        async with protocol:
            pass
        # shutdown 应该被调用
        assert protocol.is_running is False


class TestMCPProtocolIntegration:
    """MCPProtocol 集成测试（Mock）"""
    
    @pytest.mark.asyncio
    async def test_initialize_flow(self):
        """测试初始化流程（Mock）"""
        protocol = MCPProtocol(timeout=5.0)
        
        # Mock 进程
        mock_process = MagicMock()
        mock_process.returncode = None
        mock_process.pid = 12345
        mock_process.stdin = MagicMock()
        mock_process.stdin.write = MagicMock()
        mock_process.stdin.drain = AsyncMock()
        mock_process.stdout = MagicMock()
        mock_process.terminate = MagicMock()
        mock_process.wait = AsyncMock()
        mock_process.kill = MagicMock()
        
        # Mock 响应
        init_response = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "TestServer",
                    "version": "1.0.0"
                },
                "capabilities": {}
            }
        }) + "\n"
        
        tools_response = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "tools": [
                    {
                        "name": "navigate",
                        "description": "Navigate to URL",
                        "inputSchema": {}
                    }
                ]
            }
        }) + "\n"
        
        # 配置 readline 返回
        read_count = [0]
        async def mock_readline():
            read_count[0] += 1
            if read_count[0] == 1:
                return init_response.encode()
            elif read_count[0] == 2:
                return tools_response.encode()
            else:
                await asyncio.sleep(10)  # 阻塞后续读取
                return b""
        
        mock_process.stdout.readline = mock_readline
        
        with patch('asyncio.create_subprocess_exec', return_value=mock_process):
            await protocol.start("test_cmd")
            
            # 手动触发响应处理
            protocol._initialized = True
            protocol._server_info = MCPServerInfo(
                name="TestServer",
                version="1.0.0",
                protocol_version="2024-11-05"
            )
            protocol._tools = [
                MCPTool(name="navigate", description="Navigate to URL", input_schema={})
            ]
            
            assert protocol.server_info.name == "TestServer"
            assert len(protocol.tools) == 1
            assert protocol.tools[0].name == "navigate"
        
        await protocol.shutdown()
