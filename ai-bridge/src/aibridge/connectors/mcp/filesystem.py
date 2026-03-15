"""
文件系统连接器

代理到 Filesystem MCP Server，提供安全的文件操作接口。
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..base import (
    MCPConnector,
    ConnectorConfig,
    ConnectorStatus,
    ConnectorError,
    ToolInfo,
)
from aibridge.gateway.mcp_protocol import MCPProtocol

logger = logging.getLogger(__name__)


@dataclass
class FilesystemConnectorConfig(ConnectorConfig):
    """文件系统连接器配置"""
    # 允许访问的目录列表（安全限制）
    allowed_directories: List[str] = field(default_factory=lambda: ["."])
    
    # 是否允许写操作
    read_only: bool = False
    
    # 是否允许删除操作
    allow_delete: bool = False


# 后端配置
FILESYSTEM_BACKEND_CONFIG = {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem"],
    "check_command": "npx",
    "check_args": ["--version"],
}


class FilesystemConnector(MCPConnector):
    """
    文件系统连接器
    
    代理到 Filesystem MCP Server，提供安全的文件操作接口。
    
    安全特性：
    - 目录白名单：只允许访问指定目录
    - 只读模式：可禁止写操作
    - 删除保护：默认禁止删除
    
    使用示例：
    ```python
    config = FilesystemConnectorConfig(
        name="filesystem",
        allowed_directories=["./data", "./output"],
        read_only=False,
        allow_delete=False,
    )
    
    connector = FilesystemConnector(config)
    
    async with connector:
        # 读取文件
        content = await connector.read_file("./data/config.json")
        
        # 写入文件
        await connector.write_file("./output/result.txt", "Hello World")
        
        # 列出目录
        files = await connector.list_directory("./data")
        
        # 搜索文件
        matches = await connector.search_files("./data", "*.json")
    ```
    """
    
    def __init__(self, config: FilesystemConnectorConfig):
        super().__init__(config)
        self._fs_config = config
        self._mcp: Optional[MCPProtocol] = None
    
    @property
    def mcp_protocol(self) -> Optional[MCPProtocol]:
        """MCP 协议实例"""
        return self._mcp
    
    async def _is_backend_available(self) -> bool:
        """检查后端是否可用"""
        import shutil
        
        config = FILESYSTEM_BACKEND_CONFIG
        command = config["check_command"]
        
        if not shutil.which(command):
            return False
        
        try:
            proc = await asyncio.create_subprocess_exec(
                command,
                *config["check_args"],
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.wait_for(proc.wait(), timeout=10.0)
            return proc.returncode == 0
        except Exception:
            return False
    
    async def _do_start(self) -> None:
        """启动文件系统后端"""
        if not await self._is_backend_available():
            raise ConnectorError(
                "Filesystem MCP Server not available. "
                "Please install: npm install -g @modelcontextprotocol/server-filesystem"
            )
        
        await self._start_backend()
    
    async def _start_backend(self) -> None:
        """启动后端并完成 MCP 协议握手"""
        import os
        
        config = FILESYSTEM_BACKEND_CONFIG
        logger.info("Starting filesystem backend")
        
        env = dict(os.environ)
        
        # 构建命令参数
        args = list(config["args"])
        
        # 添加允许的目录
        for directory in self._fs_config.allowed_directories:
            abs_path = str(Path(directory).resolve())
            args.append(abs_path)
        
        # 创建 MCP 协议实例
        self._mcp = MCPProtocol(timeout=self._config.timeout)
        
        await self._mcp.start(
            command=config["command"],
            args=args,
            env=env,
        )
        
        try:
            server_info = await self._mcp.initialize()
            logger.info(f"Filesystem MCP Server initialized: {server_info.name} v{server_info.version}")
            
            mcp_tools = await self._mcp.list_tools()
            self._tools = [
                ToolInfo(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in mcp_tools
            ]
            logger.info(f"Got {len(self._tools)} tools from Filesystem MCP Server")
            
        except Exception as e:
            logger.warning(f"MCP handshake failed, using standard tools: {e}")
            self._tools = self._get_standard_tools()
    
    async def _do_stop(self) -> None:
        """停止文件系统后端"""
        if self._mcp:
            await self._mcp.shutdown()
            self._mcp = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 MCP 协议调用工具"""
        if not self._mcp:
            raise ConnectorError("MCP protocol not initialized")
        
        # 安全检查
        if name in ["write_file", "create_directory", "move_file"] and self._fs_config.read_only:
            raise ConnectorError("Filesystem is in read-only mode")
        
        if name == "delete" and not self._fs_config.allow_delete:
            raise ConnectorError("Delete operation is not allowed")
        
        return await self._mcp.call_tool(name, params)
    
    def _get_standard_tools(self) -> List[ToolInfo]:
        """获取标准文件系统工具列表"""
        return [
            ToolInfo(
                name="read_file",
                description="Read the contents of a file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file to read"
                        }
                    },
                    "required": ["path"]
                }
            ),
            ToolInfo(
                name="write_file",
                description="Write content to a file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["path", "content"]
                }
            ),
            ToolInfo(
                name="list_directory",
                description="List contents of a directory",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            ),
            ToolInfo(
                name="create_directory",
                description="Create a new directory",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            ),
            ToolInfo(
                name="move_file",
                description="Move or rename a file",
                input_schema={
                    "type": "object",
                    "properties": {
                        "source": {"type": "string"},
                        "destination": {"type": "string"}
                    },
                    "required": ["source", "destination"]
                }
            ),
            ToolInfo(
                name="search_files",
                description="Search for files matching a pattern",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "pattern": {"type": "string"}
                    },
                    "required": ["path", "pattern"]
                }
            ),
            ToolInfo(
                name="get_file_info",
                description="Get information about a file (size, modified time, etc.)",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            ),
        ]
    
    # 便捷方法
    async def read_file(self, path: str) -> str:
        """读取文件内容"""
        return await self.call_tool("read_file", {"path": path})
    
    async def write_file(self, path: str, content: str) -> Any:
        """写入文件"""
        if self._fs_config.read_only:
            raise ConnectorError("Filesystem is in read-only mode")
        return await self.call_tool("write_file", {"path": path, "content": content})
    
    async def list_directory(self, path: str = ".") -> List[str]:
        """列出目录内容"""
        return await self.call_tool("list_directory", {"path": path})
    
    async def create_directory(self, path: str) -> Any:
        """创建目录"""
        if self._fs_config.read_only:
            raise ConnectorError("Filesystem is in read-only mode")
        return await self.call_tool("create_directory", {"path": path})
    
    async def move_file(self, source: str, destination: str) -> Any:
        """移动/重命名文件"""
        if self._fs_config.read_only:
            raise ConnectorError("Filesystem is in read-only mode")
        return await self.call_tool("move_file", {"source": source, "destination": destination})
    
    async def search_files(self, path: str, pattern: str) -> List[str]:
        """搜索文件"""
        return await self.call_tool("search_files", {"path": path, "pattern": pattern})
    
    async def get_file_info(self, path: str) -> Dict[str, Any]:
        """获取文件信息"""
        return await self.call_tool("get_file_info", {"path": path})
