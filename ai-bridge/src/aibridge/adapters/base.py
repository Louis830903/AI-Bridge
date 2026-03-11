"""
Base Adapter - Abstract base class for all adapters
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


class AdapterType(str, Enum):
    """Types of adapters."""
    
    BROWSER = "browser"
    IM = "im"
    OFFICE = "office"
    DESKTOP = "desktop"
    CUSTOM = "custom"


@dataclass
class AdapterInfo:
    """Adapter metadata."""
    
    id: str  # Unique identifier, e.g., "chrome", "feishu"
    name: str  # Display name, e.g., "Google Chrome"
    type: AdapterType  # Adapter type
    version: str = "1.0.0"  # Adapter version
    platforms: List[str] = field(default_factory=lambda: ["windows"])
    actions: List[str] = field(default_factory=list)  # Supported actions
    description: str = ""
    author: str = ""
    homepage: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value if isinstance(self.type, AdapterType) else self.type,
            "version": self.version,
            "platforms": self.platforms,
            "actions": self.actions,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
        }


class BaseAdapter(ABC):
    """
    Abstract base class for all adapters.
    
    All adapters must inherit from this class and implement the required methods.
    This is the glue code interface that wraps underlying libraries.
    """
    
    # Subclasses must define this
    info: AdapterInfo
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the adapter.
        
        Args:
            config: Adapter-specific configuration dictionary
        """
        self.config = config or {}
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        """Check if the adapter is connected."""
        return self._connected
    
    @property
    def adapter_id(self) -> str:
        """Get the adapter ID."""
        return self.info.id
    
    @property
    def adapter_name(self) -> str:
        """Get the adapter display name."""
        return self.info.name
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the application.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Disconnect from the application.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the application is available.
        
        Returns:
            True if application is available, False otherwise
        """
        pass
    
    @abstractmethod
    async def execute(
        self,
        action: str,
        target: Optional[Dict[str, Any]] = None,
        value: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an action on the application.
        
        Args:
            action: The action to perform (e.g., "click", "type", "read")
            target: Element locator dictionary
            value: Value for the operation
            options: Additional options
            
        Returns:
            Response dictionary with keys: success, data, error, screenshot, etc.
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the adapter.
        
        Returns:
            Health status dictionary
        """
        try:
            available = await self.is_available()
            return {
                "adapter": self.info.id,
                "name": self.info.name,
                "available": available,
                "connected": self._connected,
                "status": "healthy" if available else "unavailable"
            }
        except Exception as e:
            return {
                "adapter": self.info.id,
                "name": self.info.name,
                "available": False,
                "connected": False,
                "status": "error",
                "error": str(e)
            }
    
    def supports_action(self, action: str) -> bool:
        """
        Check if the adapter supports a specific action.
        
        Args:
            action: The action to check
            
        Returns:
            True if supported, False otherwise
        """
        return action in self.info.actions
    
    def get_supported_actions(self) -> List[str]:
        """Get list of supported actions."""
        return self.info.actions.copy()
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.info.id}, connected={self._connected})>"


class SyncBaseAdapter(ABC):
    """
    Synchronous version of BaseAdapter for adapters that don't need async.
    """
    
    info: AdapterInfo
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @abstractmethod
    def connect(self) -> bool:
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        pass
    
    @abstractmethod
    def execute(
        self,
        action: str,
        target: Optional[Dict[str, Any]] = None,
        value: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        pass
    
    def health_check(self) -> Dict[str, Any]:
        try:
            available = self.is_available()
            return {
                "adapter": self.info.id,
                "name": self.info.name,
                "available": available,
                "connected": self._connected,
                "status": "healthy" if available else "unavailable"
            }
        except Exception as e:
            return {
                "adapter": self.info.id,
                "name": self.info.name,
                "available": False,
                "connected": False,
                "status": "error",
                "error": str(e)
            }
