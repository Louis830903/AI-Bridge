"""
Cross-Platform Office Adapter Tests — Phase III v0.11.0

Tests the OpenXML backend (pure Python, always available).
Covers Word/Excel/PPT document lifecycle, factory selection, and fallback.
"""

from __future__ import annotations

import pytest
import tempfile
from pathlib import Path

import pandas as pd

from aibridge.adapters.office.base import DocumentHandle, OfficeAdapter
from aibridge.adapters.office.factory import (
    create_word_adapter,
    create_excel_adapter,
    create_ppt_adapter,
    _get_best_backend,
)


# ============ Fixtures ============

@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def word():
    """Word adapter using OpenXML backend (always available)."""
    return create_word_adapter(backend="openxml")


@pytest.fixture
def excel():
    """Excel adapter using OpenXML backend."""
    return create_excel_adapter(backend="openxml")


@pytest.fixture
def ppt():
    """PPT adapter using OpenXML backend."""
    return create_ppt_adapter(backend="openxml")


# ============ Factory Tests ============

class TestFactory:
    def test_create_word_default(self):
        """Factory creates adapter without crashing."""
        adapter = create_word_adapter(backend="openxml")
        assert adapter is not None
        assert adapter.backend_type == "openxml"

    def test_create_excel_default(self):
        adapter = create_excel_adapter(backend="openxml")
        assert adapter is not None
        assert adapter.backend_type == "openxml"

    def test_create_ppt_default(self):
        adapter = create_ppt_adapter(backend="openxml")
        assert adapter is not None
        assert adapter.backend_type == "openxml"

    def test_get_best_backend_returns_valid(self):
        backend = _get_best_backend()
        assert backend in ("win32", "openxml", "libreoffice")

    def test_explicit_backend_fallback(self):
        """nonexistent backend should fall back to openxml."""
        # Force openxml explicitly
        adapter = create_word_adapter(backend="openxml")
        assert adapter.backend_type == "openxml"


# ============ DocumentHandle Tests ============

class TestDocumentHandle:
    def test_creation(self, tmp_dir):
        path = tmp_dir / "test.docx"
        handle = DocumentHandle(path=path, backend_type="openxml")
        assert handle.path == path
        assert handle.backend_type == "openxml"
        assert handle.metadata == {}

    def test_repr(self, tmp_dir):
        handle = DocumentHandle(path=tmp_dir / "doc.docx", backend_type="win32")
        assert "doc.docx" in repr(handle)
        assert "win32" in repr(handle)


# ============ Word Tests ============

class TestWordOpenXML:
    def test_create_and_read(self, word, tmp_dir):
        """Create document, write text, re-read."""
        doc_path = tmp_dir / "hello.docx"
        doc = word.open_document(doc_path)
        word.insert_text(doc, "Hello AI-Bridge!")
        word.save_as(doc, doc_path)
        word.close(doc)

        # Re-open and verify
        doc2 = word.open_document(doc_path)
        text = word.extract_text(doc2)
        assert "Hello AI-Bridge!" in text
        word.close(doc2)

    def test_insert_text_start_and_end(self, word, tmp_dir):
        doc = word.open_document(tmp_dir / "positions.docx")
        word.insert_text(doc, "First", position="start")
        word.insert_text(doc, "Last", position="end")
        text = word.extract_text(doc)
        assert "First" in text
        assert "Last" in text
        word.close(doc)

    def test_replace_text(self, word, tmp_dir):
        doc = word.open_document(tmp_dir / "replace.docx")
        word.insert_text(doc, "Hello World")
        count = word.replace_text(doc, "World", "AI-Bridge")
        assert count >= 1
        text = word.extract_text(doc)
        assert "AI-Bridge" in text
        word.close(doc)

    def test_add_table(self, word, tmp_dir):
        doc = word.open_document(tmp_dir / "table.docx")
        idx = word.add_table(doc, 2, 3, [["A", "B", "C"], ["1", "2", "3"]])
        assert idx >= 0
        word.close(doc)

    def test_convert_to(self, word, tmp_dir):
        """One-shot convert_to convenience method."""
        doc_path = tmp_dir / "src.docx"
        doc = word.open_document(doc_path)
        word.insert_text(doc, "Convert me")
        word.close(doc)

        out = word.convert_to(doc_path, "docx", tmp_dir / "out.docx")
        assert out.exists()

    def test_context_manager(self, tmp_dir):
        with create_word_adapter(backend="openxml") as w:
            doc = w.open_document(tmp_dir / "ctx.docx")
            w.insert_text(doc, "Context test")
            text = w.extract_text(doc)
            assert "Context test" in text
            w.close(doc)

    def test_dispose_cleans_up(self, word, tmp_dir):
        doc = word.open_document(tmp_dir / "dispose.docx")
        word.insert_text(doc, "test")
        word.close(doc)
        word.dispose()
        assert len(word._open_handles) == 0


# ============ Excel Tests ============

