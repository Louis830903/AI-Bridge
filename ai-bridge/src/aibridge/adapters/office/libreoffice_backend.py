"""
LibreOffice Backend — Phase III v0.11.0

Cross-platform Office backend using LibreOffice subprocess (soffice).
Used as fallback when neither pywin32 (Windows COM) nor pure OpenXML
libraries are sufficient.

Requires LibreOffice installed and `soffice` on PATH.
"""

from __future__ import annotations

import logging
import subprocess
import shutil
from pathlib import Path
from typing import Optional

import pandas as pd

from aibridge.adapters.office.base import (
    DocumentHandle,
    WordAdapter,
    ExcelAdapter,
    PPTAdapter,
)

logger = logging.getLogger(__name__)

BACKEND_TYPE = "libreoffice"


def _find_soffice() -> str | None:
    """Find LibreOffice executable path."""
    for name in ("soffice", "libreoffice"):
        path = shutil.which(name)
        if path:
            return path
    return None


class _LibreOfficeMixin:
    """Shared LibreOffice helpers."""

    @classmethod
    def is_available(cls) -> bool:
        return _find_soffice() is not None

    def _run_soffice(self, args: list[str], timeout: int = 60) -> None:
        """Run soffice with args, raise on failure."""
        soffice = _find_soffice()
        if not soffice:
            raise RuntimeError("LibreOffice not found on PATH")

        cmd = [soffice, "--headless"] + args
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout,
        )
        if result.returncode != 0:
            logger.warning(f"soffice stderr: {result.stderr}")
            raise RuntimeError(
                f"LibreOffice command failed (rc={result.returncode}): "
                f"{' '.join(cmd)}"
            )

    def _convert_via_soffice(
        self, input_path: Path, output_dir: Path, fmt: str
    ) -> Path:
        """Convert input → output format using soffice."""
        self._run_soffice([
            f"--convert-to", fmt,
            "--outdir", str(output_dir),
            str(input_path),
        ])
        # soffice generates: output_dir / input.stem.fmt
        out = output_dir / f"{input_path.stem}.{fmt}"
        return out


# ============ Word ============

class LibreOfficeWordAdapter(_LibreOfficeMixin, WordAdapter):
    """Word adapter using LibreOffice subprocess."""

    _backend_type = BACKEND_TYPE

    def open_document(self, path: Path) -> DocumentHandle:
        path = Path(path)
        handle = DocumentHandle(path=path, backend_type=BACKEND_TYPE)
        self._open_handles[str(path)] = handle
        return handle

    def save_as(
        self, doc: DocumentHandle, target_path: Path, format: str | None = None
    ) -> DocumentHandle:
        target_path = Path(target_path)
        fmt = format or target_path.suffix.lstrip(".")
        # Convert to target format via soffice
        out = self._convert_via_soffice(
            doc.path, target_path.parent, fmt
        )
        # Rename if needed
        if out != target_path:
            shutil.move(str(out), str(target_path))
        return DocumentHandle(path=target_path, backend_type=BACKEND_TYPE)

    def export_pdf(
        self, doc: DocumentHandle, output_path: Path | None = None
    ) -> Path:
        output_path = Path(output_path or doc.path.with_suffix(".pdf"))
        return self._convert_via_soffice(
            doc.path, output_path.parent, "pdf"
        )

    def extract_text(self, doc: DocumentHandle) -> str:
        # Convert to txt via soffice, then read
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            txt_file = self._convert_via_soffice(doc.path, tmp, "txt")
            return txt_file.read_text(encoding="utf-8", errors="replace")

    def extract_tables(self, doc: DocumentHandle) -> list[pd.DataFrame]:
        # Convert to csv via soffice
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            csv_file = self._convert_via_soffice(doc.path, tmp, "csv")
            try:
                df = pd.read_csv(csv_file)
                return [df] if not df.empty else []
            except Exception:
                return []

    def close(self, doc: DocumentHandle) -> None:
        self._open_handles.pop(str(doc.path), None)

    def insert_text(
        self, doc: DocumentHandle, text: str, position: str = "end"
    ) -> None:
        raise NotImplementedError(
            "LibreOffice backend does not support content editing. "
            "Use OpenXML or Win32 backend."
        )

    def replace_text(self, doc: DocumentHandle, old: str, new: str) -> int:
        raise NotImplementedError(
            "LibreOffice backend does not support content editing."
        )

    def add_table(
        self,
        doc: DocumentHandle,
        rows: int,
        cols: int,
        data: list[list] | None = None,
    ) -> int:
        raise NotImplementedError(
            "LibreOffice backend does not support content editing."
        )

    def get_comments(self, doc: DocumentHandle) -> list[dict]:
        return []  # Not supported via headless


# ============ Excel ============

