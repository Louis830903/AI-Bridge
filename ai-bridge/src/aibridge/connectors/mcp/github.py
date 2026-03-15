"""
GitHub 连接器

代理到 GitHub MCP Server，提供 GitHub 操作接口。
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
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
class GitHubConnectorConfig(ConnectorConfig):
    """GitHub 连接器配置"""
    # GitHub Personal Access Token
    token: str = ""
    
    # 默认仓库（可选）
    default_owner: str = ""
    default_repo: str = ""
    
    # API 配置
    api_base_url: str = "https://api.github.com"  # 支持 GitHub Enterprise


# 后端配置
GITHUB_BACKEND_CONFIG = {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-github"],
    "check_command": "npx",
    "check_args": ["--version"],
}


class GitHubConnector(MCPConnector):
    """
    GitHub 连接器
    
    代理到 GitHub MCP Server，提供 GitHub 操作接口。
    
    功能：
    - 仓库管理：创建、Fork、搜索仓库
    - Issue 管理：创建、更新、评论
    - PR 管理：创建、合并、审查
    - 文件操作：读取、创建、更新文件
    - 分支管理：创建、删除分支
    
    使用示例：
    ```python
    import os
    
    # WARNING: 生产环境请使用环境变量，不要硬编码凭证
    config = GitHubConnectorConfig(
        name="github",
        token=os.environ.get("GITHUB_TOKEN"),  # 从环境变量读取
        default_owner="myorg",
        default_repo="myrepo"
    )
    
    connector = GitHubConnector(config)
    
    async with connector:
        # 搜索仓库
        repos = await connector.search_repositories("AI-Bridge")
        
        # 创建 Issue
        issue = await connector.create_issue(
            owner="myorg",
            repo="myrepo",
            title="Bug report",
            body="Description..."
        )
        
        # 获取文件内容
        content = await connector.get_file_contents(
            owner="myorg",
            repo="myrepo",
            path="README.md"
        )
    ```
    """
    
    def __init__(self, config: GitHubConnectorConfig):
        super().__init__(config)
        self._gh_config = config
        self._mcp: Optional[MCPProtocol] = None
    
    @property
    def mcp_protocol(self) -> Optional[MCPProtocol]:
        """MCP 协议实例"""
        return self._mcp
    
    async def _is_backend_available(self) -> bool:
        """检查后端是否可用"""
        import shutil
        
        config = GITHUB_BACKEND_CONFIG
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
        """启动 GitHub 后端"""
        if not self._gh_config.token:
            raise ConnectorError("GitHub token is required")
        
        if not await self._is_backend_available():
            raise ConnectorError(
                "GitHub MCP Server not available. "
                "Please install: npm install -g @modelcontextprotocol/server-github"
            )
        
        await self._start_backend()
    
    async def _start_backend(self) -> None:
        """启动后端并完成 MCP 协议握手"""
        import os
        
        config = GITHUB_BACKEND_CONFIG
        logger.info("Starting GitHub backend")
        
        env = dict(os.environ)
        
        # 设置 GitHub Token
        env["GITHUB_PERSONAL_ACCESS_TOKEN"] = self._gh_config.token
        
        if self._gh_config.api_base_url != "https://api.github.com":
            env["GITHUB_API_URL"] = self._gh_config.api_base_url
        
        # 创建 MCP 协议实例
        self._mcp = MCPProtocol(timeout=self._config.timeout)
        
        await self._mcp.start(
            command=config["command"],
            args=config["args"],
            env=env,
        )
        
        try:
            server_info = await self._mcp.initialize()
            logger.info(f"GitHub MCP Server initialized: {server_info.name} v{server_info.version}")
            
            mcp_tools = await self._mcp.list_tools()
            self._tools = [
                ToolInfo(
                    name=t.name,
                    description=t.description,
                    input_schema=t.input_schema,
                )
                for t in mcp_tools
            ]
            logger.info(f"Got {len(self._tools)} tools from GitHub MCP Server")
            
        except Exception as e:
            logger.warning(f"MCP handshake failed, using standard tools: {e}")
            self._tools = self._get_standard_tools()
    
    async def _do_stop(self) -> None:
        """停止 GitHub 后端"""
        if self._mcp:
            await self._mcp.shutdown()
            self._mcp = None
    
    async def _do_call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """通过 MCP 协议调用工具"""
        if not self._mcp:
            raise ConnectorError("MCP protocol not initialized")
        
        return await self._mcp.call_tool(name, params)
    
    def _get_standard_tools(self) -> List[ToolInfo]:
        """获取标准 GitHub 工具列表"""
        return [
            # 仓库操作
            ToolInfo(
                name="search_repositories",
                description="Search GitHub repositories",
                input_schema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"}
                    },
                    "required": ["query"]
                }
            ),
            ToolInfo(
                name="get_file_contents",
                description="Get contents of a file from a repository",
                input_schema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "path": {"type": "string"},
                        "branch": {"type": "string"}
                    },
                    "required": ["owner", "repo", "path"]
                }
            ),
            ToolInfo(
                name="create_or_update_file",
                description="Create or update a file in a repository",
                input_schema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                        "message": {"type": "string"},
                        "branch": {"type": "string"},
                        "sha": {"type": "string"}
                    },
                    "required": ["owner", "repo", "path", "content", "message"]
                }
            ),
            
            # Issue 操作
            ToolInfo(
                name="create_issue",
                description="Create a new issue",
                input_schema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "labels": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["owner", "repo", "title"]
                }
            ),
            ToolInfo(
                name="list_issues",
                description="List issues in a repository",
                input_schema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"]}
                    },
                    "required": ["owner", "repo"]
                }
            ),
            
            # PR 操作
            ToolInfo(
                name="create_pull_request",
                description="Create a pull request",
                input_schema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "title": {"type": "string"},
                        "body": {"type": "string"},
                        "head": {"type": "string"},
                        "base": {"type": "string"}
                    },
                    "required": ["owner", "repo", "title", "head", "base"]
                }
            ),
            ToolInfo(
                name="list_pull_requests",
                description="List pull requests in a repository",
                input_schema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "state": {"type": "string", "enum": ["open", "closed", "all"]}
                    },
                    "required": ["owner", "repo"]
                }
            ),
            
            # 分支操作
            ToolInfo(
                name="create_branch",
                description="Create a new branch",
                input_schema={
                    "type": "object",
                    "properties": {
                        "owner": {"type": "string"},
                        "repo": {"type": "string"},
                        "branch": {"type": "string"},
                        "from_branch": {"type": "string"}
                    },
                    "required": ["owner", "repo", "branch"]
                }
            ),
        ]
    
    def _with_defaults(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """添加默认的 owner 和 repo"""
        result = dict(params)
        if "owner" not in result and self._gh_config.default_owner:
            result["owner"] = self._gh_config.default_owner
        if "repo" not in result and self._gh_config.default_repo:
            result["repo"] = self._gh_config.default_repo
        return result
    
    # 便捷方法 - 仓库
    async def search_repositories(self, query: str) -> Any:
        """搜索仓库"""
        return await self.call_tool("search_repositories", {"query": query})
    
    async def get_file_contents(
        self,
        path: str,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        branch: Optional[str] = None
    ) -> Any:
        """获取文件内容"""
        params = self._with_defaults({"path": path})
        if owner:
            params["owner"] = owner
        if repo:
            params["repo"] = repo
        if branch:
            params["branch"] = branch
        return await self.call_tool("get_file_contents", params)
    
    async def create_or_update_file(
        self,
        path: str,
        content: str,
        message: str,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        branch: Optional[str] = None,
        sha: Optional[str] = None
    ) -> Any:
        """创建或更新文件"""
        params = self._with_defaults({
            "path": path,
            "content": content,
            "message": message
        })
        if owner:
            params["owner"] = owner
        if repo:
            params["repo"] = repo
        if branch:
            params["branch"] = branch
        if sha:
            params["sha"] = sha
        return await self.call_tool("create_or_update_file", params)
    
    # 便捷方法 - Issue
    async def create_issue(
        self,
        title: str,
        body: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        labels: Optional[List[str]] = None
    ) -> Any:
        """创建 Issue"""
        params = self._with_defaults({"title": title})
        if owner:
            params["owner"] = owner
        if repo:
            params["repo"] = repo
        if body:
            params["body"] = body
        if labels:
            params["labels"] = labels
        return await self.call_tool("create_issue", params)
    
    async def list_issues(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        state: str = "open"
    ) -> Any:
        """列出 Issue"""
        params = self._with_defaults({"state": state})
        if owner:
            params["owner"] = owner
        if repo:
            params["repo"] = repo
        return await self.call_tool("list_issues", params)
    
    # 便捷方法 - PR
    async def create_pull_request(
        self,
        title: str,
        head: str,
        base: str,
        body: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> Any:
        """创建 Pull Request"""
        params = self._with_defaults({
            "title": title,
            "head": head,
            "base": base
        })
        if owner:
            params["owner"] = owner
        if repo:
            params["repo"] = repo
        if body:
            params["body"] = body
        return await self.call_tool("create_pull_request", params)
    
    async def list_pull_requests(
        self,
        owner: Optional[str] = None,
        repo: Optional[str] = None,
        state: str = "open"
    ) -> Any:
        """列出 Pull Request"""
        params = self._with_defaults({"state": state})
        if owner:
            params["owner"] = owner
        if repo:
            params["repo"] = repo
        return await self.call_tool("list_pull_requests", params)
    
    # 便捷方法 - 分支
    async def create_branch(
        self,
        branch: str,
        from_branch: Optional[str] = None,
        owner: Optional[str] = None,
        repo: Optional[str] = None
    ) -> Any:
        """创建分支"""
        params = self._with_defaults({"branch": branch})
        if owner:
            params["owner"] = owner
        if repo:
            params["repo"] = repo
        if from_branch:
            params["from_branch"] = from_branch
        return await self.call_tool("create_branch", params)
