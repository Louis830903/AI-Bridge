"""
Tests for IntentEvolutionEngine
Phase II — P2-4
"""

import pytest
import json
import tempfile
from pathlib import Path

from aibridge.core.domain_registry import DomainIntentRegistry
from aibridge.core.intent_pattern import (
    IntentPattern,
    IntentMatch,
    Slot,
    SlotType,
)
from aibridge.core.intent_evolution import (
    IntentEvolutionEngine,
    IntentProposal,
)


# ============ Fixtures ============

@pytest.fixture
def registry():
    return DomainIntentRegistry()


@pytest.fixture
def temp_storage(tmp_path):
    return tmp_path / "intent_evolution.json"


@pytest.fixture
def evolution_engine(registry, temp_storage):
    return IntentEvolutionEngine(registry, storage_path=temp_storage)


@pytest.fixture
def sample_llm_match():
    """模拟 L3 LLM 返回的 IntentMatch"""
    pattern = IntentPattern(
        id="media.new_convert",
        domain="media",
        patterns=["把{输入:path}编码成{格式:format}"],
        description="视频编码转换",
        confidence_threshold=0.5,
        slots=[
            Slot("输入", SlotType.PATH, description="输入文件"),
            Slot("格式", SlotType.FORMAT, description="目标格式",
                 enum_values=["mp4", "avi", "h264"]),
        ],
        examples=["把video.mp4编码成h264"],
        adapter_id="ffmpeg",
    )
    return IntentMatch(
        pattern=pattern,
        confidence=0.75,
        matched_text="把video.mp4编码成h264",
        route="llm",
    )


# ============ Proposal Tests ============

class TestIntentProposal:
    def test_creation(self, sample_llm_match):
        proposal = IntentProposal(
            pattern=sample_llm_match.pattern,
            source_input="把video.mp4编码成h264",
            confidence=0.75,
        )
        assert proposal.status == "pending"
        assert proposal.frequency == 1
        assert proposal.pattern.id == "media.new_convert"

    def test_to_dict_and_from_dict(self, sample_llm_match):
        proposal = IntentProposal(
            pattern=sample_llm_match.pattern,
            source_input="把video.mp4编码成h264",
            confidence=0.75,
            frequency=2,
        )
        data = proposal.to_dict()
        restored = IntentProposal.from_dict(data)
        assert restored.pattern.id == "media.new_convert"
        assert restored.frequency == 2
        assert restored.confidence == 0.75


# ============ Observe Tests ============

class TestObserve:
    def test_observe_creates_proposal(self, evolution_engine, sample_llm_match):
        result = evolution_engine.observe(
            "把video.mp4编码成h264", sample_llm_match
        )
        assert result is not None
        assert result.pattern.id == "media.new_convert"
        assert result.frequency == 1
        assert evolution_engine.total_proposals == 1

    def test_observe_increments_frequency(self, evolution_engine, sample_llm_match):
        # 第一次
        evolution_engine.observe("把video.mp4编码成h264", sample_llm_match)
        # 第二次（相同输入）
        result = evolution_engine.observe("把video.mp4编码成h264", sample_llm_match)
        assert result.frequency == 2
        assert evolution_engine.total_proposals == 1  # 不会重复创建

    def test_observe_skips_non_llm_match(self, evolution_engine):
        """非 llm route 的匹配不被观察"""
        pattern = IntentPattern(
            id="test.x", domain="test",
            patterns=["{x:string}"], description="test",
        )
        match = IntentMatch(
            pattern=pattern, confidence=0.9, matched_text="hello",
            route="exact",
        )
        result = evolution_engine.observe("hello", match)
        assert result is None
        assert evolution_engine.total_proposals == 0

    def test_observe_skips_semantic_route(self, evolution_engine):
        pattern = IntentPattern(
            id="test.y", domain="test",
            patterns=["{x:string}"], description="test",
        )
        match = IntentMatch(
            pattern=pattern, confidence=0.7, matched_text="hello",
            route="semantic",
        )
        result = evolution_engine.observe("hello", match)
        assert result is None

    def test_observe_different_inputs_creates_separate(self, evolution_engine,
                                                       sample_llm_match):
        evolution_engine.observe("把video.mp4编码成h264", sample_llm_match)
        evolution_engine.observe("把另一个文件编码成h264", sample_llm_match)
        assert evolution_engine.total_proposals == 2


