"""
LibreOffice CLI Adapter for AI-Bridge

Wraps LibreOffice soffice CLI for headless document conversion and operations.

LibreOffice provides powerful headless mode for batch document processing:
  - Document format conversion (Word ↔ PDF ↔ HTML ↔ images)
  - Spreadsheet operations
  - Presentation export

Commands:
  Linux/macOS: soffice, libreoffice
  Windows: soffice.exe (in LibreOffice install dir)

Usage:
    adapter = LibreOfficeAdapter()
    await adapter.initialize()
    
    # Convert Word to PDF
    result = await adapter.execute("convert", options={
        "input": "document.docx",
        "format": "pdf"
    })
    
    # Batch convert all docx to pdf
    result = await adapter.execute("convert", options={
        "input": "*.docx",
        "format": "pdf",
        "outdir": "./output"
    })
"""

import os
import platform
import logging
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from aibridge.core.protocol import Action, Response
from .base import CLIAdapter

logger = logging.getLogger(__name__)


class LibreOfficeAdapter(CLIAdapter):
    """AI-Bridge adapter for LibreOffice headless operations."""
    
    cli_name = "soffice"
    cli_module = None
    adapter_display_name = "LibreOffice CLI"
    adapter_version = "1.0.0"
    auto_install_cli = False
    default_timeout = 120  # Conversions can take time
    
    # Supported input formats
    INPUT_FORMATS = {
        # Document formats
        ".doc", ".docx", ".odt", ".rtf", ".txt", ".html", ".htm",
        ".xml", ".wps", ".wpd",
        # Spreadsheet formats
        ".xls", ".xlsx", ".ods", ".csv", ".tsv",
        # Presentation formats
        ".ppt", ".pptx", ".odp",
        # Other
        ".pdf",
    }
    
    # Output format mappings
    OUTPUT_FORMATS = {
        # Document outputs
        "pdf": "pdf",
        "docx": "docx",
        "doc": "doc",
        "odt": "odt",
        "rtf": "rtf",
        "txt": "txt",
        "html": "html",
        "xhtml": "xhtml",
        "xml": "xml",
        # Spreadsheet outputs
        "xlsx": "xlsx",
        "xls": "xls",
        "ods": "ods",
        "csv": "csv",
        # Presentation outputs
        "pptx": "pptx",
        "ppt": "ppt",
        "odp": "odp",
        # Image outputs (for presentations)
        "png": "png",
        "jpg": "jpg",
        "gif": "gif",
        "svg": "svg",
    }
    
    SUPPORTED_ACTIONS = [
        "convert", "to",
        "to_pdf", "to_docx", "to_html", "to_xlsx", "to_csv", "to_png",
        "print", "version", "list_formats",
    ]
    
    def __init__(self, config=None):
        super().__init__(config)
        self._platform = platform.system().lower()
        self._user_profile_dir: Optional[str] = None
    
    async def _find_cli(self) -> Optional[str]:
        """Find LibreOffice executable."""
        # Check common names in PATH
        for name in ["soffice", "libreoffice", "soffice.exe"]:
            exe = shutil.which(name)
            if exe:
                return exe
        
        # Platform-specific search
        if self._platform == "windows":
            return self._find_windows_libreoffice()
        elif self._platform == "darwin":
            return self._find_macos_libreoffice()
        
        return None
    
    def _find_windows_libreoffice(self) -> Optional[str]:
        """Find LibreOffice on Windows."""
        search_paths = []
        
        # Program Files locations
        for env_var in ["PROGRAMFILES", "PROGRAMFILES(X86)"]:
            pf = os.environ.get(env_var)
            if pf:
                search_paths.append(os.path.join(pf, "LibreOffice", "program"))
        
        # Check each path
        for base_path in search_paths:
            soffice = os.path.join(base_path, "soffice.exe")
            if os.path.exists(soffice):
                return soffice
        
        return None
    
    def _find_macos_libreoffice(self) -> Optional[str]:
        """Find LibreOffice on macOS."""
        app_path = "/Applications/LibreOffice.app/Contents/MacOS/soffice"
        if os.path.exists(app_path):
            return app_path
        return None
    
    def _get_user_profile_arg(self) -> List[str]:
        """Get user profile argument to avoid conflicts with running instance."""
        if not self._user_profile_dir:
            import tempfile
            self._user_profile_dir = tempfile.mkdtemp(prefix="libreoffice_aibridge_")
        return [f"-env:UserInstallation=file:///{self._user_profile_dir.replace(os.sep, '/')}"]
    
    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        return {
            "convert": self._handle_convert,
            "to": self._handle_convert,
            "to_pdf": self._handle_to_pdf,
            "to_docx": self._handle_to_docx,
            "to_html": self._handle_to_html,
            "to_xlsx": self._handle_to_xlsx,
            "to_csv": self._handle_to_csv,
            "to_png": self._handle_to_png,
            "print": self._handle_print,
            "version": self._handle_version,
            "list_formats": self._handle_list_formats,
        }
    
    async def _handle_convert(self, action: Action) -> Response:
        """Convert document to specified format.
        
        Args:
            input: Input file path or glob pattern
            format/to: Output format (pdf, docx, html, xlsx, csv, png, etc.)
            outdir: Output directory (default: same as input)
            filter: LibreOffice filter name (advanced)
        """
        params = action.params
        input_path = params.get("input") or params.get("file") or params.get("value")
        output_format = params.get("format") or params.get("to") or "pdf"
        output_dir = params.get("outdir") or params.get("output_dir")
        lo_filter = params.get("filter")
        
        if not input_path:
            return Response(success=False, error="input file is required")
        
        # Validate output format
        output_format = output_format.lower().lstrip(".")
        if output_format not in self.OUTPUT_FORMATS:
            return Response(
                success=False, 
                error=f"Unsupported format: {output_format}. Supported: {list(self.OUTPUT_FORMATS.keys())}"
            )
        
        # Build command arguments
        args = [
            "--headless",
            "--invisible",
            "--nologo",
            "--nofirststartwizard",
        ]
        
        # Add user profile to avoid conflicts
        args.extend(self._get_user_profile_arg())
        
        # Convert-to argument
        if lo_filter:
            args.append(f"--convert-to={output_format}:{lo_filter}")
        else:
            args.append(f"--convert-to={output_format}")
        
        # Output directory
        if output_dir:
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            args.append(f"--outdir={output_dir}")
        
        # Input file
        args.append(input_path)
        
        # Run conversion
        result = await self._run_cli("", args=args, json_output=False)
        
        if result.success or result.returncode == 0:
            # Determine output file path
            input_p = Path(input_path)
            if output_dir:
                output_file = Path(output_dir) / f"{input_p.stem}.{output_format}"
            else:
                output_file = input_p.parent / f"{input_p.stem}.{output_format}"
            
            return Response(
                success=True,
                data={
                    "message": f"Converted {input_path} to {output_format}",
                    "output": str(output_file),
                    "format": output_format
                }
            )
        else:
            return Response(
                success=False,
                error=result.error or result.stderr or "Conversion failed"
            )
    
    async def _handle_to_pdf(self, action: Action) -> Response:
        """Convert to PDF."""
        action.params["format"] = "pdf"
        return await self._handle_convert(action)
    
    async def _handle_to_docx(self, action: Action) -> Response:
        """Convert to DOCX."""
        action.params["format"] = "docx"
        return await self._handle_convert(action)
    
    async def _handle_to_html(self, action: Action) -> Response:
        """Convert to HTML."""
        action.params["format"] = "html"
        return await self._handle_convert(action)
    
    async def _handle_to_xlsx(self, action: Action) -> Response:
        """Convert to XLSX."""
        action.params["format"] = "xlsx"
        return await self._handle_convert(action)
    
    async def _handle_to_csv(self, action: Action) -> Response:
        """Convert to CSV."""
        action.params["format"] = "csv"
        return await self._handle_convert(action)
    
    async def _handle_to_png(self, action: Action) -> Response:
        """Convert to PNG (for presentations)."""
        action.params["format"] = "png"
        return await self._handle_convert(action)
    
    async def _handle_print(self, action: Action) -> Response:
        """Print document.
        
        Args:
            input/file: File to print
            printer: Printer name (optional, uses default)
        """
        params = action.params
        input_path = params.get("input") or params.get("file") or params.get("value")
        printer = params.get("printer")
        
        if not input_path:
            return Response(success=False, error="input file is required")
        
        if not Path(input_path).exists():
            return Response(success=False, error=f"File not found: {input_path}")
        
        args = [
            "--headless",
            "--invisible",
        ]
        args.extend(self._get_user_profile_arg())
        
        if printer:
            args.append(f"--pt={printer}")
            args.append(input_path)
        else:
            args.append("-p")
            args.append(input_path)
        
        result = await self._run_cli("", args=args, json_output=False)
        
        if result.success or result.returncode == 0:
            return Response(success=True, data={"message": f"Sent {input_path} to printer"})
        else:
            return Response(success=False, error=result.error or "Print failed")
    
    async def _handle_version(self, action: Action) -> Response:
        """Get LibreOffice version."""
        result = await self._run_cli("", args=["--version"], json_output=False)
        
        version_str = result.stdout.strip() if result.stdout else "Unknown"
        
        return Response(
            success=True,
            data={
                "version": version_str,
                "executable": self._cli_executable,
                "platform": self._platform
            }
        )
    
    async def _handle_list_formats(self, action: Action) -> Response:
        """List supported formats."""
        return Response(
            success=True,
            data={
                "input_formats": sorted(self.INPUT_FORMATS),
                "output_formats": sorted(self.OUTPUT_FORMATS.keys()),
                "common_conversions": [
                    "docx → pdf",
                    "xlsx → csv",
                    "pptx → pdf",
                    "odt → docx",
                    "html → pdf",
                    "csv → xlsx",
                ]
            }
        )
    
    async def cleanup(self) -> None:
        """Clean up temporary user profile."""
        await super().cleanup()
        
        if self._user_profile_dir and os.path.exists(self._user_profile_dir):
            try:
                import shutil
                shutil.rmtree(self._user_profile_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp profile: {e}")
