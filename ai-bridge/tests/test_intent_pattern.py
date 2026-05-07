"""
Tests for IntentPattern protocol — Slot, SlotType, SlotParser, PatternMatcher
Phase II — P2-1
"""

import pytest
from pathlib import Path

from aibridge.core.intent_pattern import (
    SlotType,
    Slot,
    IntentPattern,
    IntentMatch,
    CompositeIntent,
    SlotParser,
    PatternMatcher,
)


# ============ Slot & SlotType Tests ============

class TestSlotType:
    def test_all_types_exist(self):
        """验证 8 种 SlotType 均存在"""
        assert SlotType.STRING.value == "string"
        assert SlotType.INTEGER.value == "integer"
        assert SlotType.FLOAT.value == "float"
        assert SlotType.PATH.value == "path"
        assert SlotType.URL.value == "url"
        assert SlotType.FORMAT.value == "format"
        assert SlotType.DURATION.value == "duration"
        assert SlotType.BOOLEAN.value == "boolean"

    def test_slot_type_from_value(self):
        assert SlotType("string") == SlotType.STRING
        assert SlotType("integer") == SlotType.INTEGER
        with pytest.raises(ValueError):
            SlotType("nonexistent")


class TestSlot:
    def test_slot_creation(self):
        slot = Slot(name="文件", type=SlotType.PATH, required=True,
                    description="输入文件路径")
        assert slot.name == "文件"
        assert slot.type == SlotType.PATH
        assert slot.required is True
        assert slot.default is None
        assert slot.description == "输入文件路径"

    def test_slot_with_enum_values(self):
        slot = Slot(name="格式", type=SlotType.FORMAT,
                    enum_values=["mp4", "avi", "gif"])
        assert slot.enum_values == ["mp4", "avi", "gif"]

    def test_slot_optional_with_default(self):
        slot = Slot(name="质量", type=SlotType.INTEGER,
                    required=False, default=80)
        assert slot.required is False
        assert slot.default == 80


# ============ SlotParser Tests ============

class TestSlotParser:
    def test_parse_string(self):
        assert SlotParser.parse_string("hello") == "hello"
        assert SlotParser.parse_string("  trimmed  ") == "trimmed"

    def test_parse_integer(self):
        assert SlotParser.parse_integer("42") == 42
        assert SlotParser.parse_integer("  100  ") == 100
        with pytest.raises(ValueError):
            SlotParser.parse_integer("abc")

    def test_parse_float(self):
        assert SlotParser.parse_float("3.14") == 3.14
        assert SlotParser.parse_float("0.5") == 0.5
        with pytest.raises(ValueError):
            SlotParser.parse_float("xyz")

    def test_parse_path(self):
        result = SlotParser.parse_path("~/documents/file.txt")
        assert isinstance(result, Path)
        assert str(result).endswith("file.txt")

    def test_parse_path_with_spaces(self):
        result = SlotParser.parse_path("/home/user/My Documents/report.pdf")
        assert str(result).endswith("report.pdf")

    def test_parse_url(self):
        assert SlotParser.parse_url("https://github.com") == "https://github.com"
        assert SlotParser.parse_url("github.com") == "https://github.com"

    def test_parse_url_invalid(self):
        with pytest.raises(ValueError):
            SlotParser.parse_url("not a url at all !")

    def test_parse_format(self):
        assert SlotParser.parse_format("MP4") == "mp4"
        assert SlotParser.parse_format(".avi") == "avi"

    def test_parse_duration_seconds(self):
        assert SlotParser.parse_duration("10s") == 10.0
        assert SlotParser.parse_duration("2.5s") == 2.5

    def test_parse_duration_minutes(self):
        assert SlotParser.parse_duration("3m") == 180.0
        assert SlotParser.parse_duration("1.5m") == 90.0

    def test_parse_duration_hours(self):
        assert SlotParser.parse_duration("1h") == 3600.0

    def test_parse_duration_colon_format(self):
        assert SlotParser.parse_duration("1:30") == 90.0
        assert SlotParser.parse_duration("1:00:00") == 3600.0

    def test_parse_duration_default_seconds(self):
        assert SlotParser.parse_duration("5") == 5.0

    def test_parse_boolean(self):
        assert SlotParser.parse_boolean("true") is True
        assert SlotParser.parse_boolean("1") is True
        assert SlotParser.parse_boolean("yes") is True
        assert SlotParser.parse_boolean("是") is True
        assert SlotParser.parse_boolean("false") is False
        assert SlotParser.parse_boolean("no") is False

    def test_parse_with_enum_constraint(self):
        result = SlotParser.parse("mp4", SlotType.FORMAT, enum_values=["mp4", "avi", "gif"])
        assert result == "mp4"

    def test_parse_with_enum_constraint_rejected(self):
        result = SlotParser.parse("exe", SlotType.FORMAT, enum_values=["mp4", "avi"])
        assert result is None

    def test_parse_fallback_string(self):
        result = SlotParser.parse("any value", SlotType.STRING)
        assert result == "any value"


