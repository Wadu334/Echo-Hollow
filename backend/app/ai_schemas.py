from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AIActionProposal:
    tool_name: str
    actor_id: str
    args: dict[str, Any]
    priority: int
    reason: str
    source_memory_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "actor_id": self.actor_id,
            "args": self.args,
            "priority": self.priority,
            "reason": self.reason,
            "source_memory_ids": self.source_memory_ids,
        }


@dataclass
class AIDialogueResponse:
    speaker_id: str
    target_id: str
    topic: str
    line: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "speaker_id": self.speaker_id,
            "target_id": self.target_id,
            "topic": self.topic,
            "line": self.line,
        }


@dataclass
class AIMemorySummary:
    owner_id: str
    topic: str
    summary: str
    importance: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "topic": self.topic,
            "summary": self.summary,
            "importance": self.importance,
        }