# ============ Approval Tests ============

class TestApproval:
    def test_get_pending_proposals_below_threshold(self, evolution_engine,
                                                    sample_llm_match):
        evolution_engine.observe("把video.mp4编码成h264", sample_llm_match)
        # frequency=1 < min_frequency=3
        pending = evolution_engine.get_pending_proposals(min_frequency=3)
        assert len(pending) == 0

    def test_get_pending_proposals_meets_threshold(self, evolution_engine,
                                                    sample_llm_match):
        for _ in range(3):
            evolution_engine.observe("把video.mp4编码成h264", sample_llm_match)
        pending = evolution_engine.get_pending_proposals(min_frequency=3)
        assert len(pending) == 1

    def test_approve_registers_to_l1(self, evolution_engine, registry,
                                      sample_llm_match):
        evolution_engine.observe("把video.mp4编码成h264", sample_llm_match)
        key = evolution_engine._normalize("把video.mp4编码成h264")
        proposal = evolution_engine.approve(key)
        assert proposal is not None
        assert proposal.status == "approved"
        # 验证已注册到 L1
        pattern = registry.get_pattern("media.new_convert")
        assert pattern is not None

    def test_approve_nonexistent_key(self, evolution_engine):
        result = evolution_engine.approve("nonexistent")
        assert result is None

    def test_reject_proposal(self, evolution_engine, sample_llm_match):
        evolution_engine.observe("把video.mp4编码成h264", sample_llm_match)
        key = evolution_engine._normalize("把video.mp4编码成h264")
        proposal = evolution_engine.reject(key)
        assert proposal is not None
        assert proposal.status == "rejected"

    def test_rejected_not_in_pending(self, evolution_engine, sample_llm_match):
        for _ in range(3):
            evolution_engine.observe("把video.mp4编码成h264", sample_llm_match)
        key = evolution_engine._normalize("把video.mp4编码成h264")
        evolution_engine.reject(key)
        pending = evolution_engine.get_pending_proposals(min_frequency=1)
        assert all(p.status != "rejected" for p in pending)


# ============ Persistence Tests ============

class TestPersistence:
    def test_save_and_load(self, registry, temp_storage, sample_llm_match):
        engine = IntentEvolutionEngine(registry, storage_path=temp_storage)
        engine.observe("把video.mp4编码成h264", sample_llm_match)

        # 新引擎从同一文件加载
        engine2 = IntentEvolutionEngine(registry, storage_path=temp_storage)
        assert engine2.total_proposals == 1
        key = engine2._normalize("把video.mp4编码成h264")
        loaded = engine2.get_proposal(key)
        assert loaded is not None
        assert loaded.pattern.id == "media.new_convert"

    def test_load_empty_file(self, registry, tmp_path):
        empty_file = tmp_path / "empty.json"
        empty_file.write_text("{}")
        engine = IntentEvolutionEngine(registry, storage_path=empty_file)
        assert engine.total_proposals == 0

    def test_load_corrupted_file(self, registry, tmp_path):
        corrupted = tmp_path / "corrupted.json"
        corrupted.write_text("{not valid json")
        engine = IntentEvolutionEngine(registry, storage_path=corrupted)
        assert engine.total_proposals == 0  # 不崩溃

    def test_persist_after_approve(self, registry, temp_storage, sample_llm_match):
        engine = IntentEvolutionEngine(registry, storage_path=temp_storage)
        engine.observe("把video.mp4编码成h264", sample_llm_match)
        key = engine._normalize("把video.mp4编码成h264")
        engine.approve(key)

        # 重新加载
        engine2 = IntentEvolutionEngine(registry, storage_path=temp_storage)
        loaded = engine2.get_proposal(key)
        assert loaded is not None
        assert loaded.status == "approved"
