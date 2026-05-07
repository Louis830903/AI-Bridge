"""
Office Adapter Cross-Platform Base — Phase III v0.11.0

Abstract base classes for Word/Excel/PPT adapters with strategy pattern.
Three backend implementations: Win32 (COM), OpenXML (python-docx/openpyxl), LibreOffice (subprocess).

Provides:
- DocumentHandle: platform-agnostic document reference
- OfficeAdapter: core document operations (open/save/export/extract)
- WordAdapter: Word-specific operations (insert/replace/table/comments)
- ExcelAdapter: Excel-specific operations (range/chart/pivot/formula)
- PPTAdapter: PPT-specific operations (slide/textbox/image)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import pandas as pd


# ============ Document Handle ============

@dataclass
class DocumentHandle:
    """Cross-platform document reference.

    Holds minimal state — the backend implementation manages the actual
    document object internally via handle_id.
    """

    path: Path
    backend_type: str  # "win32" | "openxml" | "libreoffice"
    metadata: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f"DocumentHandle(path={self.path.name!r}, "
            f"backend={self.backend_type!r})"
        )


# ============ Core Office Adapter ============

class OfficeAdapter(ABC):
    """Abstract base for all Office document adapters.

    Provides the common document lifecycle: open → operate → save/export → close.
    Three backends implement this interface:
    - Win32OfficeAdapter (COM on Windows)
    - OpenXMLOfficeAdapter (python-docx/openpyxl, pure Python)
    - LibreOfficeAdapter (subprocess, cross-platform via soffice)
    """

    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self._open_handles: dict[str, DocumentHandle] = {}

    # -- Abstract methods (backend must implement) --

    @abstractmethod
    def open_document(self, path: Path) -> DocumentHandle:
        """Open a document and return a handle.

        Args:
            path: Path to the document file.

        Returns:
            DocumentHandle for subsequent operations.
        """
        ...

    @abstractmethod
    def save_as(
        self,
        doc: DocumentHandle,
        target_path: Path,
        format: str | None = None,
    ) -> DocumentHandle:
        """Save document to a new path/format.

        Args:
            doc: Document handle from open_document.
            target_path: Destination path.
            format: Target format extension (e.g. "pdf", "docx", "xlsx").

        Returns:
            Updated DocumentHandle pointing to target_path.
        """
        ...

    @abstractmethod
    def export_pdf(
        self, doc: DocumentHandle, output_path: Path | None = None
    ) -> Path:
        """Export document as PDF.

        Args:
            doc: Document handle.
            output_path: Output PDF path (auto-generated if None).

        Returns:
            Path to the generated PDF file.
        """
        ...

    @abstractmethod
    def extract_text(self, doc: DocumentHandle) -> str:
        """Extract all text content from the document."""
        ...

    @abstractmethod
    def extract_tables(self, doc: DocumentHandle) -> list[pd.DataFrame]:
        """Extract all tables from the document as DataFrames."""
        ...

    @abstractmethod
    def close(self, doc: DocumentHandle) -> None:
        """Close the document and release resources."""
        ...

    # -- Convenience methods (default implementations) --

    def convert_to(
        self,
        input_path: Path,
        output_format: str,
        output_path: Path | None = None,
    ) -> Path:
        """One-shot conversion: open → save_as → close.

        Args:
            input_path: Source document path.
            output_format: Target format (e.g. "pdf", "docx").
            output_path: Optional output path.

        Returns:
            Path to the converted file.
        """
        doc = self.open_document(input_path)
        try:
            if output_path is None:
                output_path = input_path.with_suffix(f".{output_format}")
            result = self.save_as(doc, output_path, output_format)
            return result.path
        finally:
            self.close(doc)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.dispose()

    def dispose(self) -> None:
        """Release all resources. Subclasses may override for cleanup."""
        handles = list(self._open_handles.values())
        for h in handles:
            try:
                self.close(h)
            except Exception:
                pass
        self._open_handles.clear()

    @classmethod
    @abstractmethod
    def is_available(cls) -> bool:
        """Check if this backend is available on the current platform."""
        ...

    @property
    def backend_type(self) -> str:
        """Return the backend type string (set by subclasses)."""
        return getattr(self, '_backend_type', 'unknown')


# ============ Word Adapter ============

class WordAdapter(OfficeAdapter):
    """Abstract interface for Word-specific operations.

    Implemented by:
    - Win32WordAdapter (COM)
    - OpenXMLWordAdapter (python-docx)
    - LibreOfficeWordAdapter (soffice)
    """

    @abstractmethod
    def insert_text(
        self, doc: DocumentHandle, text: str, position: str = "end"
    ) -> None:
        """Insert text at the specified position.

        Args:
            doc: Document handle.
            text: Text content to insert.
            position: "start", "end", or bookmark name.
        """
        ...

    @abstractmethod
    def replace_text(self, doc: DocumentHandle, old: str, new: str) -> int:
        """Replace all occurrences of old with new.

        Returns:
            Number of replacements made.
        """
        ...

    @abstractmethod
    def add_table(
        self,
        doc: DocumentHandle,
        rows: int,
        cols: int,
        data: list[list] | None = None,
    ) -> int:
        """Add a table to the document.

        Args:
            doc: Document handle.
            rows: Number of rows.
            cols: Number of columns.
            data: Optional 2D list to populate the table.

        Returns:
            Index of the added table.
        """
        ...

    @abstractmethod
    def get_comments(self, doc: DocumentHandle) -> list[dict]:
        """Extract all comments from the document.

        Returns:
            List of dicts with keys: author, text, date, paragraph.
        """
        ...


# ============ Excel Adapter ============

class ExcelAdapter(OfficeAdapter):
    """Abstract interface for Excel-specific operations.

    Implemented by:
    - Win32ExcelAdapter (COM)
    - OpenXMLExcelAdapter (openpyxl)
    - LibreOfficeExcelAdapter (soffice)
    """

    @abstractmethod
    def read_range(self, doc: DocumentHandle, range_str: str) -> pd.DataFrame:
        """Read a cell range into a DataFrame.

        Args:
            doc: Document handle.
            range_str: Excel range notation (e.g. "A1:C10", "Sheet1!A1:B2").

        Returns:
            DataFrame with the range contents.
        """
        ...

    @abstractmethod
    def write_range(
        self, doc: DocumentHandle, range_str: str, data: pd.DataFrame
    ) -> None:
        """Write a DataFrame to a cell range.

        Args:
            doc: Document handle.
            range_str: Target range (e.g. "A1").
            data: DataFrame to write.
        """
        ...

    @abstractmethod
    def add_chart(
        self,
        doc: DocumentHandle,
        data_range: str,
        chart_type: str,
        position: str,
    ) -> None:
        """Add a chart to the spreadsheet.

        Args:
            doc: Document handle.
            data_range: Source data range.
            chart_type: "bar", "line", "pie", "scatter".
            position: Target cell for chart placement.
        """
        ...

    @abstractmethod
    def create_pivot(
        self,
        doc: DocumentHandle,
        source_range: str,
        rows: list[str],
        values: list[str],
    ) -> None:
        """Create a pivot table.

        Args:
            doc: Document handle.
            source_range: Source data range.
            rows: Row field names.
            values: Value field names.
        """
        ...

    @abstractmethod
    def apply_formula(
        self, doc: DocumentHandle, cell: str, formula: str
    ) -> None:
        """Apply an Excel formula to a cell.

        Args:
            doc: Document handle.
            cell: Target cell (e.g. "C1").
            formula: Excel formula (e.g. "=SUM(A1:A10)").
        """
        ...


# ============ PPT Adapter ============

class PPTAdapter(OfficeAdapter):
    """Abstract interface for PowerPoint-specific operations.

    Implemented by:
    - Win32PPTAdapter (COM)
    - OpenXMLPPTAdapter (python-pptx)
    - LibreOfficePPTAdapter (soffice)
    """

    @abstractmethod
    def add_slide(self, doc: DocumentHandle, layout: str = "blank") -> int:
        """Add a new slide.

        Args:
            doc: Document handle.
            layout: Slide layout name ("blank", "title", "content").

        Returns:
            Index of the new slide (1-based).
        """
        ...

    @abstractmethod
    def add_text_box(
        self,
        doc: DocumentHandle,
        slide_index: int,
        text: str,
        position: tuple[float, float, float, float] | None = None,
    ) -> None:
        """Add a text box to a slide.

        Args:
            doc: Document handle.
            slide_index: 1-based slide index.
            text: Text content.
            position: (left, top, width, height) in inches. Default centers.
        """
        ...

    @abstractmethod
    def add_image(
        self,
        doc: DocumentHandle,
        slide_index: int,
        image_path: Path,
        position: tuple[float, float, float, float] | None = None,
    ) -> None:
        """Add an image to a slide.

        Args:
            doc: Document handle.
            slide_index: 1-based slide index.
            image_path: Path to image file.
            position: (left, top, width, height) in inches.
        """
        ...
