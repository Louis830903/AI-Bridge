"""
IntentEvolutionEngine — 意图自进化系统

从 L3 LLM 成功案例中学习，生成意图注册提案。
支持提案累积、频率阈值审核、审批/拒绝、JSON 持久化。

Phase II — 意图引擎通用化 (v0.10.0)
"""

from __future__ import annotations

import json
import time
import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from aibridge.core.intent_pattern import IntentPattern, IntentMatch
from aibridge.core.domain_registry import DomainIntentRegistry

logger = logging.getLogger(__name__)


@dataclass
class IntentProposal:
    """L3 LLM 解析成功后生成的意图注册提案"""
    pattern: IntentPattern
    source_input: str               # 触发提案的原始输入
    confidence: float
    frequency: int = 1              # 累计出现次数
    proposed_at: float = field(default_factory=time.time)
    status: str = "pending"         # pending | approved | rejected

    def to_dict(self) -> dict:
        return {
            "pattern_id": self.pattern.id,
            "pattern_domain": self.pattern.domain,
            "pattern_patterns": self.pattern.patterns,
            "pattern_description": self.pattern.description,
            "pattern_confidence_threshold": self.pattern.confidence_threshold,
            "pattern_slots": [
                {
                    "name": s.name,
                    "type": s.type.value,
                    "required": s.required,
                    "default": s.default,
                    "description": s.description,
                    "enum_values": s.enum_values,
                }
                for s in self.pattern.slots
            ],
            "pattern_examples": self.pattern.examples,
            "pattern_adapter_id": self.pattern.adapter_id,
            "pattern_tags": self.pattern.tags,
            "source_input": self.source_input,
            "confidence": self.confidence,
            "frequency": self.frequency,
            "proposed_at": self.proposed_at,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IntentProposal":
        from aibridge.core.intent_pattern import Slot, SlotType
        slots = [
            Slot(
                name=s["name"],
                type=SlotType(s["type"]),
                required=s.get("required", True),
                default=s.get("default"),
                description=s.get("description", ""),
                enum_values=s.get("enum_values", []),
            )
            for s in data.get("pattern_slots", [])
        ]
        pattern = IntentPattern(
            id=data["pattern_id"],
            domain=data["pattern_domain"],
            patterns=data["pattern_patterns"],
            description=data["pattern_description"],
            confidence_threshold=data.get("pattern_confidence_threshold", 0.6),
            slots=slots,
            examples=data.get("pattern_examples", []),
            adapter_id=data.get("pattern_adapter_id", ""),
            tags=data.get("pattern_tags", []),
        )
        return cls(
            pattern=pattern,
            source_input=data["source_input"],
            confidence=data["confidence"],
            frequency=data.get("frequency", 1),
            proposed_at=data.get("proposed_at", time.time()),
            status=data.get("status", "pending"),
        )


class IntentEvolutionEngine:
    """意图自进化引擎——从 L3 成功案例中学习"""

    def __init__(
        self,
        registry: DomainIntentRegistry,
        storage_path: Optional[Path] = None,
    ):
        self.registry = registry
        self.storage_path = storage_path or Path("data/intent_evolution.json")
        self._proposals: dict[str, IntentProposal] = {}
        self._load()

    # ========== 观察 ==========

    def observe(self, user_input: str, match: IntentMatch) -> IntentProposal | None:
        """观察 L3 解析结果，生成或更新提案。

        Args:
            user_input: 触发 L3 的原始用户输入
            match: L3 LLM 返回的 IntentMatch (route="llm")

        Returns:
            提案对象（新建或更新）

        Raises:
            ValueError: match.route 不是 "llm"
        """
        if match.route != "llm":
            logger.debug(
                f"Skipping non-LLM match: {match.pattern.id} (route={match.route})"
            )
            return None

        key = self._normalize(user_input)
        if key in self._proposals:
            proposal = self._proposals[key]
            proposal.frequency += 1
            proposal.confidence = max(proposal.confidence, match.confidence)
            logger.info(
                f"Updated proposal '{key}': frequency={proposal.frequency}"
            )
        else:
            proposal = IntentProposal(
                pattern=match.pattern,
                source_input=user_input,
                confidence=match.confidence,
            )
            self._proposals[key] = proposal
            logger.info(
                f"New proposal '{key}': {match.pattern.id} "
                f"(conf={match.confidence:.2f})"
            )

        self._save()
        return proposal

    # ========== 审核 ==========

    def get_pending_proposals(self, min_frequency: int = 3) -> list[IntentProposal]:
        """获取达到频率阈值的待审核提案"""
        return [
            p for p in self._proposals.values()
            if p.status == "pending" and p.frequency >= min_frequency
        ]

    def approve(self, key: str) -> IntentProposal | None:
        """审核通过，注册到 L1。

        Args:
            key: 归一化后的提案键

        Returns:
            已批准的提案，如果不存在则返回 None
        """
        if key not in self._proposals:
            logger.warning(f"Proposal '{key}' not found")
            return None

        proposal = self._proposals[key]
        if proposal.status != "pending":
            logger.warning(
                f"Proposal '{key}' already {proposal.status}, cannot approve"
            )
            return proposal

        proposal.status = "approved"
        try:
            self.registry.register(
                proposal.pattern.adapter_id, [proposal.pattern]
            )
            logger.info(
                f"Approved and registered proposal '{key}': {proposal.pattern.id}"
            )
        except Exception as e:
            logger.error(f"Failed to register approved pattern: {e}")
            proposal.status = "pending"  # 回滚
            raise

        self._save()
        return proposal

    def reject(self, key: str) -> IntentProposal | None:
        """审核拒绝

        Args:
            key: 归一化后的提案键

        Returns:
            已拒绝的提案，如果不存在则返回 None
        """
        if key not in self._proposals:
            logger.warning(f"Proposal '{key}' not found")
            return None

        proposal = self._proposals[key]
        proposal.status = "rejected"
        self._save()
        logger.info(f"Rejected proposal '{key}': {proposal.pattern.id}")
        return proposal

    # ========== 查询 ==========

    @property
    def total_proposals(self) -> int:
        return len(self._proposals)

    def get_proposal(self, key: str) -> IntentProposal | None:
        return self._proposals.get(key)

    def get_proposals_by_status(self, status: str) -> list[IntentProposal]:
        return [p for p in self._proposals.values() if p.status == status]

    # ========== 内部 ==========

    def _normalize(self, text: str) -> str:
        """输入归一化——生成提案键"""
        # 去空白、小写、去标点
        normalized = text.strip().lower()
        normalized = re.sub(r'[^\w\u4e00-\u9fff\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized[:80]  # 截断到 80 字符

    def _load(self) -> None:
        """从 JSON 文件加载持久化提案"""
        if not self.storage_path.exists():
            return

        try:
            data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            for key, item in data.items():
                try:
                    self._proposals[key] = IntentProposal.from_dict(item)
                except Exception as e:
                    logger.warning(f"Failed to load proposal '{key}': {e}")
            logger.info(
                f"Loaded {len(self._proposals)} proposals from {self.storage_path}"
            )
        except Exception as e:
            logger.error(f"Failed to load evolution data: {e}")

    def _save(self) -> None:
        """持久化提案到 JSON 文件"""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                key: proposal.to_dict()
                for key, proposal in self._proposals.items()
            }
            self.storage_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Failed to save evolution data: {e}")
