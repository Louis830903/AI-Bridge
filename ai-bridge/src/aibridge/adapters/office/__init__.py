"""Office adapters module."""

from aibridge.adapters.office.word import WordAdapter
from aibridge.adapters.office.excel import ExcelAdapter
from aibridge.adapters.office.powerpoint import PowerPointAdapter
from aibridge.adapters.office.wps import WPSWriterAdapter, WPSSpreadsheetAdapter

__all__ = [
    "WordAdapter", "ExcelAdapter", "PowerPointAdapter",
    "WPSWriterAdapter", "WPSSpreadsheetAdapter"
]
