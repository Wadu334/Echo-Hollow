from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .ai_gateway import AIProvider, create_ai_provider
from .ai_schemas import AIActionProposal


@dataclass
class AgentRuntimeStep:
    phase: str
    summary: str
    observation: str | None = None
    proposal: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "summary": self.summary,
            "observation": self.observation,
            "proposal": self.proposal,
        }


@dataclass
class AgentRuntimeDecision:
    actor_id: str
    decision: str
    context: dict[str, Any]
    steps: list[AgentRuntimeStep]
    tool_proposal: AIActionProposal | None
    queued_action_id: str | None
    public_reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_id": self.actor_id,
            "decision": self.decision,
            "context": self.context,
            "steps": [step.to_dict() for step in self.steps],
            "tool_proposal": self.tool_proposal.to_dict() if self.tool_proposal else None,
            "queued_action_id": self.queued_action_id,
            "public_reason": self.public_reason,
        }


class AgentRuntimeV1:
    """Bounded public-trace NPC runtime.

    The loop keeps the familiar ReAct shape:
    observe -> retrieve -> propose -> validate/defer -> observe result.
    It never stores hidden chain-of-thought; trace fields are player-facing
    summaries and compact context packets.
    """

    def __init__(
        self,
        provider: AIProvider | None = None,
        action_budget: int = 1,
        cooldown_minutes: int = 10,
        ttl_minutes: int = 90,
    ) -> None:
        self.provider = provider or create_ai_provider()
        self.action_budget = action_budget
        self.cooldown_minutes = cooldown_minutes
        self.ttl_minutes = ttl_minutes
        self._cooldowns: dict[str, int] = {}

    def propose_step(
        self,
        world: Any,
        actor_id: str,
        triggering_memory: Any | None = None,
    ) -> AgentRuntimeDecision:
        context = self.assemble_context(world, actor_id, triggering_memory)
        steps = [
            AgentRuntimeStep(
                phase="observe",
                summary="Normalized actor state, episode phase, and recent public events.",
                observation=f"Episode phase: {context['episode_phase']}",
            ),
            AgentRuntimeStep(
                phase="retrieve",
                summary=(
                    f"Loaded {len(context['retrieved_memories'])} memories, "
                    f"{len(context['relationships'])} relationships, and active rumor state."
                ),
                observation="Context packet is ready for bounded action scoring.",
            ),
        ]

        proposal = self._select_proposal(world, context)
        if proposal.tool_name == "noop":
            steps.append(
                AgentRuntimeStep(
                    phase="propose",
                    summary="No useful action passed the deterministic utility threshold.",
                    proposal=proposal.to_dict(),
                )
            )
            return AgentRuntimeDecision(
                actor_id=actor_id,
                decision="no_agent_action",
                context=context,
                steps=steps,
                tool_proposal=None,
                queued_action_id=None,
                public_reason=proposal.reason,
            )

        steps.append(
            AgentRuntimeStep(
                phase="propose",
                summary="Selected the highest utility deterministic action proposal for Director review.",
                proposal=proposal.to_dict(),
            )
        )
        return AgentRuntimeDecision(
            actor_id=actor_id,
            decision="action_proposed",
            context=context,
            steps=steps,
            tool_proposal=proposal,
            queued_action_id=None,
            public_reason=proposal.reason,
        )

    def run_step(
        self,
        world: Any,
        actor_id: str,
        triggering_memory: Any | None = None,
    ) -> AgentRuntimeDecision:
        """Backward-compatible wrapper that routes scheduling through Director when present."""
        decision = self.propose_step(world, actor_id, triggering_memory)
        if decision.tool_proposal is None:
            return decision

        director = getattr(world, "director", None)
        if director is not None:
            director_decision = director.review_agent_decision(world, decision)
            if director_decision.queued_action_ids:
                return AgentRuntimeDecision(
                    actor_id=decision.actor_id,
                    decision="action_queued",
                    context=decision.context,
                    steps=decision.steps,
                    tool_proposal=decision.tool_proposal,
                    queued_action_id=director_decision.queued_action_ids[0],
                    public_reason=decision.public_reason,
                )
            return decision

        # AgentRuntime is proposal-only. A world without a Director may inspect
        # the proposal, but it must not acquire a hidden mutation path.
        return decision

    def assemble_context(
        self,
        world: Any,
        actor_id: str,
        triggering_memory: Any | None = None,
    ) -> dict[str, Any]:
        actor = world.npcs[actor_id].to_dict()
        memory_dict = triggering_memory.to_dict() if triggering_memory is not None else None
        topic = "missing_seeds"
        if memory_dict:
            topic = str(memory_dict.get("topic", topic))

        retrieved_memories = [
            memory.to_dict()
            for memory in world.memories.values()
            if memory.owner_id == actor_id and memory.topic == topic
        ][-6:]
        relationships = {
            key: relationship.to_dict()
            for key, relationship in world.relationships.items()
            if relationship.owner_id == actor_id
        }
        event = world.world_events["evt_missing_seeds"]
        return {
            "actor_id": actor_id,
            "actor": actor,
            "current_goal": actor.get("current_goal"),
            "triggering_memory": memory_dict,
            "retrieved_memories": retrieved_memories,
            "relationships": relationships,
            "rumors": {key: rumor.to_dict() for key, rumor in world.rumors.items()},
            "active_event_facts": event["facts"],
            "episode_phase": event["phase"],
            "allowed_tools": [
                "npc_move_to",
                "npc_talk_to",
                "npc_share_memory",
                "npc_gossip",
                "npc_investigate",
            ],
            "world_minute": world.world_minute,
            "observations": [
                f"{actor_id} is at {actor['current_location']}.",
                f"Missing Seeds phase is {event['phase']}.",
            ],
        }

    def _select_proposal(self, world: Any, context: dict[str, Any]) -> AIActionProposal:
        actor_id = str(context["actor_id"])
        phase = str(context["episode_phase"])

        if phase.startswith("resolved_"):
            return AIActionProposal(
                tool_name="noop",
                actor_id=actor_id,
                args={"actor_id": actor_id},
                priority=0,
                reason="The Missing Seeds episode is already resolved.",
            )

        provider_proposal = self.provider.propose_action(context)

        if provider_proposal.tool_name != "noop":
            return provider_proposal

        if actor_id == "mira" and phase in {
            "conflicting_claims",
            "suspicion_spread",
            "confrontation_pending",
        }:
            rumor = world.rumors["rumor_tomo_took_seeds"]
            if "mira" in rumor.current_holder_ids:
                if "rumor_skepticism" in context["actor"].get("behavior_modifiers", []):
                    return AIActionProposal(
                        tool_name="npc_investigate",
                        actor_id="mira",
                        args={
                            "actor_id": "mira",
                            "subject_id": "warehouse",
                            "episode_id": "evt_missing_seeds",
                            "causal_claim_id": "tomo_took_seeds",
                        },
                        priority=8,
                        reason="Mira's reflection modifier favors checking the warehouse before accusing Tomo.",
                    )
                return AIActionProposal(
                    tool_name="npc_talk_to",
                    actor_id="mira",
                    args={
                        "actor_id": "mira",
                        "target_id": "tomo",
                        "topic": "missing_seeds",
                        "episode_id": "evt_missing_seeds",
                        "social_act": "careful_confrontation",
                        "causal_claim_id": "tomo_took_seeds",
                    },
                    priority=7,
                    reason="Mira needs to confront the named villager before rumor confidence rises.",
                )

        if actor_id == "mira" and phase == "confrontation_happened":
            rumor = world.rumors["rumor_tomo_took_seeds"]
            if "mira" in rumor.current_holder_ids and "ivo" not in rumor.current_holder_ids:
                return AIActionProposal(
                    tool_name="npc_gossip",
                    actor_id="mira",
                    args={
                        "actor_id": "mira",
                        "target_id": "ivo",
                        "rumor_id": rumor.rumor_id,
                        "episode_id": "evt_missing_seeds",
                    },
                    priority=4,
                    reason="Without evidence, Mira may repeat the rumor to Ivo and amplify suspicion.",
                )

        return provider_proposal

    def _cooldown_key(self, proposal: AIActionProposal) -> str:
        target = proposal.args.get("target_id") or proposal.args.get("subject_id") or proposal.args.get("location_id")
        return f"{proposal.actor_id}:{proposal.tool_name}:{target}"
