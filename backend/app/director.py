from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


DIRECTOR_DECISION_TYPES = {
    "approve",
    "defer",
    "reject",
    "rewrite",
    "fallback",
    "inject_episode_beat",
    "budget_skipped",
    "duplicate_skipped",
    "noop",
}

SOCIAL_TOOLS = {"npc_talk_to", "npc_gossip", "npc_share_memory", "npc_investigate"}


@dataclass
class DirectorConfig:
    max_agent_steps_per_tick: int = 2
    max_social_actions_per_hour: int = 4
    max_gossip_spread_per_day: int = 6
    min_minutes_between_major_beats: int = 30
    fallback_move_delay_minutes: int = 1
    fallback_retry_delay_minutes: int = 2
    suspicion_spread_beat_delay_minutes: int = 45
    enable_episode_interventions: bool = True
    enable_llm_director: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_agent_steps_per_tick": self.max_agent_steps_per_tick,
            "max_social_actions_per_hour": self.max_social_actions_per_hour,
            "max_gossip_spread_per_day": self.max_gossip_spread_per_day,
            "min_minutes_between_major_beats": self.min_minutes_between_major_beats,
            "fallback_move_delay_minutes": self.fallback_move_delay_minutes,
            "fallback_retry_delay_minutes": self.fallback_retry_delay_minutes,
            "suspicion_spread_beat_delay_minutes": self.suspicion_spread_beat_delay_minutes,
            "enable_episode_interventions": self.enable_episode_interventions,
            "enable_llm_director": self.enable_llm_director,
        }


@dataclass
class DirectorDecision:
    decision_id: str
    decision_type: str
    actor_id: str | None
    tool_name: str | None
    priority: int
    reason: str
    source: str
    proposal: dict[str, Any] | None = None
    queued_action_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.decision_type not in DIRECTOR_DECISION_TYPES:
            raise ValueError(f"Unknown director decision type: {self.decision_type}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type,
            "actor_id": self.actor_id,
            "tool_name": self.tool_name,
            "priority": self.priority,
            "reason": self.reason,
            "source": self.source,
            "proposal": self.proposal,
            "queued_action_ids": self.queued_action_ids,
        }


@dataclass
class DirectorTrace:
    world_minute: int
    phase: str | None
    summary: str
    decisions: list[DirectorDecision]

    def to_dict(self) -> dict[str, Any]:
        return {
            "world_minute": self.world_minute,
            "phase": self.phase,
            "summary": self.summary,
            "decisions": [decision.to_dict() for decision in self.decisions],
        }


