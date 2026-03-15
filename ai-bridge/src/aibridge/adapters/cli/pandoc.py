"""
Pandoc Adapter for AI-Bridge

Wraps Pandoc CLI to provide document format conversion capabilities.

Requires: Pandoc installed and in PATH

Usage:
    adapter = PandocAdapter()
    await adapter.initialize()
    
    # Convert Markdown to PDF
    result = await adapter.execute(Action(
        name="convert",
        params={"input": "doc.md", "output": "doc.pdf", "to": "pdf"}
    ))
"""

from typing import Any, Callable, Dict, List, Optional
from aibridge.core.protocol import Action, Response
from .base import CLIAdapter, CLIResult


class PandocAdapter(CLIAdapter):
    """AI-Bridge adapter for Pandoc document conversion."""
    
    cli_name = "pandoc"
    cli_module = None
    auto_install_cli = False
    default_timeout = 60
    
    ALLOWED_EXTENSIONS = {
        '.md', '.markdown', '.txt', '.rst', '.org',
        '.html', '.htm', '.pdf', '.docx', '.odt',
        '.rtf', '.tex', '.latex', '.epub', '.doc',
        '.odt', '.pptx', '.slide'
    }
    
    SUPPORTED_ACTIONS = [
        "convert", "to",
        "md_to_pdf", "md_to_docx", "md_to_html",
        "html_to_md", "docx_to_md", "pdf_to_text",
        "list_formats",
    ]
    
    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        return {
            "convert": self._handle_convert,
            "to": self._handle_convert,
            "md_to_pdf": self._handle_md_to_pdf,
            "md_to_docx": self._handle_md_to_docx,
            "md_to_html": self._handle_md_to_html,
            "html_to_md": self._handle_html_to_md,
            "docx_to_md": self._handle_docx_to_md,
            "pdf_to_text": self._handle_pdf_to_text,
            "list_formats": self._handle_list_formats,
        }
    
    async def _handle_convert(self, action: Action) -> Response:
        """Convert document format."""
        params = action.params
        input_file = params.get("input") or params.get("from")
        output_file = params.get("output") or params.get("to")
        format_from = params.get("format_from") or params.get("from_format")
        format_to = params.get("format_to") or params.get("to_format")
        
        if not input_file or not output_file:
            return Response(success=False, error="input and output are required")
        
        # Validate paths
        for path, name in [(input_file, "input"), (output_file, "output")]:
            is_valid, error = self._validate_path(path, allowed_extensions=self.ALLOWED_EXTENSIONS)
            if not is_valid:
                return Response(success=False, error=f"Invalid {name}: {error}")
        
        cmd_args = [input_file, "-o", output_file]
        
        if format_from:
            cmd_args.extend(["-f", format_from])
        if format_to:
            cmd_args.extend(["-t", format_to])
        
        # Additional options
        if params.get("standalone"):
            cmd_args.append("--standalone")
        if params.get("toc"):
            cmd_args.append("--toc")
        if params.get("number_sections"):
            cmd_args.append("--number-sections")
        
        result = await self._run_cli("", args=cmd_args)
        return self._cli_result_to_response(result)
    
    # Alias handlers
    async def _handle_md_to_pdf(self, action: Action) -> Response:
        action.params["format_to"] = "pdf"
        return await self._handle_convert(action)
    
    async def _handle_md_to_docx(self, action: Action) -> Response:
        action.params["format_to"] = "docx"
        return await self._handle_convert(action)
    
    async def _handle_md_to_html(self, action: Action) -> Response:
        action.params["format_to"] = "html"
        return await self._handle_convert(action)
    
    async def _handle_html_to_md(self, action: Action) -> Response:
        action.params["format_from"] = "html"
        action.params["format_to"] = "markdown"
        return await self._handle_convert(action)
    
    async def _handle_docx_to_md(self, action: Action) -> Response:
        action.params["format_from"] = "docx"
        action.params["format_to"] = "markdown"
        return await self._handle_convert(action)
    
    async def _handle_pdf_to_text(self, action: Action) -> Response:
        action.params["format_to"] = "plain"
        return await self._handle_convert(action)
    
    async def _handle_list_formats(self, action: Action) -> Response:
        result = await self._run_cli("--list-output-formats")
        return self._cli_result_to_response(result)
