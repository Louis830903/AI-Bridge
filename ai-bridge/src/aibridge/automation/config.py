"""
多平台养号配置

定义各平台的养号策略和入口 URL。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum


class CommentStyle(Enum):
    """评论风格"""
    TECH = "tech"           # 技术性评论
    CASUAL = "casual"       # 随意简短
    ENTHUSIASTIC = "enthusiastic"  # 热情洋溢


@dataclass
class PlatformConfig:
    """平台配置"""
    name: str                           # 平台名称
    entry_urls: List[str]               # 入口 URL 列表
    actions: List[str]                  # 支持的动作
    comment_style: CommentStyle = CommentStyle.TECH
    daily_limit: int = 20               # 每日操作上限
    interval_seconds: Tuple[int, int] = (3, 8)    # 操作间隔（最小, 最大）秒
    requires_login: bool = True         # 是否需要登录
    notes: str = ""                     # 备注


# 预置平台配置
PLATFORM_CONFIGS: Dict[str, PlatformConfig] = {
    "reddit": PlatformConfig(
        name="Reddit",
        entry_urls=[
            "https://www.reddit.com/r/Python/hot/",
            "https://www.reddit.com/r/programming/hot/",
            "https://www.reddit.com/r/opensource/hot/",
            "https://www.reddit.com/r/MachineLearning/hot/",
        ],
        actions=["upvote", "comment", "save"],
        comment_style=CommentStyle.TECH,
        daily_limit=30,
        notes="r/Python 对新账号有 karma 限制，建议先在其他 subreddit 积累",
    ),
    
    "hackernews": PlatformConfig(
        name="Hacker News",
        entry_urls=[
            "https://news.ycombinator.com/",
            "https://news.ycombinator.com/newest",
            "https://news.ycombinator.com/show",
        ],
        actions=["upvote", "comment"],
        comment_style=CommentStyle.TECH,
        daily_limit=20,
        interval_seconds=(5, 15),
        notes="HN 对低质量评论非常敏感，建议评论要有深度",
    ),
    
    "twitter": PlatformConfig(
        name="Twitter/X",
        entry_urls=[
            "https://twitter.com/home",
            "https://x.com/home",
        ],
        actions=["upvote", "comment", "share", "follow"],
        comment_style=CommentStyle.CASUAL,
        daily_limit=50,
        notes="Twitter 对自动化行为检测较严格",
    ),
    
    "linkedin": PlatformConfig(
        name="LinkedIn",
        entry_urls=[
            "https://www.linkedin.com/feed/",
        ],
        actions=["upvote", "comment", "follow"],
        comment_style=CommentStyle.TECH,
        daily_limit=30,
        notes="LinkedIn 适合专业性内容互动",
    ),
    
    "github": PlatformConfig(
        name="GitHub",
        entry_urls=[
            "https://github.com/trending",
            "https://github.com/trending/python",
        ],
        actions=["upvote", "follow"],  # star, follow
        comment_style=CommentStyle.TECH,
        daily_limit=30,
        notes="GitHub star 和 follow 有助于提升账号活跃度",
    ),
    
    "zhihu": PlatformConfig(
        name="知乎",
        entry_urls=[
            "https://www.zhihu.com/hot",
            "https://www.zhihu.com/",
        ],
        actions=["upvote", "comment", "follow", "save"],
        comment_style=CommentStyle.TECH,
        daily_limit=30,
        notes="知乎对营销内容审核较严",
    ),
    
    "v2ex": PlatformConfig(
        name="V2EX",
        entry_urls=[
            "https://www.v2ex.com/",
            "https://www.v2ex.com/?tab=hot",
        ],
        actions=["upvote", "comment", "checkin"],
        comment_style=CommentStyle.CASUAL,
        daily_limit=20,
        notes="V2EX 有每日签到功能",
    ),
    
    "juejin": PlatformConfig(
        name="掘金",
        entry_urls=[
            "https://juejin.cn/",
            "https://juejin.cn/frontend",
            "https://juejin.cn/backend",
        ],
        actions=["upvote", "comment", "save"],
        comment_style=CommentStyle.TECH,
        daily_limit=30,
        notes="掘金适合技术文章互动",
    ),
    
    "bilibili": PlatformConfig(
        name="哔哩哔哩",
        entry_urls=[
            "https://www.bilibili.com/",
            "https://www.bilibili.com/v/tech/",
        ],
        actions=["upvote", "coin", "save", "comment"],
        comment_style=CommentStyle.ENTHUSIASTIC,
        daily_limit=30,
        notes="B站有独特的投币系统",
    ),
    
    "youtube": PlatformConfig(
        name="YouTube",
        entry_urls=[
            "https://www.youtube.com/",
            "https://www.youtube.com/feed/trending",
        ],
        actions=["upvote", "comment", "follow"],
        comment_style=CommentStyle.CASUAL,
        daily_limit=30,
        notes="YouTube 评论可以积累订阅者",
    ),
    
    "producthunt": PlatformConfig(
        name="Product Hunt",
        entry_urls=[
            "https://www.producthunt.com/",
        ],
        actions=["upvote", "comment", "follow"],
        comment_style=CommentStyle.ENTHUSIASTIC,
        daily_limit=20,
        notes="Product Hunt 对产品推广很重要",
    ),
    
    "devto": PlatformConfig(
        name="Dev.to",
        entry_urls=[
            "https://dev.to/",
            "https://dev.to/top/week",
        ],
        actions=["upvote", "comment", "save", "follow"],
        comment_style=CommentStyle.TECH,
        daily_limit=30,
        notes="Dev.to 是技术博客的好平台",
    ),
    
    "medium": PlatformConfig(
        name="Medium",
        entry_urls=[
            "https://medium.com/",
        ],
        actions=["upvote", "comment", "follow"],  # clap
        comment_style=CommentStyle.TECH,
        daily_limit=30,
        notes="Medium 使用 clap 而不是 like",
    ),
    
    "stackoverflow": PlatformConfig(
        name="Stack Overflow",
        entry_urls=[
            "https://stackoverflow.com/",
            "https://stackoverflow.com/questions?tab=Newest",
        ],
        actions=["upvote", "comment"],
        comment_style=CommentStyle.TECH,
        daily_limit=20,
        notes="Stack Overflow 需要 reputation 才能执行某些操作",
    ),
    
    "weibo": PlatformConfig(
        name="微博",
        entry_urls=[
            "https://weibo.com/",
            "https://s.weibo.com/top/summary",
        ],
        actions=["upvote", "comment", "share", "follow"],
        comment_style=CommentStyle.CASUAL,
        daily_limit=50,
        notes="微博适合热点话题互动",
    ),
}


def get_platform_config(platform: str) -> Optional[PlatformConfig]:
    """获取平台配置"""
    return PLATFORM_CONFIGS.get(platform.lower())


def list_platforms() -> List[str]:
    """列出所有支持的平台"""
    return list(PLATFORM_CONFIGS.keys())


def get_platforms_by_action(action: str) -> List[str]:
    """获取支持特定动作的平台列表"""
    return [
        name for name, config in PLATFORM_CONFIGS.items()
        if action in config.actions
    ]
