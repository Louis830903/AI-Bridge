"""
Office Adapter Factory — Phase III v0.11.0

Auto-selects the best available backend:
1. Win32 (Windows + pywin32) — richest feature set
2. LibreOffice (cross-platform, soffice on PATH) — good PDF/convert
3. OpenXML (pure Python) — always available fallback
"""

from __future__ import annotations

import platform
import shutil
import logging
from typing import Optional

from aibridge.adapters.office.base import WordAdapter, ExcelAdapter, PPTAdapter

logger = logging.getLogger(__name__)


def _check_pywin32() -> bool:
    try:
        import win32com.client  # noqa: F401
        return True
    except ImportError:
        return False


def _check_libreoffice() -> bool:
    return (
        shutil.which("soffice") is not None
        or shutil.which("libreoffice") is not None
    )


def _get_best_backend() -> str:
    """Auto-select the best available backend for the current platform."""
    if platform.system() == "Windows" and _check_pywin32():
        return "win32"
    if _check_libreoffice():
        return "libreoffice"
    return "openxml"


def create_word_adapter(backend: str | None = None) -> WordAdapter:
    """Create a Word adapter with automatic backend selection.

    Args:
        backend: Force a specific backend ("win32", "openxml", "libreoffice").
                 Auto-selects best if None.

    Returns:
        WordAdapter instance.

    Raises:
        RuntimeError: If the requested backend is unavailable.
    """
    backend = backend or _get_best_backend()

    if backend == "win32":
        from aibridge.adapters.office.win32_backend import Win32WordAdapter
        if not Win32WordAdapter.is_available():
            logger.warning("Win32 backend unavailable, falling back to openxml")
            from aibridge.adapters.office.openxml_backend import OpenXMLWordAdapter
            return OpenXMLWordAdapter()
        return Win32WordAdapter()

    elif backend == "libreoffice":
        from aibridge.adapters.office.libreoffice_backend import LibreOfficeWordAdapter
        if not LibreOfficeWordAdapter.is_available():
            logger.warning("LibreOffice backend unavailable, falling back to openxml")
            from aibridge.adapters.office.openxml_backend import OpenXMLWordAdapter
            return OpenXMLWordAdapter()
        return LibreOfficeWordAdapter()

    else:  # openxml (default fallback)
        from aibridge.adapters.office.openxml_backend import OpenXMLWordAdapter
        return OpenXMLWordAdapter()


def create_excel_adapter(backend: str | None = None) -> ExcelAdapter:
    """Create an Excel adapter with automatic backend selection.

    Args:
        backend: Force a specific backend. Auto-selects best if None.

    Returns:
        ExcelAdapter instance.
    """
    backend = backend or _get_best_backend()

    if backend == "win32":
        from aibridge.adapters.office.win32_backend import Win32ExcelAdapter
        if not Win32ExcelAdapter.is_available():
            logger.warning("Win32 backend unavailable, falling back to openxml")
            from aibridge.adapters.office.openxml_backend import OpenXMLExcelAdapter
            return OpenXMLExcelAdapter()
        return Win32ExcelAdapter()

    elif backend == "libreoffice":
        from aibridge.adapters.office.libreoffice_backend import LibreOfficeExcelAdapter
        if not LibreOfficeExcelAdapter.is_available():
            logger.warning("LibreOffice backend unavailable, falling back to openxml")
            from aibridge.adapters.office.openxml_backend import OpenXMLExcelAdapter
            return OpenXMLExcelAdapter()
        return LibreOfficeExcelAdapter()

    else:
        from aibridge.adapters.office.openxml_backend import OpenXMLExcelAdapter
        return OpenXMLExcelAdapter()


def create_ppt_adapter(backend: str | None = None) -> PPTAdapter:
    """Create a PowerPoint adapter with automatic backend selection.

    Args:
        backend: Force a specific backend. Auto-selects best if None.

    Returns:
        PPTAdapter instance.
    """
    backend = backend or _get_best_backend()

    if backend == "win32":
        from aibridge.adapters.office.win32_backend import Win32PPTAdapter
        if not Win32PPTAdapter.is_available():
            logger.warning("Win32 backend unavailable, falling back to openxml")
            from aibridge.adapters.office.openxml_backend import OpenXMLPPTAdapter
            return OpenXMLPPTAdapter()
        return Win32PPTAdapter()

    elif backend == "libreoffice":
        from aibridge.adapters.office.libreoffice_backend import LibreOfficePPTAdapter
        if not LibreOfficePPTAdapter.is_available():
            logger.warning("LibreOffice backend unavailable, falling back to openxml")
            from aibridge.adapters.office.openxml_backend import OpenXMLPPTAdapter
            return OpenXMLPPTAdapter()
        return LibreOfficePPTAdapter()

    else:
        from aibridge.adapters.office.openxml_backend import OpenXMLPPTAdapter
        return OpenXMLPPTAdapter()
