"""
Configuration - Configuration management for AI-Bridge
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import yaml


@dataclass
class AdapterConfig:
    """Configuration for a single adapter."""
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ServerConfig:
    """Server configuration."""
    transport: str = "stdio"  # stdio, http, sse
    host: str = "127.0.0.1"
    port: int = 8765
    log_level: str = "INFO"


@dataclass
class Config:
    """Main configuration class."""
    server: ServerConfig = field(default_factory=ServerConfig)
    adapters: Dict[str, AdapterConfig] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create Config from dictionary."""
        server_data = data.get("server", {})
        server = ServerConfig(**server_data)
        
        adapters = {}
        for name, adapter_data in data.get("adapters", {}).items():
            if isinstance(adapter_data, dict):
                enabled = adapter_data.pop("enabled", True)
                adapters[name] = AdapterConfig(enabled=enabled, config=adapter_data)
            else:
                adapters[name] = AdapterConfig(enabled=bool(adapter_data))
        
        options = data.get("options", {})
        
        return cls(server=server, adapters=adapters, options=options)
    
    def get_adapter_config(self, adapter_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific adapter."""
        adapter = self.adapters.get(adapter_id)
        if adapter and adapter.enabled:
            return adapter.config
        return None
    
    def is_adapter_enabled(self, adapter_id: str) -> bool:
        """Check if an adapter is enabled."""
        adapter = self.adapters.get(adapter_id)
        return adapter.enabled if adapter else False


def expand_env_vars(data: Any) -> Any:
    """Expand environment variables in configuration values."""
    if isinstance(data, str):
        # Handle ${VAR} or $VAR syntax
        if data.startswith("${") and data.endswith("}"):
            var_name = data[2:-1]
            return os.environ.get(var_name, data)
        elif data.startswith("$"):
            var_name = data[1:]
            return os.environ.get(var_name, data)
        return data
    elif isinstance(data, dict):
        return {k: expand_env_vars(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [expand_env_vars(item) for item in data]
    return data


def load_config(path: Optional[str] = None) -> Config:
    """
    Load configuration from file.
    
    Args:
        path: Path to config file. If None, searches for aibridge.yaml
        
    Returns:
        Config instance
    """
    if path is None:
        # Search for config file
        search_paths = [
            Path.cwd() / "aibridge.yaml",
            Path.cwd() / "aibridge.yml",
            Path.cwd() / ".aibridge.yaml",
            Path.home() / ".aibridge" / "config.yaml",
        ]
        
        for search_path in search_paths:
            if search_path.exists():
                path = str(search_path)
                break
    
    if path and Path(path).exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if data:
                data = expand_env_vars(data)
                return Config.from_dict(data)
    
    # Return default config
    return Config()


def save_config(config: Config, path: str):
    """
    Save configuration to file.
    
    Args:
        config: Config instance to save
        path: Path to save to
    """
    data = {
        "server": {
            "transport": config.server.transport,
            "host": config.server.host,
            "port": config.server.port,
            "log_level": config.server.log_level,
        },
        "adapters": {
            name: {"enabled": adapter.enabled, **adapter.config}
            for name, adapter in config.adapters.items()
        },
        "options": config.options,
    }
    
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


# Default configuration template
DEFAULT_CONFIG_TEMPLATE = """# AI-Bridge Configuration

server:
  transport: stdio          # stdio | http | sse
  host: 127.0.0.1
  port: 8765
  log_level: INFO          # DEBUG | INFO | WARNING | ERROR

adapters:
  # Browser adapters
  chrome:
    enabled: true
    cdp_url: "http://localhost:9222"
    
  edge:
    enabled: false
    cdp_url: "http://localhost:9223"
  
  # IM adapters
  feishu:
    enabled: true
    app_id: ${FEISHU_APP_ID}
    app_secret: ${FEISHU_APP_SECRET}
    
  dingtalk:
    enabled: true
    app_key: ${DINGTALK_APP_KEY}
    app_secret: ${DINGTALK_APP_SECRET}
    
  wecom:
    enabled: true
    corp_id: ${WECOM_CORP_ID}
    corp_secret: ${WECOM_CORP_SECRET}
    agent_id: ${WECOM_AGENT_ID}
  
  # Office adapters
  office:
    enabled: true
    visible: true
    
  wps:
    enabled: true
    visible: true
  
  # Desktop adapter
  desktop:
    enabled: true
    backend: uia            # uia | win32

options:
  default_timeout: 10000    # Default timeout in ms
  default_wait_after: 500   # Default wait after operation in ms
  screenshot_on_error: true # Take screenshot on error
  ocr_fallback: true        # Enable OCR fallback
"""
