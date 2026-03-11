"""
Generic Desktop Adapter - Windows UI Automation
Glue code wrapping pywinauto
"""

import logging
import re
from typing import Any, Dict, List, Optional
from aibridge.adapters.base import SyncBaseAdapter, AdapterInfo, AdapterType

logger = logging.getLogger(__name__)

# Lazy import
pywinauto = None


def get_pywinauto():
    global pywinauto
    if pywinauto is None:
        from pywinauto import Application
        pywinauto = Application
    return pywinauto


class GenericDesktopAdapter(SyncBaseAdapter):
    """
    通用桌面应用适配器 - 通过Windows UI Automation操控任意桌面应用
    
    这是胶水代码，封装 pywinauto 库。
    支持两种后端：uia (UI Automation) 和 win32
    """
    
    info = AdapterInfo(
        id="desktop",
        name="通用桌面",
        type=AdapterType.DESKTOP,
        version="1.0.0",
        platforms=["windows"],
        actions=[
            "launch", "connect", "close", "click", "type",
            "read", "list_elements", "focus", "screenshot"
        ],
        description="Generic Windows desktop automation via UIA",
    )
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.backend = self.config.get("backend", "uia")  # uia or win32
        self._app = None
    
    def connect(self) -> bool:
        """初始化（不连接到特定应用）"""
        self._connected = True
        return True
    
    def disconnect(self) -> bool:
        """断开连接"""
        self._app = None
        self._connected = False
        return True
    
    def is_available(self) -> bool:
        """检查pywinauto是否可用"""
        try:
            get_pywinauto()
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
        """执行桌面操作"""
        target = target or {}
        logger.debug(f"Executing action: {action}, target: {target}")
        
        try:
            if action == "launch":
                return self._launch(target, value)
            
            elif action == "connect":
                return self._connect_app(target, value)
            
            elif action == "close":
                return self._close()
            
            elif action == "click":
                return self._click(target)
            
            elif action == "type":
                return self._type(target, value)
            
            elif action == "read":
                return self._read(target)
            
            elif action == "list_elements":
                return self._list_elements()
            
            elif action == "focus":
                return self._focus()
            
            elif action == "screenshot":
                return self._screenshot(target)
            
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
                
        except Exception as e:
            logger.error(f"Desktop action '{action}' failed: {e}")
            return {"success": False, "error": str(e)}
    
    def _launch(self, target: Dict, value: Any) -> Dict[str, Any]:
        """启动应用"""
        Application = get_pywinauto()
        path = target.get("path") or value
        
        if not path:
            return {"success": False, "error": "path is required"}
        
        self._app = Application(backend=self.backend).start(path)
        return {"success": True}
    
    def _connect_app(self, target: Dict, value: Any) -> Dict[str, Any]:
        """连接到已运行的应用"""
        Application = get_pywinauto()
        
        title = target.get("title") or target.get("name") or value
        process = target.get("process")
        
        if title:
            # 转义正则特殊字符，防止注入攻击
            escaped_title = re.escape(title)
            self._app = Application(backend=self.backend).connect(title_re=f".*{escaped_title}.*")
        elif process:
            self._app = Application(backend=self.backend).connect(process=process)
        else:
            return {"success": False, "error": "title or process is required"}
        
        return {"success": True}
    
    def _close(self) -> Dict[str, Any]:
        """关闭应用"""
        if self._app:
            try:
                self._app.top_window().close()
            except Exception:
                pass
            self._app = None
        return {"success": True}
    
    def _click(self, target: Dict) -> Dict[str, Any]:
        """点击元素"""
        if not self._app:
            return {"success": False, "error": "No application connected"}
        
        criteria = self._build_criteria(target)
        window = self._app.top_window()
        
        element = window.child_window(**criteria)
        element.click_input()
        
        return {"success": True}
    
    def _type(self, target: Dict, value: Any) -> Dict[str, Any]:
        """输入文本"""
        if not self._app:
            return {"success": False, "error": "No application connected"}
        
        text = value if isinstance(value, str) else str(value)
        window = self._app.top_window()
        
        if target:
            criteria = self._build_criteria(target)
            element = window.child_window(**criteria)
            element.type_keys(text, with_spaces=True)
        else:
            # 直接输入到当前焦点
            window.type_keys(text, with_spaces=True)
        
        return {"success": True}
    
    def _read(self, target: Dict) -> Dict[str, Any]:
        """读取元素文本"""
        if not self._app:
            return {"success": False, "error": "No application connected"}
        
        window = self._app.top_window()
        
        if target:
            criteria = self._build_criteria(target)
            element = window.child_window(**criteria)
            text = element.window_text()
        else:
            text = window.window_text()
        
        return {"success": True, "data": text}
    
    def _list_elements(self) -> Dict[str, Any]:
        """列出窗口中的所有可交互元素"""
        if not self._app:
            return {"success": False, "error": "No application connected"}
        
        window = self._app.top_window()
        elements = []
        
        for child in window.descendants():
            try:
                info = child.element_info
                elements.append({
                    "name": child.window_text()[:100] if child.window_text() else "",
                    "control_type": info.control_type,
                    "automation_id": info.automation_id,
                    "class_name": info.class_name,
                })
            except Exception:
                pass
            
            if len(elements) >= 50:  # 限制数量
                break
        
        return {"success": True, "elements": elements}
    
    def _focus(self) -> Dict[str, Any]:
        """聚焦窗口"""
        if not self._app:
            return {"success": False, "error": "No application connected"}
        
        window = self._app.top_window()
        window.set_focus()
        
        return {"success": True}
    
    def _screenshot(self, target: Dict) -> Dict[str, Any]:
        """截图"""
        if not self._app:
            return {"success": False, "error": "No application connected"}
        
        import base64
        from io import BytesIO
        
        window = self._app.top_window()
        image = window.capture_as_image()
        
        # 转换为base64
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        b64 = base64.b64encode(buffer.getvalue()).decode()
        
        return {"success": True, "screenshot": b64}
    
    def _build_criteria(self, target: Dict) -> Dict[str, Any]:
        """构建pywinauto查找条件"""
        criteria = {}
        
        if target.get("name"):
            criteria["title"] = target["name"]
        if target.get("title"):
            criteria["title"] = target["title"]
        if target.get("automation_id"):
            criteria["auto_id"] = target["automation_id"]
        if target.get("class_name"):
            criteria["class_name"] = target["class_name"]
        if target.get("control_type"):
            criteria["control_type"] = target["control_type"]
        if target.get("role"):
            criteria["control_type"] = target["role"]
        
        return criteria
