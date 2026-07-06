from __future__ import annotations

from typing import Any


MISSING_SEEDS_PHASES = [
    "public_problem",
    "conflicting_claims",
    "suspicion_spread",
    "confrontation_pending",
    "confrontation_happened",
    "evidence_found",
    "resolution_pending",
    "resolved_reconciled",
    "resolved_false_accusation",
    "resolved_player_manipulated",
]


class MissingSeedsEpisodeManager:
    def __init__(self, event_id: str = "evt_missing_seeds") -> None:
        self.event_id = event_id

    def on_claim_memory(self, world: Any, memory: Any) -> None:
        event = world.world_events[self.event_id]
        if memory.topic != "missing_seeds" or memory.owner_id != "mira":
            return
        if event["phase"] == "public_problem":
            self.set_phase(world, "conflicting_claims")
            event["rumor_started_minute"] = world.world_minute

    def on_action_executed(self, world: Any, action: Any) -> None:
        event = world.world_events[self.event_id]
        if event["phase"].startswith("resolved_"):
            return

        if action.tool_name == "npc_talk_to" and action.actor_id == "mira" and action.args.get("target_id") == "tomo":
            self.set_phase(world, "confrontation_happened")
            event["confrontation_minute"] = world.world_minute
            return

        if action.tool_name == "npc_gossip" and action.args.get("rumor_id") == "rumor_tomo_took_seeds":
            if event["phase"] in {"conflicting_claims", "confrontation_pending", "confrontation_happened"}:
                self.set_phase(world, "suspicion_spread")
            return

        if action.tool_name == "npc_investigate" and action.args.get("subject_id") == "warehouse":
            if event["phase"] in {"conflicting_claims", "suspicion_spread", "confrontation_pending", "confrontation_happened"}:
                self.set_phase(world, "evidence_found")
            return

    def on_tick(self, world: Any) -> None:
        event = world.world_events[self.event_id]
        phase = event["phase"]
        if phase.startswith("resolved_"):
            return

        rumor = world.rumors["rumor_tomo_took_seeds"]
        if rumor.spread_count >= 3 and phase in {"conflicting_claims", "confrontation_pending", "confrontation_happened"}:
            self.set_phase(world, "suspicion_spread")

        rumor_started = event.get("rumor_started_minute")
        confrontation_minute = event.get("confrontation_minute")
        if phase in {"conflicting_claims", "suspicion_spread", "confrontation_pending", "confrontation_happened"}:
            too_long_since_rumor = rumor_started is not None and world.world_minute - int(rumor_started) >= 180
            too_long_since_confrontation = (
                confrontation_minute is not None and world.world_minute - int(confrontation_minute) >= 90
            )
            if too_long_since_rumor or too_long_since_confrontation:
                self.resolve_event(world, "false_accusation")

    def set_phase(self, world: Any, phase: str) -> None:
        if phase not in MISSING_SEEDS_PHASES:
            raise ValueError(f"Unknown Missing Seeds phase: {phase}")
        event = world.world_events[self.event_id]
        if event["phase"] == phase:
            return
        previous = event["phase"]
        event["phase"] = phase
        event["phase_started_minute"] = world.world_minute
        world._append_event(
            event_type="episode_phase_changed",
            actor_id=None,
            target_id=self.event_id,
            payload={"from": previous, "to": phase},
        )

    def resolve_event(self, world: Any, path: str) -> None:
        event = world.world_events[self.event_id]
        if event["phase"].startswith("resolved_"):
            return

        if path == "reconciled":
            resolved_phase = "resolved_reconciled"
            event["resolution_path"] = "reconciled"
            event["state"] = "resolved"
            world._change_relationship("mira", "tomo", {"trust": 0.22, "affinity": 0.08}, self.event_id)
            world._change_relationship("tomo", "mira", {"trust": 0.12, "affinity": 0.06}, self.event_id)
            rumor = world.rumors["rumor_tomo_took_seeds"]
            rumor.verified_state = "false"
            rumor.confidence = 0.08
            world._write_reflection_memory(
                owner_id="mira",
                summary="Mira corrected the Tomo seed rumor after evidence showed the bag was torn near the warehouse.",
                source_event_log_id=self.event_id,
                modifier="rumor_skepticism",
            )
        elif path == "false_accusation":
            resolved_phase = "resolved_false_accusation"
            event["resolution_path"] = "false_accusation"
            event["state"] = "resolved"
            world._change_relationship("mira", "tomo", {"trust": -0.2, "affinity": -0.08}, self.event_id)
            world._change_relationship("tomo", "mira", {"trust": -0.28, "affinity": -0.12}, self.event_id)
            if "falsely_accused" not in world.npcs["tomo"].status_flags:
                world.npcs["tomo"].status_flags.append("falsely_accused")
            world._write_reflection_memory(
                owner_id="mira",
                summary="Mira accused Tomo before proof arrived and learned to investigate before repeating rumors.",
                source_event_log_id=self.event_id,
                modifier="investigate_before_accuse",
            )
        elif path == "player_manipulated":
            resolved_phase = "resolved_player_manipulated"
            event["resolution_path"] = "player_manipulated"
            event["state"] = "resolved"
            world._change_relationship("mira", "player", {"trust": -0.24, "affinity": -0.08}, self.event_id)
        else:
            raise ValueError(f"Unknown Missing Seeds resolution path: {path}")

        self.set_phase(world, resolved_phase)
        world._append_event(
            event_type="event_resolved",
            actor_id=None,
            target_id=self.event_id,
            payload={"event_id": self.event_id, "path": path, "phase": resolved_phase},
        )