class LibreOfficeExcelAdapter(_LibreOfficeMixin, ExcelAdapter):
    """Excel adapter using LibreOffice subprocess."""

    _backend_type = BACKEND_TYPE

    def open_document(self, path: Path) -> DocumentHandle:
        path = Path(path)
        handle = DocumentHandle(path=path, backend_type=BACKEND_TYPE)
        self._open_handles[str(path)] = handle
        return handle

    def save_as(
        self, doc: DocumentHandle, target_path: Path, format: str | None = None
    ) -> DocumentHandle:
        target_path = Path(target_path)
        fmt = format or target_path.suffix.lstrip(".")
        out = self._convert_via_soffice(
            doc.path, target_path.parent, fmt
        )
        if out != target_path:
            shutil.move(str(out), str(target_path))
        return DocumentHandle(path=target_path, backend_type=BACKEND_TYPE)

    def export_pdf(
        self, doc: DocumentHandle, output_path: Path | None = None
    ) -> Path:
        output_path = Path(output_path or doc.path.with_suffix(".pdf"))
        return self._convert_via_soffice(
            doc.path, output_path.parent, "pdf"
        )

    def extract_text(self, doc: DocumentHandle) -> str:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            csv_file = self._convert_via_soffice(doc.path, tmp, "csv")
            return csv_file.read_text(encoding="utf-8", errors="replace")

    def extract_tables(self, doc: DocumentHandle) -> list[pd.DataFrame]:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            csv_file = self._convert_via_soffice(doc.path, tmp, "csv")
            try:
                df = pd.read_csv(csv_file)
                return [df] if not df.empty else []
            except Exception:
                return []

    def close(self, doc: DocumentHandle) -> None:
        self._open_handles.pop(str(doc.path), None)

    def read_range(self, doc: DocumentHandle, range_str: str) -> pd.DataFrame:
        dfs = self.extract_tables(doc)
        return dfs[0] if dfs else pd.DataFrame()

    def write_range(
        self, doc: DocumentHandle, range_str: str, data: pd.DataFrame
    ) -> None:
        raise NotImplementedError(
            "LibreOffice backend does not support content editing."
        )

    def add_chart(
        self, doc: DocumentHandle, data_range: str, chart_type: str, position: str
    ) -> None:
        raise NotImplementedError("LibreOffice backend does not support charts.")

    def create_pivot(
        self, doc: DocumentHandle, source_range: str,
        rows: list[str], values: list[str],
    ) -> None:
        raise NotImplementedError("LibreOffice backend does not support pivots.")

    def apply_formula(
        self, doc: DocumentHandle, cell: str, formula: str
    ) -> None:
        raise NotImplementedError("LibreOffice backend does not support formulas.")


# ============ PowerPoint ============

class LibreOfficePPTAdapter(_LibreOfficeMixin, PPTAdapter):
    """PowerPoint adapter using LibreOffice subprocess."""

    _backend_type = BACKEND_TYPE

    def open_document(self, path: Path) -> DocumentHandle:
        path = Path(path)
        handle = DocumentHandle(path=path, backend_type=BACKEND_TYPE)
        self._open_handles[str(path)] = handle
        return handle

    def save_as(
        self, doc: DocumentHandle, target_path: Path, format: str | None = None
    ) -> DocumentHandle:
        target_path = Path(target_path)
        fmt = format or target_path.suffix.lstrip(".")
        out = self._convert_via_soffice(
            doc.path, target_path.parent, fmt
        )
        if out != target_path:
            shutil.move(str(out), str(target_path))
        return DocumentHandle(path=target_path, backend_type=BACKEND_TYPE)

    def export_pdf(
        self, doc: DocumentHandle, output_path: Path | None = None
    ) -> Path:
        output_path = Path(output_path or doc.path.with_suffix(".pdf"))
        return self._convert_via_soffice(
            doc.path, output_path.parent, "pdf"
        )

    def extract_text(self, doc: DocumentHandle) -> str:
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            txt_file = self._convert_via_soffice(doc.path, tmp, "txt")
            return txt_file.read_text(encoding="utf-8", errors="replace")

    def extract_tables(self, doc: DocumentHandle) -> list[pd.DataFrame]:
        return []  # Headless PPT table extraction not reliable

    def close(self, doc: DocumentHandle) -> None:
        self._open_handles.pop(str(doc.path), None)

    def add_slide(self, doc: DocumentHandle, layout: str = "blank") -> int:
        raise NotImplementedError(
            "LibreOffice backend does not support content editing."
        )

    def add_text_box(
        self, doc: DocumentHandle, slide_index: int, text: str,
        position: tuple[float, float, float, float] | None = None,
    ) -> None:
        raise NotImplementedError(
            "LibreOffice backend does not support content editing."
        )

    def add_image(
        self, doc: DocumentHandle, slide_index: int, image_path: Path,
        position: tuple[float, float, float, float] | None = None,
    ) -> None:
        raise NotImplementedError(
            "LibreOffice backend does not support content editing."
        )
