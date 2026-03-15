"""
Phase 3 新连接器单元测试

测试 DatabaseConnector, FilesystemConnector, GitHubConnector
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from aibridge.connectors.mcp import (
    DatabaseConnector,
    DatabaseConnectorConfig,
    DatabaseBackend,
    FilesystemConnector,
    FilesystemConnectorConfig,
    GitHubConnector,
    GitHubConnectorConfig,
)
from aibridge.connectors.base import ConnectorStatus, ConnectorError


class TestDatabaseConnectorConfig:
    """DatabaseConnectorConfig 测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = DatabaseConnectorConfig(name="db")
        
        assert config.backend == DatabaseBackend.AUTO
        assert config.pg_host == "localhost"
        assert config.pg_port == 5432
        assert config.read_only is False
    
    def test_postgresql_config(self):
        """测试 PostgreSQL 配置"""
        config = DatabaseConnectorConfig(
            name="postgres",
            backend=DatabaseBackend.POSTGRESQL,
            pg_host="db.example.com",
            pg_port=5433,
            pg_database="mydb",
            pg_user="admin",
            pg_password="secret",
        )
        
        assert config.backend == DatabaseBackend.POSTGRESQL
        assert config.pg_host == "db.example.com"
        assert config.pg_port == 5433
    
    def test_sqlite_config(self):
        """测试 SQLite 配置"""
        config = DatabaseConnectorConfig(
            name="sqlite",
            backend=DatabaseBackend.SQLITE,
            sqlite_path="./data.db",
        )
        
        assert config.backend == DatabaseBackend.SQLITE
        assert config.sqlite_path == "./data.db"
    
    def test_connection_string(self):
        """测试连接字符串优先"""
        config = DatabaseConnectorConfig(
            name="db",
            pg_connection_string="postgresql://user:pass@host/db"
        )
        
        assert config.pg_connection_string is not None


class TestDatabaseConnector:
    """DatabaseConnector 测试"""
    
    @pytest.fixture
    def connector(self):
        config = DatabaseConnectorConfig(
            name="test-db",
            backend=DatabaseBackend.SQLITE,
            sqlite_path=":memory:",
        )
        return DatabaseConnector(config)
    
    def test_initial_status(self, connector):
        """测试初始状态"""
        assert connector.status == ConnectorStatus.DISCONNECTED
        assert connector.active_backend is None
    
    def test_standard_tools(self, connector):
        """测试标准工具列表"""
        tools = connector._get_standard_tools()
        
        tool_names = [t.name for t in tools]
        assert "query" in tool_names
        assert "list_tables" in tool_names
        assert "describe_table" in tool_names


class TestDatabaseBackend:
    """DatabaseBackend 枚举测试"""
    
    def test_backend_values(self):
        """测试后端枚举值"""
        assert DatabaseBackend.POSTGRESQL.value == "postgresql"
        assert DatabaseBackend.SQLITE.value == "sqlite"
        assert DatabaseBackend.AUTO.value == "auto"


class TestFilesystemConnectorConfig:
    """FilesystemConnectorConfig 测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = FilesystemConnectorConfig(name="fs")
        
        assert config.allowed_directories == ["."]
        assert config.read_only is False
        assert config.allow_delete is False
    
    def test_custom_config(self):
        """测试自定义配置"""
        config = FilesystemConnectorConfig(
            name="fs",
            allowed_directories=["./data", "./output"],
            read_only=True,
            allow_delete=False,
        )
        
        assert len(config.allowed_directories) == 2
        assert config.read_only is True


class TestFilesystemConnector:
    """FilesystemConnector 测试"""
    
    @pytest.fixture
    def connector(self):
        config = FilesystemConnectorConfig(
            name="test-fs",
            allowed_directories=["./test_data"],
        )
        return FilesystemConnector(config)
    
    def test_initial_status(self, connector):
        """测试初始状态"""
        assert connector.status == ConnectorStatus.DISCONNECTED
    
    def test_standard_tools(self, connector):
        """测试标准工具列表"""
        tools = connector._get_standard_tools()
        
        tool_names = [t.name for t in tools]
        assert "read_file" in tool_names
        assert "write_file" in tool_names
        assert "list_directory" in tool_names
        assert "search_files" in tool_names
    
    @pytest.mark.asyncio
    async def test_read_only_blocks_write(self, connector):
        """测试只读模式阻止写操作"""
        connector._fs_config.read_only = True
        
        with pytest.raises(ConnectorError, match="read-only"):
            await connector.write_file("test.txt", "content")
    
    @pytest.mark.asyncio
    async def test_delete_protection(self, connector):
        """测试删除保护"""
        connector._mcp = MagicMock()
        connector._fs_config.allow_delete = False
        
        with pytest.raises(ConnectorError, match="not allowed"):
            await connector._do_call_tool("delete", {"path": "test.txt"})


class TestGitHubConnectorConfig:
    """GitHubConnectorConfig 测试"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = GitHubConnectorConfig(name="gh")
        
        assert config.token == ""
        assert config.api_base_url == "https://api.github.com"
    
    def test_with_token(self):
        """测试带 Token 配置"""
        config = GitHubConnectorConfig(
            name="gh",
            token="ghp_xxxxxxxxxxxx",
            default_owner="myorg",
            default_repo="myrepo",
        )
        
        assert config.token.startswith("ghp_")
        assert config.default_owner == "myorg"
    
    def test_enterprise_config(self):
        """测试 GitHub Enterprise 配置"""
        config = GitHubConnectorConfig(
            name="ghe",
            token="ghp_xxxx",
            api_base_url="https://github.mycompany.com/api/v3"
        )
        
        assert "mycompany" in config.api_base_url


class TestGitHubConnector:
    """GitHubConnector 测试"""
    
    @pytest.fixture
    def connector(self):
        config = GitHubConnectorConfig(
            name="test-gh",
            token="ghp_test_token",
            default_owner="testorg",
            default_repo="testrepo",
        )
        return GitHubConnector(config)
    
    def test_initial_status(self, connector):
        """测试初始状态"""
        assert connector.status == ConnectorStatus.DISCONNECTED
    
    def test_standard_tools(self, connector):
        """测试标准工具列表"""
        tools = connector._get_standard_tools()
        
        tool_names = [t.name for t in tools]
        assert "search_repositories" in tool_names
        assert "create_issue" in tool_names
        assert "create_pull_request" in tool_names
        assert "get_file_contents" in tool_names
    
    def test_with_defaults(self, connector):
        """测试默认值填充"""
        params = connector._with_defaults({"title": "Test"})
        
        assert params["owner"] == "testorg"
        assert params["repo"] == "testrepo"
        assert params["title"] == "Test"
    
    def test_with_defaults_no_override(self, connector):
        """测试不覆盖已有值"""
        params = connector._with_defaults({
            "owner": "other",
            "repo": "other-repo",
        })
        
        assert params["owner"] == "other"
        assert params["repo"] == "other-repo"
    
    @pytest.mark.asyncio
    async def test_start_without_token_fails(self):
        """测试无 Token 时启动失败"""
        config = GitHubConnectorConfig(name="gh", token="")
        connector = GitHubConnector(config)
        
        with pytest.raises(ConnectorError, match="token is required"):
            await connector._do_start()
