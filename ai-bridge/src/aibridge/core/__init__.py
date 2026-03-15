"""
AI-Bridge Core - 核心功能模块
"""

# 意图识别和 O-R-A 循环
from .intent_engine import IntentEngine, IntentType, IntentResult, ActionStep

# 多 Agent 编排器 (v4.0 增强)
from .orchestrator import (
    Orchestrator,
    TaskGraph,
    TaskNode,
    TaskState,
    ExecutionResult,
    # 向后兼容别名
    TaskResult,
    TaskStatus,
    # 便捷函数
    create_sequential_graph,
    create_parallel_graph,
    create_fan_out_fan_in_graph,
)

# 会话持久化
from .session_manager import SessionManager, SessionData

# 智能等待
from .smart_wait import SmartWait, RetryHandler, WaitCondition

# 批量执行
from .batch_executor import BatchExecutor, BatchMode, BatchAction, BatchResult

# 多模态支持
from .multimodal import MultiModalLocator, PageAnalyzer, PageAnalysis

# 安全沙箱
from .security import (
    SecurityManager,
    SecurityPolicy,
    SecureAdapterWrapper,
    PermissionLevel
)

# LLM 共享接口
from .llm_provider import (
    LLMProvider,
    OpenAILLMProvider,
    AgentSharedLLM,
    NoOpLLMProvider,
    create_llm_provider
)

__all__ = [
    # 意图识别
    "IntentEngine",
    "IntentType",
    "IntentResult",
    "ActionStep",
    # 多 Agent 编排 (v4.0)
    "Orchestrator",
    "TaskGraph",
    "TaskNode",
    "TaskState",
    "ExecutionResult",
    "TaskResult",     # 向后兼容
    "TaskStatus",     # 向后兼容
    "create_sequential_graph",
    "create_parallel_graph",
    "create_fan_out_fan_in_graph",
    # 会话管理
    "SessionManager",
    "SessionData",
    # 智能等待
    "SmartWait",
    "RetryHandler",
    "WaitCondition",
    # 批量执行
    "BatchExecutor",
    "BatchMode",
    "BatchAction",
    "BatchResult",
    # 多模态
    "MultiModalLocator",
    "PageAnalyzer",
    "PageAnalysis",
    # 安全
    "SecurityManager",
    "SecurityPolicy",
    "SecureAdapterWrapper",
    "PermissionLevel",
    # LLM 共享
    "LLMProvider",
    "OpenAILLMProvider",
    "AgentSharedLLM",
    "NoOpLLMProvider",
    "create_llm_provider"
]
