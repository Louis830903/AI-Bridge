"""
AAIP Protocol - AI Application Interaction Protocol
Core protocol definitions for AI-Bridge
"""

from enum import Enum
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime


class Action(str, Enum):
    """Standard operation types supported by AAIP protocol."""
    
    # Element Interaction
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    CLEAR = "clear"
    SELECT = "select"
    CHECK = "check"
    SCROLL = "scroll"
    DRAG = "drag"
    HOVER = "hover"
    
    # Information Retrieval
    READ = "read"
    SCREENSHOT = "screenshot"
    GET_ATTRIBUTE = "get_attribute"
    GET_STATE = "get_state"
    LIST_ELEMENTS = "list_elements"
    FIND = "find"
    
    # Flow Control
    WAIT = "wait"
    WAIT_GONE = "wait_gone"
    WAIT_STABLE = "wait_stable"
    FOCUS = "focus"
    LAUNCH = "launch"
    CLOSE = "close"
    SWITCH = "switch"
    
    # Navigation (Browser)
    GOTO = "goto"
    BACK = "back"
    FORWARD = "forward"
    RELOAD = "reload"
    
    # Special Operations
    EXECUTE = "execute"
    UPLOAD = "upload"
    DOWNLOAD = "download"
    SEND_KEYS = "send_keys"
    
    # IM Specific
    SEND = "send"
    SEND_CARD = "send_card"
    LIST_CHATS = "list_chats"
    LIST_MEMBERS = "list_members"
    
    # Office Specific
    CREATE = "create"
    OPEN = "open"
    SAVE = "save"
    EXPORT = "export"
    WRITE = "write"


class ElementRole(str, Enum):
    """Standard element roles."""
    
    BUTTON = "button"
    INPUT = "input"
    TEXT = "text"
    LINK = "link"
    IMAGE = "image"
    MENU = "menu"
    MENU_ITEM = "menu_item"
    TAB = "tab"
    LIST = "list"
    LIST_ITEM = "list_item"
    TREE = "tree"
    TREE_ITEM = "tree_item"
    TABLE = "table"
    ROW = "row"
    CELL = "cell"
    CHECKBOX = "checkbox"
    RADIO = "radio"
    COMBOBOX = "combobox"
    SLIDER = "slider"
    SCROLLBAR = "scrollbar"
    WINDOW = "window"
    DIALOG = "dialog"
    PANE = "pane"
    GROUP = "group"
    TOOLBAR = "toolbar"
    STATUSBAR = "statusbar"


@dataclass
class Target:
    """Element locator for targeting UI elements."""
    
    # General locators
    name: Optional[str] = None
    role: Optional[str] = None
    index: int = 0
    
    # Advanced locators
    automation_id: Optional[str] = None
    class_name: Optional[str] = None
    xpath: Optional[str] = None
    css: Optional[str] = None
    
    # Fuzzy locators
    contains_text: Optional[str] = None
    regex: Optional[str] = None
    
    # Relative locators
    near: Optional["Target"] = None
    inside: Optional["Target"] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values."""
        result = {}
        for key, value in self.__dict__.items():
            if value is not None:
                if isinstance(value, Target):
                    result[key] = value.to_dict()
                else:
                    result[key] = value
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Target":
        """Create Target from dictionary."""
        if data is None:
            return None
        
        # Handle nested targets
        if "near" in data and data["near"]:
            data["near"] = cls.from_dict(data["near"])
        if "inside" in data and data["inside"]:
            data["inside"] = cls.from_dict(data["inside"])
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RequestOptions:
    """Additional options for a request."""
    
    timeout: int = 10000  # Timeout in milliseconds
    wait_after: int = 500  # Wait after operation in milliseconds
    retry: int = 0  # Number of retries
    screenshot: bool = False  # Whether to return screenshot
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timeout": self.timeout,
            "wait_after": self.wait_after,
            "retry": self.retry,
            "screenshot": self.screenshot,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RequestOptions":
        if data is None:
            return cls()
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Request:
    """AAIP protocol request."""
    
    app: str  # Target application ID
    action: str  # Operation type
    target: Optional[Target] = None  # Element locator
    value: Optional[Any] = None  # Operation value
    options: RequestOptions = field(default_factory=RequestOptions)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "app": self.app,
            "action": self.action,
        }
        if self.target:
            result["target"] = self.target.to_dict() if isinstance(self.target, Target) else self.target
        if self.value is not None:
            result["value"] = self.value
        result["options"] = self.options.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Request":
        return cls(
            app=data.get("app", ""),
            action=data.get("action", ""),
            target=Target.from_dict(data.get("target")) if data.get("target") else None,
            value=data.get("value"),
            options=RequestOptions.from_dict(data.get("options")),
        )


@dataclass
class Response:
    """AAIP protocol response."""
    
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    screenshot: Optional[str] = None  # Base64 encoded
    duration: Optional[int] = None  # Execution time in milliseconds
    elements: Optional[List[Dict]] = None  # For list_elements action
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {"success": self.success}
        if self.data is not None:
            result["data"] = self.data
        if self.error:
            result["error"] = self.error
        if self.screenshot:
            result["screenshot"] = self.screenshot
        if self.duration is not None:
            result["duration"] = self.duration
        if self.elements:
            result["elements"] = self.elements
        if self.metadata:
            result["metadata"] = self.metadata
        return result
    
    @classmethod
    def success_response(cls, data: Any = None, **kwargs) -> "Response":
        """Create a success response."""
        return cls(success=True, data=data, **kwargs)
    
    @classmethod
    def error_response(cls, error: str, **kwargs) -> "Response":
        """Create an error response."""
        return cls(success=False, error=error, **kwargs)


# Type aliases for convenience
ActionType = Action
TargetType = Target
RequestType = Request
ResponseType = Response
