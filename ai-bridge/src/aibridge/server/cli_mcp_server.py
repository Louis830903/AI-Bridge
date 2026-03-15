"""
Pre-configured MCP Server for CLI-Anything Adapters

Automatically registers all available CLI adapters as MCP Tools.

Usage:
    # Start the server
    python -m aibridge.server.cli_mcp_server
    
    # Or programmatically
    from aibridge.server.cli_mcp_server import create_cli_mcp_server
    server = create_cli_mcp_server()
    await server.run_stdio()
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type

from .mcp_server import AIBridgeMCPServer
from .mcp_tools import mcp_tool, MCPToolRegistry
from .adapter_discovery import AdapterDiscovery, auto_discover_and_register

logger = logging.getLogger(__name__)


# Define action schemas for built-in CLI adapters
# These provide rich metadata for MCP Tool descriptions

GIMP_ACTIONS = {
    "open_image": {
        "description": "Open an image file in GIMP",
        "parameters": {
            "file_path": {"type": "string", "description": "Path to the image file to open"}
        }
    },
    "apply_filter": {
        "description": "Apply a filter effect to the current image",
        "parameters": {
            "filter": {"type": "string", "description": "Filter name (blur, brightness, contrast, sharpen, edge_detect)", "enum": ["blur", "brightness", "contrast", "sharpen", "edge_detect"]},
            "radius": {"type": "number", "description": "Blur radius (for blur filter)", "required": False},
            "factor": {"type": "number", "description": "Adjustment factor (for brightness/contrast)", "required": False}
        }
    },
    "export_image": {
        "description": "Export the current image to a file",
        "parameters": {
            "output_path": {"type": "string", "description": "Path to save the exported image"},
            "format": {"type": "string", "description": "Export format (png, jpg, gif, bmp)", "enum": ["png", "jpg", "jpeg", "gif", "bmp", "tiff"], "required": False},
            "quality": {"type": "number", "description": "Export quality 0-100 (for JPG)", "required": False}
        }
    },
}

BLENDER_ACTIONS = {
    "scene_new": {
        "description": "Create a new Blender scene",
        "parameters": {
            "name": {"type": "string", "description": "Scene name", "required": False},
        }
    },
    "object_add": {
        "description": "Add a 3D object to the scene",
        "parameters": {
            "type": {"type": "string", "description": "Object type", "enum": ["cube", "sphere", "cylinder", "cone", "torus", "plane"]},
            "name": {"type": "string", "description": "Object name", "required": False},
            "location": {"type": "array", "description": "Position [x, y, z]", "required": False},
        }
    },
    "render": {
        "description": "Render the scene to an image",
        "parameters": {
            "output_path": {"type": "string", "description": "Output file path", "required": False},
            "engine": {"type": "string", "description": "Render engine", "enum": ["cycles", "eevee"], "required": False},
            "resolution": {"type": "array", "description": "[width, height]", "required": False},
        }
    },
}

FFMPEG_ACTIONS = {
    "convert": {
        "description": "Convert video/audio format",
        "parameters": {
            "input": {"type": "string", "description": "Input file path"},
            "output": {"type": "string", "description": "Output file path"},
            "codec": {"type": "string", "description": "Video codec", "required": False},
        }
    },
    "extract_audio": {
        "description": "Extract audio from video",
        "parameters": {
            "input": {"type": "string", "description": "Input video file"},
            "output": {"type": "string", "description": "Output audio file", "required": False},
            "format": {"type": "string", "description": "Audio format (mp3, aac, wav, flac)", "required": False}
        }
    },
    "trim": {
        "description": "Trim/cut video segment",
        "parameters": {
            "input": {"type": "string", "description": "Input file"},
            "start": {"type": "string", "description": "Start time (e.g., 00:01:30 or seconds)"},
            "duration": {"type": "number", "description": "Duration in seconds", "required": False},
        }
    },
}

SHOTCUT_ACTIONS = {
    "project_new": {
        "description": "Create a new video editing project",
        "parameters": {
            "name": {"type": "string", "description": "Project name", "required": False},
            "profile": {"type": "string", "description": "Video profile (e.g., hd1080p30)", "required": False}
        }
    },
    "timeline_add_clip": {
        "description": "Add a video/audio clip to the timeline",
        "parameters": {
            "file_path": {"type": "string", "description": "Media file path"},
            "track": {"type": "number", "description": "Track number", "required": False},
        }
    },
    "export": {
        "description": "Export the project to a video file",
        "parameters": {
            "output_path": {"type": "string", "description": "Output file path"},
            "format": {"type": "string", "description": "Export format", "required": False},
        }
    },
}


def _register_builtin_adapters(
    server: AIBridgeMCPServer,
    include_gimp: bool = True,
    include_blender: bool = True,
    include_ffmpeg: bool = True,
    include_shotcut: bool = True
) -> list:
    """Register built-in adapters to the server."""
    adapters_registered = []
    
    if include_gimp:
        try:
            from aibridge.adapters.cli.gimp import GIMPAdapter
            server.register_adapter(GIMPAdapter, GIMP_ACTIONS, prefix="gimp_")
            adapters_registered.append("GIMP")
            logger.info("✅ Registered GIMP adapter")
        except ImportError as e:
            logger.warning(f"⚠️ Could not register GIMP adapter: {e}")
    
    if include_blender:
        try:
            from aibridge.adapters.cli.blender import BlenderAdapter
            server.register_adapter(BlenderAdapter, BLENDER_ACTIONS, prefix="blender_")
            adapters_registered.append("Blender")
            logger.info("✅ Registered Blender adapter")
        except ImportError as e:
            logger.warning(f"⚠️ Could not register Blender adapter: {e}")
    
    if include_ffmpeg:
        try:
            from aibridge.adapters.cli.ffmpeg import FFmpegAdapter
            server.register_adapter(FFmpegAdapter, FFMPEG_ACTIONS, prefix="ffmpeg_")
            adapters_registered.append("FFmpeg")
            logger.info("✅ Registered FFmpeg adapter")
        except ImportError as e:
            logger.warning(f"⚠️ Could not register FFmpeg adapter: {e}")
    
    if include_shotcut:
        try:
            from aibridge.adapters.cli.shotcut import ShotcutAdapter
            server.register_adapter(ShotcutAdapter, SHOTCUT_ACTIONS, prefix="shotcut_")
            adapters_registered.append("Shotcut")
            logger.info("✅ Registered Shotcut adapter")
        except ImportError as e:
            logger.warning(f"⚠️ Could not register Shotcut adapter: {e}")
    
    return adapters_registered


async def _auto_discover_adapters(
    server: AIBridgeMCPServer,
    config_path: Optional[str] = None
) -> list:
    """Auto-discover and register additional adapters."""
    adapters_registered = []
    
    try:
        discovery = AdapterDiscovery(config_path=config_path)
        discovered = await discovery.discover_all()
        
        for name, info in discovered.items():
            if info.available and info.adapter_class and name not in ["gimp", "blender", "ffmpeg", "shotcut"]:
                try:
                    # Generate schemas
                    schemas = {}
                    for action in getattr(info.adapter_class, "SUPPORTED_ACTIONS", []):
                        schemas[action] = {
                            "description": f"Execute {action}",
                            "parameters": {"input": {"type": "string", "required": False}}
                        }
                    
                    server.register_adapter(info.adapter_class, schemas, prefix=f"{name}_")
                    adapters_registered.append(name)
                    logger.info(f"✅ Auto-registered adapter: {name}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to auto-register {name}: {e}")
    except Exception as e:
        logger.warning(f"⚠️ Auto-discovery failed: {e}")
    
    return adapters_registered


async def create_cli_mcp_server_async(
    include_gimp: bool = True,
    include_blender: bool = True,
    include_ffmpeg: bool = True,
    include_shotcut: bool = True,
    auto_discover: bool = True,
    config_path: Optional[str] = None
) -> AIBridgeMCPServer:
    """
    Create a pre-configured MCP Server with CLI adapters (async version).
    
    Args:
        include_gimp: Whether to include GIMP adapter
        include_blender: Whether to include Blender adapter
        include_ffmpeg: Whether to include FFmpeg adapter
        include_shotcut: Whether to include Shotcut adapter
        auto_discover: Whether to auto-discover additional adapters
        config_path: Path to adapter configuration file
        
    Returns:
        Configured AIBridgeMCPServer instance
    """
    server = AIBridgeMCPServer(
        name="ai-bridge-cli",
        version="2.0.0"
    )
    
    # Register built-in adapters
    adapters_registered = _register_builtin_adapters(
        server, include_gimp, include_blender, include_ffmpeg, include_shotcut
    )
    
    # Auto-discover additional adapters
    if auto_discover:
        discovered_adapters = await _auto_discover_adapters(server, config_path)
        adapters_registered.extend(discovered_adapters)
    
    logger.info(f"🚀 MCP Server ready with adapters: {adapters_registered}")
    return server


def create_cli_mcp_server(
    include_gimp: bool = True,
    include_blender: bool = True,
    include_ffmpeg: bool = True,
    include_shotcut: bool = True,
    auto_discover: bool = True,
    config_path: Optional[str] = None
) -> AIBridgeMCPServer:
    """
    Synchronous wrapper for create_cli_mcp_server_async.
    
    Creates a pre-configured MCP Server with CLI adapters.
    """
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context - create server synchronously with built-in adapters only
            server = AIBridgeMCPServer(name="ai-bridge-cli", version="2.0.0")
            _register_builtin_adapters(server, include_gimp, include_blender, include_ffmpeg, include_shotcut)
            if auto_discover:
                logger.warning(
                    "Auto-discover is disabled when called from async context. "
                    "Use create_cli_mcp_server_async() for full functionality."
                )
            return server
        else:
            # Use the async version
            return loop.run_until_complete(create_cli_mcp_server_async(
                include_gimp=include_gimp,
                include_blender=include_blender,
                include_ffmpeg=include_ffmpeg,
                include_shotcut=include_shotcut,
                auto_discover=auto_discover,
                config_path=config_path
            ))
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(create_cli_mcp_server_async(
            include_gimp=include_gimp,
            include_blender=include_blender,
            include_ffmpeg=include_ffmpeg,
            include_shotcut=include_shotcut,
            auto_discover=auto_discover,
            config_path=config_path
        ))


async def main():
    """Main entry point for CLI MCP Server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI-Bridge CLI MCP Server")
    parser.add_argument(
        "--transport", choices=["stdio", "http"], default="stdio",
        help="Transport protocol (default: stdio)"
    )
    parser.add_argument("--host", default="localhost", help="HTTP host (for http transport)")
    parser.add_argument("--port", type=int, default=8080, help="HTTP port (for http transport)")
    parser.add_argument("--no-gimp", action="store_true", help="Disable GIMP adapter")
    parser.add_argument("--no-blender", action="store_true", help="Disable Blender adapter")
    parser.add_argument("--no-ffmpeg", action="store_true", help="Disable FFmpeg adapter")
    parser.add_argument("--no-shotcut", action="store_true", help="Disable Shotcut adapter")
    parser.add_argument("--no-auto-discover", action="store_true", help="Disable auto-discovery")
    parser.add_argument("--config", help="Path to adapter configuration file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument("--list-adapters", action="store_true", help="List available adapters and exit")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # List adapters mode
    if args.list_adapters:
        discovery = AdapterDiscovery(config_path=args.config)
        adapters = await discovery.discover_all()
        
        print("\n" + "=" * 60)
        print("Available Adapters")
        print("=" * 60)
        
        for name, info in adapters.items():
            status = "✅ Available" if info.available else "❌ Not Available"
            print(f"\n{name}")
            print(f"  Status: {status}")
            print(f"  CLI: {info.cli_name}")
            if info.cli_path:
                print(f"  Path: {info.cli_path}")
            if info.error:
                print(f"  Error: {info.error}")
            desc = info.metadata.get("description", "")
            if desc:
                print(f"  Description: {desc}")
        
        print("\n" + "=" * 60)
        return
    
    # Create server
    server = await create_cli_mcp_server_async(
        include_gimp=not args.no_gimp,
        include_blender=not args.no_blender,
        include_ffmpeg=not args.no_ffmpeg,
        include_shotcut=not args.no_shotcut,
        auto_discover=not args.no_auto_discover,
        config_path=args.config
    )
    
    # Run server
    if args.transport == "stdio":
        await server.run_stdio()
    else:
        await server.run_http(host=args.host, port=args.port)


if __name__ == "__main__":
    asyncio.run(main())
