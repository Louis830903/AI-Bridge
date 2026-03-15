"""
Auto-Discovery for CLI-Anything Adapters

Automatically discovers and registers available CLI-Anything tools
as AI-Bridge adapters with MCP Tool support.

Usage:
    from aibridge.server.adapter_discovery import AdapterDiscovery
    
    # Discover all adapters
    discovery = AdapterDiscovery()
    adapters = await discovery.discover_all()
    
    # Auto-register to MCP server
    server = create_cli_mcp_server()
    await discovery.register_to_server(server)
"""

import asyncio
import importlib
import inspect
import json
import logging
import os
import pkgutil
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Callable

from aibridge.core.protocol import Response
from aibridge.adapters.base import BaseAdapter

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredAdapter:
    """Information about a discovered adapter."""
    name: str
    class_name: str
    adapter_class: Optional[Type] = None
    cli_name: str = ""
    cli_path: Optional[str] = None
    version: Optional[str] = None
    available: bool = False
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdapterDiscovery:
    """
    Discovers and manages CLI-Anything adapters.
    
    Supports:
    - Built-in adapters (GIMP, Blender, FFmpeg, Shotcut, etc.)
    - Auto-discovery of CLI-Anything generated tools
    - Dynamic registration with MCP server
    - Configuration file based registration
    """
    
    # Known built-in adapters
    BUILTIN_ADAPTERS = {
        "gimp": {
            "module": "aibridge.adapters.cli.gimp",
            "class": "GIMPAdapter",
            "cli_name": "gimp-cli",
            "description": "Image editing via GIMP",
        },
        "blender": {
            "module": "aibridge.adapters.cli.blender",
            "class": "BlenderAdapter",
            "cli_name": "blender",
            "description": "3D modeling and rendering via Blender",
        },
        "ffmpeg": {
            "module": "aibridge.adapters.cli.ffmpeg",
            "class": "FFmpegAdapter",
            "cli_name": "ffmpeg",
            "description": "Audio/video processing via FFmpeg",
        },
        "shotcut": {
            "module": "aibridge.adapters.cli.shotcut",
            "class": "ShotcutAdapter",
            "cli_name": "melt",
            "description": "Video editing via Shotcut/MLT",
        },
        "imagemagick": {
            "module": "aibridge.adapters.cli.imagemagick",
            "class": "ImageMagickAdapter",
            "cli_name": "convert",
            "description": "Advanced image processing via ImageMagick",
        },
        "pandoc": {
            "module": "aibridge.adapters.cli.pandoc",
            "class": "PandocAdapter",
            "cli_name": "pandoc",
            "description": "Document format conversion via Pandoc",
        },
        "playwright": {
            "module": "aibridge.adapters.cli.playwright",
            "class": "PlaywrightAdapter",
            "cli_name": "playwright",
            "description": "Browser automation via Playwright",
        },
        "ytdlp": {
            "module": "aibridge.adapters.cli.ytdlp",
            "class": "YTDLPAdapter",
            "cli_name": "yt-dlp",
            "description": "Video downloading via yt-dlp",
        },
        "aider": {
            "module": "aibridge.adapters.cli.aider",
            "class": "AiderAdapter",
            "cli_name": "aider",
            "description": "AI pair programming via Aider",
        },
    }
    
    # Common CLI-Anything generated tool patterns
    CLI_ANYTHING_PATTERNS = [
        "cli-anything-*",
        "cli_*",
        "*cli",
        "*-cli",
    ]
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self._discovered: Dict[str, DiscoveredAdapter] = {}
        self._adapters_dir = Path(__file__).parent.parent / "adapters" / "cli"
    
    async def discover_all(self) -> Dict[str, DiscoveredAdapter]:
        """
        Discover all available adapters.
        
        Returns:
            Dict of adapter name -> DiscoveredAdapter
        """
        self._discovered = {}
        
        # 1. Discover built-in adapters
        await self._discover_builtin()
        
        # 2. Discover CLI-Anything generated tools
        await self._discover_cli_anything()
        
        # 3. Discover from config file
        await self._discover_from_config()
        
        # 4. Discover custom adapters in adapters/cli directory
        await self._discover_custom_adapters()
        
        logger.info(f"Discovered {len(self._discovered)} adapters: {list(self._discovered.keys())}")
        return self._discovered
    
    async def _discover_builtin(self):
        """Discover built-in adapters."""
        for name, info in self.BUILTIN_ADAPTERS.items():
            try:
                # Try to import the module
                module = importlib.import_module(info["module"])
                adapter_class = getattr(module, info["class"])
                
                # Check if CLI is available
                cli_path = shutil.which(info["cli_name"])
                
                self._discovered[name] = DiscoveredAdapter(
                    name=name,
                    class_name=info["class"],
                    adapter_class=adapter_class,
                    cli_name=info["cli_name"],
                    cli_path=cli_path,
                    version=None,
                    available=cli_path is not None,
                    error=None if cli_path else f"CLI tool '{info['cli_name']}' not found in PATH",
                    metadata={"description": info["description"], "type": "builtin"}
                )
                
                if cli_path:
                    logger.info(f"✅ Built-in adapter available: {name} ({info['cli_name']})")
                else:
                    logger.warning(f"⚠️ Built-in adapter not available: {name} ({info['cli_name']} not found)")
                    
            except Exception as e:
                logger.warning(f"⚠️ Failed to load built-in adapter {name}: {e}")
                self._discovered[name] = DiscoveredAdapter(
                    name=name,
                    class_name=info["class"],
                    adapter_class=None,
                    cli_name=info["cli_name"],
                    cli_path=None,
                    version=None,
                    available=False,
                    error=str(e),
                    metadata={"description": info.get("description"), "type": "builtin"}
                )
    
    async def _discover_cli_anything(self):
        """Discover CLI-Anything generated tools."""
        # Look for python modules matching CLI-Anything patterns
        cli_anything_modules = []
        
        try:
            import sys
            for module_name in list(sys.modules.keys()):
                for pattern in ["cli_anything", "cli-anything"]:
                    if pattern in module_name.lower():
                        cli_anything_modules.append(module_name)
            
            # Also check installed packages
            result = await asyncio.create_subprocess_exec(
                "pip", "list", "--format=json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            
            if result.returncode == 0:
                packages = json.loads(stdout)
                for pkg in packages:
                    pkg_name = pkg.get("name", "").lower()
                    if "cli-anything" in pkg_name or pkg_name.startswith("cli_"):
                        # Try to discover this package
                        await self._try_discover_package(pkg["name"])
                        
        except Exception as e:
            logger.debug(f"Error discovering CLI-Anything tools: {e}")
    
    async def _try_discover_package(self, package_name: str):
        """Try to discover a Python package as CLI-Anything tool."""
        try:
            # Try to import and find CLI entry point
            module = importlib.import_module(package_name.replace("-", "_"))
            
            # Look for CLI entry point
            cli_name = package_name.replace("cli-anything-", "").replace("cli_anything_", "")
            cli_name = f"{cli_name}-cli"
            cli_path = shutil.which(cli_name)
            
            if cli_path:
                # Generate adapter class name
                adapter_name = f"{cli_name.replace('-', '_').replace('cli', '').title()}Adapter"
                
                self._discovered[cli_name] = DiscoveredAdapter(
                    name=cli_name,
                    class_name=adapter_name,
                    adapter_class=None,  # Would need dynamic generation
                    cli_name=cli_name,
                    cli_path=cli_path,
                    version=getattr(module, "__version__", None),
                    available=True,
                    metadata={
                        "description": f"CLI-Anything generated tool: {package_name}",
                        "type": "cli-anything",
                        "package": package_name
                    }
                )
                logger.info(f"✅ Discovered CLI-Anything tool: {cli_name}")
                
        except Exception as e:
            logger.debug(f"Could not discover package {package_name}: {e}")
    
    async def _discover_from_config(self):
        """Discover adapters from configuration file."""
        if not self.config_path:
            # Try default locations
            default_paths = [
                ".aibridge/adapters.json",
                "~/.config/aibridge/adapters.json",
                "/etc/aibridge/adapters.json",
            ]
            for path in default_paths:
                expanded = Path(path).expanduser()
                if expanded.exists():
                    self.config_path = str(expanded)
                    break
        
        if not self.config_path or not Path(self.config_path).exists():
            return
        
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
            
            for adapter_config in config.get("adapters", []):
                name = adapter_config.get("name")
                if not name or name in self._discovered:
                    continue
                
                cli_name = adapter_config.get("cli_name")
                cli_path = shutil.which(cli_name) if cli_name else None
                
                self._discovered[name] = DiscoveredAdapter(
                    name=name,
                    class_name=adapter_config.get("class_name", f"{name.title()}Adapter"),
                    adapter_class=None,
                    cli_name=cli_name,
                    cli_path=cli_path,
                    version=None,
                    available=cli_path is not None,
                    metadata={
                        "description": adapter_config.get("description", ""),
                        "type": "config",
                        **adapter_config.get("metadata", {})
                    }
                )
        except Exception as e:
            logger.warning(f"Error loading adapter config: {e}")
    
    async def _discover_custom_adapters(self):
        """Discover custom adapters in the adapters/cli directory."""
        if not self._adapters_dir.exists():
            return
        
        try:
            # Import CLIAdapter dynamically to avoid circular imports
            from aibridge.adapters.cli import CLIAdapter
            
            for file_path in self._adapters_dir.glob("*.py"):
                if file_path.name.startswith("_") or file_path.name in ["base.py"]:
                    continue
                
                module_name = f"aibridge.adapters.cli.{file_path.stem}"
                
                try:
                    module = importlib.import_module(module_name)
                    
                    # Find adapter classes
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, CLIAdapter) and 
                            obj != CLIAdapter and
                            not name.startswith("_")):
                            
                            cli_name = getattr(obj, "cli_name", None)
                            if cli_name:
                                cli_path = shutil.which(cli_name)
                                adapter_name = name.lower().replace("adapter", "")
                                
                                if adapter_name not in self._discovered:
                                    self._discovered[adapter_name] = DiscoveredAdapter(
                                        name=adapter_name,
                                        class_name=name,
                                        adapter_class=obj,
                                        cli_name=cli_name,
                                        cli_path=cli_path,
                                        version=None,
                                        available=cli_path is not None,
                                        metadata={
                                            "description": obj.__doc__ or "",
                                            "type": "custom",
                                            "module": module_name
                                        }
                                    )
                                    if cli_path:
                                        logger.info(f"✅ Custom adapter discovered: {adapter_name}")
                                        
                except Exception as e:
                    logger.debug(f"Could not load custom adapter from {file_path}: {e}")
                    
        except Exception as e:
            logger.debug(f"Error discovering custom adapters: {e}")
    
    def get_available_adapters(self) -> Dict[str, DiscoveredAdapter]:
        """Get only available adapters."""
        return {name: info for name, info in self._discovered.items() if info.available}
    
    def get_adapter_class(self, name: str) -> Optional[Type]:
        """Get adapter class by name."""
        info = self._discovered.get(name)
        return info.adapter_class if info else None
    
    async def register_to_server(self, server) -> List[str]:
        """
        Register discovered adapters to MCP server.
        
        Returns:
            List of registered adapter names
        """
        registered = []
        
        from aibridge.server.mcp_tools import register_adapter_actions
        
        for name, info in self._discovered.items():
            if not info.available or not info.adapter_class:
                continue
            
            try:
                # Get action schemas from adapter
                action_schemas = self._generate_action_schemas(info.adapter_class)
                
                # Register with server
                prefix = f"{name}_"
                server.register_adapter(info.adapter_class, action_schemas, prefix=prefix)
                registered.append(name)
                logger.info(f"✅ Registered adapter to MCP server: {name}")
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to register adapter {name}: {e}")
        
        return registered
    
    def _generate_action_schemas(self, adapter_class: Type) -> Dict[str, dict]:
        """Generate MCP action schemas from adapter class."""
        schemas = {}
        
        # Get supported actions from class
        actions = getattr(adapter_class, "SUPPORTED_ACTIONS", [])
        
        for action_name in actions:
            # Generate basic schema
            schemas[action_name] = {
                "description": f"Execute {action_name} action",
                "parameters": {
                    "input": {"type": "string", "description": "Input file or data", "required": False},
                    "output": {"type": "string", "description": "Output file or path", "required": False},
                }
            }
        
        return schemas


