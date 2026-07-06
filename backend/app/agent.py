from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentContext:
    actor_id: str
    objective: str
    triggering_memory: dict[str, Any]
    retrieved_memories: list[dict[str, Any]]
    relationship_state: dict[str, Any] | None
    world_facts: list[dict[str, Any]]
    allowed_tools: list[str]
    observations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "objective": self.objective,
            "triggering_memory": self.triggering_memory,
            "retrieved_memories": self.retrieved_memories,
            "relationship_state": self.relationship_state,
            "world_facts": self.world_facts,
            "allowed_tools": self.allowed_tools,
            "observations": self.observations,
        }


@dataclass
class ToolProposal:
    tool_name: str
    actor_id: str
    target_id: str
    topic: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "topic": self.topic,
            "reason": self.reason,
        }


@dataclass
class AgentStep:
    phase: str
    summary: str
    tool_proposal: ToolProposal | None = None
    observation: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "summary": self.summary,
            "tool_proposal": self.tool_proposal.to_dict() if self.tool_proposal else None,
            "observation": self.observation,
        }


@dataclass
class AgentDecision:
    actor_id: str
    decision: str
    context: AgentContext
    steps: list[AgentStep]
    tool_proposal: ToolProposal | None
    public_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "decision": self.decision,
            "context": self.context.to_dict(),
            "steps": [step.to_dict() for step in self.steps],
            "tool_proposal": self.tool_proposal.to_dict() if self.tool_proposal else None,
            "public_reason": self.public_reason,
        }


class DeterministicAgentLoop:
    """Small ReAct-style loop without an LLM.

    The structure mirrors popular agent runtimes:
    observe -> retrieve context -> propose tool -> observe validator result.

    It intentionally stores concise public summaries, not hidden chain-of-thought.
    Future LLM integration can replace the decision policy while keeping the
    context packet, tool proposal contract, and validation boundary stable.
    """

    def decide_after_memory(self, context: AgentContext) -> AgentDecision:
        steps = [
            AgentStep(
                phase="observe",
                summary="Received a new memory and normalized it into the agent context.",
                observation=context.triggering_memory.get("summary"),
            ),
            AgentStep(
                phase="retrieve",
                summary=(
                    f"Loaded {len(context.retrieved_memories)} related memories, "
                    "relationship state, and active event facts."
                ),
                observation="Context packet is ready for a bounded tool decision.",
            ),
        ]

        target_id = context.triggering_memory.get("target_id")
        topic = context.triggering_memory.get("topic", "missing_seeds")

        if (
            context.actor_id == "mira"
            and topic == "missing_seeds"
            and target_id in {"tomo", "ivo"}
            and "talk_to" in context.allowed_tools
        ):
            proposal = ToolProposal(
                tool_name="talk_to",
                actor_id=context.actor_id,
                target_id=target_id,
                topic=topic,
                reason="Mira prioritizes restoring order and wants to question the named person.",
            )
            steps.append(
                AgentStep(
                    phase="act",
                    summary="Proposed a bounded social investigation tool.",
                    tool_proposal=proposal,
                )
            )
            return AgentDecision(
                actor_id=context.actor_id,
                decision="investigate_missing_seeds",
                context=context,
                steps=steps,
                tool_proposal=proposal,
                public_reason="A missing-seeds memory named a specific villager, so Mira shifts into investigation.",
            )

        steps.append(
            AgentStep(
                phase="act",
                summary="No tool proposal matched deterministic policy.",
            )
        )
        return AgentDecision(
            actor_id=context.actor_id,
            decision="no_agent_action",
            context=context,
            steps=steps,
            tool_proposal=None,
            public_reason="The memory did not meet the threshold for a deterministic agent action.",
        )

