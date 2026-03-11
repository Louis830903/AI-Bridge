"""
语义词库 - 定义跨平台的通用动作语义

基于 accessibility tree 的语义信息进行匹配，
支持多语言、多平台的通用识别。
"""

from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, ClassVar


@dataclass
class ActionSemantics:
    """动作语义词库（单例模式，避免重复初始化）"""
    
    # 单例实例缓存
    _instance: ClassVar[Optional['ActionSemantics']] = None
    
    # 点赞/喜欢类动作
    UPVOTE: Set[str] = field(default_factory=lambda: {
        # 英文
        "upvote", "like", "heart", "love", "clap", "applause",
        "thumbs up", "thumbs_up", "thumb up", "+1",
        # 中文
        "点赞", "赞", "赞同", "喜欢", "顶", "支持", "有用",
        # 符号
        "👍", "❤️", "♥", "🔺", "▲",
    })
    
    # 踩/不喜欢类动作
    DOWNVOTE: Set[str] = field(default_factory=lambda: {
        "downvote", "dislike", "thumbs down", "-1",
        "点踩", "踩", "反对", "没用",
        "👎", "🔻", "▼",
    })
    
    # 关注/订阅类动作
    FOLLOW: Set[str] = field(default_factory=lambda: {
        "follow", "subscribe", "join", "connect", "add friend",
        "关注", "订阅", "加入", "加好友", "连接", "关注他", "关注她",
        "➕", "+",
    })
    
    # 取消关注类动作
    UNFOLLOW: Set[str] = field(default_factory=lambda: {
        "unfollow", "unsubscribe", "leave", "disconnect",
        "取消关注", "取消订阅", "退出", "已关注",
    })
    
    # 评论/回复类动作
    COMMENT: Set[str] = field(default_factory=lambda: {
        "comment", "reply", "respond", "add comment", "write comment",
        "评论", "回复", "发表评论", "写评论", "发言", "加入对话",
        "💬", "🗨️",
    })
    
    # 转发/分享类动作
    SHARE: Set[str] = field(default_factory=lambda: {
        "share", "retweet", "repost", "forward", "spread",
        "分享", "转发", "转推", "转载", "共享",
        "🔄", "↗️",
    })
    
    # 收藏/保存类动作
    SAVE: Set[str] = field(default_factory=lambda: {
        "save", "bookmark", "favorite", "collect", "star",
        "收藏", "保存", "书签", "加星", "添加收藏",
        "⭐", "🔖", "★",
    })
    
    # 签到类动作
    CHECKIN: Set[str] = field(default_factory=lambda: {
        "check in", "check-in", "checkin", "sign in", "daily",
        "签到", "每日签到", "打卡", "签到领奖",
        "📅", "✅",
    })
    
    # 投币类动作（B站特有）
    COIN: Set[str] = field(default_factory=lambda: {
        "coin", "tip", "donate",
        "投币", "硬币", "打赏",
        "🪙",
    })
    
    # 提交类动作
    SUBMIT: Set[str] = field(default_factory=lambda: {
        "submit", "post", "send", "publish",
        "提交", "发布", "发送", "发表",
    })
    
    # 输入框标识
    INPUT_BOX: Set[str] = field(default_factory=lambda: {
        "comment", "reply", "write", "input", "textarea", "text",
        "评论", "回复", "输入", "加入对话", "说点什么", "写下你的评论",
        "what's happening", "what do you think", "add a comment",
    })
    
    # ========== 监控类语义 ==========
    
    # 价格相关
    PRICE: Set[str] = field(default_factory=lambda: {
        "price", "cost", "fee", "￥", "$", "€", "£",
        "价格", "售价", "现价", "原价", "促销价", "特价", "到手价",
        "元", "起",
    })
    
    # 库存相关
    STOCK: Set[str] = field(default_factory=lambda: {
        "stock", "inventory", "available", "in stock", "out of stock", "sold out",
        "库存", "有货", "无货", "缺货", "补货", "售罄", "已售罄",
        "立即购买", "加入购物车", "预约", "到货通知",
    })
    
    # 登录相关
    LOGIN: Set[str] = field(default_factory=lambda: {
        "login", "log in", "sign in", "signin", "authenticate",
        "登录", "登入", "登陆", "用户登录",
    })
    
    # 确认/提交相关
    CONFIRM: Set[str] = field(default_factory=lambda: {
        "confirm", "ok", "yes", "agree", "accept", "continue",
        "确认", "确定", "同意", "接受", "继续", "下一步",
    })
    
    # 预约/订制相关
    BOOKING: Set[str] = field(default_factory=lambda: {
        "book", "reserve", "appointment", "schedule",
        "预约", "预定", "挂号", "置顶", "订制",
    })
    
    # 播放相关
    PLAY: Set[str] = field(default_factory=lambda: {
        "play", "start", "resume", "watch",
        "播放", "开始", "继续播放", "观看",
        "▶", "▶️",
    })
    
    # 下载相关
    DOWNLOAD: Set[str] = field(default_factory=lambda: {
        "download", "save", "export", "get",
        "下载", "保存", "导出", "获取",
    })
    
    # 翻页相关
    NEXT_PAGE: Set[str] = field(default_factory=lambda: {
        "next", "next page", "more", "continue", "load more",
        "下一页", "下一章", "更多", "加载更多", "继续阅读",
        "→", "›", "»",
    })
    
    # 考勤打卡相关
    CLOCK_IN: Set[str] = field(default_factory=lambda: {
        "clock in", "punch in", "check in", "attendance",
        "打卡", "上班打卡", "下班打卡", "考勤", "签到",
    })
    
    @classmethod
    def _get_instance(cls) -> 'ActionSemantics':
        """获取单例实例（避免重复初始化开销）"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def _get_action_sets(cls) -> Dict[str, Set[str]]:
        """获取动作类型到关键词集合的映射（内部方法，消除重复代码）"""
        instance = cls._get_instance()
        return {
            # 养号类
            "upvote": instance.UPVOTE,
            "downvote": instance.DOWNVOTE,
            "follow": instance.FOLLOW,
            "unfollow": instance.UNFOLLOW,
            "comment": instance.COMMENT,
            "share": instance.SHARE,
            "save": instance.SAVE,
            "checkin": instance.CHECKIN,
            "coin": instance.COIN,
            "submit": instance.SUBMIT,
            # 监控类
            "price": instance.PRICE,
            "stock": instance.STOCK,
            "login": instance.LOGIN,
            "confirm": instance.CONFIRM,
            "booking": instance.BOOKING,
            "play": instance.PLAY,
            "download": instance.DOWNLOAD,
            "next_page": instance.NEXT_PAGE,
            "clock_in": instance.CLOCK_IN,
        }
    
    @classmethod
    def get_action_keywords(cls, action_type: str) -> Set[str]:
        """获取指定动作类型的关键词集合"""
        action_map = cls._get_action_sets()
        action_map["input"] = cls._get_instance().INPUT_BOX
        return action_map.get(action_type.lower(), set())
    
    @classmethod
    def match_action(cls, text: str) -> List[str]:
        """
        根据文本匹配可能的动作类型
        
        Args:
            text: 元素文本（如按钮名称）
            
        Returns:
            匹配到的动作类型列表
        """
        if not text:
            return []
        
        text_lower = text.lower().strip()
        matched = []
        
        for action_type, keywords in cls._get_action_sets().items():
            for keyword in keywords:
                if keyword.lower() in text_lower or text_lower in keyword.lower():
                    matched.append(action_type)
                    break
        
        return matched
    
    @classmethod
    def is_input_box(cls, text: str) -> bool:
        """判断是否为输入框"""
        if not text:
            return False
        
        text_lower = text.lower().strip()
        for keyword in cls._get_instance().INPUT_BOX:
            if keyword.lower() in text_lower:
                return True
        return False


# 平台别名映射（用于 URL 识别）
PLATFORM_ALIASES: Dict[str, str] = {
    # Reddit
    "reddit.com": "reddit",
    "old.reddit.com": "reddit",
    
    # Twitter/X
    "twitter.com": "twitter",
    "x.com": "twitter",
    
    # Hacker News
    "news.ycombinator.com": "hackernews",
    
    # LinkedIn
    "linkedin.com": "linkedin",
    "www.linkedin.com": "linkedin",
    
    # GitHub
    "github.com": "github",
    
    # 知乎
    "zhihu.com": "zhihu",
    "www.zhihu.com": "zhihu",
    
    # V2EX
    "v2ex.com": "v2ex",
    "www.v2ex.com": "v2ex",
    
    # 掘金
    "juejin.cn": "juejin",
    
    # B站
    "bilibili.com": "bilibili",
    "www.bilibili.com": "bilibili",
    
    # YouTube
    "youtube.com": "youtube",
    "www.youtube.com": "youtube",
    
    # Product Hunt
    "producthunt.com": "producthunt",
    "www.producthunt.com": "producthunt",
    
    # Dev.to
    "dev.to": "devto",
    
    # Medium
    "medium.com": "medium",
    
    # Stack Overflow
    "stackoverflow.com": "stackoverflow",
    
    # 微博
    "weibo.com": "weibo",
    "www.weibo.com": "weibo",
}


def identify_platform(url: str) -> str:
    """
    根据 URL 识别平台
    
    Args:
        url: 页面 URL
        
    Returns:
        平台标识符，无法识别时返回空字符串
    """
    # 输入验证
    if not url or not isinstance(url, str):
        return ""
    
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(url)
    except Exception:
        return ""
    
    domain = parsed.netloc.lower()
    
    if not domain:
        return ""
    
    # 移除 www. 前缀进行匹配
    domain_variants = [domain, domain.replace("www.", "")]
    
    for variant in domain_variants:
        if variant in PLATFORM_ALIASES:
            return PLATFORM_ALIASES[variant]
    
    # 未知平台，返回域名作为标识
    return domain.replace("www.", "").split(".")[0]
