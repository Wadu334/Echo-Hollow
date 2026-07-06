from __future__ import annotations

import os
from typing import Any, Protocol

from .ai_schemas import AIActionProposal, AIDialogueResponse, AIMemorySummary


class AIProvider(Protocol):
    def propose_action(self, context: dict[str, Any]) -> AIActionProposal:
        ...

    def generate_dialogue(self, context: dict[str, Any]) -> AIDialogueResponse:
        ...

    def summarize_memory(self, context: dict[str, Any]) -> AIMemorySummary:
        ...


class DeterministicAIProvider:
    """Mock provider used by tests and local demos.

    The provider returns advisory objects only. World validators and scenario
    systems remain the sole authority for mutating state.
    """

    def propose_action(self, context: dict[str, Any]) -> AIActionProposal:
        actor_id = str(context.get("actor", {}).get("npc_id", context.get("actor_id", "mira")))
        triggering_memory = context.get("triggering_memory") or {}
        target_id = triggering_memory.get("target_id")
        source_memory_ids = []
        if triggering_memory.get("memory_id"):
            source_memory_ids.append(str(triggering_memory["memory_id"]))

        behavior_modifiers = set(context.get("actor", {}).get("behavior_modifiers", []))
        if actor_id == "mira" and target_id == "tomo" and "rumor_skepticism" in behavior_modifiers:
            return AIActionProposal(
                tool_name="npc_investigate",
                actor_id=actor_id,
                args={"actor_id": actor_id, "subject_id": "warehouse"},
                priority=8,
                reason="Mira has learned to verify seed rumors before accusing Tomo.",
                source_memory_ids=source_memory_ids,
            )

        if actor_id == "mira" and target_id in {"tomo", "ivo"}:
            return AIActionProposal(
                tool_name="npc_talk_to",
                actor_id=actor_id,
                args={"actor_id": actor_id, "target_id": target_id, "topic": "missing_seeds"},
                priority=7,
                reason="Mira should question the named villager before the rumor hardens.",
                source_memory_ids=source_memory_ids,
            )

        return AIActionProposal(
            tool_name="noop",
            actor_id=actor_id,
            args={"actor_id": actor_id},
            priority=0,
            reason="No deterministic action is useful for this context.",
            source_memory_ids=source_memory_ids,
        )

    def generate_dialogue(self, context: dict[str, Any]) -> AIDialogueResponse:
        speaker_id = str(context.get("speaker_id", "mira"))
        target_id = str(context.get("target_id", "tomo"))
        topic = str(context.get("topic", "missing_seeds"))
        lines = {
            ("mira", "tomo", "missing_seeds"): "Tomo, I heard your name tied to the missing seeds. I need your side before this spreads.",
            ("tomo", "mira", "missing_seeds"): "I did not take them. I need those seeds as much as anyone.",
            ("mira", "ivo", "missing_seeds"): "Ivo, repeat only what you can stand behind. This village is already tense.",
        }
        return AIDialogueResponse(
            speaker_id=speaker_id,
            target_id=target_id,
            topic=topic,
            line=lines.get((speaker_id, target_id, topic), "We should slow down and check the facts."),
        )

    def summarize_memory(self, context: dict[str, Any]) -> AIMemorySummary:
        owner_id = str(context.get("owner_id", "mira"))
        topic = str(context.get("topic", "missing_seeds"))
        source = str(context.get("summary", "A new village event was noticed."))
        return AIMemorySummary(
            owner_id=owner_id,
            topic=topic,
            summary=source[:180],
            importance=float(context.get("importance", 0.5)),
        )


class OpenAIProvider:
    """Optional placeholder kept behind env configuration.

    Real API calls are intentionally not wired into tests or demos yet.
    """

    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIProvider.")
        self.api_key = api_key

    def propose_action(self, context: dict[str, Any]) -> AIActionProposal:
        return DeterministicAIProvider().propose_action(context)

    def generate_dialogue(self, context: dict[str, Any]) -> AIDialogueResponse:
        return DeterministicAIProvider().generate_dialogue(context)

    def summarize_memory(self, context: dict[str, Any]) -> AIMemorySummary:
        return DeterministicAIProvider().summarize_memory(context)


def create_ai_provider() -> AIProvider:
    if os.getenv("ECHO_HOLLOW_AI_PROVIDER", "").lower() == "openai":
        return OpenAIProvider(api_key=os.getenv("OPENAI_API_KEY", ""))
    return DeterministicAIProvider()
