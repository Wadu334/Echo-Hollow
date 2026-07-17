from __future__ import annotations

from typing import Any

from .missing_seeds import (
    CAREFUL_CONFRONTATION,
    MISSING_SEEDS_EVENT_ID,
    MISSING_SEEDS_PHASES,
    MISSING_SEEDS_RUMOR_ID,
    TERMINAL_PHASES,
    TOMO_CLAIM_ID,
    TORN_SEED_BAG_EVIDENCE_ID,
    MissingSeedsRules,
)


class MissingSeedsEpisodeManager:
    def __init__(
        self,
        event_id: str = MISSING_SEEDS_EVENT_ID,
        rules: MissingSeedsRules | None = None,
    ) -> None:
        self.event_id = event_id
        self.rules = rules or MissingSeedsRules(event_id)

    def on_claim_memory(self, world: Any, memory: Any) -> None:
        event = self.rules.event(world)
        if memory.topic != "missing_seeds" or memory.owner_id != "mira":
            return
        if event["phase"] == "public_problem" and self.set_phase(world, "conflicting_claims"):
            event["rumor_started_minute"] = world.world_minute

    def on_action_queued(self, world: Any, action: Any) -> None:
        if action.tool_name != "npc_talk_to":
            return
        if action.args.get("episode_id") != self.event_id:
            return
        if action.args.get("social_act") != CAREFUL_CONFRONTATION:
            return
        if action.args.get("causal_claim_id") != TOMO_CLAIM_ID:
            return
        if self.rules.confrontation_recorded(world, TOMO_CLAIM_ID):
            return
        phase = str(self.rules.event(world)["phase"])
        if phase in {"conflicting_claims", "suspicion_spread"}:
            self.set_phase(world, "confrontation_pending")

    def on_action_executed(self, world: Any, action: Any) -> None:
        event = self.rules.event(world)
        if self.rules.is_terminal_phase(str(event["phase"])):
            return

        if (
            action.tool_name == "npc_talk_to"
            and action.actor_id == "mira"
            and action.args.get("target_id") == "tomo"
            and action.args.get("episode_id") == self.event_id
            and action.args.get("social_act") == CAREFUL_CONFRONTATION
            and action.args.get("causal_claim_id") == TOMO_CLAIM_ID
        ):
            if self.rules.record_confrontation(world, TOMO_CLAIM_ID):
                self.set_phase(world, "confrontation_happened")
                event["confrontation_minute"] = world.world_minute
            return

        if action.tool_name == "npc_gossip" and action.args.get("rumor_id") == MISSING_SEEDS_RUMOR_ID:
            if event["phase"] in {"conflicting_claims", "confrontation_pending", "confrontation_happened"}:
                self.set_phase(world, "suspicion_spread")

    def on_tick(self, world: Any) -> None:
        event = self.rules.event(world)
        phase = str(event["phase"])
        if self.rules.is_terminal_phase(phase):
            return

        rumor = world.rumors[MISSING_SEEDS_RUMOR_ID]
        if rumor.spread_count >= 3 and phase in {
            "conflicting_claims",
            "confrontation_pending",
            "confrontation_happened",
        }:
            if self.set_phase(world, "suspicion_spread"):
                phase = "suspicion_spread"

        rumor_started = event.get("rumor_started_minute")
        confrontation_minute = event.get("confrontation_minute")
        if phase in {
            "conflicting_claims",
            "suspicion_spread",
            "confrontation_pending",
            "confrontation_happened",
        }:
            too_long_since_rumor = rumor_started is not None and world.world_minute - int(rumor_started) >= 180
            too_long_since_confrontation = (
                confrontation_minute is not None and world.world_minute - int(confrontation_minute) >= 90
            )
            if too_long_since_rumor or too_long_since_confrontation:
                self.resolve_event(world, "false_accusation")

    def set_phase(self, world: Any, phase: str) -> bool:
        if phase not in MISSING_SEEDS_PHASES:
            raise ValueError(f"Unknown Missing Seeds phase: {phase}")
        event = self.rules.event(world)
        current = str(event["phase"])
        if current == phase:
            return False
        if self.rules.validate_transition(current, phase) is not None:
            return False
        event["phase"] = phase
        event["phase_started_minute"] = world.world_minute
        world._append_event(
            event_type="episode_phase_changed",
            actor_id=None,
            target_id=self.event_id,
            payload={"from": current, "to": phase},
        )
        return True

    def resolve_event(self, world: Any, path: str) -> dict[str, Any] | None:
        event = self.rules.event(world)
        phase = str(event["phase"])
        if phase in TERMINAL_PHASES:
            return None

        evidence_id: str | None = None
        if path == "reconciled":
            resolved_phase = "resolved_reconciled"
            evidence_id = TORN_SEED_BAG_EVIDENCE_ID
            if evidence_id not in event["shared_evidence_ids"]:
                return None
        elif path == "false_accusation":
            resolved_phase = "resolved_false_accusation"
        elif path == "player_manipulated":
            resolved_phase = "resolved_player_manipulated"
        else:
            raise ValueError(f"Unknown Missing Seeds resolution path: {path}")

        if self.rules.validate_transition(phase, resolved_phase) is not None:
            return None
        if self.rules.resolution_effect_applied(world, path, evidence_id):
            return None
        if not self.rules.record_resolution_effect(world, path, evidence_id):
            return None

        reflection_text = ""
        event["resolution_path"] = path
        event["state"] = "resolved"
        if path == "reconciled":
            world._change_relationship("mira", "tomo", {"trust": 0.22, "affinity": 0.08}, self.event_id)
            world._change_relationship("tomo", "mira", {"trust": 0.12, "affinity": 0.06}, self.event_id)
            rumor = world.rumors[MISSING_SEEDS_RUMOR_ID]
            rumor.verified_state = "false"
            rumor.confidence = 0.08
            world.npcs["mira"].mood = "relieved"
            world.npcs["tomo"].mood = "vindicated"
            if "suspicious_of_tomo" in world.npcs["mira"].status_flags:
                world.npcs["mira"].status_flags.remove("suspicious_of_tomo")
            for npc_id, flag in (("mira", "rumor_corrected"), ("tomo", "name_cleared")):
                if flag not in world.npcs[npc_id].status_flags:
                    world.npcs[npc_id].status_flags.append(flag)
            reflection_text = (
                "Mira corrected the Tomo seed rumor after evidence showed the bag was torn near the warehouse."
            )
            world._write_reflection_memory(
                owner_id="mira",
                summary=reflection_text,
                source_event_log_id=self.event_id,
                modifier="rumor_skepticism",
            )
        elif path == "false_accusation":
            world._change_relationship("mira", "tomo", {"trust": -0.2, "affinity": -0.08}, self.event_id)
            world._change_relationship("tomo", "mira", {"trust": -0.28, "affinity": -0.12}, self.event_id)
            world.npcs["mira"].mood = "regretful"
            world.npcs["tomo"].mood = "hurt"
            if "falsely_accused" not in world.npcs["tomo"].status_flags:
                world.npcs["tomo"].status_flags.append("falsely_accused")
            reflection_text = (
                "Mira accused Tomo before proof arrived and learned to investigate before repeating rumors."
            )
            world._write_reflection_memory(
                owner_id="mira",
                summary=reflection_text,
                source_event_log_id=self.event_id,
                modifier="investigate_before_accuse",
            )
        else:
            world._change_relationship("mira", "player", {"trust": -0.24, "affinity": -0.08}, self.event_id)
            reflection_text = "Mira needs time before trusting the player's claims again."

        if not self.set_phase(world, resolved_phase):
            return None
        cancelled_action_ids = self.rules.cancel_episode_actions(
            world,
            reason=f"Missing Seeds resolved via {path}.",
        )
        presentation = self._publish_outcome(
            world,
            path=path,
            phase=resolved_phase,
            reflection_text=reflection_text,
            cancelled_action_ids=cancelled_action_ids,
        )
        return presentation

    def _publish_outcome(
        self,
        world: Any,
        *,
        path: str,
        phase: str,
        reflection_text: str,
        cancelled_action_ids: list[str],
    ) -> dict[str, Any]:
        copy = {
            "reconciled": {
                "type": "reconciliation_consequence",
                "title": "The Rumor Is Put Right",
                "line": "Mira shows Tomo the torn bag and admits the rumor was wrong.",
                "reaction_text": "Tomo's hurt eases when the village finally hears the evidence.",
                "relationship_trend_text": "Trust between Mira and Tomo is beginning to recover.",
            },
            "false_accusation": {
                "type": "false_accusation_consequence",
                "title": "An Accusation Lingers",
                "line": "The rumor hardened before anyone brought proof.",
                "reaction_text": "Tomo remains hurt by how quickly suspicion became blame.",
                "relationship_trend_text": "Trust between Mira and Tomo has fallen.",
            },
            "player_manipulated": {
                "type": "manipulation_consequence",
                "title": "Trust Needs Repair",
                "line": "Mira realizes the story was shaped to mislead her.",
                "reaction_text": "The village pauses before accepting another claim.",
                "relationship_trend_text": "Mira's trust in the player has fallen.",
            },
        }[path]
        presentation_id = f"presentation_{self.event_id}_{path}"
        event_log_id = world._append_event(
            event_type="event_resolved",
            actor_id=None,
            target_id=self.event_id,
            payload={
                "event_id": self.event_id,
                "path": path,
                "phase": phase,
                "presentation_id": presentation_id,
                "cancelled_action_ids": cancelled_action_ids,
            },
        )
        presentation = {
            "presentation_id": presentation_id,
            **copy,
            "reflection_text": reflection_text,
            "path": path,
            "event_log_id": event_log_id,
        }
        world._event_log[-1].payload["outcome"] = presentation
        world.pending_presentations[presentation_id] = presentation
        event = self.rules.event(world)
        event["outcome_presentation_id"] = presentation_id
        if presentation_id not in event["presentation_ids"]:
            event["presentation_ids"].append(presentation_id)
        return presentation


__all__ = [
    "MISSING_SEEDS_PHASES",
    "MissingSeedsEpisodeManager",
]
