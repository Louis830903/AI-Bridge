"""
通用养号自动化引擎

支持跨平台的语义化养号操作，无需为每个平台单独编写逻辑。

核心组件：
- ActionSemantics: 语义词库，定义各类动作的关键词
- AccountNurtureEngine: 养号引擎，分析页面并推荐动作
- PLATFORM_CONFIGS: 多平台配置

Example:
    from aibridge.automation import AccountNurtureEngine, PLATFORM_CONFIGS
    
    # 创建引擎
    engine = AccountNurtureEngine()
    
    # 分析快照
    actions = engine.analyze(snapshot_text, target_actions=["upvote", "comment"])
    
    # 获取平台配置
    config = PLATFORM_CONFIGS.get("reddit")
"""

from .semantics import ActionSemantics, identify_platform, PLATFORM_ALIASES
from .engine import (
    AccountNurtureEngine,
    ActionType,
    PageElement,
    NurtureAction,
    NurtureResult,
    SnapshotParser,
    analyze_page,
    get_upvote_targets,
)
from .config import (
    PlatformConfig,
    CommentStyle,
    PLATFORM_CONFIGS,
    get_platform_config,
    list_platforms,
    get_platforms_by_action,
)

__all__ = [
    # 语义
    "ActionSemantics",
    "identify_platform",
    "PLATFORM_ALIASES",
    # 引擎
    "AccountNurtureEngine",
    "ActionType",
    "PageElement",
    "NurtureAction",
    "NurtureResult",
    "SnapshotParser",
    "analyze_page",
    "get_upvote_targets",
    # 配置
    "PlatformConfig",
    "CommentStyle",
    "PLATFORM_CONFIGS",
    "get_platform_config",
    "list_platforms",
    "get_platforms_by_action",
]
