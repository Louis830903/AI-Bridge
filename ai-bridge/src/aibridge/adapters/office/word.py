"""
Word Adapter - Microsoft Word automation via COM
Glue code wrapping pywin32
"""

import logging
from typing import Any, Dict, Optional
from aibridge.adapters.base import SyncBaseAdapter, AdapterInfo, AdapterType

logger = logging.getLogger(__name__)

# Lazy import
win32com = None


def get_win32com():
    global win32com
    if win32com is None:
        import win32com.client as w32
        win32com = w32
    return win32com


class WordAdapter(SyncBaseAdapter):
    """
    Microsoft Word适配器 - 通过COM接口进行文档操作
    
    这是胶水代码，封装 pywin32 的 COM 接口。
    """
    
    info = AdapterInfo(
        id="word",
        name="Microsoft Word",
        type=AdapterType.OFFICE,
        version="1.0.0",
        platforms=["windows"],
        actions=[
            "create", "open", "save", "close", "read", "write",
            "export", "list_elements"
        ],
        description="Microsoft Word automation via COM",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.visible = self.config.get("visible", True)
        self._app = None
        self._doc = None
    
    def connect(self) -> bool:
        """连接Word应用"""
        try:
            w32 = get_win32com()
            self._app = w32.Dispatch("Word.Application")
            self._app.Visible = self.visible
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to Word: {e}")
    
    def disconnect(self) -> bool:
        """断开连接"""
        try:
            if self._doc:
                self._doc.Close(False)
            if self._app:
                self._app.Quit()
            self._connected = False
            return True
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """检查Word是否可用"""
        try:
            w32 = get_win32com()
            app = w32.Dispatch("Word.Application")
            app.Quit()
            return True
        except Exception:
            return False
    
    def execute(
        self,
        action: str,
        target: Optional[Dict[str, Any]] = None,
        value: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """执行Word操作"""
        target = target or {}
        logger.debug(f"Word executing action: {action}")
        
        try:
            if action == "create":
                return self._create(target, value)
            
            elif action == "open":
                path = target.get("path") or value
                return self._open(path)
            
            elif action == "save":
                path = target.get("path") or value
                return self._save(path)
            
            elif action == "close":
                return self._close()
            
            elif action == "read":
                return self._read()
            
            elif action == "write":
                return self._write(target, value)
            
            elif action == "export":
                path = target.get("path") or value
                format_type = target.get("format", "pdf")
                return self._export(path, format_type)
            
            elif action == "list_elements":
                return self._list_elements()
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Word action '{action}' failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _create(self, target: Dict, value: Any) -> Dict[str, Any]:
        """创建新文档"""
        self._doc = self._app.Documents.Add()
        
        content = value or target.get("content")
        if content:
            self._doc.Content.Text = content
        
        path = target.get("path")
        if path:
            self._doc.SaveAs(path)
        
        return {"success": True}
    
    def _open(self, path: str) -> Dict[str, Any]:
        """打开文档"""
        if not path:
            return {"success": False, "error": "path is required"}
        
        self._doc = self._app.Documents.Open(path)
        return {"success": True}
    
    def _save(self, path: Optional[str] = None) -> Dict[str, Any]:
        """保存文档"""
        if not self._doc:
            return {"success": False, "error": "No document open"}
        
        if path:
            self._doc.SaveAs(path)
        else:
            self._doc.Save()
        return {"success": True}
    
    def _close(self) -> Dict[str, Any]:
        """关闭文档"""
        if self._doc:
            self._doc.Close(False)
            self._doc = None
        return {"success": True}
    
    def _read(self) -> Dict[str, Any]:
        """读取文档内容"""
        if not self._doc:
            return {"success": False, "error": "No document open"}
        
        text = self._doc.Content.Text
        return {"success": True, "data": text}
    
    def _write(self, target: Dict, value: Any) -> Dict[str, Any]:
        """写入内容"""
        if not self._doc:
            return {"success": False, "error": "No document open"}
        
        content = value if isinstance(value, str) else str(value)
        position = target.get("position", "end")
        
        if position == "end":
            # 在末尾追加
            self._doc.Content.InsertAfter(content)
        elif position == "start":
            # 在开头插入
            self._doc.Content.InsertBefore(content)
        else:
            # 替换全部内容
            self._doc.Content.Text = content
        
        return {"success": True}
    
    def _export(self, path: str, format_type: str) -> Dict[str, Any]:
        """导出文档"""
        if not self._doc:
            return {"success": False, "error": "No document open"}
        
        if not path:
            return {"success": False, "error": "path is required"}
        
        if format_type.lower() == "pdf":
            # 17 = wdFormatPDF
            self._doc.SaveAs(path, FileFormat=17)
        else:
            self._doc.SaveAs(path)
        
        return {"success": True}
    
    def _list_elements(self) -> Dict[str, Any]:
        """列出文档元素"""
        if not self._doc:
            return {"success": False, "error": "No document open"}
        
        elements = []
        
        # 段落
        for i, para in enumerate(self._doc.Paragraphs):
            if i >= 20:  # 限制数量
                break
            text = para.Range.Text.strip()
            if text:
                elements.append({
                    "type": "paragraph",
                    "index": i,
                    "text": text[:100]
                })
        
        # 表格
        for i, table in enumerate(self._doc.Tables):
            elements.append({
                "type": "table",
                "index": i,
                "rows": table.Rows.Count,
                "columns": table.Columns.Count
            })
        
        return {"success": True, "elements": elements}