class VillageDirector:
    """Deterministic global scheduler for NPC proposals.

    The director coordinates pacing and queueing only. It does not mutate
    memories, relationships, facts, or episode phase/resolution.
    """

    def __init__(self, config: DirectorConfig | None = None) -> None:
        self.config = config or DirectorConfig()
        self._decision_counter = 0
        self._agent_step_minutes: list[int] = []
        self._social_action_minutes: list[int] = []
        self._gossip_day_counts: dict[int, int] = {}
        self._last_major_beat_minute: int | None = None
        self.last_trace: DirectorTrace | None = None

    def on_memory_written(self, world: Any, memory: Any) -> list[str]:
        if memory.owner_id not in world.npcs or memory.topic != "missing_seeds":
            return []
        if not self._has_agent_step_budget(world):
            decision = self._decision(
                decision_type="budget_skipped",
                actor_id=memory.owner_id,
                tool_name=None,
                priority=0,
                reason="Director skipped proposal because the per-tick agent step budget is exhausted.",
                source="memory_written",
                proposal={"memory_id": memory.memory_id, "topic": memory.topic},
            )
            self._record_trace(world, "Agent proposal skipped by Director budget.", [decision])
            return []

        self._agent_step_minutes.append(world.world_minute)
        agent_decision = world.agent_runtime.propose_step(world, memory.owner_id, memory)
        world.last_agent_trace = agent_decision.to_dict()
        world._append_event(
            event_type="agent_action_planned",
            actor_id=memory.owner_id,
            target_id=None,
            payload=world.last_agent_trace,
        )
        decision = self.review_agent_decision(world, agent_decision)
        return decision.queued_action_ids

    def review_agent_decision(self, world: Any, agent_decision: Any) -> DirectorDecision:
        proposal = agent_decision.tool_proposal
        if proposal is None:
            decision = self._decision(
                decision_type="noop",
                actor_id=agent_decision.actor_id,
                tool_name=None,
                priority=0,
                reason=agent_decision.public_reason,
                source="agent_runtime",
                proposal=None,
            )
            self._record_trace(world, "Director observed no actionable NPC proposal.", [decision])
            return decision

        proposal_dict = proposal.to_dict()
        if world.has_pending_action(proposal.actor_id, proposal.tool_name, proposal.args):
            decision = self._decision(
                decision_type="duplicate_skipped",
                actor_id=proposal.actor_id,
                tool_name=proposal.tool_name,
                priority=proposal.priority,
                reason="Equivalent action is already pending in the action queue.",
                source="agent_runtime",
                proposal=proposal_dict,
            )
            self._record_trace(world, "Director skipped a duplicate action proposal.", [decision])
            return decision

        if self._budget_exceeded(world, proposal.tool_name, proposal.priority):
            decision = self._decision(
                decision_type="budget_skipped",
                actor_id=proposal.actor_id,
                tool_name=proposal.tool_name,
                priority=proposal.priority,
                reason="Director skipped a low-priority action because its pacing budget is exhausted.",
                source="agent_runtime",
                proposal=proposal_dict,
            )
            self._record_trace(world, "Director skipped an action due to pacing budget.", [decision])
            return decision

        action_id = world.enqueue_action(
            actor_id=proposal.actor_id,
            tool_name=proposal.tool_name,
            args=proposal.args,
            priority=proposal.priority,
            execute_after_minute=world.world_minute,
            expires_at_minute=world.world_minute + world.agent_runtime.ttl_minutes,
            source_memory_ids=proposal.source_memory_ids,
            reason=proposal.reason,
        )
        self._record_budget_use(world, proposal.tool_name)
        decision = self._decision(
            decision_type="approve",
            actor_id=proposal.actor_id,
            tool_name=proposal.tool_name,
            priority=proposal.priority,
            reason=proposal.reason,
            source="agent_runtime",
            proposal=proposal_dict,
            queued_action_ids=[action_id],
        )
        self._record_trace(world, "Director approved an NPC proposal for validation.", [decision])
        return decision

    def on_tick(self, world: Any) -> list[str]:
        self._prune_recent_budget_windows(world)
        decision = self.inject_episode_beat_if_needed(world)
        return decision.queued_action_ids if decision else []

    def on_action_rejected(
        self,
        world: Any,
        action: Any,
        validation_result: dict[str, Any],
    ) -> DirectorDecision | None:
        if action.tool_name != "npc_talk_to" or validation_result.get("rejection_code") != "target_unavailable":
            return None
        target_id = action.args.get("target_id")
        if action.actor_id not in world.npcs or target_id not in world.npcs:
            return None

        target_location = world.npcs[str(target_id)].current_location
        move_action_id = world.enqueue_action(
            actor_id=action.actor_id,
            tool_name="npc_move_to",
            args={"actor_id": action.actor_id, "location_id": target_location},
            priority=action.priority + 1,
            execute_after_minute=world.world_minute + self.config.fallback_move_delay_minutes,
            expires_at_minute=world.world_minute + 30,
            source_memory_ids=action.source_memory_ids,
            reason=f"Director fallback for {action.action_id}: move toward unavailable target.",
            status="fallback_planned",
        )
        retry_action_id = world.enqueue_action(
            actor_id=action.actor_id,
            tool_name=action.tool_name,
            args=action.args,
            priority=max(0, action.priority - 1),
            execute_after_minute=world.world_minute + self.config.fallback_retry_delay_minutes,
            expires_at_minute=world.world_minute + world.agent_runtime.ttl_minutes,
            source_memory_ids=action.source_memory_ids,
            reason=f"Director retry after fallback movement for {action.action_id}.",
        )
        decision = self._decision(
            decision_type="fallback",
            actor_id=action.actor_id,
            tool_name=action.tool_name,
            priority=action.priority,
            reason="Director scheduled movement and retry after target was unavailable.",
            source="validator_rejection",
            proposal=action.to_dict(),
            queued_action_ids=[move_action_id, retry_action_id],
        )
        self._record_trace(world, "Director planned fallback movement for a rejected NPC talk action.", [decision])
        return decision

    def inject_episode_beat_if_needed(self, world: Any) -> DirectorDecision | None:
        if not self.config.enable_episode_interventions:
            return None
        event = world.world_events.get("evt_missing_seeds")
        if not event or event.get("phase") != "suspicion_spread":
            return None
        phase_started_minute = int(event.get("phase_started_minute") or world.world_minute)
        if world.world_minute - phase_started_minute < self.config.suspicion_spread_beat_delay_minutes:
            return None
        if (
            self._last_major_beat_minute is not None
            and world.world_minute - self._last_major_beat_minute < self.config.min_minutes_between_major_beats
        ):
            return None
        if self._has_equivalent_pending_action(
            world,
            actor_id="mira",
            tool_name="npc_talk_to",
            args={"actor_id": "mira", "target_id": "tomo", "topic": "missing_seeds"},
        ):
            return None

        tomo_location = world.npcs["tomo"].current_location
        move_action_id = world.enqueue_action(
            actor_id="mira",
            tool_name="npc_move_to",
            args={"actor_id": "mira", "location_id": tomo_location},
            priority=8,
            execute_after_minute=world.world_minute,
            expires_at_minute=world.world_minute + 30,
            source_memory_ids=[],
            reason="Director injected a Missing Seeds confrontation beat: move Mira toward Tomo.",
            status="fallback_planned",
        )
        talk_action_id = world.enqueue_action(
            actor_id="mira",
            tool_name="npc_talk_to",
            args={"actor_id": "mira", "target_id": "tomo", "topic": "missing_seeds"},
            priority=8,
            execute_after_minute=world.world_minute + self.config.fallback_retry_delay_minutes,
            expires_at_minute=world.world_minute + world.agent_runtime.ttl_minutes,
            source_memory_ids=[],
            reason="Director injected a Missing Seeds confrontation beat.",
        )
        self._last_major_beat_minute = world.world_minute
        decision = self._decision(
            decision_type="inject_episode_beat",
            actor_id="mira",
            tool_name="npc_talk_to",
            priority=8,
            reason="Suspicion has spread long enough that the episode needs a confrontation beat.",
            source="episode_beat",
            proposal={"event_id": "evt_missing_seeds", "phase": "suspicion_spread"},
            queued_action_ids=[move_action_id, talk_action_id],
        )
        self._record_trace(world, "Director injected a Missing Seeds confrontation beat.", [decision])
        return decision

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config.to_dict(),
            "last_trace": self.last_trace.to_dict() if self.last_trace else None,
            "recent_agent_steps": len(self._agent_step_minutes),
            "recent_social_actions": len(self._social_action_minutes),
            "gossip_day_counts": self._gossip_day_counts,
            "last_major_beat_minute": self._last_major_beat_minute,
        }

    def _decision(
        self,
        decision_type: str,
        actor_id: str | None,
        tool_name: str | None,
        priority: int,
        reason: str,
        source: str,
        proposal: dict[str, Any] | None,
        queued_action_ids: list[str] | None = None,
    ) -> DirectorDecision:
        self._decision_counter += 1
        return DirectorDecision(
            decision_id=f"dir_{self._decision_counter:06d}",
            decision_type=decision_type,
            actor_id=actor_id,
            tool_name=tool_name,
            priority=priority,
            reason=reason,
            source=source,
            proposal=proposal,
            queued_action_ids=queued_action_ids or [],
        )

    def _record_trace(self, world: Any, summary: str, decisions: list[DirectorDecision]) -> None:
        phase = None
        if "evt_missing_seeds" in world.world_events:
            phase = world.world_events["evt_missing_seeds"].get("phase")
        trace = DirectorTrace(
            world_minute=world.world_minute,
            phase=phase,
            summary=summary,
            decisions=decisions,
        )
        self.last_trace = trace
        world.last_director_trace = trace.to_dict()
        for decision in decisions:
            event_type = self._event_type_for_decision(decision.decision_type)
            world._append_event(
                event_type=event_type,
                actor_id=decision.actor_id,
                target_id=decision.queued_action_ids[0] if decision.queued_action_ids else None,
                payload=decision.to_dict(),
            )

    def _event_type_for_decision(self, decision_type: str) -> str:
        return {
            "fallback": "director_fallback_planned",
            "inject_episode_beat": "director_episode_beat_injected",
            "budget_skipped": "director_budget_skipped",
            "duplicate_skipped": "director_duplicate_skipped",
        }.get(decision_type, "director_decision")

    def _has_agent_step_budget(self, world: Any) -> bool:
        self._agent_step_minutes = [
            minute for minute in self._agent_step_minutes if minute == world.world_minute
        ]
        return len(self._agent_step_minutes) < self.config.max_agent_steps_per_tick

    def _budget_exceeded(self, world: Any, tool_name: str, priority: int) -> bool:
        if priority >= 7 and tool_name != "npc_gossip":
            return False
        self._prune_recent_budget_windows(world)
        if tool_name == "npc_gossip":
            day = world.day
            if self._gossip_day_counts.get(day, 0) >= self.config.max_gossip_spread_per_day:
                return True
        if tool_name in SOCIAL_TOOLS:
            return len(self._social_action_minutes) >= self.config.max_social_actions_per_hour and priority < 7
        return False

    def _record_budget_use(self, world: Any, tool_name: str) -> None:
        if tool_name in SOCIAL_TOOLS:
            self._social_action_minutes.append(world.world_minute)
        if tool_name == "npc_gossip":
            self._gossip_day_counts[world.day] = self._gossip_day_counts.get(world.day, 0) + 1

    def _prune_recent_budget_windows(self, world: Any) -> None:
        self._social_action_minutes = [
            minute for minute in self._social_action_minutes if world.world_minute - minute < 60
        ]
        self._agent_step_minutes = [
            minute for minute in self._agent_step_minutes if minute == world.world_minute
        ]

    def _has_equivalent_pending_action(
        self,
        world: Any,
        actor_id: str,
        tool_name: str,
        args: dict[str, Any],
    ) -> bool:
        return world.has_pending_action(actor_id, tool_name, args)
