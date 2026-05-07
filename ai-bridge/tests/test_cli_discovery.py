"""
CLI Tool Discovery Tests — Phase III v0.11.0

Tests for cross-platform CLI tool detection and installation guidance.
Covers ToolInfo, CLIToolDiscovery, TOOL_DB integrity, and platform awareness.
"""

from __future__ import annotations

import platform
import pytest

from aibridge.core.cli_discovery import (
    ToolInfo,
    TOOL_DB,
    CLIToolDiscovery,
)


# ═══════════════════════════════════════════════════════════════════
# TestToolInfo
# ═══════════════════════════════════════════════════════════════════

class TestToolInfo:
    """ToolInfo dataclass tests."""

    def test_create_available_tool(self):
        """ToolInfo created for an available tool."""
        info = ToolInfo(
            name="git",
            path="/usr/bin/git",
            version="2.40.0",
            platform="Linux",
            available=True,
        )
        assert info.name == "git"
        assert info.path == "/usr/bin/git"
        assert info.version == "2.40.0"
        assert info.platform == "Linux"
        assert info.available is True
        assert info.install_hint is None

    def test_create_unavailable_tool_with_hint(self):
        """ToolInfo for an unavailable tool with install hint."""
        info = ToolInfo(
            name="ffmpeg",
            available=False,
            install_hint="winget install Gyan.FFmpeg",
        )
        assert info.name == "ffmpeg"
        assert info.path is None
        assert info.version is None
        assert info.available is False
        assert info.install_hint == "winget install Gyan.FFmpeg"

    def test_defaults(self):
        """ToolInfo defaults are set correctly."""
        info = ToolInfo(name="test")
        assert info.name == "test"
        assert info.path is None
        assert info.version is None
        assert info.platform == platform.system()
        assert info.available is False
        assert info.install_hint is None

    def test_repr_available(self):
        """repr shows ✓ for available tools."""
        info = ToolInfo(name="git", path="/usr/bin/git", available=True)
        rep = repr(info)
        assert "✓" in rep
        assert "git" in rep

    def test_repr_unavailable(self):
        """repr shows ✗ for unavailable tools."""
        info = ToolInfo(name="ffmpeg", available=False)
        rep = repr(info)
        assert "✗" in rep
        assert "ffmpeg" in rep


# ═══════════════════════════════════════════════════════════════════
# TestToolDB
# ═══════════════════════════════════════════════════════════════════

class TestToolDB:
    """TOOL_DB integrity tests."""

    REQUIRED_TOOLS = [
        "ffmpeg", "pandoc", "docker", "imagemagick",
        "gimp", "blender", "shotcut", "git", "node",
        "python3", "prettier", "aider", "playwright",
        "soffice", "wkhtmltopdf",
    ]

    REQUIRED_PLATFORMS = ["Windows", "Darwin", "Linux"]

    def test_contains_all_expected_tools(self):
        """TOOL_DB contains all 15 expected tools."""
        for tool in self.REQUIRED_TOOLS:
            assert tool in TOOL_DB, f"{tool} missing from TOOL_DB"

    def test_each_tool_has_install_hints(self):
        """Every tool has install hints for all 3 platforms."""
        for name, meta in TOOL_DB.items():
            assert "install" in meta, f"{name} missing install"
            for plat in self.REQUIRED_PLATFORMS:
                assert plat in meta["install"], (
                    f"{name} missing install hint for {plat}"
                )

    def test_each_tool_has_version_flag(self):
        """Every tool has a version_flag."""
        for name, meta in TOOL_DB.items():
            assert "version_flag" in meta, f"{name} missing version_flag"
            assert meta["version_flag"], f"{name} has empty version_flag"

    def test_soffice_has_alt_names(self):
        """soffice has libreoffice as alt name."""
        meta = TOOL_DB["soffice"]
        assert "alt_names" in meta
        assert "libreoffice" in meta["alt_names"]


# ═══════════════════════════════════════════════════════════════════
# TestCLIToolDiscovery
# ═══════════════════════════════════════════════════════════════════