class DynamicAdapterGenerator:
    """
    Dynamically generates adapter classes for discovered CLI tools.
    
    This allows automatic adapter creation for CLI-Anything generated tools
    without pre-defined adapter classes.
    """
    
    @staticmethod
    def generate_adapter_class(
        cli_name: str,
        cli_module: Optional[str] = None,
        actions: Optional[List[str]] = None,
        class_name: Optional[str] = None
    ) -> Type:
        """
        Dynamically generate an adapter class for a CLI tool.
        
        Args:
            cli_name: Name of the CLI executable
            cli_module: Python module name if applicable
            actions: List of supported action names
            class_name: Custom class name (default: auto-generated)
            
        Returns:
            Generated adapter class
        """
        from aibridge.adapters.cli import CLIAdapter
        
        if not class_name:
            # Auto-generate class name from CLI name
            class_name = "".join(
                part.title() for part in cli_name.replace("-", "_").split("_")
            ).replace("Cli", "").replace("CLI", "") + "Adapter"
        
        actions = actions or ["process", "analyze", "export"]
        
        # Create handler methods
        handlers = {}
        for action in actions:
            handlers[f"_handle_{action}"] = DynamicAdapterGenerator._create_handler(action)
        
        # Create the class
        adapter_class = type(
            class_name,
            (CLIAdapter,),
            {
                "cli_name": cli_name,
                "cli_module": cli_module,
                "SUPPORTED_ACTIONS": actions,
                "_get_action_handlers": lambda self: {
                    action: getattr(self, f"_handle_{action}")
                    for action in actions
                },
                **handlers
            }
        )
        
        return adapter_class
    
    @staticmethod
    def _create_handler(action_name: str) -> Callable:
        """Create a handler method for an action."""
        async def handler(self, action):
            try:
                result = await self._run_cli(
                    action_name,
                    kwargs=action.params
                )
                return self._cli_result_to_response(result)
            except Exception as e:
                return Response(
                    success=False,
                    error=f"Failed to execute {action_name}: {e}"
                )
        
        handler.__name__ = f"_handle_{action_name}"
        return handler


async def auto_discover_and_register(server) -> List[str]:
    """
    Convenience function to auto-discover and register all adapters.
    
    Usage:
        from aibridge.server.cli_mcp_server import create_cli_mcp_server
        from aibridge.server.adapter_discovery import auto_discover_and_register
        
        server = create_cli_mcp_server()
        registered = await auto_discover_and_register(server)
        print(f"Registered adapters: {registered}")
    """
    discovery = AdapterDiscovery()
    await discovery.discover_all()
    return await discovery.register_to_server(server)
