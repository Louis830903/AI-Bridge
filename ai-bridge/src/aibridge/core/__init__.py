"""
AI-Bridge Core - 核心功能模块
"""

# 意图识别和 O-R-A 循环
from .intent_engine import IntentEngine, IntentType, IntentResult, ActionStep
from .orchestrator import Orchestrator, TaskResult, TaskStatus

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

__all__ = [
    # 意图和编排
    "IntentEngine",
    "IntentType",
    "IntentResult",
    "ActionStep",
    "Orchestrator",
    "TaskResult",
    "TaskStatus",
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
    "PermissionLevel"
]