class TestCLIToolDiscovery:
    """CLIToolDiscovery class tests."""

    @pytest.fixture
    def discovery(self):
        return CLIToolDiscovery()

    # ── detect ──────────────────────────────────────────────────

    def test_detect_returns_toolinfo(self, discovery):
        """detect() always returns a ToolInfo instance."""
        info = discovery.detect("git")
        assert isinstance(info, ToolInfo)

    def test_detect_known_tool(self, discovery):
        """detect() on a tool that certainly exists (git)."""
        info = discovery.detect("git")
        assert info.name == "git"
        # git is almost certainly installed on dev machines
        assert info.available is True, f"git should be available, got: {info}"
        assert info.path is not None

    def test_detect_unknown_tool(self, discovery):
        """detect() on non-existent tool returns unavailable."""
        info = discovery.detect("nonexistent_tool_xyz_123")
        assert isinstance(info, ToolInfo)
        assert info.name == "nonexistent_tool_xyz_123"
        assert info.available is False
        assert info.path is None
        assert info.install_hint == "Unknown tool: nonexistent_tool_xyz_123"

    def test_detect_caches_results(self, discovery):
        """detect() caches — second call returns same instance."""
        info1 = discovery.detect("git")
        info2 = discovery.detect("git")
        assert info1 is info2  # same object (cached)

    def test_detect_includes_install_hint(self, discovery):
        """detect() provides install_hint even when unavailable on current OS."""
        info = discovery.detect("ffmpeg")
        # hint should be for current platform
        if not info.available:
            current_platform = platform.system()
            assert info.install_hint is not None
            assert len(info.install_hint) > 0

    def test_detect_version_on_available_tool(self, discovery):
        """detect() retrieves version for available tools."""
        info = discovery.detect("git")
        if info.available:
            assert info.version is not None
            assert len(info.version) > 0

    # ── detect_all ──────────────────────────────────────────────

    def test_detect_all_returns_all(self, discovery):
        """detect_all() returns dict with all TOOL_DB entries."""
        results = discovery.detect_all()
        assert isinstance(results, dict)
        assert len(results) == len(TOOL_DB)
        for name in TOOL_DB:
            assert name in results
            assert isinstance(results[name], ToolInfo)

    def test_detect_all_uses_cache(self, discovery):
        """detect_all() caches individual results."""
        # First call populates cache
        results1 = discovery.detect_all()
        # Second call uses cache (no subprocess calls for already-detected)
        results2 = discovery.detect_all()
        # Should return equivalent results
        for name in TOOL_DB:
            assert results1[name] is results2[name]

    # ── suggest_alternative ─────────────────────────────────────

    def test_suggest_alternative_known(self, discovery):
        """suggest_alternative() returns hint for known tools."""
        alt = discovery.suggest_alternative("ffmpeg")
        assert alt is not None
        assert "Python" in alt or "subprocess" in alt or "encoder" in alt

    def test_suggest_alternative_unknown(self, discovery):
        """suggest_alternative() returns None for unknown tools."""
        alt = discovery.suggest_alternative("nonexistent_tool_xyz")
        assert alt is None

    def test_suggest_alternative_coverage(self, discovery):
        """suggest_alternative() covering multiple tools."""
        # Tools we know have alternatives
        alternatives = {
            "ffmpeg": "encoder",
            "pandoc": "openpyxl",
            "docker": "subprocess",
            "imagemagick": "Pillow",
            "gimp": "Pillow",
            "blender": "FFmpeg",
            "shotcut": "FFmpeg",
            "prettier": "Ruff",
        }
        for tool, keyword in alternatives.items():
            alt = discovery.suggest_alternative(tool)
            assert alt is not None, f"{tool} should have alternative"
            assert keyword.lower() in alt.lower(), (
                f"{tool} alternative should mention {keyword}, got: {alt}"
            )

    # ── warm_up ─────────────────────────────────────────────────

    def test_warm_up_returns_all(self, discovery):
        """warm_up() is equivalent to detect_all()."""
        results = discovery.warm_up()
        assert isinstance(results, dict)
        assert len(results) == len(TOOL_DB)

    # ── get_summary ─────────────────────────────────────────────

    def test_get_summary_returns_string(self, discovery):
        """get_summary() returns a formatted string."""
        summary = discovery.get_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0
        assert "CLI Tool Discovery" in summary

    def test_get_summary_includes_platform(self, discovery):
        """get_summary() includes the current platform."""
        summary = discovery.get_summary()
        current_platform = platform.system()
        assert current_platform in summary

    def test_get_summary_has_available_section(self, discovery):
        """get_summary() reports available tools with ✓."""
        summary = discovery.get_summary()
        assert "✓ Available" in summary or "Available" in summary

    def test_get_summary_has_unavailable_section(self, discovery):
        """get_summary() reports missing tools section."""
        summary = discovery.get_summary()
        # Either lists missing tools or shows count
        assert "✗ Missing" in summary or "Missing" in summary


# ═══════════════════════════════════════════════════════════════════
# TestPlatformAwareness
# ═══════════════════════════════════════════════════════════════════

class TestPlatformAwareness:
    """Platform-specific behavior tests."""

    @pytest.fixture
    def discovery(self):
        return CLIToolDiscovery()

    def test_system_detected(self, discovery):
        """System platform is detected correctly."""
        info = discovery.detect("git")
        expected_platform = platform.system()
        assert info.platform == expected_platform

    def test_tool_info_platform_matches_system(self):
        """ToolInfo platform matches actual system by default."""
        info = ToolInfo(name="test")
        assert info.platform == platform.system()

    def test_cross_platform_hints_all_os(self):
        """Every tool has install hints for all supported OSes."""
        supported_oses = {"Windows", "Darwin", "Linux"}
        for name, meta in TOOL_DB.items():
            install = meta.get("install", {})
            hint_oses = set(install.keys())
            assert supported_oses == hint_oses, (
                f"{name}: install hints OS mismatch: {hint_oses} != {supported_oses}"
            )


# ═══════════════════════════════════════════════════════════════════
# TestEdgeCases
# ═══════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge case and robustness tests."""

    @pytest.fixture
    def discovery(self):
        return CLIToolDiscovery()

    def test_detect_empty_string(self, discovery):
        """detect() with empty string returns unavailable."""
        info = discovery.detect("")
        assert isinstance(info, ToolInfo)
        assert info.available is False
        assert info.path is None

    def test_detect_case_sensitive(self, discovery):
        """detect() is case-sensitive (TOOL_DB keys are lowercase)."""
        info = discovery.detect("GIT")
        # "GIT" is not in TOOL_DB (lowercase keys)
        assert info.available is False or "Unknown tool" in (info.install_hint or "")

    def test_multiple_instances_independent(self):
        """Multiple CLIToolDiscovery instances are independent."""
        d1 = CLIToolDiscovery()
        d2 = CLIToolDiscovery()
        r1 = d1.detect_all()
        r2 = d2.detect_all()
        assert len(r1) == len(r2) == len(TOOL_DB)