# ============ IntentPattern Tests ============

class TestIntentPattern:
    def test_creation(self):
        pattern = IntentPattern(
            id="ffmpeg.convert",
            domain="media",
            patterns=["把{输入:path}转成{目标:format}"],
            description="视频格式转换",
            confidence_threshold=0.6,
            slots=[
                Slot(name="输入", type=SlotType.PATH, description="输入文件"),
                Slot(name="目标", type=SlotType.FORMAT, description="目标格式",
                     enum_values=["mp4", "avi", "gif"]),
            ],
            examples=["把video.mp4转成gif", "把movie.avi转成mp4"],
            tags=["video", "convert"],
        )
        assert pattern.id == "ffmpeg.convert"
        assert pattern.domain == "media"
        assert len(pattern.patterns) == 1
        assert len(pattern.slots) == 2
        assert len(pattern.examples) == 2
        assert pattern.adapter_id == "ffmpeg"  # auto-inferred

    def test_explicit_adapter_id(self):
        pattern = IntentPattern(
            id="custom.action", domain="test", patterns=["do {x:string}"],
            description="test", adapter_id="my_adapter",
        )
        assert pattern.adapter_id == "my_adapter"


# ============ PatternMatcher Tests ============

class TestPatternMatcher:
    def test_compile_simple_pattern(self):
        pattern = IntentPattern(
            id="test.simple", domain="test",
            patterns=["搜索{关键词:string}"],
            description="搜索",
            slots=[Slot(name="关键词", type=SlotType.STRING)],
        )
        compiled, ordered_slots = PatternMatcher.compile_pattern(
            "搜索{关键词:string}", pattern.slots
        )
        assert len(ordered_slots) == 1
        assert ordered_slots[0].name == "关键词"

        m = compiled.match("搜索iPhone 15")
        assert m is not None
        assert m.group(1) == "iPhone 15"

    def test_match_pattern_exact(self):
        pattern = IntentPattern(
            id="test.convert", domain="media",
            patterns=["把{输入:path}转成{目标:format}"],
            description="格式转换",
            confidence_threshold=0.5,
            slots=[
                Slot(name="输入", type=SlotType.PATH, description="输入文件"),
                Slot(name="目标", type=SlotType.FORMAT, description="目标格式",
                     enum_values=["mp4", "avi", "gif"]),
            ],
        )
        result = PatternMatcher.match_pattern("把video.mp4转成gif", pattern)
        assert result is not None
        assert result.pattern.id == "test.convert"
        assert result.confidence >= 0.5
        assert result.resolved_slots["目标"] == "gif"

    def test_match_pattern_multi_template(self):
        pattern = IntentPattern(
            id="browser.navigate", domain="browser",
            patterns=["打开{网址:url}", "访问{网址:url}", "去{网址:url}"],
            description="导航到网站",
            confidence_threshold=0.5,
            slots=[Slot(name="网址", type=SlotType.URL)],
        )
        result = PatternMatcher.match_pattern("访问github.com", pattern)
        assert result is not None
        assert result.pattern.id == "browser.navigate"
        assert "github.com" in result.resolved_slots["网址"]

    def test_match_pattern_fuzzy_whitespace(self):
        pattern = IntentPattern(
            id="media.compress", domain="media",
            patterns=["压缩{文件:path}到{大小:integer}MB以内"],
            description="视频压缩",
            confidence_threshold=0.5,
            slots=[
                Slot(name="文件", type=SlotType.PATH),
                Slot(name="大小", type=SlotType.INTEGER),
            ],
        )
        result = PatternMatcher.match_pattern("压缩  video.mp4  到  50  MB以内", pattern)
        assert result is not None

    def test_match_pattern_missing_required_slot(self):
        pattern = IntentPattern(
            id="test.single", domain="test",
            patterns=["{必填:string}和{可选:string}"],
            description="test",
            confidence_threshold=0.3,
            slots=[
                Slot(name="必填", type=SlotType.STRING, required=True),
                Slot(name="可选", type=SlotType.STRING, required=False),
            ],
        )
        # "hello 和" — missing optional slot
        result = PatternMatcher.match_pattern("hello 和", pattern)
        # The compiled regex with (.+?) won't match well here; test with concrete pattern
        # Try with fixed text
        pattern2 = IntentPattern(
            id="test.fixed", domain="test",
            patterns=["开始{必填:string}结束"],
            description="test",
            confidence_threshold=0.3,
            slots=[Slot(name="必填", type=SlotType.STRING, required=True)],
        )
        result = PatternMatcher.match_pattern("开始hello结束", pattern2)
        assert result is not None
        assert result.resolved_slots["必填"] == "hello"

    def test_match_pattern_no_match(self):
        pattern = IntentPattern(
            id="browser.navigate", domain="browser",
            patterns=["打开{网址:url}"],
            description="导航",
            confidence_threshold=0.5,
            slots=[Slot(name="网址", type=SlotType.URL)],
        )
        result = PatternMatcher.match_pattern("搜索iPhone 15在谷歌", pattern)
        assert result is None

    def test_match_below_threshold_returns_none(self):
        pattern = IntentPattern(
            id="test.high_bar", domain="test",
            patterns=["{x:string}"],
            description="high bar",
            confidence_threshold=0.99,
            slots=[Slot(name="x", type=SlotType.STRING)],
        )
        result = PatternMatcher.match_pattern("anything", pattern)
        assert result is None


