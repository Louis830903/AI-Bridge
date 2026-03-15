"""Prettier Adapter for AI-Bridge

Provides code formatting capabilities through Prettier CLI.
Prettier is an opinionated code formatter supporting many languages.

Installation: npm install -g prettier

Supported languages:
- JavaScript, TypeScript, JSX, TSX
- JSON, YAML, Markdown
- HTML, CSS, SCSS, Less
- GraphQL, Vue, Angular

Usage example:
```python
from aibridge.adapters.cli import PrettierAdapter
from aibridge.core.protocol import Action

adapter = PrettierAdapter()
await adapter.initialize()

# Format a file
result = await adapter.execute(Action(
    name="format",
    params={"input": "app.js"}
))

# Format and write back
result = await adapter.execute(Action(
    name="write",
    params={"input": "src/**/*.ts"}
))

# Check if files are formatted
result = await adapter.execute(Action(
    name="check",
    params={"input": "src/"}
))
```
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List

from aibridge.core.protocol import Action, Response
from .base import CLIAdapter, CLIResult

logger = logging.getLogger(__name__)


class PrettierAdapter(CLIAdapter):
    """AI-Bridge adapter for Prettier code formatting."""
    
    cli_name = "prettier"
    cli_module = "prettier"
    auto_install_cli = True  # 可以通过 npm 自动安装
    
    SUPPORTED_ACTIONS = [
        "format", "write", "check", "list_different",
        "config", "plugins"
    ]

    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        """Map action names to handler methods."""
        return {
            "format": self._handle_format,
            "write": self._handle_write,
            "check": self._handle_check,
            "list_different": self._handle_list_different,
            "config": self._handle_config,
            "plugins": self._handle_plugins,
        }

    async def _handle_format(self, action: Action) -> Response:
        """Format code and return formatted content."""
        params = action.params
        input_path = params.get("input")
        content = params.get("content")  # 也可以格式化字符串内容
        
        if not input_path and not content:
            return Response(success=False, error="input or content is required")
        
        args = []
        
        # 配置选项
        if params.get("parser"):
            args.extend(["--parser", params["parser"]])
        if params.get("tab_width"):
            args.extend(["--tab-width", str(params["tab_width"])])
        if params.get("use_tabs"):
            args.append("--use-tabs")
        if params.get("single_quote"):
            args.append("--single-quote")
        if params.get("trailing_comma"):
            args.extend(["--trailing-comma", params["trailing_comma"]])
        if params.get("bracket_spacing") is False:
            args.append("--no-bracket-spacing")
        if params.get("config"):
            args.extend(["--config", params["config"]])
        
        if content:
            # 从 stdin 读取
            args.append("--stdin-filepath")
            args.append(params.get("filepath", "file.js"))
            result = await self._run_prettier_stdin(args, content)
        else:
            args.append(input_path)
            result = await self._run_prettier(args)
        
        return self._cli_result_to_response(result)

    async def _handle_write(self, action: Action) -> Response:
        """Format and write back to file."""
        params = action.params
        input_path = params.get("input")
        
        if not input_path:
            return Response(success=False, error="input is required")
        
        args = ["--write"]
        
        # 可选：忽略未知文件
        if params.get("ignore_unknown"):
            args.append("--ignore-unknown")
        
        # Glob 模式
        if isinstance(input_path, list):
            args.extend(input_path)
        else:
            args.append(input_path)
        
        result = await self._run_prettier(args)
        return self._cli_result_to_response(result)

    async def _handle_check(self, action: Action) -> Response:
        """Check if files are formatted."""
        params = action.params
        input_path = params.get("input")
        
        if not input_path:
            return Response(success=False, error="input is required")
        
        args = ["--check"]
        
        if isinstance(input_path, list):
            args.extend(input_path)
        else:
            args.append(input_path)
        
        result = await self._run_prettier(args)
        
        # check 命令失败表示有文件需要格式化
        if not result.success:
            return Response(
                success=True,
                data={
                    "formatted": False,
                    "message": "Some files need formatting",
                    "details": result.stdout
                }
            )
        return Response(
            success=True,
            data={
                "formatted": True,
                "message": "All files are properly formatted"
            }
        )

    async def _handle_list_different(self, action: Action) -> Response:
        """List files that differ from Prettier formatting."""
        params = action.params
        input_path = params.get("input")
        
        if not input_path:
            return Response(success=False, error="input is required")
        
        args = ["--list-different"]
        
        if isinstance(input_path, list):
            args.extend(input_path)
        else:
            args.append(input_path)
        
        result = await self._run_prettier(args)
        
        # 解析输出文件列表
        files = [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        
        return Response(
            success=True,
            data={
                "files": files,
                "count": len(files)
            }
        )

    async def _handle_config(self, action: Action) -> Response:
        """Find and show Prettier config for a file."""
        params = action.params
        file_path = params.get("file")
        
        if not file_path:
            return Response(success=False, error="file is required")
        
        args = ["--find-config-path", file_path]
        result = await self._run_prettier(args)
        
        config_path = result.stdout.strip() if result.success else None
        
        return Response(
            success=True,
            data={
                "config_path": config_path,
                "found": bool(config_path)
            }
        )

    async def _handle_plugins(self, action: Action) -> Response:
        """List available Prettier plugins."""
        # Prettier 本身没有列出插件的命令，但可以尝试获取支持的解析器
        args = ["--help"]
        result = await self._run_prettier(args)
        
        # 从帮助信息中提取支持的解析器
        parsers = []
        in_parser_section = False
        for line in result.stdout.split('\n'):
            if '--parser' in line:
                in_parser_section = True
                continue
            if in_parser_section:
                if line.strip().startswith('--'):
                    break
                parsers.append(line.strip())
        
        return Response(
            success=True,
            data={
                "parsers": parsers,
                "help": result.stdout
            }
        )

    async def _run_prettier(self, args: List[str]) -> CLIResult:
        """Run Prettier with arguments."""
        cmd = ["prettier"] + args
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            
            return CLIResult(
                success=proc.returncode == 0,
                returncode=proc.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                data=None,
                error=None if proc.returncode == 0 else stderr.decode('utf-8', errors='replace')
            )
        except Exception as e:
            return CLIResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="",
                error=str(e)
            )

    async def _run_prettier_stdin(self, args: List[str], content: str) -> CLIResult:
        """Run Prettier with stdin input."""
        cmd = ["prettier"] + args
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=content.encode('utf-8')),
                timeout=60
            )
            
            return CLIResult(
                success=proc.returncode == 0,
                returncode=proc.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                data={"formatted": stdout.decode('utf-8', errors='replace')},
                error=None if proc.returncode == 0 else stderr.decode('utf-8', errors='replace')
            )
        except Exception as e:
            return CLIResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="",
                error=str(e)
            )
