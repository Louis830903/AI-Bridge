"""
Agent Card 扩展数据结构

提供 A2A 协议的 Agent Card 扩展，支持：
- Card 签名验证（防止篡改）
- 可见性控制（公开/私有/不可搜索）
- 状态管理（活跃/非活跃/已弃用）
- 性能指标（延迟/成功率/调用量）
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import hashlib
import hmac
import json


class CardVisibility(str, Enum):
    """Card 可见性"""
    PUBLIC = "public"      # 公开可发现
    PRIVATE = "private"    # 仅限授权访问
    UNLISTED = "unlisted"  # 不可搜索但可直接访问


class CardStatus(str, Enum):
    """Card 状态"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPRECATED = "deprecated"


@dataclass
class AgentCapabilitySchema:
    """能力输入/输出 Schema"""
    type: str = "object"
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "properties": self.properties,
            "required": self.required,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCapabilitySchema":
        return cls(
            type=data.get("type", "object"),
            properties=data.get("properties", {}),
            required=data.get("required", []),
        )


@dataclass
class AgentCapability:
    """Agent 能力描述"""
    name: str
    description: str = ""
    input_schema: Optional[AgentCapabilitySchema] = None
    output_schema: Optional[AgentCapabilitySchema] = None
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "name": self.name,
            "description": self.description,
        }
        if self.input_schema:
            result["input_schema"] = self.input_schema.to_dict()
        if self.output_schema:
            result["output_schema"] = self.output_schema.to_dict()
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCapability":
        input_schema = None
        output_schema = None
        if "input_schema" in data:
            input_schema = AgentCapabilitySchema.from_dict(data["input_schema"])
        if "output_schema" in data:
            output_schema = AgentCapabilitySchema.from_dict(data["output_schema"])
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            input_schema=input_schema,
            output_schema=output_schema,
        )


@dataclass
class AgentCardMetadata:
    """Agent Card 元数据"""
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    visibility: CardVisibility = CardVisibility.PUBLIC
    status: CardStatus = CardStatus.ACTIVE
    tags: List[str] = field(default_factory=list)
    categories: List[str] = field(default_factory=list)
    owner_id: Optional[str] = None
    signature: Optional[str] = None  # Card 签名，防止篡改
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "visibility": self.visibility.value,
            "status": self.status.value,
            "tags": self.tags,
            "categories": self.categories,
            "owner_id": self.owner_id,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCardMetadata":
        created_at = data.get("created_at")
        updated_at = data.get("updated_at")
        
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        elif created_at is None:
            created_at = datetime.utcnow()
            
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at)
        elif updated_at is None:
            updated_at = datetime.utcnow()
        
        return cls(
            created_at=created_at,
            updated_at=updated_at,
            version=data.get("version", "1.0.0"),
            visibility=CardVisibility(data.get("visibility", "public")),
            status=CardStatus(data.get("status", "active")),
            tags=data.get("tags", []),
            categories=data.get("categories", []),
            owner_id=data.get("owner_id"),
            signature=data.get("signature"),
        )


