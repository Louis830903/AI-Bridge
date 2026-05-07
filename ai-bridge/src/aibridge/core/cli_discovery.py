"""
CLI Tool Discovery — Phase III v0.11.0

Cross-platform tool detection and installation guidance.
Covers 20+ CLI tools used by AI-Bridge adapters (ffmpeg, pandoc, docker, etc.)

Auto-detects platform and provides appropriate install commands.
"""

from __future__ import annotations

import platform
import shutil
import subprocess
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """Information about a CLI tool on the current system."""

    name: str
    path: str | None = None
    version: str | None = None
    platform: str = field(default_factory=platform.system)
    available: bool = False
    install_hint: str | None = None

    def __repr__(self) -> str:
        status = "✓" if self.available else "✗"
        return f"ToolInfo({self.name} {status} path={self.path!r})"


# Tool metadata database: name → {install hints per platform, version flag, min version}
TOOL_DB: dict[str, dict] = {
    "ffmpeg": {
        "install": {
            "Windows": "winget install Gyan.FFmpeg",
            "Darwin": "brew install ffmpeg",
            "Linux": "sudo apt install ffmpeg",
        },
        "version_flag": "-version",
        "version_parser": "line1",
        "min_version": "4.0",
    },
    "pandoc": {
        "install": {
            "Windows": "winget install JohnMacFarlane.Pandoc",
            "Darwin": "brew install pandoc",
            "Linux": "sudo apt install pandoc",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "docker": {
        "install": {
            "Windows": "winget install Docker.DockerDesktop",
            "Darwin": "brew install --cask docker",
            "Linux": "sudo apt install docker.io",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "imagemagick": {
        "install": {
            "Windows": "winget install ImageMagick.ImageMagick",
            "Darwin": "brew install imagemagick",
            "Linux": "sudo apt install imagemagick",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "gimp": {
        "install": {
            "Windows": "winget install GIMP.GIMP",
            "Darwin": "brew install --cask gimp",
            "Linux": "sudo apt install gimp",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "blender": {
        "install": {
            "Windows": "winget install BlenderFoundation.Blender",
            "Darwin": "brew install --cask blender",
            "Linux": "sudo apt install blender",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "shotcut": {
        "install": {
            "Windows": "winget install Meltytech.Shotcut",
            "Darwin": "brew install --cask shotcut",
            "Linux": "sudo apt install shotcut",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "git": {
        "install": {
            "Windows": "winget install Git.Git",
            "Darwin": "brew install git",
            "Linux": "sudo apt install git",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "node": {
        "install": {
            "Windows": "winget install OpenJS.NodeJS",
            "Darwin": "brew install node",
            "Linux": "sudo apt install nodejs",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "python3": {
        "install": {
            "Windows": "winget install Python.Python.3",
            "Darwin": "brew install python@3",
            "Linux": "sudo apt install python3",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "prettier": {
        "install": {
            "Windows": "npm install -g prettier",
            "Darwin": "brew install prettier",
            "Linux": "npm install -g prettier",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "aider": {
        "install": {
            "Windows": "pip install aider-chat",
            "Darwin": "pip install aider-chat",
            "Linux": "pip install aider-chat",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "playwright": {
        "install": {
            "Windows": "npx playwright install",
            "Darwin": "npx playwright install",
            "Linux": "npx playwright install",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
    "soffice": {
        "install": {
            "Windows": "winget install TheDocumentFoundation.LibreOffice",
            "Darwin": "brew install --cask libreoffice",
            "Linux": "sudo apt install libreoffice",
        },
        "version_flag": "--version",
        "version_parser": "line1",
        "alt_names": ["libreoffice"],
    },
    "wkhtmltopdf": {
        "install": {
            "Windows": "winget install wkhtmltopdf.wkhtmltopdf",
            "Darwin": "brew install wkhtmltopdf",
            "Linux": "sudo apt install wkhtmltopdf",
        },
        "version_flag": "--version",
        "version_parser": "line1",
    },
}


class CLIToolDiscovery:
    """Cross-platform CLI tool detection and installation guidance.

    Usage:
        discovery = CLIToolDiscovery()
        info = discovery.detect("ffmpeg")
        if not info.available:
            print(info.install_hint)
    """

    def __init__(self):
        self._system = platform.system()
        self._cache: dict[str, ToolInfo] = {}

    def detect(self, tool_name: str) -> ToolInfo:
        """Detect if a CLI tool is available.

        Results are cached — subsequent calls return instantly.

        Args:
            tool_name: Tool name matching TOOL_DB key.

        Returns:
            ToolInfo with availability, path, version, and install hint.
        """
        if tool_name in self._cache:
            return self._cache[tool_name]

        meta = TOOL_DB.get(tool_name)
        if meta is None:
            info = ToolInfo(
                name=tool_name,
                available=False,
                install_hint=f"Unknown tool: {tool_name}",
            )
            self._cache[tool_name] = info
            return info

        # Check all possible names for this tool
        names = [tool_name] + meta.get("alt_names", [])
        found_path = None
        for name in names:
            found_path = shutil.which(name)
            if found_path:
                break

        version = None
        if found_path:
            version = self._get_version(found_path, meta)

        install_hint = meta.get("install", {}).get(self._system)

        info = ToolInfo(
            name=tool_name,
            path=found_path,
            version=version,
            platform=self._system,
            available=found_path is not None,
            install_hint=install_hint,
        )
        self._cache[tool_name] = info
        return info

    def detect_all(self) -> dict[str, ToolInfo]:
        """Batch-detect all known tools.

        Returns:
            Dict mapping tool name → ToolInfo.
        """
        results = {}
        for name in TOOL_DB:
            results[name] = self.detect(name)
        return results

    def suggest_alternative(self, tool_name: str) -> str | None:
        """Suggest an alternative if a tool is unavailable.

        Args:
            tool_name: Name of the unavailable tool.

        Returns:
            Alternative suggestion string, or None.
        """
        alternatives = {
            "ffmpeg": "Try using Python subprocess with built-in encoders.",
            "pandoc": "Use python-docx/openpyxl for document conversion instead.",
            "docker": "Use local Python virtualenv or subprocess directly.",
            "imagemagick": "Use Pillow (PIL) for image processing.",
            "gimp": "Use Pillow or ImageMagick CLI for headless processing.",
            "blender": "Use FFmpeg for basic media processing.",
            "shotcut": "Use FFmpeg CLI for video editing.",
            "prettier": "Use Black or Ruff for Python code formatting.",
        }
        return alternatives.get(tool_name)

    def warm_up(self) -> dict[str, ToolInfo]:
        """Warm up — detect all tools and populate cache."""
        return self.detect_all()

    def get_summary(self) -> str:
        """Human-readable summary of all detected tools."""
        results = self.detect_all()
        available = [n for n, i in results.items() if i.available]
        unavailable = [n for n, i in results.items() if not i.available]

        lines = [
            f"CLI Tool Discovery — {self._system}",
            f"{'='*40}",
            f"✓ Available ({len(available)}/{len(results)}): "
            + ", ".join(available),
        ]
        if unavailable:
            lines.append(
                f"✗ Missing ({len(unavailable)}/{len(results)}): "
                + ", ".join(unavailable)
            )
        return "\n".join(lines)

    def _get_version(self, exe_path: str, meta: dict) -> str | None:
        """Try to get tool version via subprocess."""
        flag = meta.get("version_flag", "--version")
        try:
            result = subprocess.run(
                [exe_path, flag],
                capture_output=True, text=True, timeout=5,
            )
            output = result.stdout or result.stderr
            if output:
                return output.strip().split("\n")[0][:100]
        except Exception:
            pass
        return None
