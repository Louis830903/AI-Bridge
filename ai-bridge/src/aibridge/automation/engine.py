"""
通用养号引擎核心

基于语义匹配的跨平台养号自动化引擎。
通过分析页面快照的 accessibility tree，自动识别并执行养号动作。
"""

import re
import random
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum

from .semantics import ActionSemantics, identify_platform


class ActionType(Enum):
    """动作类型枚举"""
    UPVOTE = "upvote"
    DOWNVOTE = "downvote"
    FOLLOW = "follow"
    COMMENT = "comment"
    SHARE = "share"
    SAVE = "save"
    CHECKIN = "checkin"
    COIN = "coin"


@dataclass
class PageElement:
    """页面元素"""
    uid: str
    element_type: str  # button, link, textbox, etc.
    text: str
    pressed: bool = False
    expanded: bool = False
    disabled: bool = False
    url: Optional[str] = None
    
    @property
    def is_actionable(self) -> bool:
        """是否可执行动作"""
        return not self.disabled and not self.pressed


@dataclass
class NurtureAction:
    """养号动作"""
    action_type: ActionType
    element: PageElement
    priority: int = 0  # 优先级，数字越大越优先
    
    
@dataclass
class NurtureResult:
    """养号结果"""
    success: bool
    action_type: ActionType
    element_uid: str
    message: str = ""


class SnapshotParser:
    """快照解析器 - 解析 Chrome DevTools MCP 的页面快照"""
    
    # 匹配快照行的正则：uid=xxx type "text" [attributes]
    LINE_PATTERN = re.compile(
        r'uid=(\S+)\s+(\w+)\s+"([^"]*)"(?:\s+(.*))?'
    )
    
    # 匹配简单行的正则：uid=xxx type
    SIMPLE_LINE_PATTERN = re.compile(
        r'uid=(\S+)\s+(\w+)(?:\s+(.*))?'
    )
    
    @classmethod
    def parse(cls, snapshot_text: str) -> List[PageElement]:
        """
        解析快照文本为元素列表
        
        Args:
            snapshot_text: Chrome DevTools MCP 返回的快照文本
            
        Returns:
            页面元素列表
        """
        # 空快照处理
        if not snapshot_text or not snapshot_text.strip():
            return []
        
        elements = []
        parse_errors = []
        
        for line_num, line in enumerate(snapshot_text.split("\n"), 1):
            line = line.strip()
            if not line or not line.startswith("uid="):
                continue
            
            try:
                element = cls._parse_line(line)
                if element:
                    elements.append(element)
            except Exception as e:
                parse_errors.append(f"Line {line_num}: {e}")
        
        # 记录解析错误但不中断
        if parse_errors:
            logging.getLogger(__name__).warning(
                f"快照解析出现 {len(parse_errors)} 个警告"
            )
        
        return elements
    
    @classmethod
    def _parse_line(cls, line: str) -> Optional[PageElement]:
        """解析单行快照"""
        # 尝试匹配带文本的行
        match = cls.LINE_PATTERN.match(line)
        if match:
            uid, elem_type, text, attrs_str = match.groups()
            attrs = cls._parse_attributes(attrs_str or "")
            return PageElement(
                uid=uid,
                element_type=elem_type,
                text=text,
                pressed=attrs.get("pressed", False),
                expanded=attrs.get("expanded", False),
                disabled=attrs.get("disabled", False),
                url=attrs.get("url"),
            )
        
        # 尝试匹配简单行
        match = cls.SIMPLE_LINE_PATTERN.match(line)
        if match:
            uid, elem_type, attrs_str = match.groups()
            attrs = cls._parse_attributes(attrs_str or "")
            return PageElement(
                uid=uid,
                element_type=elem_type,
                text="",
                pressed=attrs.get("pressed", False),
                expanded=attrs.get("expanded", False),
                disabled=attrs.get("disabled", False),
                url=attrs.get("url"),
            )
        
        return None
    
    @staticmethod
    def _parse_attributes(attrs_str: str) -> Dict[str, Any]:
        """解析属性字符串"""
        attrs = {}
        if "pressed" in attrs_str:
            attrs["pressed"] = True
        if "expanded" in attrs_str:
            attrs["expanded"] = True
        if "disabled" in attrs_str or "disableable disabled" in attrs_str:
            attrs["disabled"] = True
        
        # 提取 URL
        url_match = re.search(r'url="([^"]*)"', attrs_str)
        if url_match:
            attrs["url"] = url_match.group(1)
        
        return attrs


