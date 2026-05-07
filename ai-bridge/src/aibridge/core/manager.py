"""
Adapter Manager - Manages registration and lifecycle of adapters
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Type, Union
from aibridge.adapters.base import BaseAdapter, SyncBaseAdapter

logger = logging.getLogger(__name__)


class AdapterManager:
    """
    Manages adapter registration, lifecycle, and dispatch.
    
    This is the central hub that coordinates all adapters.
    """
    
    def __init__(self):
        self._adapters: Dict[str, BaseAdapter] = {}
        self._sync_adapters: Dict[str, SyncBaseAdapter] = {}
    
    def register(self, adapter: BaseAdapter) -> None:
        """
        Register an async adapter.
        
        Args:
            adapter: The adapter instance to register
        """
        if adapter.info.id in self._adapters:
            logger.warning(
                f"Adapter '{adapter.info.id}' is already registered, replacing. "
                f"Old adapter will NOT be automatically disconnected."
            )
        self._adapters[adapter.info.id] = adapter
    
    def register_sync(self, adapter: SyncBaseAdapter) -> None:
        """
        Register a sync adapter.
        
        Args:
            adapter: The sync adapter instance to register
        """
        self._sync_adapters[adapter.info.id] = adapter
    
    def unregister(self, adapter_id: str) -> bool:
        """
        Unregister an adapter.
        
        Args:
            adapter_id: The adapter ID to unregister
            
        Returns:
            True if successfully unregistered, False if not found
        """
        if adapter_id in self._adapters:
            del self._adapters[adapter_id]
            return True
        if adapter_id in self._sync_adapters:
            del self._sync_adapters[adapter_id]
            return True
        return False
    
    def get_adapter(self, adapter_id: str) -> Optional[BaseAdapter]:
        """Get an async adapter by ID."""
        return self._adapters.get(adapter_id)
    
    def get_sync_adapter(self, adapter_id: str) -> Optional[SyncBaseAdapter]:
        """Get a sync adapter by ID."""
        return self._sync_adapters.get(adapter_id)
    
    def get_any_adapter(self, adapter_id: str) -> Optional[Union[BaseAdapter, SyncBaseAdapter]]:
        """Get any adapter (async or sync) by ID."""
        return self._adapters.get(adapter_id) or self._sync_adapters.get(adapter_id)
    
    def list_adapters(self) -> List[Dict[str, Any]]:
        """
        List all registered adapters with their info.
        
        Returns:
            List of adapter info dictionaries
        """
        adapters = []
        
        for adapter in self._adapters.values():
            adapters.append({
                **adapter.info.to_dict(),
                "async": True,
                "connected": adapter.is_connected,
            })
        
        for adapter in self._sync_adapters.values():
            adapters.append({
                **adapter.info.to_dict(),
                "async": False,
                "connected": adapter.is_connected,
            })
        
        return adapters
    
    def list_adapter_ids(self) -> List[str]:
        """Get list of all adapter IDs."""
        return list(self._adapters.keys()) + list(self._sync_adapters.keys())
    
    async def connect_all(self) -> Dict[str, bool]:
        """
        Connect all adapters.
        
        Returns:
            Dictionary mapping adapter ID to connection success
        """
        results = {}
        
        # Connect async adapters
        for adapter_id, adapter in self._adapters.items():
            try:
                results[adapter_id] = await adapter.connect()
            except Exception as e:
                logger.warning(f"Failed to connect adapter '{adapter_id}': {e}")
                results[adapter_id] = False
        
        # Connect sync adapters
        for adapter_id, adapter in self._sync_adapters.items():
            try:
                results[adapter_id] = adapter.connect()
            except Exception as e:
                logger.warning(f"Failed to connect sync adapter '{adapter_id}': {e}")
                results[adapter_id] = False
        
        return results
    
    async def disconnect_all(self) -> Dict[str, bool]:
        """
        Disconnect all adapters.
        
        Returns:
            Dictionary mapping adapter ID to disconnection success
        """
        results = {}
        
        for adapter_id, adapter in self._adapters.items():
            try:
                results[adapter_id] = await adapter.disconnect()
            except Exception as e:
                logger.warning(f"Failed to disconnect adapter '{adapter_id}': {e}")
                results[adapter_id] = False
        
        for adapter_id, adapter in self._sync_adapters.items():
            try:
                results[adapter_id] = adapter.disconnect()
            except Exception as e:
                logger.warning(f"Failed to disconnect sync adapter '{adapter_id}': {e}")
                results[adapter_id] = False
        
        return results
    
    async def execute(
        self,
        app: str,
        action: str,
        target: Optional[Dict[str, Any]] = None,
        value: Optional[Any] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute an action on a specific adapter.
        
        Args:
            app: Target application/adapter ID
            action: Action to perform
            target: Element locator
            value: Operation value
            options: Additional options
            
        Returns:
            Response dictionary
        """
        # Try async adapter first
        adapter = self._adapters.get(app)
        if adapter:
            # 首次连接：如果未连接，先自动连接
            if not adapter.is_connected:
                try:
                    await adapter.connect()
                except Exception as e:
                    return {"success": False, "error": f"Failed to connect: {e}"}

            try:
                return await adapter.execute(action, target, value, options)
            except Exception as first_error:
                # 仅在适配器确实断开连接时才尝试自动重连
                if not adapter.is_connected:
                    try:
                        logger.info(f"Adapter '{app}' disconnected, attempting reconnect...")
                        await adapter.connect()
                        return await adapter.execute(action, target, value, options)
                    except Exception as reconnect_error:
                        return {
                            "success": False,
                            "error": f"Reconnect failed: {reconnect_error}"
                        }
                # 非连接错误：直接返回原始错误
                return {"success": False, "error": str(first_error)}
        
        # Try sync adapter
        sync_adapter = self._sync_adapters.get(app)
        if sync_adapter:
            if not sync_adapter.is_connected:
                try:
                    sync_adapter.connect()
                except Exception as e:
                    return {"success": False, "error": f"Failed to connect: {e}"}
            
            # Run sync adapter in executor to not block
            return await asyncio.to_thread(
                sync_adapter.execute,
                action, target, value, options
            )
        
        return {"success": False, "error": f"Unknown application: {app}"}
    
    async def health_check_all(self) -> Dict[str, Dict[str, Any]]:
        """
        Perform health check on all adapters.
        
        Returns:
            Dictionary mapping adapter ID to health status
        """
        results = {}
        
        for adapter_id, adapter in self._adapters.items():
            results[adapter_id] = await adapter.health_check()
        
        for adapter_id, adapter in self._sync_adapters.items():
            results[adapter_id] = adapter.health_check()
        
        return results
