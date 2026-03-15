"""
Unified Adapter Configuration System
统一的适配器配置系统
"""

from abc import ABC
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, Optional, List
import os


@dataclass
class BaseAdapterConfig(ABC):
    """
    适配器配置基类
    
    所有适配器配置都应继承此类，提供统一的配置接口。
    """
    enabled: bool = True
    timeout: int = 30
    retry_count: int = 3
    retry_delay: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseAdapterConfig":
        """从字典创建配置"""
        # 过滤掉不存在的字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    @classmethod
    def from_env(cls, prefix: str = "") -> "BaseAdapterConfig":
        """从环境变量创建配置"""
        data = {}
        for field_name in cls.__dataclass_fields__:
            env_key = f"{prefix}_{field_name}".upper() if prefix else field_name.upper()
            env_value = os.environ.get(env_key)
            if env_value is not None:
                # 尝试类型转换
                field_type = cls.__dataclass_fields__[field_name].type
                try:
                    if field_type == bool:
                        data[field_name] = env_value.lower() in ('true', '1', 'yes')
                    elif field_type == int:
                        data[field_name] = int(env_value)
                    elif field_type == float:
                        data[field_name] = float(env_value)
                    else:
                        data[field_name] = env_value
                except (ValueError, TypeError):
                    data[field_name] = env_value
        return cls(**data) if data else cls()


# ============ Browser Adapters ============

@dataclass
class ChromeConfig(BaseAdapterConfig):
    """Chrome 浏览器配置"""
    cdp_url: str = "http://localhost:9222"
    headless: bool = False
    user_data_dir: Optional[str] = None
    
    @classmethod
    def from_env(cls, prefix: str = "CHROME") -> "ChromeConfig":
        return super().from_env(prefix)


@dataclass
class EdgeConfig(BaseAdapterConfig):
    """Edge 浏览器配置"""
    cdp_url: str = "http://localhost:9223"
    headless: bool = False
    user_data_dir: Optional[str] = None
    
    @classmethod
    def from_env(cls, prefix: str = "EDGE") -> "EdgeConfig":
        return super().from_env(prefix)


# ============ Office Adapters ============

@dataclass
class OfficeConfig(BaseAdapterConfig):
    """Microsoft Office 配置"""
    visible: bool = True
    display_alerts: bool = False
    
    @classmethod
    def from_env(cls, prefix: str = "OFFICE") -> "OfficeConfig":
        return super().from_env(prefix)


@dataclass
class WPSConfig(BaseAdapterConfig):
    """WPS Office 配置"""
    visible: bool = True
    
    @classmethod
    def from_env(cls, prefix: str = "WPS") -> "WPSConfig":
        return super().from_env(prefix)


# 配置类型映射
CONFIG_CLASS_MAP = {
    "chrome": ChromeConfig,
    "edge": EdgeConfig,
    "office": OfficeConfig,
    "wps": WPSConfig,
}


def create_config(adapter_id: str, data: Dict[str, Any]) -> BaseAdapterConfig:
    """
    根据适配器 ID 创建对应的配置实例
    
    Args:
        adapter_id: 适配器 ID
        data: 配置数据字典
        
    Returns:
        对应的配置实例
    """
    config_class = CONFIG_CLASS_MAP.get(adapter_id, BaseAdapterConfig)
    return config_class.from_dict(data) if data else config_class()