@dataclass
class AgentCardExtended:
    """扩展的 Agent Card，支持发布与发现"""
    
    # 基础信息
    id: str
    name: str
    description: str
    capabilities: List[AgentCapability]
    endpoint: str
    
    # 扩展字段
    metadata: AgentCardMetadata = field(default_factory=AgentCardMetadata)
    
    # 通信配置
    protocols: List[str] = field(default_factory=lambda: ["a2a", "mcp"])
    auth_required: bool = False
    auth_schemes: List[str] = field(default_factory=list)  # ["api_key", "jwt", "oauth2"]
    
    # 性能指标（用于发现排序）
    avg_latency_ms: Optional[float] = None
    success_rate: Optional[float] = None
    total_calls: int = 0
    
    def sign(self, secret_key: str) -> str:
        """生成 Card 签名
        
        Args:
            secret_key: 签名密钥
            
        Returns:
            签名字符串
        """
        payload = json.dumps({
            "id": self.id,
            "name": self.name,
            "endpoint": self.endpoint,
            "capabilities": [c.name for c in self.capabilities],
            "version": self.metadata.version,
        }, sort_keys=True)
        signature = hmac.new(
            secret_key.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()
        self.metadata.signature = signature
        return signature
    
    def verify(self, secret_key: str) -> bool:
        """验证 Card 签名
        
        Args:
            secret_key: 签名密钥
            
        Returns:
            签名是否有效
        """
        if not self.metadata.signature:
            return False
        stored_signature = self.metadata.signature
        # 临时清除签名以重新计算
        self.metadata.signature = None
        expected = self.sign(secret_key)
        # 使用安全比较
        result = hmac.compare_digest(stored_signature, expected)
        if not result:
            # 恢复原签名
            self.metadata.signature = stored_signature
        return result
    
    def update_metrics(
        self,
        latency_ms: float,
        success: bool
    ) -> None:
        """更新性能指标
        
        Args:
            latency_ms: 本次调用延迟（毫秒）
            success: 是否成功
        """
        self.total_calls += 1
        
        # 更新平均延迟（指数移动平均）
        if self.avg_latency_ms is None:
            self.avg_latency_ms = latency_ms
        else:
            alpha = 0.1  # 平滑因子
            self.avg_latency_ms = alpha * latency_ms + (1 - alpha) * self.avg_latency_ms
        
        # 更新成功率
        if self.success_rate is None:
            self.success_rate = 1.0 if success else 0.0
        else:
            # 滑动窗口成功率
            alpha = 0.05
            self.success_rate = alpha * (1.0 if success else 0.0) + (1 - alpha) * self.success_rate
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "endpoint": self.endpoint,
            "metadata": self.metadata.to_dict(),
            "protocols": self.protocols,
            "auth_required": self.auth_required,
            "auth_schemes": self.auth_schemes,
            "avg_latency_ms": self.avg_latency_ms,
            "success_rate": self.success_rate,
            "total_calls": self.total_calls,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCardExtended":
        """从字典构造"""
        capabilities = []
        for cap_data in data.get("capabilities", []):
            if isinstance(cap_data, dict):
                capabilities.append(AgentCapability.from_dict(cap_data))
        
        metadata = AgentCardMetadata.from_dict(data.get("metadata", {}))
        
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            capabilities=capabilities,
            endpoint=data.get("endpoint", ""),
            metadata=metadata,
            protocols=data.get("protocols", ["a2a", "mcp"]),
            auth_required=data.get("auth_required", False),
            auth_schemes=data.get("auth_schemes", []),
            avg_latency_ms=data.get("avg_latency_ms"),
            success_rate=data.get("success_rate"),
            total_calls=data.get("total_calls", 0),
        )
    
    def to_a2a_card(self) -> Dict[str, Any]:
        """转换为标准 A2A Agent Card 格式
        
        返回符合 A2A 协议规范的 Agent Card
        """
        return {
            "name": self.name,
            "description": self.description,
            "url": self.endpoint,
            "version": self.metadata.version,
            "capabilities": {
                cap.name: {
                    "description": cap.description,
                    "inputSchema": cap.input_schema.to_dict() if cap.input_schema else {},
                    "outputSchema": cap.output_schema.to_dict() if cap.output_schema else {},
                }
                for cap in self.capabilities
            },
            "authentication": {
                "required": self.auth_required,
                "schemes": self.auth_schemes,
            } if self.auth_required else None,
            "provider": {
                "name": "AI-Bridge",
                "url": "https://github.com/liuhaotian/ai-bridge"
            }
        }


def create_card(
    id: str,
    name: str,
    description: str,
    endpoint: str,
    capabilities: List[Dict[str, Any]] = None,
    tags: List[str] = None,
    categories: List[str] = None,
    visibility: CardVisibility = CardVisibility.PUBLIC,
    auth_required: bool = False,
    auth_schemes: List[str] = None,
) -> AgentCardExtended:
    """创建 Agent Card 的便捷函数
    
    Args:
        id: 唯一标识符
        name: Agent 名称
        description: 描述
        endpoint: 服务端点
        capabilities: 能力列表
        tags: 标签
        categories: 分类
        visibility: 可见性
        auth_required: 是否需要认证
        auth_schemes: 认证方案
        
    Returns:
        AgentCardExtended 实例
    """
    caps = []
    for cap in (capabilities or []):
        if isinstance(cap, dict):
            caps.append(AgentCapability.from_dict(cap))
        elif isinstance(cap, AgentCapability):
            caps.append(cap)
    
    metadata = AgentCardMetadata(
        visibility=visibility,
        tags=tags or [],
        categories=categories or [],
    )
    
    return AgentCardExtended(
        id=id,
        name=name,
        description=description,
        capabilities=caps,
        endpoint=endpoint,
        metadata=metadata,
        auth_required=auth_required,
        auth_schemes=auth_schemes or [],
    )
