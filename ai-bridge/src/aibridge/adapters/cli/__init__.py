"""CLI Adapter Package for AI-Bridge

Provides base class and implementations for wrapping CLI-Anything generated tools
as AI-Bridge adapters.

Example:
    from aibridge.adapters.cli import CLIAdapter, GIMPAdapter, BlenderAdapter

    # Use the base class for custom adapters
    class MyCLIAdapter(CLIAdapter):
        cli_name = "my-tool"

    # Or use pre-built adapters
    adapter = GIMPAdapter()
    await adapter.initialize()
"""

from .base import CLIAdapter, CLICommand, CLIResult

__all__ = [
    "CLIAdapter",
    "CLICommand",
    "CLIResult",
]

# Built-in adapters - import if available
_BUILTIN_ADAPTERS = {
    # Original 4 adapters
    "gimp": ("aibridge.adapters.cli.gimp", "GIMPAdapter"),
    "blender": ("aibridge.adapters.cli.blender", "BlenderAdapter"),
    "ffmpeg": ("aibridge.adapters.cli.ffmpeg", "FFmpegAdapter"),
    "shotcut": ("aibridge.adapters.cli.shotcut", "ShotcutAdapter"),
    # New 5 adapters
    "aider": ("aibridge.adapters.cli.aider", "AiderAdapter"),
    "imagemagick": ("aibridge.adapters.cli.imagemagick", "ImageMagickAdapter"),
    "pandoc": ("aibridge.adapters.cli.pandoc", "PandocAdapter"),
    "ytdlp": ("aibridge.adapters.cli.ytdlp", "YTDLPAdapter"),
    "playwright": ("aibridge.adapters.cli.playwright", "PlaywrightAdapter"),
}

# Try to import each built-in adapter
for _name, (_module, _class) in _BUILTIN_ADAPTERS.items():
    try:
        _mod = __import__(_module, fromlist=[_class])
        _adapter_class = getattr(_mod, _class)
        globals()[_class] = _adapter_class
        __all__.append(_class)
    except ImportError:
        pass  # Adapter not available
