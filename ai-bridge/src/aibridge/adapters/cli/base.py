"""CLI Adapter Base Class for AI-Bridge

Provides a unified interface to wrap CLI-Anything generated tools
and expose them as AI-Bridge adapters with MCP protocol support.
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
from abc import abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from aibridge.adapters.base import BaseAdapter
from aibridge.core.protocol import Action, Response

logger = logging.getLogger(__name__)

# Security constants
DANGEROUS_CHARS = re.compile(r'[;|&$`\\<>]')
PATH_TRAVERSAL_PATTERN = re.compile(r'\.{2,}[/\\]')
VALID_FILENAME_PATTERN = re.compile(r'^[^\\/:\*?"<>|]*$')


@dataclass
class CLIAdapterConfig:
    """Configuration for CLI adapters."""
    cli_path: Optional[str] = None
    timeout: int = 60
    working_dir: Optional[str] = None


@dataclass
class CLICommand:
    """Represents a CLI command to execute."""
    command: str
    args: List[str] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    json_output: bool = True
    working_dir: Optional[str] = None
    timeout: int = 60

    def build(self) -> List[str]:
        """Build the full command list for subprocess."""
        cmd = [self.command, *self.args]
        
        for key, value in self.kwargs.items():
            if isinstance(value, bool):
                if value:
                    cmd.append(f"--{key}")
            else:
                cmd.extend([f"--{key}", str(value)])
        
        if self.json_output and "--json" not in cmd:
            cmd.append("--json")
        
        return cmd


@dataclass
class CLIResult:
    """Result of a CLI command execution."""
    success: bool
    returncode: int
    stdout: str
    stderr: str
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @classmethod
    def from_subprocess(cls, result: subprocess.CompletedProcess, parse_json: bool = True) -> "CLIResult":
        """Create CLIResult from subprocess result."""
        success = result.returncode == 0
        data = None
        error = None
        
        if parse_json and result.stdout:
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON output: {result.stdout[:200]}")
        
        if not success:
            error = result.stderr.strip() if result.stderr else f"Exit code: {result.returncode}"
        
        return cls(
            success=success,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            data=data,
            error=error
        )


class CLIAdapter(BaseAdapter):
    """Base adapter for CLI-Anything generated tools."""
    
    # Override these in subclasses
    cli_name: str = "cli-tool"
    cli_module: Optional[str] = None
    cli_path: Optional[str] = None
    
    # Configuration
    default_timeout: int = 60
    auto_install_cli: bool = False

    def __init__(self, config: Optional[CLIAdapterConfig] = None):
        super().__init__(config)
        self.config = config or CLIAdapterConfig()
        self._cli_executable: Optional[str] = None
        self._session_state: Dict[str, Any] = {}
        self._action_handlers: Dict[str, Callable] = {}

    async def initialize(self) -> bool:
        """Initialize the adapter by verifying CLI is available."""
        try:
            self._cli_executable = await self._find_cli()
            if not self._cli_executable:
                if self.auto_install_cli:
                    logger.info(f"CLI tool {self.cli_name} not found, attempting auto-install...")
                    await self._install_cli()
                    self._cli_executable = await self._find_cli()
                
                if not self._cli_executable:
                    logger.error(f"CLI tool {self.cli_name} not found. "
                                f"Please install it via: pip install {self.cli_module or self.cli_name}")
                    return False
            
            self._action_handlers = self._get_action_handlers()
            logger.info(f"CLI adapter initialized: {self.cli_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize CLI adapter: {e}")
            return False

    async def _find_cli(self) -> Optional[str]:
        """Find the CLI executable."""
        # 1. Check explicit path
        if self.cli_path and os.path.isfile(self.cli_path):
            return self.cli_path
        
        # 2. Check config override
        if hasattr(self.config, 'cli_path') and self.config.cli_path:
            return self.config.cli_path
        
        # 3. Check in PATH
        cli_in_path = shutil.which(self.cli_name)
        if cli_in_path:
            return cli_in_path
        
        # 4. Check if it's a Python module
        if self.cli_module:
            python_exe = shutil.which("python3") or shutil.which("python")
            if python_exe:
                test_cmd = [python_exe, "-m", self.cli_module.split('.')[0], "--help"]
                try:
                    result = subprocess.run(test_cmd, capture_output=True, timeout=5, text=True)
                    if result.returncode == 0:
                        return f"{python_exe} -m {self.cli_module}"
                except Exception:
                    pass
        
        return None

    async def _install_cli(self) -> bool:
        """Attempt to auto-install the CLI tool."""
        if not self.cli_module:
            return False
        
        try:
            cmd = ["pip", "install", self.cli_module.replace('.', '-').lower()]
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode == 0:
                logger.info(f"Successfully installed {self.cli_module}")
                return True
            else:
                logger.error(f"Failed to install CLI: {stderr.decode()}")
                return False
        except Exception as e:
            logger.error(f"Error installing CLI: {e}")
            return False

    async def execute(self, action: Action) -> Response:
        """Execute an action by dispatching to the appropriate handler."""
        if not self._cli_executable:
            return Response(
                status=ResponseStatus.ERROR,
                error="CLI adapter not initialized. Call initialize() first."
            )
        
        handler = self._action_handlers.get(action.name)
        if not handler:
            handler = getattr(self, f"_handle_{action.name}", None)
        
        if not handler:
            return Response(
                status=ResponseStatus.ERROR,
                error=f"Unknown action: {action.name}. Supported: {list(self._action_handlers.keys())}"
            )
        
        try:
            return await handler(action)
        except Exception as e:
            logger.exception(f"Error executing action {action.name}")
            return Response(status=ResponseStatus.ERROR, error=f"Execution failed: {str(e)}")

    @abstractmethod
    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        """Return a mapping of action names to handler methods."""
        return {}

    async def _run_cli(
        self,
        command: str,
        args: Optional[List[str]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        json_output: bool = True,
        working_dir: Optional[str] = None,
        timeout: Optional[int] = None,
        env: Optional[Dict[str, str]] = None
    ) -> CLIResult:
        """Run a CLI command and parse the result."""
        cmd_parts = self._cli_executable.split()
        cmd_parts.append(command)
        
        if args:
            cmd_parts.extend(args)
        
        if kwargs:
            for key, value in kwargs.items():
                if isinstance(value, bool):
                    if value:
                        cmd_parts.append(f"--{key}")
                elif value is not None:
                    cmd_parts.extend([f"--{key}", str(value)])
        
        if json_output:
            cmd_parts.append("--json")
        
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        logger.debug(f"Running CLI: {' '.join(cmd_parts)}")
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=working_dir,
                env=run_env
            )
            
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout or self.default_timeout
            )
            
            result = subprocess.CompletedProcess(
                cmd_parts,
                returncode=proc.returncode,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace')
            )
            
            return CLIResult.from_subprocess(result, parse_json=json_output)
            
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            return CLIResult(
                success=False,
                returncode=-1,
                stdout="",
                stderr="",
                error=f"Command timed out after {timeout or self.default_timeout}s"
            )
        except Exception as e:
            return CLIResult(success=False, returncode=-1, stdout="", stderr="", error=str(e))

    def _cli_result_to_response(self, result: CLIResult) -> Response:
        """Convert CLIResult to AI-Bridge Response."""
        if result.success:
            return Response(
                success=True,
                data=result.data or {"output": result.stdout},
                metadata={"cli_returncode": result.returncode}
            )
        else:
            return Response(
                success=False,
                error=result.error or result.stderr or "Unknown CLI error",
                metadata={"cli_returncode": result.returncode}
            )

    # Security validation methods
    def _validate_path(self, path: str, allow_absolute: bool = True, 
                       allowed_extensions: Optional[Set[str]] = None) -> tuple:
        """Validate a file path for security issues."""
        if not path:
            return False, "Path cannot be empty"
        
        if '\x00' in path:
            return False, "Path contains null bytes"
        
        if DANGEROUS_CHARS.search(path):
            return False, f"Path contains dangerous characters: {path}"
        
        if PATH_TRAVERSAL_PATTERN.search(path):
            return False, f"Path traversal detected: {path}"
        
        if not allow_absolute and os.path.isabs(path):
            return False, f"Absolute paths not allowed: {path}"
        
        if allowed_extensions:
            ext = Path(path).suffix.lower()
            if ext not in allowed_extensions:
                return False, f"File type not allowed. Allowed: {', '.join(allowed_extensions)}"
        
        return True, ""

    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize a filename to prevent security issues."""
        if not filename:
            return ""
        
        sanitized = DANGEROUS_CHARS.sub('', filename)
        sanitized = PATH_TRAVERSAL_PATTERN.sub('', sanitized)
        sanitized = sanitized.strip('. ')
        return sanitized

    async def cleanup(self) -> None:
        """Clean up resources."""
        self._session_state.clear()
        logger.info(f"CLI adapter cleaned up: {self.cli_name}")

    def get_capabilities(self) -> List[str]:
        """Return list of supported capabilities."""
        return list(self._action_handlers.keys())

    async def health_check(self) -> bool:
        """Check if CLI tool is healthy and responsive."""
        if not self._cli_executable:
            return False
        
        try:
            result = await self._run_cli("--help", timeout=10)
            return result.success
        except Exception:
            return False