class AccountNurtureEngine:
    """
    通用养号引擎
    
    使用方式：
    1. 传入页面快照
    2. 引擎自动识别可执行的养号动作
    3. 返回推荐的动作列表
    4. 调用方执行动作
    
    Example:
        engine = AccountNurtureEngine()
        
        # 分析快照，获取推荐动作
        actions = engine.analyze(snapshot_text, target_actions=["upvote", "comment"])
        
        # 遍历执行
        for action in actions:
            print(f"建议: {action.action_type.value} -> {action.element.uid}")
    """
    
    def __init__(self):
        self.semantics = ActionSemantics()
    
    def analyze(
        self, 
        snapshot_text: str, 
        target_actions: Optional[List[str]] = None,
        max_actions: int = 10,
        skip_pressed: bool = True,
    ) -> List[NurtureAction]:
        """
        分析快照，返回推荐的养号动作
        
        Args:
            snapshot_text: 页面快照文本
            target_actions: 目标动作类型列表，如 ["upvote", "comment"]
                           不指定则返回所有可识别的动作
            max_actions: 最大返回动作数
            skip_pressed: 是否跳过已执行的动作（如已点赞）
            
        Returns:
            推荐的养号动作列表，按优先级排序
        """
        # 解析快照
        elements = SnapshotParser.parse(snapshot_text)
        
        # 识别动作
        actions = []
        for element in elements:
            # 跳过已执行的动作
            if skip_pressed and element.pressed:
                continue
            
            # 跳过禁用的元素
            if element.disabled:
                continue
            
            # 只处理可交互元素
            if element.element_type not in ("button", "link"):
                continue
            
            # 匹配动作类型
            matched_types = ActionSemantics.match_action(element.text)
            
            for action_type_str in matched_types:
                # 过滤目标动作
                if target_actions and action_type_str not in target_actions:
                    continue
                
                try:
                    action_type = ActionType(action_type_str)
                    priority = self._calculate_priority(element, action_type)
                    actions.append(NurtureAction(
                        action_type=action_type,
                        element=element,
                        priority=priority,
                    ))
                except ValueError:
                    continue
        
        # 按优先级排序
        actions.sort(key=lambda x: x.priority, reverse=True)
        
        return actions[:max_actions]
    
    def find_input_box(self, snapshot_text: str) -> Optional[PageElement]:
        """
        查找评论输入框
        
        Args:
            snapshot_text: 页面快照文本
            
        Returns:
            输入框元素，未找到返回 None
        """
        elements = SnapshotParser.parse(snapshot_text)
        
        for element in elements:
            if element.element_type == "textbox":
                if ActionSemantics.is_input_box(element.text):
                    return element
        
        return None
    
    def find_submit_button(self, snapshot_text: str) -> Optional[PageElement]:
        """
        查找提交按钮
        
        Args:
            snapshot_text: 页面快照文本
            
        Returns:
            提交按钮元素
        """
        elements = SnapshotParser.parse(snapshot_text)
        submit_keywords = ActionSemantics.get_action_keywords("submit")
        
        for element in elements:
            if element.element_type == "button" and not element.disabled:
                text_lower = element.text.lower()
                for keyword in submit_keywords:
                    if keyword.lower() in text_lower:
                        return element
        
        return None
    
    def _calculate_priority(self, element: PageElement, action_type: ActionType) -> int:
        """
        计算动作优先级
        
        优先级规则：
        - 点赞类动作优先级较高
        - 带有数字（如赞数）的元素优先级更高
        - 主帖的动作优先级高于评论
        """
        priority = 0
        
        # 动作类型基础优先级
        type_priority = {
            ActionType.UPVOTE: 100,
            ActionType.SAVE: 80,
            ActionType.FOLLOW: 70,
            ActionType.SHARE: 60,
            ActionType.COMMENT: 50,
            ActionType.COIN: 40,
            ActionType.CHECKIN: 90,  # 签到优先级高
        }
        priority += type_priority.get(action_type, 0)
        
        # 按钮类型优先级
        if element.element_type == "button":
            priority += 10
        
        return priority
    
    @staticmethod
    def generate_comment(topic: str = "", style: str = "tech") -> str:
        """
        生成评论内容
        
        Args:
            topic: 帖子主题/关键词（用于未来个性化）
            style: 风格 - tech(技术), casual(随意), enthusiastic(热情)
            
        Returns:
            评论文本
            
        Raises:
            ValueError: 当 style 无效时
        """
        tech_comments = [
            "This is really impressive! Looking forward to trying it out.",
            "Great work! The implementation looks solid.",
            "Interesting approach. Have you considered performance benchmarks?",
            "Thanks for sharing! This solves a problem I've been thinking about.",
            "Nice! The API design is clean and intuitive.",
            "Solid release. The new features look promising.",
            "This is exactly what I needed. Thanks!",
        ]
        
        casual_comments = [
            "Nice!",
            "Cool project!",
            "Thanks for sharing!",
            "Looks great!",
            "Interesting!",
        ]
        
        enthusiastic_comments = [
            "This is amazing! Can't wait to use it!",
            "Absolutely love this! Great job!",
            "Wow, this is exactly what I've been looking for!",
            "Incredible work! The community needed this!",
        ]
        
        style_map = {
            "tech": tech_comments,
            "casual": casual_comments,
            "enthusiastic": enthusiastic_comments,
        }
        
        if style not in style_map:
            raise ValueError(
                f"无效的评论风格 '{style}'，支持的风格: {list(style_map.keys())}"
            )
        
        comments = style_map[style]
        
        # TODO: 未来可以基于 topic 进行个性化
        _ = topic  # 标记为有意未使用
        
        return random.choice(comments)


# 便捷函数
def analyze_page(snapshot: str, actions: Optional[List[str]] = None) -> List[NurtureAction]:
    """
    便捷函数：分析页面快照
    
    Args:
        snapshot: 页面快照文本
        actions: 目标动作列表，如 ["upvote", "follow"]
        
    Returns:
        推荐的养号动作列表
    """
    engine = AccountNurtureEngine()
    return engine.analyze(snapshot, target_actions=actions)


def get_upvote_targets(snapshot: str, max_count: int = 5) -> List[PageElement]:
    """
    便捷函数：获取可点赞的目标
    
    Args:
        snapshot: 页面快照文本
        max_count: 最大返回数量
        
    Returns:
        可点赞的元素列表
    """
    engine = AccountNurtureEngine()
    actions = engine.analyze(snapshot, target_actions=["upvote"], max_actions=max_count)
    return [action.element for action in actions]
