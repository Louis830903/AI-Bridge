"""
Aider Adapter for AI-Bridge

Wraps Aider CLI to provide AI-assisted coding capabilities
to AI agents through the AI-Bridge protocol.

Aider is an AI pair programming tool that integrates with git
and allows AI to edit code in your local repository.

Requires:
    Aider installed: pip install aider-chat

Usage:
    adapter = AiderAdapter()
    await adapter.initialize()
    
    # Start coding session
    result = await adapter.execute(Action(
        name="chat",
        params={"message": "Add a function to calculate fibonacci"}
    ))
    
    # Edit specific files
    result = await adapter.execute(Action(
        name="edit",
        params={
            "files": ["main.py"],
            "prompt": "Add error handling to the main function"
        }
    ))
"""

from typing import Any, Callable, Dict, List, Optional

from aibridge.core.protocol import Response
from .base import CLIAdapter, CLIResult


class AiderAdapter(CLIAdapter):
    """
    AI-Bridge adapter for Aider AI pair programming.
    
    Provides:
    - Chat with AI about code
    - Edit files with AI assistance
    - Git integration (commit, diff)
    - Multi-file editing
    - Code review and suggestions
    """
    
    # CLI configuration
    cli_name = "aider"
    cli_module = "aider-chat"
    auto_install_cli = True
    default_timeout = 300  # AI operations can take time
    
    # Supported action types
    SUPPORTED_ACTIONS = [
        # Chat
        "chat", "ask", "question",
        # File operations
        "edit", "add", "drop", "read",
        # Git operations
        "commit", "diff", "git_status",
        # Code operations
        "lint", "test", "run",
        # Session management
        "reset", "clear",
    ]
    
    def _get_action_handlers(self) -> Dict[str, Callable]:
        """Map action names to handler methods."""
        return {
            # Chat
            "chat": self._handle_chat,
            "ask": self._handle_chat,
            "question": self._handle_chat,
            # File operations
            "edit": self._handle_edit,
            "add": self._handle_add,
            "drop": self._handle_drop,
            "read": self._handle_read,
            # Git operations
            "commit": self._handle_commit,
            "diff": self._handle_diff,
            "git_status": self._handle_git_status,
            # Code operations
            "lint": self._handle_lint,
            "test": self._handle_test,
            "run": self._handle_run,
            # Session
            "reset": self._handle_reset,
            "clear": self._handle_clear,
        }
    
    # Chat Operations
    async def _handle_chat(self, action) -> Response:
        """Chat with AI about code."""
        params = action.params
        message = params.get("message") or params.get("prompt") or params.get("question")
        
        if not message:
            return Response(success=False, error="message is required")
        
        # Sanitize message
        message = message.replace('"', '\\"')
        
        result = await self._run_cli(
            "",
            args=["--message", message],
            timeout=params.get("timeout", 300)
        )
        return self._cli_result_to_response(result)
    
    # File Operations
    async def _handle_edit(self, action) -> Response:
        """Edit files with AI assistance."""
        params = action.params
        files = params.get("files") or params.get("file")
        prompt = params.get("prompt") or params.get("message")
        
        if not files:
            return Response(success=False, error="files are required")
        if not prompt:
            return Response(success=False, error="prompt is required")
        
        # Validate file paths
        if isinstance(files, str):
            files = [files]
        
        for file_path in files:
            is_valid, error = self._validate_path(file_path)
            if not is_valid:
                return Response(success=False, error=f"Invalid file: {error}")
        
        # Sanitize prompt
        prompt = prompt.replace('"', '\\"')
        
        # Build command
        args = list(files) + ["--message", prompt]
        result = await self._run_cli("", args=args, timeout=params.get("timeout", 300))
        return self._cli_result_to_response(result)
    
    async def _handle_add(self, action) -> Response:
        """Add files to the chat."""
        params = action.params
        files = params.get("files") or params.get("file")
        
        if not files:
            return Response(success=False, error="files are required")
        
        if isinstance(files, str):
            files = [files]
        
        # Validate files
        for file_path in files:
            is_valid, error = self._validate_path(file_path)
            if not is_valid:
                return Response(success=False, error=f"Invalid file: {error}")
        
        result = await self._run_cli("/add", args=files)
        return self._cli_result_to_response(result)
    
    async def _handle_drop(self, action) -> Response:
        """Drop files from the chat."""
        params = action.params
        files = params.get("files") or params.get("file")
        
        if not files:
            # Drop all if no files specified
            result = await self._run_cli("/drop")
        else:
            if isinstance(files, str):
                files = [files]
            result = await self._run_cli("/drop", args=files)
        return self._cli_result_to_response(result)
    
    async def _handle_read(self, action) -> Response:
        """Read file content."""
        params = action.params
        file_path = params.get("file") or params.get("path")
        
        if not file_path:
            return Response(success=False, error="file path is required")
        
        is_valid, error = self._validate_path(file_path)
        if not is_valid:
            return Response(success=False, error=f"Invalid file: {error}")
        
        result = await self._run_cli("/read", args=[file_path])
        return self._cli_result_to_response(result)
    
    # Git Operations
    async def _handle_commit(self, action) -> Response:
        """Commit changes."""
        params = action.params
        message = params.get("message") or params.get("commit_message")
        
        args = []
        if message:
            args = ["--message", message.replace('"', '\\"')]
        
        result = await self._run_cli("/commit", args=args)
        return self._cli_result_to_response(result)
    
    async def _handle_diff(self, action) -> Response:
        """Show git diff."""
        result = await self._run_cli("/diff")
        return self._cli_result_to_response(result)
    
    async def _handle_git_status(self, action) -> Response:
        """Show git status."""
        result = await self._run_cli("/git")
        return self._cli_result_to_response(result)
    
    # Code Operations
    async def _handle_lint(self, action) -> Response:
        """Run linter on files."""
        params = action.params
        files = params.get("files")
        
        args = []
        if files:
            if isinstance(files, str):
                files = [files]
            args = files
        
        result = await self._run_cli("/lint", args=args)
        return self._cli_result_to_response(result)
    
    async def _handle_test(self, action) -> Response:
        """Run tests."""
        params = action.params
        test_command = params.get("command") or params.get("test_command")
        
        args = []
        if test_command:
            args = [test_command]
        
        result = await self._run_cli("/test", args=args)
        return self._cli_result_to_response(result)
    
    async def _handle_run(self, action) -> Response:
        """Run a shell command."""
        params = action.params
        command = params.get("command")
        
        if not command:
            return Response(success=False, error="command is required")
        
        # Security: validate command
        dangerous_chars = [';', '|', '&', '$', '`', '>', '<']
        for char in dangerous_chars:
            if char in command:
                return Response(
                    success=False,
                    error=f"Command contains dangerous character: {char}"
                )
        
        result = await self._run_cli("/run", args=[command])
        return self._cli_result_to_response(result)
    
    # Session Management
    async def _handle_reset(self, action) -> Response:
        """Reset the chat."""
        result = await self._run_cli("/reset")
        return self._cli_result_to_response(result)
    
    async def _handle_clear(self, action) -> Response:
        """Clear the chat history."""
        result = await self._run_cli("/clear")
        return self._cli_result_to_response(result)