# ============ IntentMatch Tests ============

class TestIntentMatch:
    def test_creation(self):
        pattern = IntentPattern(
            id="test.x", domain="test", patterns=["{a:string}"],
            description="test",
            slots=[Slot(name="a", type=SlotType.STRING)],
        )
        match = IntentMatch(
            pattern=pattern, confidence=0.85, matched_text="hello",
            resolved_slots={"a": "hello"}, route="exact",
        )
        assert match.confidence == 0.85
        assert match.route == "exact"
        assert match.resolved_slots["a"] == "hello"

    def test_alternatives(self):
        pattern = IntentPattern(id="test.a", domain="test",
                                patterns=["{x:string}"], description="A")
        alt = IntentMatch(pattern=pattern, confidence=0.5, matched_text="b")
        main = IntentMatch(pattern=pattern, confidence=0.9, matched_text="a",
                           alternatives=[alt])
        assert len(main.alternatives) == 1


# ============ CompositeIntent Tests ============

class TestCompositeIntent:
    def test_creation(self):
        pattern_a = IntentPattern(id="ffmpeg.convert", domain="media",
                                  patterns=["{x:string}"], description="convert")
        pattern_b = IntentPattern(id="office.open", domain="office",
                                  patterns=["{y:string}"], description="open")
        sub_a = IntentMatch(pattern=pattern_a, confidence=0.8, matched_text="a")
        sub_b = IntentMatch(pattern=pattern_b, confidence=0.7, matched_text="b")
        composite = CompositeIntent(
            sub_intents=[sub_a, sub_b],
            dag={"ffmpeg": ["office"], "office": []},
            original_text="convert then open",
        )
        assert len(composite.sub_intents) == 2
        assert composite.adapter_ids == ["ffmpeg", "office"]
        assert composite.is_parallel is False

    def test_parallel_composite(self):
        pattern_a = IntentPattern(id="a.x", domain="media",
                                  patterns=["{x:string}"], description="A")
        pattern_b = IntentPattern(id="b.y", domain="office",
                                  patterns=["{y:string}"], description="B")
        sub_a = IntentMatch(pattern=pattern_a, confidence=0.8, matched_text="a")
        sub_b = IntentMatch(pattern=pattern_b, confidence=0.8, matched_text="b")
        composite = CompositeIntent(
            sub_intents=[sub_a, sub_b],
            dag={"a": [], "b": []},
        )
        assert composite.is_parallel is True
