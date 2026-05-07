"""Office adapters module — Phase III v0.11.0 cross-platform architecture.

Strategy pattern: auto-select Win32/OpenXML/LibreOffice backend.
"""

# Backward-compatible exports (legacy COM adapters)
from aibridge.adapters.office.word import WordAdapter
from aibridge.adapters.office.excel import ExcelAdapter
from aibridge.adapters.office.powerpoint import PowerPointAdapter
from aibridge.adapters.office.wps import WPSWriterAdapter, WPSSpreadsheetAdapter

# New cross-platform factory functions
from aibridge.adapters.office.factory import (
    create_word_adapter,
    create_excel_adapter,
    create_ppt_adapter,
)

# New cross-platform abstract base classes
from aibridge.adapters.office.base import (
    DocumentHandle,
    OfficeAdapter,
    WordAdapter as CrossWordAdapter,
    ExcelAdapter as CrossExcelAdapter,
    PPTAdapter as CrossPPTAdapter,
)

__all__ = [
    # Legacy adapters (backward compat)
    "WordAdapter", "ExcelAdapter", "PowerPointAdapter",
    "WPSWriterAdapter", "WPSSpreadsheetAdapter",
    # Cross-platform factory
    "create_word_adapter", "create_excel_adapter", "create_ppt_adapter",
    # Abstract bases
    "DocumentHandle", "OfficeAdapter",
    "CrossWordAdapter", "CrossExcelAdapter", "CrossPPTAdapter",
]
