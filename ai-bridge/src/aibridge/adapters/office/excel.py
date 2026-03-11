"""
Excel Adapter - Microsoft Excel automation via COM
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


class ExcelAdapter(SyncBaseAdapter):
    """
    Microsoft Excel适配器 - 通过COM接口进行表格操作
    
    这是胶水代码，封装 pywin32 的 COM 接口。
    """
    
    info = AdapterInfo(
        id="excel",
        name="Microsoft Excel",
        type=AdapterType.OFFICE,
        version="1.0.0",
        platforms=["windows"],
        actions=[
            "create", "open", "save", "close", "read", "write",
            "read_range", "write_range", "list_elements", "export"
        ],
        description="Microsoft Excel automation via COM",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.visible = self.config.get("visible", True)
        self._app = None
        self._workbook = None
    
    def connect(self) -> bool:
        """连接Excel应用"""
        try:
            w32 = get_win32com()
            self._app = w32.Dispatch("Excel.Application")
            self._app.Visible = self.visible
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to Excel: {e}")
    
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
            self._connected = False
            return False
    
    def is_available(self) -> bool:
        """检查Excel是否可用"""
        try:
            w32 = get_win32com()
            app = w32.Dispatch("Excel.Application")
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
        """执行Excel操作"""
        target = target or {}
        logger.debug(f"Excel executing action: {action}")
        
        try:
            if action == "create":
                return self._create(target, value)
            
            elif action == "open":
                path = target.get("path") or target.get("file") or value
                return self._open(path)
            
            elif action == "save":
                path = target.get("path") or value
                return self._save(path)
            
            elif action == "close":
                return self._close()
            
            elif action == "read":
                return self._read_cell(target, value)
            
            elif action == "write":
                return self._write_cell(target, value)
            
            elif action == "read_range":
                return self._read_range(target)
            
            elif action == "write_range":
                return self._write_range(target, value)
            
            elif action == "list_elements":
                return self._list_elements()
            
            elif action == "export":
                path = target.get("path") or value
                return self._export(path)
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Excel action '{action}' failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _create(self, target: Dict, value: Any) -> Dict[str, Any]:
        """创建新工作簿"""
        self._workbook = self._app.Workbooks.Add()
        
        path = target.get("path")
        if path:
            self._workbook.SaveAs(path)
        
        return {"success": True}
    
    def _open(self, path: str) -> Dict[str, Any]:
        """打开工作簿"""
        if not path:
            return {"success": False, "error": "path is required"}
        
        self._workbook = self._app.Workbooks.Open(path)
        return {"success": True}
    
    def _save(self, path: Optional[str] = None) -> Dict[str, Any]:
        """保存工作簿"""
        if not self._workbook:
            return {"success": False, "error": "No workbook open"}
        
        if path:
            self._workbook.SaveAs(path)
        else:
            self._workbook.Save()
        return {"success": True}
    
    def _close(self) -> Dict[str, Any]:
        """关闭工作簿"""
        if self._workbook:
            self._workbook.Close(False)
            self._workbook = None
        return {"success": True}
    
    def _read_cell(self, target: Dict, value: Any) -> Dict[str, Any]:
        """读取单元格"""
        if not self._workbook:
            return {"success": False, "error": "No workbook open"}
        
        sheet_name = target.get("sheet", "Sheet1")
        cell = target.get("cell") or value
        
        if not cell:
            return {"success": False, "error": "cell is required"}
        
        try:
            sheet = self._workbook.Sheets(sheet_name)
            cell_value = sheet.Range(cell).Value
            return {"success": True, "data": cell_value}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _write_cell(self, target: Dict, value: Any) -> Dict[str, Any]:
        """写入单元格"""
        if not self._workbook:
            return {"success": False, "error": "No workbook open"}
        
        sheet_name = target.get("sheet", "Sheet1")
        cell = target.get("cell")
        
        if not cell:
            return {"success": False, "error": "cell is required"}
        
        try:
            sheet = self._workbook.Sheets(sheet_name)
            sheet.Range(cell).Value = value
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _read_range(self, target: Dict) -> Dict[str, Any]:
        """读取范围"""
        if not self._workbook:
            return {"success": False, "error": "No workbook open"}
        
        sheet_name = target.get("sheet", "Sheet1")
        range_str = target.get("range", "A1:A10")
        
        try:
            sheet = self._workbook.Sheets(sheet_name)
            values = sheet.Range(range_str).Value
            
            # 转换为列表
            if values is None:
                data = []
            elif isinstance(values, tuple):
                data = [list(row) if isinstance(row, tuple) else [row] for row in values]
            else:
                data = [[values]]
            
            return {"success": True, "data": data}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _write_range(self, target: Dict, value: Any) -> Dict[str, Any]:
        """写入范围"""
        if not self._workbook:
            return {"success": False, "error": "No workbook open"}
        
        sheet_name = target.get("sheet", "Sheet1")
        range_str = target.get("range")
        
        if not range_str:
            return {"success": False, "error": "range is required"}
        
        try:
            sheet = self._workbook.Sheets(sheet_name)
            sheet.Range(range_str).Value = value
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _list_elements(self) -> Dict[str, Any]:
        """列出工作簿元素"""
        if not self._workbook:
            return {"success": False, "error": "No workbook open"}
        
        elements = []
        
        # 列出所有工作表
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
    
    def _export(self, path: str) -> Dict[str, Any]:
        """导出为PDF"""
        if not self._workbook:
            return {"success": False, "error": "No workbook open"}
        
        if not path:
            return {"success": False, "error": "path is required"}
        
        # 0 = xlTypePDF
        self._workbook.ExportAsFixedFormat(0, path)
        return {"success": True}
