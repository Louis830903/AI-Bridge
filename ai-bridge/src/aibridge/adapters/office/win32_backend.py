"""
Win32 COM Backend — Phase III v0.11.0

Windows-only Office backend using pywin32 COM automation.
Migrates existing COM logic from word.py/excel.py/powerpoint.py
into the new strategy-pattern architecture.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Any

import pandas as pd

from aibridge.adapters.office.base import (
    DocumentHandle,
    WordAdapter,
    ExcelAdapter,
    PPTAdapter,
)

logger = logging.getLogger(__name__)

BACKEND_TYPE = "win32"

# Lazy pywin32 import
_win32com: Any = None


def _get_win32com():
    global _win32com
    if _win32com is None:
        import win32com.client
        _win32com = win32com.client
    return _win32com


class _Win32Mixin:
    """Shared COM helpers."""

    @classmethod
    def is_available(cls) -> bool:
        try:
            import platform
            if platform.system() != "Windows":
                return False
            import win32com.client  # noqa: F401
            return True
        except ImportError:
            return False


# ============ Word ============

class Win32WordAdapter(_Win32Mixin, WordAdapter):
    """Word adapter using pywin32 COM."""

    _backend_type = BACKEND_TYPE
    _prog_id = "Word.Application"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._app = None
        self._doc = None

    def open_document(self, path: Path) -> DocumentHandle:
        w32 = _get_win32com()
        path = Path(path)

        if self._app is None:
            self._app = w32.Dispatch(self._prog_id)
            self._app.Visible = self.config.get("visible", False)

        if path.exists():
            self._doc = self._app.Documents.Open(str(path))
        else:
            self._doc = self._app.Documents.Add()

        handle = DocumentHandle(path=path, backend_type=BACKEND_TYPE)
        self._open_handles[str(path)] = handle
        return handle

    def save_as(
        self, doc: DocumentHandle, target_path: Path, format: str | None = None
    ) -> DocumentHandle:
        target_path = Path(target_path)
        if format and format.lower() == "pdf":
            # 17 = wdFormatPDF
            self._doc.SaveAs(str(target_path), FileFormat=17)
        else:
            if format:
                target_path = target_path.with_suffix(f".{format}")
            self._doc.SaveAs(str(target_path))
        return DocumentHandle(path=target_path, backend_type=BACKEND_TYPE)

    def export_pdf(
        self, doc: DocumentHandle, output_path: Path | None = None
    ) -> Path:
        output_path = Path(output_path or doc.path.with_suffix(".pdf"))
        self._doc.SaveAs(str(output_path), FileFormat=17)
        return output_path

    def extract_text(self, doc: DocumentHandle) -> str:
        return self._doc.Content.Text if self._doc else ""

    def extract_tables(self, doc: DocumentHandle) -> list[pd.DataFrame]:
        if not self._doc:
            return []
        tables = []
        for table in self._doc.Tables:
            data = []
            for row in table.Rows:
                cells = [col.Range.Text.rstrip("\r\x07") for col in row.Cells]
                data.append(cells)
            if data:
                tables.append(
                    pd.DataFrame(data[1:], columns=data[0])
                    if len(data) > 1 and data[0]
                    else pd.DataFrame(data)
                )
        return tables

    def close(self, doc: DocumentHandle) -> None:
        if self._doc:
            try:
                self._doc.Close(SaveChanges=False)
            except Exception:
                pass
            self._doc = None
        if self._app:
            try:
                self._app.Quit()
            except Exception:
                pass
            self._app = None
        self._open_handles.pop(str(doc.path), None)

    def insert_text(
        self, doc: DocumentHandle, text: str, position: str = "end"
    ) -> None:
        if position == "start":
            self._doc.Content.InsertBefore(text)
        else:
            self._doc.Content.InsertAfter(text)

    def replace_text(self, doc: DocumentHandle, old: str, new: str) -> int:
        if not self._doc:
            return 0
        from win32com.client import constants as wc
        find = self._doc.Content.Find
        find.Text = old
        find.Replacement.Text = new
        find.Execute(Replace=wc.wdReplaceAll)
        return 1  # COM doesn't easily return count

    def add_table(
        self,
        doc: DocumentHandle,
        rows: int,
        cols: int,
        data: list[list] | None = None,
    ) -> int:
        table = self._doc.Tables.Add(self._doc.Content, rows, cols)
        idx = self._doc.Tables.Count - 1
        if data:
            for i, row_data in enumerate(data):
                for j, val in enumerate(row_data):
                    if i < rows and j < cols:
                        table.Cell(i + 1, j + 1).Range.Text = str(val)
        return idx

    def get_comments(self, doc: DocumentHandle) -> list[dict]:
        if not self._doc:
            return []
        comments = []
        for comment in self._doc.Comments:
            comments.append({
                "author": comment.Author,
                "text": comment.Range.Text,
                "date": str(comment.Date) if comment.Date else "",
            })
        return comments


# ============ Excel ============

class Win32ExcelAdapter(_Win32Mixin, ExcelAdapter):
    """Excel adapter using pywin32 COM."""

    _backend_type = BACKEND_TYPE
    _prog_id = "Excel.Application"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._app = None
        self._wb = None

    def open_document(self, path: Path) -> DocumentHandle:
        w32 = _get_win32com()
        path = Path(path)

        if self._app is None:
            self._app = w32.Dispatch(self._prog_id)
            self._app.Visible = self.config.get("visible", False)

        if path.exists():
            self._wb = self._app.Workbooks.Open(str(path))
        else:
            self._wb = self._app.Workbooks.Add()

        handle = DocumentHandle(path=path, backend_type=BACKEND_TYPE)
        self._open_handles[str(path)] = handle
        return handle

    def save_as(
        self, doc: DocumentHandle, target_path: Path, format: str | None = None
    ) -> DocumentHandle:
        target_path = Path(target_path)
        if format:
            target_path = target_path.with_suffix(f".{format}")
        self._wb.SaveAs(str(target_path))
        return DocumentHandle(path=target_path, backend_type=BACKEND_TYPE)

    def export_pdf(
        self, doc: DocumentHandle, output_path: Path | None = None
    ) -> Path:
        output_path = Path(output_path or doc.path.with_suffix(".pdf"))
        # 0 = xlTypePDF
        self._wb.ExportAsFixedFormat(0, str(output_path))
        return output_path

    def extract_text(self, doc: DocumentHandle) -> str:
        texts = []
        for sheet in self._wb.Sheets:
            used = sheet.UsedRange
            if used.Value:
                values = used.Value
                if isinstance(values, tuple):
                    for row in values:
                        row_vals = row if isinstance(row, tuple) else (row,)
                        texts.append(" | ".join(str(c) for c in row_vals if c is not None))
        return "\n".join(texts)

    def extract_tables(self, doc: DocumentHandle) -> list[pd.DataFrame]:
        tables = []
        for sheet in self._wb.Sheets:
            used = sheet.UsedRange
            if used.Value:
                values = used.Value
                if isinstance(values, tuple):
                    if len(values) > 1 and values[0]:
                        df = pd.DataFrame(values[1:], columns=list(values[0]))
                    else:
                        df = pd.DataFrame(values)
                    tables.append(df)
        return tables

    def close(self, doc: DocumentHandle) -> None:
        if self._wb:
            try:
                self._wb.Close(SaveChanges=False)
            except Exception:
                pass
            self._wb = None
        if self._app:
            try:
                self._app.Quit()
            except Exception:
                pass
            self._app = None
        self._open_handles.pop(str(doc.path), None)

    def read_range(self, doc: DocumentHandle, range_str: str) -> pd.DataFrame:
        sheet_name = "Sheet1"
        rng = range_str
        if "!" in range_str:
            sheet_name, rng = range_str.split("!", 1)

        sheet = self._wb.Sheets(sheet_name)
        values = sheet.Range(rng).Value
        if values is None:
            return pd.DataFrame()
        if isinstance(values, tuple):
            if len(values) > 1 and isinstance(values[0], tuple):
                return pd.DataFrame(values[1:], columns=list(values[0]))
            return pd.DataFrame([list(v) if isinstance(v, tuple) else [v] for v in values])
        return pd.DataFrame([[values]])

    def write_range(
        self, doc: DocumentHandle, range_str: str, data: pd.DataFrame
    ) -> None:
        sheet_name = "Sheet1"
        rng = range_str
        if "!" in range_str:
            sheet_name, rng = range_str.split("!", 1)

        sheet = self._wb.Sheets(sheet_name)
        # Convert DataFrame to tuple of tuples for COM
        values = tuple(tuple(row) for row in data.values)
        sheet.Range(rng).Value = values

    def add_chart(
        self,
        doc: DocumentHandle,
        data_range: str,
        chart_type: str,
        position: str,
    ) -> None:
        chart_type_map = {"bar": 51, "line": 4, "pie": 5, "scatter": -4169}
        sheet = self._wb.ActiveSheet
        chart_obj = sheet.Shapes.AddChart2(
            201, chart_type_map.get(chart_type, 51)
        ).Chart
        chart_obj.SetSourceData(sheet.Range(data_range))
        sheet.Shapes(chart_obj.Parent.Name).Left = sheet.Range(position).Left
        sheet.Shapes(chart_obj.Parent.Name).Top = sheet.Range(position).Top

    def create_pivot(
        self,
        doc: DocumentHandle,
        source_range: str,
        rows: list[str],
        values: list[str],
    ) -> None:
        # COM pivot table — simplified
        sheet = self._wb.ActiveSheet
        pc = self._wb.PivotCaches().Add(1, sheet.Range(source_range))
        pt = pc.CreatePivotTable(
            sheet.Range("K1"),  # default position
            f"Pivot_{len(self._wb.Sheets)}",
        )
        for field in rows:
            pt.PivotFields(field).Orientation = 1  # xlRowField
        for field in values:
            pt.PivotFields(field).Orientation = 4  # xlDataField

    def apply_formula(
        self, doc: DocumentHandle, cell: str, formula: str
    ) -> None:
        self._wb.ActiveSheet.Range(cell).Formula = formula


# ============ PowerPoint ============

class Win32PPTAdapter(_Win32Mixin, PPTAdapter):
    """PowerPoint adapter using pywin32 COM."""

    _backend_type = BACKEND_TYPE
    _prog_id = "PowerPoint.Application"

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config)
        self._app = None
        self._prs = None

    def open_document(self, path: Path) -> DocumentHandle:
        w32 = _get_win32com()
        path = Path(path)

        if self._app is None:
            self._app = w32.Dispatch(self._prog_id)
            self._app.Visible = True  # PowerPoint must be visible

        if path.exists():
            self._prs = self._app.Presentations.Open(str(path))
        else:
            self._prs = self._app.Presentations.Add()

        handle = DocumentHandle(path=path, backend_type=BACKEND_TYPE)
        self._open_handles[str(path)] = handle
        return handle

    def save_as(
        self, doc: DocumentHandle, target_path: Path, format: str | None = None
    ) -> DocumentHandle:
        target_path = Path(target_path)
        if format and format.lower() == "pdf":
            self._prs.SaveAs(str(target_path), 32)  # ppSaveAsPDF
        else:
            if format:
                target_path = target_path.with_suffix(f".{format}")
            self._prs.SaveAs(str(target_path))
        return DocumentHandle(path=target_path, backend_type=BACKEND_TYPE)

    def export_pdf(
        self, doc: DocumentHandle, output_path: Path | None = None
    ) -> Path:
        output_path = Path(output_path or doc.path.with_suffix(".pdf"))
        self._prs.SaveAs(str(output_path), 32)
        return output_path

    def extract_text(self, doc: DocumentHandle) -> str:
        texts = []
        for slide in self._prs.Slides:
            for shape in slide.Shapes:
                if shape.HasTextFrame:
                    t = shape.TextFrame.TextRange.Text.strip()
                    if t:
                        texts.append(t)
        return "\n".join(texts)

    def extract_tables(self, doc: DocumentHandle) -> list[pd.DataFrame]:
        tables = []
        for slide in self._prs.Slides:
            for shape in slide.Shapes:
                if shape.HasTable:
                    table = shape.Table
                    data = []
                    for row in table.Rows:
                        cells = [cell.Shape.TextFrame.TextRange.Text
                                 for cell in row.Cells]
                        data.append(cells)
                    if data:
                        tables.append(
                            pd.DataFrame(data[1:], columns=data[0])
                            if len(data) > 1 and data[0]
                            else pd.DataFrame(data)
                        )
        return tables

    def close(self, doc: DocumentHandle) -> None:
        if self._prs:
            try:
                self._prs.Close()
            except Exception:
                pass
            self._prs = None
        if self._app:
            try:
                self._app.Quit()
            except Exception:
                pass
            self._app = None
        self._open_handles.pop(str(doc.path), None)

    def add_slide(self, doc: DocumentHandle, layout: str = "blank") -> int:
        layout_map = {"blank": 12, "title": 1, "content": 2}
        layout_idx = layout_map.get(layout, 12)
        idx = self._prs.Slides.Count + 1
        slide = self._prs.Slides.Add(idx, layout_idx)
        return idx

    def add_text_box(
        self,
        doc: DocumentHandle,
        slide_index: int,
        text: str,
        position: tuple[float, float, float, float] | None = None,
    ) -> None:
        if slide_index < 1 or slide_index > self._prs.Slides.Count:
            raise IndexError(f"Slide {slide_index} out of range")

        slide = self._prs.Slides(slide_index)
        left, top, width, height = position or (100, 100, 400, 200)
        # COM uses points; convert inches to points
        textbox = slide.Shapes.AddTextbox(
            1, int(left * 72), int(top * 72),
            int(width * 72), int(height * 72),
        )
        textbox.TextFrame.TextRange.Text = text

    def add_image(
        self,
        doc: DocumentHandle,
        slide_index: int,
        image_path: Path,
        position: tuple[float, float, float, float] | None = None,
    ) -> None:
        if slide_index < 1 or slide_index > self._prs.Slides.Count:
            raise IndexError(f"Slide {slide_index} out of range")

        slide = self._prs.Slides(slide_index)
        left, top, width, height = position or (100, 100, 300, 200)
        slide.Shapes.AddPicture(
            str(image_path), 0, 1,  # LinkToFile=0, SaveWithDoc=1
            int(left * 72), int(top * 72),
            int(width * 72), int(height * 72),
        )