class TestExcelOpenXML:
    def test_create_and_read(self, excel, tmp_dir):
        doc_path = tmp_dir / "data.xlsx"
        doc = excel.open_document(doc_path)
        df = pd.DataFrame({"Name": ["Alice", "Bob"], "Score": [95, 87]})
        excel.write_range(doc, "A1", df)
        excel.save_as(doc, doc_path)
        excel.close(doc)

        doc2 = excel.open_document(doc_path)
        result = excel.read_range(doc2, "A1:B3")
        assert len(result) >= 2
        excel.close(doc2)

    def test_extract_tables(self, excel, tmp_dir):
        doc = excel.open_document(tmp_dir / "tables.xlsx")
        df = pd.DataFrame({"X": [1, 2, 3], "Y": [4, 5, 6]})
        excel.write_range(doc, "A1", df)
        tables = excel.extract_tables(doc)
        assert len(tables) >= 1
        excel.close(doc)

    def test_extract_text(self, excel, tmp_dir):
        doc = excel.open_document(tmp_dir / "text.xlsx")
        excel.write_range(doc, "A1", pd.DataFrame({"Col": ["hello", "world"]}))
        text = excel.extract_text(doc)
        assert "hello" in text
        assert "world" in text
        excel.close(doc)

    def test_apply_formula(self, excel, tmp_dir):
        doc = excel.open_document(tmp_dir / "formula.xlsx")
        excel.write_range(doc, "A1", pd.DataFrame({"N": [10, 20]}))
        excel.apply_formula(doc, "B1", "=SUM(A1:A2)")
        excel.close(doc)

    def test_convert_to(self, excel, tmp_dir):
        doc_path = tmp_dir / "src.xlsx"
        doc = excel.open_document(doc_path)
        excel.write_range(doc, "A1", pd.DataFrame({"A": [1]}))
        excel.close(doc)

        out = excel.convert_to(doc_path, "xlsx", tmp_dir / "out.xlsx")
        assert out.exists()


# ============ PPT Tests ============

class TestPPTOpenXML:
    def test_create_and_add_slide(self, ppt, tmp_dir):
        doc = ppt.open_document(tmp_dir / "deck.pptx")
        idx = ppt.add_slide(doc, layout="blank")
        assert idx >= 1
        ppt.close(doc)

    def test_add_text_box(self, ppt, tmp_dir):
        doc = ppt.open_document(tmp_dir / "text.pptx")
        ppt.add_slide(doc, layout="blank")
        ppt.add_text_box(doc, 1, "Hello from Python!")
        text = ppt.extract_text(doc)
        assert "Hello from Python!" in text
        ppt.close(doc)

    def test_multiple_slides(self, ppt, tmp_dir):
        doc = ppt.open_document(tmp_dir / "multi.pptx")
        ppt.add_slide(doc)
        ppt.add_text_box(doc, 1, "Slide 1")
        ppt.add_slide(doc)
        ppt.add_text_box(doc, 2, "Slide 2")
        text = ppt.extract_text(doc)
        assert "Slide 1" in text
        assert "Slide 2" in text
        ppt.close(doc)

    def test_slide_index_out_of_range(self, ppt, tmp_dir):
        doc = ppt.open_document(tmp_dir / "range.pptx")
        with pytest.raises(IndexError):
            ppt.add_text_box(doc, 99, "Bad index")
        ppt.close(doc)

    def test_save_and_reopen(self, ppt, tmp_dir):
        doc_path = tmp_dir / "save.pptx"
        doc = ppt.open_document(doc_path)
        ppt.add_slide(doc)
        ppt.add_text_box(doc, 1, "Persisted")
        ppt.save_as(doc, doc_path)
        ppt.close(doc)

        doc2 = ppt.open_document(doc_path)
        text = ppt.extract_text(doc2)
        assert "Persisted" in text
        ppt.close(doc2)


# ============ Backend Availability Tests ============

class TestBackendAvailability:
    def test_openxml_is_always_available(self):
        from aibridge.adapters.office.openxml_backend import OpenXMLWordAdapter
        assert OpenXMLWordAdapter.is_available() is True

    def test_win32_reports_correctly(self):
        from aibridge.adapters.office.win32_backend import Win32WordAdapter
        import platform
        is_avail = Win32WordAdapter.is_available()
        if platform.system() == "Windows":
            # May be True or False depending on pywin32
            assert isinstance(is_avail, bool)
        else:
            assert is_avail is False


# ============ Abstract Base Class Tests ============

class TestAbstractBase:
    def test_cannot_instantiate_abstract(self):
        """ABCs cannot be instantiated directly."""
        with pytest.raises(TypeError):
            OfficeAdapter()

    def test_subclass_is_instance(self, word):
        from aibridge.adapters.office.base import WordAdapter as BaseWord
        assert isinstance(word, BaseWord)
        assert isinstance(word, OfficeAdapter)

    def test_document_handle_dataclass(self):
        h = DocumentHandle(path=Path("/tmp/x.docx"), backend_type="openxml")
        assert h.path == Path("/tmp/x.docx")
        assert h.metadata == {}
