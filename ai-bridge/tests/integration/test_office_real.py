"""Integration Tests — Office 真实文档操作 (L2)

Phase IV v1.0.0 — 使用 OpenXML 后端进行 Word/Excel/PPT 集成测试。
标记为 @pytest.mark.integration，需要 --integration 标志运行。
"""

from __future__ import annotations

import pytest
from pathlib import Path

import pandas as pd

from aibridge.adapters.office.factory import (
    create_word_adapter,
    create_excel_adapter,
    create_ppt_adapter,
)


@pytest.mark.integration
class TestOfficeReal:
    """Office 文档集成测试 — OpenXML 后端"""

    def test_create_docx_write_and_read(self, tmp_path: Path):
        """创建 Word 文档 → 写入内容 → 保存 → 重开验证"""
        adapter = create_word_adapter(backend="openxml")
        doc_path = tmp_path / "integration_test.docx"

        doc = adapter.open_document(doc_path)
        adapter.insert_text(doc, "AI-Bridge Integration Test")
        adapter.close(doc)

        doc2 = adapter.open_document(doc_path)
        text = adapter.extract_text(doc2)
        assert "AI-Bridge" in text
        adapter.close(doc2)

    def test_export_pdf_from_docx(self, tmp_path: Path):
        """Word 文档导出为 PDF"""
        adapter = create_word_adapter(backend="openxml")
        doc_path = tmp_path / "test.docx"

        doc = adapter.open_document(doc_path)
        adapter.insert_text(doc, "PDF Export Test")
        adapter.close(doc)

        pdf_path = adapter.convert_to(doc_path, "pdf", tmp_path / "output.pdf")
        assert pdf_path.suffix == ".pdf"

    def test_excel_write_and_read(self, tmp_path: Path):
        """Excel 写入数据 → 读取表格验证"""
        adapter = create_excel_adapter(backend="openxml")
        doc_path = tmp_path / "test.xlsx"

        doc = adapter.open_document(doc_path)
        adapter.write_range(doc, "A1:B3", pd.DataFrame({
            "Name": ["Alice", "Bob", "Charlie"],
            "Score": [95, 87, 92],
        }))
        tables = adapter.extract_tables(doc)
        assert len(tables) >= 1
        df = tables[0]
        assert df.iloc[0, 0] == "Alice"
        assert df.iloc[0, 1] == 95
        adapter.close(doc)

    def test_ppt_add_slide_and_text(self, tmp_path: Path):
        """PPT 添加幻灯片和文本框"""
        adapter = create_ppt_adapter(backend="openxml")
        doc_path = tmp_path / "test.pptx"

        doc = adapter.open_document(doc_path)
        adapter.add_slide(doc, layout_index=0)
        adapter.add_text_box(doc, slide_index=0, text="Phase IV Integration", left=1, top=1, width=8, height=2)
        text = adapter.extract_text(doc)
        assert "Phase IV Integration" in text
        adapter.close(doc)
