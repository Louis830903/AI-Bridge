"""
WPS CLI Adapter for AI-Bridge

Wraps WPS Office command-line tools for cross-platform document operations.

On Linux/macOS:
  - wps: WPS Writer (文字)
  - et: WPS Spreadsheet (表格)  
  - wpp: WPS Presentation (演示)

On Windows:
  - Default install path: C:/Users/{user}/AppData/Local/Kingsoft/WPS Office/

Supported actions:
  - open: Open a document
  - print: Print a document
  - version: Get WPS version info

Usage:
    adapter = WPSCLIAdapter()
    await adapter.initialize()
    
    # Open a document
    result = await adapter.execute("open", value="document.docx")
    
    # Print a document
    result = await adapter.execute("print", value="document.docx")
"""

import os
import platform
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from aibridge.core.protocol import Action, Response
from .base import CLIAdapter

logger = logging.getLogger(__name__)


class WPSCLIAdapter(CLIAdapter):
    """AI-Bridge adapter for WPS Office CLI operations."""
    
    cli_name = "wps"
    cli_module = None
    adapter_display_name = "WPS Office CLI"
    adapter_version = "1.0.0"
    auto_install_cli = False
    default_timeout = 30
    
    # WPS executables for different platforms
    WPS_EXECUTABLES = {
        "linux": {
            "writer": "wps",
            "spreadsheet": "et",
            "presentation": "wpp",
        },
        "darwin": {  # macOS
            "writer": "/Applications/wpsoffice.app/Contents/MacOS/wps",
            "spreadsheet": "/Applications/wpsoffice.app/Contents/MacOS/et",
            "presentation": "/Applications/wpsoffice.app/Contents/MacOS/wpp",
        },
        "windows": {
            "writer": "wps.exe",
            "spreadsheet": "et.exe",
            "presentation": "wpp.exe",
        }
    }
    
    # File extension to WPS app mapping
    EXTENSION_MAP = {
        # Writer formats
        ".doc": "writer",
        ".docx": "writer",
        ".wps": "writer",
        ".wpt": "writer",
        ".rtf": "writer",
        ".txt": "writer",
        ".odt": "writer",
        # Spreadsheet formats
        ".xls": "spreadsheet",
        ".xlsx": "spreadsheet",
        ".et": "spreadsheet",
        ".ett": "spreadsheet",
        ".csv": "spreadsheet",
        ".ods": "spreadsheet",
        # Presentation formats
        ".ppt": "presentation",
        ".pptx": "presentation",
        ".dps": "presentation",
        ".dpt": "presentation",
        ".odp": "presentation",
        # Common formats (default to writer)
        ".pdf": "writer",
    }
    
    ALLOWED_EXTENSIONS = set(EXTENSION_MAP.keys())
    
    SUPPORTED_ACTIONS = [
        "open", "print", "version", "list_apps",
        "open_writer", "open_spreadsheet", "open_presentation",
    ]
    
    def __init__(self, config=None):
        super().__init__(config)
        self._platform = platform.system().lower()
        self._wps_paths: Dict[str, Optional[str]] = {}
    
    async def _find_cli(self) -> Optional[str]:
        """Find WPS CLI executables."""
        # Try to find main WPS executable
        import shutil
        
        executables = self.WPS_EXECUTABLES.get(self._platform, {})
        
        for app_type, exe_name in executables.items():
            # Check in PATH
            exe_path = shutil.which(exe_name)
            if exe_path:
                self._wps_paths[app_type] = exe_path
                continue
            
            # Windows: Check common install locations
            if self._platform == "windows":
                common_paths = self._get_windows_wps_paths()
                for base_path in common_paths:
                    full_path = Path(base_path) / exe_name
                    if full_path.exists():
                        self._wps_paths[app_type] = str(full_path)
                        break
        
        # Return writer as main executable if found
        return self._wps_paths.get("writer")
    
    def _get_windows_wps_paths(self) -> List[str]:
        """Get common WPS installation paths on Windows."""
        paths = []
        
        # User local install
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            paths.append(os.path.join(localappdata, "Kingsoft", "WPS Office", "ksolaunch"))
            paths.append(os.path.join(localappdata, "Kingsoft", "WPS Office"))
        
        # Program Files
        programfiles = os.environ.get("PROGRAMFILES", "C:\\Program Files")
        paths.append(os.path.join(programfiles, "Kingsoft", "WPS Office"))
        
        # 32-bit on 64-bit
        programfiles_x86 = os.environ.get("PROGRAMFILES(X86)", "")
        if programfiles_x86:
            paths.append(os.path.join(programfiles_x86, "Kingsoft", "WPS Office"))
        
        return paths
    
    def _get_app_executable(self, file_path: Optional[str] = None, app_type: str = "writer") -> Optional[str]:
        """Get the appropriate WPS executable for a file."""
        if file_path:
            ext = Path(file_path).suffix.lower()
            app_type = self.EXTENSION_MAP.get(ext, "writer")
        
        return self._wps_paths.get(app_type)
    
    def _get_action_handlers(self) -> Dict[str, Callable[[Action], Response]]:
        return {
            "open": self._handle_open,
            "print": self._handle_print,
            "version": self._handle_version,
            "list_apps": self._handle_list_apps,
            "open_writer": self._handle_open_writer,
            "open_spreadsheet": self._handle_open_spreadsheet,
            "open_presentation": self._handle_open_presentation,
        }
    
    async def _handle_open(self, action: Action) -> Response:
        """Open a document with WPS Office."""
        params = action.params
        file_path = params.get("value") or params.get("file") or params.get("path")
        
        if not file_path:
            return Response(success=False, error="file path is required")
        
        # Validate path
        is_valid, error = self._validate_path(file_path, allowed_extensions=self.ALLOWED_EXTENSIONS)
        if not is_valid:
            return Response(success=False, error=f"Invalid path: {error}")
        
        # Check file exists
        if not Path(file_path).exists():
            return Response(success=False, error=f"File not found: {file_path}")
        
        # Get appropriate executable
        exe = self._get_app_executable(file_path)
        if not exe:
            return Response(success=False, error="WPS Office not found")
        
        # Run command (non-blocking, just launches WPS)
        import subprocess
        try:
            subprocess.Popen([exe, file_path], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            return Response(success=True, data={"message": f"Opened {file_path} with WPS"})
        except Exception as e:
            return Response(success=False, error=f"Failed to open: {e}")
    
    async def _handle_print(self, action: Action) -> Response:
        """Print a document with WPS Office."""
        params = action.params
        file_path = params.get("value") or params.get("file") or params.get("path")
        
        if not file_path:
            return Response(success=False, error="file path is required")
        
        # Validate path
        is_valid, error = self._validate_path(file_path, allowed_extensions=self.ALLOWED_EXTENSIONS)
        if not is_valid:
            return Response(success=False, error=f"Invalid path: {error}")
        
        if not Path(file_path).exists():
            return Response(success=False, error=f"File not found: {file_path}")
        
        exe = self._get_app_executable(file_path)
        if not exe:
            return Response(success=False, error="WPS Office not found")
        
        # Print command varies by platform
        if self._platform == "linux":
            args = ["-p", file_path]  # Linux uses -p for print
        else:
            args = ["/p", file_path]  # Windows uses /p
        
        result = await self._run_cli("", args=[exe] + args[1:], json_output=False)
        
        if result.success:
            return Response(success=True, data={"message": f"Sent {file_path} to printer"})
        else:
            return Response(success=False, error=result.error or "Print failed")
    
    async def _handle_version(self, action: Action) -> Response:
        """Get WPS Office version info."""
        exe = self._wps_paths.get("writer")
        if not exe:
            return Response(success=False, error="WPS Office not found")
        
        result = await self._run_cli("", args=["--version"], json_output=False)
        
        return Response(
            success=True,
            data={
                "version": result.stdout.strip() if result.stdout else "Unknown",
                "platform": self._platform,
                "executables": self._wps_paths
            }
        )
    
    async def _handle_list_apps(self, action: Action) -> Response:
        """List available WPS applications."""
        return Response(
            success=True,
            data={
                "platform": self._platform,
                "available_apps": {k: v for k, v in self._wps_paths.items() if v},
                "supported_extensions": list(self.ALLOWED_EXTENSIONS)
            }
        )
    
    async def _handle_open_writer(self, action: Action) -> Response:
        """Open WPS Writer directly."""
        exe = self._wps_paths.get("writer")
        if not exe:
            return Response(success=False, error="WPS Writer not found")
        
        file_path = action.params.get("value") or action.params.get("file")
        
        import subprocess
        try:
            args = [exe]
            if file_path:
                args.append(file_path)
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return Response(success=True, data={"message": "WPS Writer launched"})
        except Exception as e:
            return Response(success=False, error=f"Failed to launch: {e}")
    
    async def _handle_open_spreadsheet(self, action: Action) -> Response:
        """Open WPS Spreadsheet directly."""
        exe = self._wps_paths.get("spreadsheet")
        if not exe:
            return Response(success=False, error="WPS Spreadsheet not found")
        
        file_path = action.params.get("value") or action.params.get("file")
        
        import subprocess
        try:
            args = [exe]
            if file_path:
                args.append(file_path)
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return Response(success=True, data={"message": "WPS Spreadsheet launched"})
        except Exception as e:
            return Response(success=False, error=f"Failed to launch: {e}")
    
    async def _handle_open_presentation(self, action: Action) -> Response:
        """Open WPS Presentation directly."""
        exe = self._wps_paths.get("presentation")
        if not exe:
            return Response(success=False, error="WPS Presentation not found")
        
        file_path = action.params.get("value") or action.params.get("file")
        
        import subprocess
        try:
            args = [exe]
            if file_path:
                args.append(file_path)
            subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return Response(success=True, data={"message": "WPS Presentation launched"})
        except Exception as e:
            return Response(success=False, error=f"Failed to launch: {e}")
