"""
PowerPoint Adapter - Microsoft PowerPoint automation via COM
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


class PowerPointAdapter(SyncBaseAdapter):
    """
    Microsoft PowerPoint适配器 - 通过COM接口进行演示文稿操作
    """
    
    info = AdapterInfo(
        id="powerpoint",
        name="Microsoft PowerPoint",
        type=AdapterType.OFFICE,
        version="1.0.0",
        platforms=["windows"],
        actions=[
            "create", "open", "save", "close", "add_slide",
            "write", "read", "list_elements", "export"
        ],
        description="Microsoft PowerPoint automation via COM",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.visible = self.config.get("visible", True)
        self._app = None
        self._presentation = None
    
    def connect(self) -> bool:
        """连接PowerPoint应用"""
        try:
            w32 = get_win32com()
            self._app = w32.Dispatch("PowerPoint.Application")
            self._app.Visible = True  # PowerPoint必须可见
            self._connected = True
            return True
        except Exception as e:
            self._connected = False
            raise ConnectionError(f"Failed to connect to PowerPoint: {e}")
    
    def disconnect(self) -> bool:
        """断开连接"""
        try:
            if self._presentation:
                self._presentation.Close()
            if self._app:
                self._app.Quit()
            self._connected = False
            return True
        except Exception:
            return False
    
    def is_available(self) -> bool:
        """检查PowerPoint是否可用"""
        try:
            w32 = get_win32com()
            app = w32.Dispatch("PowerPoint.Application")
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
        """执行PowerPoint操作"""
        target = target or {}
        logger.debug(f"PowerPoint executing action: {action}")
        
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
            
            elif action == "add_slide":
                return self._add_slide(target, value)
            
            elif action == "write":
                return self._write(target, value)
            
            elif action == "read":
                return self._read(target)
            
            elif action == "list_elements":
                return self._list_elements()
            
            elif action == "export":
                path = target.get("path") or value
                return self._export(path)
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"PowerPoint action '{action}' failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _create(self, target: Dict, value: Any) -> Dict[str, Any]:
        """创建新演示文稿"""
        self._presentation = self._app.Presentations.Add()
        
        path = target.get("path")
        if path:
            self._presentation.SaveAs(path)
        
        return {"success": True}
    
    def _open(self, path: str) -> Dict[str, Any]:
        """打开演示文稿"""
        if not path:
            return {"success": False, "error": "path is required"}
        
        self._presentation = self._app.Presentations.Open(path)
        return {"success": True}
    
    def _save(self, path: Optional[str] = None) -> Dict[str, Any]:
        """保存演示文稿"""
        if not self._presentation:
            return {"success": False, "error": "No presentation open"}
        
        if path:
            self._presentation.SaveAs(path)
        else:
            self._presentation.Save()
        return {"success": True}
    
    def _close(self) -> Dict[str, Any]:
        """关闭演示文稿"""
        if self._presentation:
            self._presentation.Close()
            self._presentation = None
        return {"success": True}
    
    def _add_slide(self, target: Dict, value: Any) -> Dict[str, Any]:
        """添加幻灯片"""
        if not self._presentation:
            return {"success": False, "error": "No presentation open"}
        
        # 11 = ppLayoutTitleOnly, 12 = ppLayoutBlank
        layout = target.get("layout", 12)
        index = self._presentation.Slides.Count + 1
        
        slide = self._presentation.Slides.Add(index, layout)
        
        # 如果提供了标题，设置标题
        title = value or target.get("title")
        if title and slide.Shapes.HasTitle:
            slide.Shapes.Title.TextFrame.TextRange.Text = title
        
        return {"success": True, "data": {"index": index}}
    
    def _write(self, target: Dict, value: Any) -> Dict[str, Any]:
        """写入内容到幻灯片"""
        if not self._presentation:
            return {"success": False, "error": "No presentation open"}
        
        slide_index = target.get("slide", 1)
        content = value if isinstance(value, str) else str(value)
        
        if slide_index > self._presentation.Slides.Count:
            return {"success": False, "error": f"Slide {slide_index} does not exist"}
        
        slide = self._presentation.Slides(slide_index)
        
        # 添加文本框
        # 坐标: Left, Top, Width, Height (单位: points)
        left = target.get("left", 100)
        top = target.get("top", 100)
        width = target.get("width", 400)
        height = target.get("height", 200)
        
        textbox = slide.Shapes.AddTextbox(1, left, top, width, height)
        textbox.TextFrame.TextRange.Text = content
        
        return {"success": True}
    
    def _read(self, target: Dict) -> Dict[str, Any]:
        """读取幻灯片内容"""
        if not self._presentation:
            return {"success": False, "error": "No presentation open"}
        
        slide_index = target.get("slide", 1)
        
        if slide_index > self._presentation.Slides.Count:
            return {"success": False, "error": f"Slide {slide_index} does not exist"}
        
        slide = self._presentation.Slides(slide_index)
        texts = []
        
        for shape in slide.Shapes:
            if shape.HasTextFrame:
                text = shape.TextFrame.TextRange.Text
                if text.strip():
                    texts.append(text)
        
        return {"success": True, "data": "\n".join(texts)}
    
    def _list_elements(self) -> Dict[str, Any]:
        """列出演示文稿元素"""
        if not self._presentation:
            return {"success": False, "error": "No presentation open"}
        
        elements = []
        
        for i, slide in enumerate(self._presentation.Slides, 1):
            slide_info = {
                "type": "slide",
                "index": i,
                "shapes": slide.Shapes.Count
            }
            
            # 获取标题
            if slide.Shapes.HasTitle:
                slide_info["title"] = slide.Shapes.Title.TextFrame.TextRange.Text
            
            elements.append(slide_info)
        
        return {"success": True, "elements": elements}
    
    def _export(self, path: str) -> Dict[str, Any]:
        """导出为PDF"""
        if not self._presentation:
            return {"success": False, "error": "No presentation open"}
        
        if not path:
            return {"success": False, "error": "path is required"}
        
        # 32 = ppSaveAsPDF
        self._presentation.SaveAs(path, 32)
        return {"success": True}
