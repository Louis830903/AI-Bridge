"""
WPS Adapter - WPS Office automation via COM
Glue code wrapping pywin32 - WPS is COM-compatible with MS Office
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


class WPSWriterAdapter(SyncBaseAdapter):
    """
    WPS文字适配器 - 通过COM接口进行文档操作
    
    WPS的COM接口与MS Office高度兼容，大部分代码可复用。
    ProgID: Kwps.Application
    """
    
    info = AdapterInfo(
        id="wps_writer",
        name="WPS文字",
        type=AdapterType.OFFICE,
        version="1.0.0",
        platforms=["windows"],
        actions=[
            "create", "open", "save", "close", "read", "write",
            "export", "list_elements"
        ],
        description="WPS文字 automation via COM",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.visible = self.config.get("visible", True)
        self._app = None
        self._doc = None
    
    def connect(self) -> bool:
        """连接WPS文字"""
        try:
            w32 = get_win32com()
            self._app = w32.Dispatch("Kwps.Application")
            self._app.Visible = self.visible
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to WPS Writer: {e}")
    
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
        """检查WPS是否可用"""
        try:
            w32 = get_win32com()
            app = w32.Dispatch("Kwps.Application")
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
        """执行WPS操作"""
        target = target or {}
        logger.debug(f"WPS Writer executing action: {action}")
        
        try:
            if action == "create":
                self._doc = self._app.Documents.Add()
                content = value or target.get("content")
                if content:
                    self._doc.Content.Text = content
                path = target.get("path")
                if path:
                    self._doc.SaveAs(path)
                return {"success": True}
            
            elif action == "open":
                path = target.get("path") or value
                if not path:
                    return {"success": False, "error": "path is required"}
                self._doc = self._app.Documents.Open(path)
                return {"success": True}
            
            elif action == "save":
                if not self._doc:
                    return {"success": False, "error": "No document open"}
                path = target.get("path") or value
                if path:
                    self._doc.SaveAs(path)
                else:
                    self._doc.Save()
                return {"success": True}
            
            elif action == "close":
                if self._doc:
                    self._doc.Close(False)
                    self._doc = None
                return {"success": True}
            
            elif action == "read":
                if not self._doc:
                    return {"success": False, "error": "No document open"}
                return {"success": True, "data": self._doc.Content.Text}
            
            elif action == "write":
                if not self._doc:
                    return {"success": False, "error": "No document open"}
                content = value if isinstance(value, str) else str(value)
                position = target.get("position", "end")
                if position == "end":
                    self._doc.Content.InsertAfter(content)
                elif position == "start":
                    self._doc.Content.InsertBefore(content)
                else:
                    self._doc.Content.Text = content
                return {"success": True}
            
            elif action == "export":
                if not self._doc:
                    return {"success": False, "error": "No document open"}
                path = target.get("path") or value
                if not path:
                    return {"success": False, "error": "path is required"}
                self._doc.SaveAs(path, FileFormat=17)  # PDF
                return {"success": True}
            
            elif action == "list_elements":
                if not self._doc:
                    return {"success": False, "error": "No document open"}
                elements = []
                for i, para in enumerate(self._doc.Paragraphs):
                    if i >= 20:
                        break
                    text = para.Range.Text.strip()
                    if text:
                        elements.append({"type": "paragraph", "index": i, "text": text[:100]})
                return {"success": True, "elements": elements}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"WPS Writer action '{action}' failed: {e}")
            return {"success": False, "error": str(e)}


class WPSSpreadsheetAdapter(SyncBaseAdapter):
    """
    WPS表格适配器 - 通过COM接口进行表格操作
    
    ProgID: Ket.Application
    """
    
    info = AdapterInfo(
        id="wps_spreadsheet",
        name="WPS表格",
        type=AdapterType.OFFICE,
        version="1.0.0",
        platforms=["windows"],
        actions=[
            "create", "open", "save", "close", "read", "write",
            "read_range", "write_range", "list_elements", "export"
        ],
        description="WPS表格 automation via COM",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.visible = self.config.get("visible", True)
        self._app = None
        self._workbook = None
    
    def connect(self) -> bool:
        """连接WPS表格"""
        try:
            w32 = get_win32com()
            self._app = w32.Dispatch("Ket.Application")
            self._app.Visible = self.visible
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to WPS Spreadsheet: {e}")
    
    def disconnect(self) -> bool:
        """断开连接"""
        try:
            if self._workbook:
                self._workbook.Close(False)
            if self._app:
                self._app.Quit()
            self._connected = False
            return True
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """检查WPS是否可用"""
        try:
            w32 = get_win32com()
            app = w32.Dispatch("Ket.Application")
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
        """执行WPS表格操作"""
        target = target or {}
        logger.debug(f"WPS Spreadsheet executing action: {action}")
        
        try:
            if action == "create":
                self._workbook = self._app.Workbooks.Add()
                path = target.get("path")
                if path:
                    self._workbook.SaveAs(path)
                return {"success": True}
            
            elif action == "open":
                path = target.get("path") or target.get("file") or value
                if not path:
                    return {"success": False, "error": "path is required"}
                self._workbook = self._app.Workbooks.Open(path)
                return {"success": True}
            
            elif action == "save":
                if not self._workbook:
                    return {"success": False, "error": "No workbook open"}
                path = target.get("path") or value
                if path:
                    self._workbook.SaveAs(path)
                else:
                    self._workbook.Save()
                return {"success": True}
            
            elif action == "close":
                if self._workbook:
                    self._workbook.Close(False)
                    self._workbook = None
                return {"success": True}
            
            elif action == "read":
                if not self._workbook:
                    return {"success": False, "error": "No workbook open"}
                sheet = target.get("sheet", "Sheet1")
                cell = target.get("cell") or value
                if not cell:
                    return {"success": False, "error": "cell is required"}
                val = self._workbook.Sheets(sheet).Range(cell).Value
                return {"success": True, "data": val}
            
            elif action == "write":
                if not self._workbook:
                    return {"success": False, "error": "No workbook open"}
                sheet = target.get("sheet", "Sheet1")
                cell = target.get("cell")
                if not cell:
                    return {"success": False, "error": "cell is required"}
                self._workbook.Sheets(sheet).Range(cell).Value = value
                return {"success": True}
            
            elif action == "list_elements":
                if not self._workbook:
                    return {"success": False, "error": "No workbook open"}
                elements = []
                for i, sheet in enumerate(self._workbook.Sheets):
                    used_range = sheet.UsedRange
                    elements.append({
                        "type": "sheet",
                        "index": i,
                        "name": sheet.Name,
                        "rows": used_range.Rows.Count,
                        "columns": used_range.Columns.Count
                    })
                return {"success": True, "elements": elements}
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"WPS Spreadsheet action '{action}' failed: {e}")
            return {"success": False, "error": str(e)}
