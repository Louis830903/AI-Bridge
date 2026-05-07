"""
IntentPattern Protocol — 意图模式协议

定义适配器向意图引擎注册能力的标准协议。
包括 Slot 类型系统、IntentPattern 能力声明、IntentMatch 匹配结果、
CompositeIntent 复合意图以及 SlotParser 槽位提取工具。

Phase II — 意图引擎通用化 (v0.10.0)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse


# ============ Slot Types ============

class SlotType(Enum):
    """槽位值类型"""
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    PATH = "path"           # 文件路径
    URL = "url"             # URL
    FORMAT = "format"       # 媒体/文档格式
    DURATION = "duration"   # 时间长度
    BOOLEAN = "boolean"


# ============ Slot ============

@dataclass
class Slot:
    """意图中的参数槽位"""
    name: str                       # 槽位名: "输入格式"
    type: SlotType                  # 值类型
    required: bool = True           # 是否必填
    default: Any = None             # 默认值
    description: str = ""           # 语义说明
    enum_values: list[str] = field(default_factory=list)  # FORMAT 等枚举值

    def __repr__(self) -> str:
        return (f"Slot(name={self.name!r}, type={self.type.value}, "
                f"required={self.required})")


# ============ IntentPattern ============

@dataclass
class IntentPattern:
    """单个意图模式——适配器向引擎注册的能力声明"""
    id: str                         # 唯一标识: "ffmpeg.convert"
    domain: str                     # 领域: "media"
    patterns: list[str]            # 自然语言模式模板 (含 {slot:type} 占位符)
    description: str               # 人类可读描述
    confidence_threshold: float = 0.6
    slots: list[Slot] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    adapter_id: str = ""           # 回填：关联的适配器
    tags: list[str] = field(default_factory=list)

    # 模式模板示例:
    # "把{输入文件:path}转成{目标格式:format}"
    # "压缩{输入文件:path}到{目标大小:integer}MB以内"

    def __post_init__(self):
        if not self.adapter_id and "." in self.id:
            # 从 id 推断 adapter_id: "ffmpeg.convert" → "ffmpeg"
            self.adapter_id = self.id.split(".")[0]


# ============ IntentMatch ============

@dataclass
class IntentMatch:
    """意图匹配结果"""
    pattern: IntentPattern          # 命中的意图模式
    confidence: float               # 置信度 0.0-1.0
    matched_text: str               # 匹配到的原始文本片段
    resolved_slots: dict[str, Any] = field(default_factory=dict)  # {"输入文件": Path("a.mp4")}
    route: str = "exact"            # "exact" | "semantic" | "llm"
    alternatives: list[IntentMatch] = field(default_factory=list)

    def __repr__(self) -> str:
        return (f"IntentMatch(pattern={self.pattern.id!r}, "
                f"confidence={self.confidence:.2f}, route={self.route!r})")


# ============ CompositeIntent ============

@dataclass
class CompositeIntent:
    """复合意图——跨多适配器的组合任务"""
    sub_intents: list[IntentMatch]          # 子意图列表
    dag: dict[str, list[str]]               # 执行 DAG: {"ffmpeg": ["office"], "office": []}
    original_text: str = ""                 # 原始用户输入

    @property
    def adapter_ids(self) -> list[str]:
        """获取涉及的所有适配器 ID"""
        return list(self.dag.keys())

    @property
    def is_parallel(self) -> bool:
        """是否为可并行的复合意图（无依赖）"""
        return all(len(deps) == 0 for deps in self.dag.values())


# ============ Slot Parsers ============

class SlotParser:
    """槽位值解析器集合——从字符串中提取类型化槽位值"""

    @staticmethod
    def parse(value_str: str, slot_type: SlotType,
              enum_values: list[str] | None = None) -> Any | None:
        """根据 SlotType 解析字符串值

        Args:
            value_str: 待解析的原始字符串
            slot_type: 目标槽位类型
            enum_values: 枚举约束值列表

        Returns:
            解析后的值，解析失败或不合规时返回 None
        """
        parser = _SLOT_PARSERS.get(slot_type)
        if parser is None:
            return value_str  # fallback: 保持字符串

        try:
            result = parser(value_str)
        except (ValueError, TypeError):
            return None

        # 枚举校验
        if enum_values and isinstance(result, str):
            if result.lower() not in (v.lower() for v in enum_values):
                return None

        return result

    @staticmethod
    def parse_string(value_str: str) -> str:
        return value_str.strip()

    @staticmethod
    def parse_integer(value_str: str) -> int:
        return int(value_str.strip())

    @staticmethod
    def parse_float(value_str: str) -> float:
        return float(value_str.strip())

    @staticmethod
    def parse_path(value_str: str) -> Path:
        s = value_str.strip().strip('"').strip("'")
        return Path(s).expanduser().resolve()

    @staticmethod
    def parse_url(value_str: str) -> str:
        s = value_str.strip()
        if not s.startswith(('http://', 'https://')):
            # 自动补全协议头
            s = 'https://' + s
        parsed = urlparse(s)
        # netloc 必须包含点号（域名）或为 localhost/IP
        if not parsed.netloc or '.' not in parsed.netloc:
            if parsed.netloc not in ('localhost',):
                # 检查是否为 IP 地址
                import re as _re
                if not _re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', parsed.netloc):
                    raise ValueError(f"Invalid URL: {value_str}")
        return s

    @staticmethod
    def parse_format(value_str: str) -> str:
        return value_str.strip().lower().lstrip('.')

    @staticmethod
    def parse_duration(value_str: str) -> float:
        """解析时长字符串，返回秒数。

        支持格式:
        - "10s", "2.5s" → 秒
        - "3m", "1.5m" → 分钟
        - "1h", "0.5h" → 小时
        - "1:30" → 分:秒
        - "5" → 默认秒
        """
        s = value_str.strip().lower()
        if ':' in s:
            parts = s.split(':')
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
            raise ValueError(f"Invalid duration format: {value_str}")
        if s.endswith('h'):
            return float(s[:-1]) * 3600
        if s.endswith('m'):
            return float(s[:-1]) * 60
        if s.endswith('s'):
            return float(s[:-1])
        return float(s)

    @staticmethod
    def parse_boolean(value_str: str) -> bool:
        s = value_str.strip().lower()
        return s in ('true', '1', 'yes', 'y', 'on', '是')


# 解析器映射表
_SLOT_PARSERS: dict[SlotType, Callable[[str], Any]] = {
    SlotType.STRING: SlotParser.parse_string,
    SlotType.INTEGER: SlotParser.parse_integer,
    SlotType.FLOAT: SlotParser.parse_float,
    SlotType.PATH: SlotParser.parse_path,
    SlotType.URL: SlotParser.parse_url,
    SlotType.FORMAT: SlotParser.parse_format,
    SlotType.DURATION: SlotParser.parse_duration,
    SlotType.BOOLEAN: SlotParser.parse_boolean,
}


# ============ Pattern Template Engine ============

class PatternMatcher:
    """将 IntentPattern 中的模板字符串编译为正则并执行匹配"""

    # 匹配 {slot_name:type} 或 {slot_name} 占位符
    _SLOT_RE = re.compile(r'\{([^{}:]+)(?::([^{}]+))?\}')

    @classmethod
    def compile_pattern(cls, pattern: str, slots: list[Slot]) -> tuple[re.Pattern, list[Slot]]:
        """编译模板字符串为正则表达式。

        将 "把{输入:path}转成{目标:format}" 转换为可匹配的正则，
        同时返回该正则各捕获组对应的 Slot 对象。

        Returns:
            (compiled_regex, ordered_slots)
        """
        slot_map: dict[str, Slot] = {s.name: s for s in slots}
        ordered_slots: list[Slot] = []
        regex_parts: list[str] = []

        last_end = 0
        for m in cls._SLOT_RE.finditer(pattern):
            # 添加占位符前的字面文本（容许空白间隔）
            literal = re.escape(pattern[last_end:m.start()])
            if literal:
                # 在非空前缀后插入可选的空白容忍
                regex_parts.append(r'\s*' + literal + r'\s*')
            else:
                regex_parts.append(literal)

            slot_name = m.group(1)
            slot_type_str = m.group(2)

            # 查找对应 Slot
            slot = slot_map.get(slot_name)
            if slot is None:
                # 自动创建 Slot（无类型注解时默认为 STRING）
                slot_type = SlotType.STRING
                if slot_type_str:
                    try:
                        slot_type = SlotType(slot_type_str)
                    except ValueError:
                        pass
                slot = Slot(name=slot_name, type=slot_type)
            elif slot_type_str:
                # 模板中的类型注解覆盖 Slot 定义
                try:
                    slot = Slot(
                        name=slot.name,
                        type=SlotType(slot_type_str),
                        required=slot.required,
                        default=slot.default,
                        description=slot.description,
                        enum_values=slot.enum_values,
                    )
                except ValueError:
                    pass

            ordered_slots.append(slot)

            # 生成捕获组（根据类型调整匹配规则）
            if slot.type in (SlotType.PATH, SlotType.URL, SlotType.FORMAT):
                # 路径/URL/格式：非空白字符
                regex_parts.append(r'(\S+)')
            elif slot.type == SlotType.DURATION:
                # 时长：数字+单位 或 数字:数字
                regex_parts.append(r'([\d:.]+[smh]?)')
            elif slot.type in (SlotType.INTEGER, SlotType.FLOAT):
                # 数字：容许空白间隔
                regex_parts.append(r'\s*(\d+\.?\d*)\s*')
            else:
                # STRING/BOOLEAN：贪心匹配至结尾（模板中唯一或最后占位符时）
                # 注意：search 模式时贪心捕获；后续占位符将自然截断
                regex_parts.append(r'\s*(.+)\s*')

            last_end = m.end()

        # 添加尾部字面文本
        tail = re.escape(pattern[last_end:])
        if tail:
            regex_parts.append(r'\s*' + tail + r'\s*')
        else:
            regex_parts.append(tail)

        full_regex = ''.join(regex_parts)
        return re.compile(full_regex, re.IGNORECASE), ordered_slots

    @classmethod
    def match_pattern(cls, user_input: str, intent_pattern: IntentPattern) -> IntentMatch | None:
        """尝试将用户输入与意图模式的所有模板匹配。

        Returns:
            IntentMatch 或 None
        """
        user_input = user_input.strip()
        best_match: IntentMatch | None = None
        best_confidence = 0.0

        for template in intent_pattern.patterns:
            compiled, ordered_slots = cls.compile_pattern(template, intent_pattern.slots)
            m = compiled.search(user_input) if compiled.pattern.startswith('.') else compiled.match(user_input)
            if m is None:
                # 尝试 search 模式（宽松匹配）
                m = compiled.search(user_input)

            if m is None:
                continue

            # 解析捕获组
            resolved: dict[str, Any] = {}
            confidence = 1.0
            for i, slot in enumerate(ordered_slots):
                group_idx = i + 1
                raw_value = m.group(group_idx) if group_idx <= m.lastindex else None
                if raw_value is None:
                    if slot.default is not None:
                        resolved[slot.name] = slot.default
                    elif slot.required:
                        confidence *= 0.5  # 必填槽位缺失，降权
                    continue
                parsed = SlotParser.parse(raw_value, slot.type, slot.enum_values)
                if parsed is None:
                    if slot.default is not None:
                        resolved[slot.name] = slot.default
                    elif not slot.required:
                        continue
                    else:
                        confidence *= 0.3
                    continue
                resolved[slot.name] = parsed

            if confidence > best_confidence:
                best_confidence = confidence
                best_match = IntentMatch(
                    pattern=intent_pattern,
                    confidence=min(confidence, 0.95),  # 模式匹配上限 0.95
                    matched_text=m.group(0),
                    resolved_slots=resolved,
                    route="exact",
                )

        if best_match and best_match.confidence >= intent_pattern.confidence_threshold:
            return best_match
        return None
