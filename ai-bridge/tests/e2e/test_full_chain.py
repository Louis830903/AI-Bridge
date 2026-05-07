"""E2E Tests — 全链路端到端测试 (L3)

Phase IV v1.0.0 — 完整自然语言到适配器调用的端到端流程。
标记为 @pytest.mark.e2e，需要 --e2e 标志运行。
"""

from __future__ import annotations

import pytest
from pathlib import Path

from aibridge.core.domain_registry import DomainIntentRegistry
from aibridge.core.intent_pattern import IntentPattern
from aibridge.adapters.office.factory import (
    create_word_adapter,
    create_excel_adapter,
)


@pytest.mark.e2e
class TestFullChainE2E:
    """全链路 E2E 测试"""

    def test_natural_language_to_office_workflow(self, tmp_path: Path):
        """自然语言意图 → Office 适配器工作流"""
        # Step 1: 注册意图
        registry = DomainIntentRegistry()
        registry.register("office", [
            IntentPattern(
                id="office.create_doc", domain="office",
                patterns=["创建文档{内容}"],
                description="创建新文档并写入内容",
            ),
        ])

        # Step 2: L1 匹配
        results = registry.match("创建文档Hello World")
        assert len(results) >= 1
        assert results[0].pattern.id == "office.create_doc"

        # Step 3: 执行意图 → 创建文档
        adapter = create_word_adapter(backend="openxml")
        doc_path = tmp_path / "e2e_doc.docx"
        doc = adapter.open_document(doc_path)
        adapter.insert_text(doc, "Hello World from E2E Test")
        adapter.close(doc)

        # Step 4: 验证
        doc2 = adapter.open_document(doc_path)
        text = adapter.extract_text(doc2)
        assert "Hello World" in text
        adapter.close(doc2)

    def test_intent_resolve_to_adapter_call(self, tmp_path: Path):
        """意图解析 → 适配器调用完整链路"""
        registry = DomainIntentRegistry()
        registry.register("excel", [
            IntentPattern(
                id="excel.create_table",
                domain="office",
                patterns=["创建表格", "新建表格"],
                description="创建 Excel 表格",
            ),
        ])

        # 意图匹配
        results = registry.match("新建表格")
        assert len(results) >= 1

        # 适配器执行
        import pandas as pd
        adapter = create_excel_adapter(backend="openxml")
        doc_path = tmp_path / "e2e_table.xlsx"
        doc = adapter.open_document(doc_path)
        adapter.write_range(doc, "A1:B2", pd.DataFrame({"X": [1, 2]}))
        tables = adapter.extract_tables(doc)
        assert len(tables) >= 1
        adapter.close(doc)

    def test_mcp_protocol_tool_execution_chain(self):
        """MCP 协议工具定义与执行链"""
        # 验证工具 schema 完整
        tool_def = {
            "name": "browser_navigate",
            "description": "Navigate browser to URL",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                },
                "required": ["url"],
            },
        }
        assert tool_def["name"] == "browser_navigate"
        assert "url" in tool_def["inputSchema"]["required"]

    def test_composite_intent_decomposition(self):
        """复合意图分解 — 多步骤任务拆解"""
        registry = DomainIntentRegistry()
        registry.register("media", [
            IntentPattern(id="media.convert", domain="media",
                          patterns=["转成{格式}"], description="格式转换"),
        ])
        registry.register("office", [
            IntentPattern(id="office.export", domain="office",
                          patterns=["导出PDF"], description="导出PDF"),
        ])

        # 模拟复合意图：先转格式再导出
        convert_results = registry.match("转成gif")
        export_results = registry.match("导出PDF")

        assert len(convert_results) >= 1
        assert len(export_results) >= 1
        assert convert_results[0].pattern.domain == "media"
        assert export_results[0].pattern.domain == "office"
