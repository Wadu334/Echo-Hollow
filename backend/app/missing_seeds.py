from __future__ import annotations

from typing import Any


MISSING_SEEDS_EVENT_ID = "evt_missing_seeds"
MISSING_SEEDS_RUMOR_ID = "rumor_tomo_took_seeds"
TOMO_CLAIM_ID = "tomo_took_seeds"
TORN_SEED_BAG_EVIDENCE_ID = "torn_seed_bag"
TORN_SEED_BAG_FACT_ID = "fact_torn_seed_bag"
TORN_SEED_BAG_CLUE_ID = "clue_torn_seed_bag"
TORN_SEED_BAG_ACTION_ID = "inspect_torn_seed_bag_clue"
RECONCILIATION_RECIPIENT_ID = "mira"
CAREFUL_CONFRONTATION = "careful_confrontation"

MISSING_SEEDS_PHASES = (
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
)

TERMINAL_PHASES = frozenset(
    {
        "resolved_reconciled",
        "resolved_false_accusation",
        "resolved_player_manipulated",
    }
)

# The graph is deliberately explicit. New episode beats must add a reviewed edge
# instead of relying on the incidental order in which tools happen to execute.
LEGAL_TRANSITIONS: dict[str, frozenset[str]] = {
    "public_problem": frozenset({"conflicting_claims"}),
    "conflicting_claims": frozenset(
        {
            "confrontation_pending",
            "suspicion_spread",
            "resolved_false_accusation",
        }
    ),
    "suspicion_spread": frozenset(
        {
            "confrontation_pending",
            "confrontation_happened",
            "evidence_found",
            "resolved_false_accusation",
        }
    ),
    "confrontation_pending": frozenset(
        {
            "confrontation_happened",
            "suspicion_spread",
            "resolved_false_accusation",
        }
    ),
    "confrontation_happened": frozenset(
        {
            "suspicion_spread",
            "evidence_found",
            "resolved_false_accusation",
        }
    ),
    "evidence_found": frozenset({"resolution_pending"}),
    "resolution_pending": frozenset(
        {
            "resolved_reconciled",
            "resolved_player_manipulated",
        }
    ),
    "resolved_reconciled": frozenset(),
    "resolved_false_accusation": frozenset(),
    "resolved_player_manipulated": frozenset(),
}

EPISODE_EXECUTABLE_STATUSES = frozenset({"proposed", "queued", "fallback_planned"})


class MissingSeedsRules:
    """Focused rules and idempotency ledger for the Missing Seeds episode.

    The service decides whether an episode operation is legal and records
    causal consumption. WorldSimulation remains responsible for applying
    accepted world mutations and emitting diffs.
    """

    def __init__(self, event_id: str = MISSING_SEEDS_EVENT_ID) -> None:
        self.event_id = event_id

    def event(self, world: Any) -> dict[str, Any]:
        event = world.world_events[self.event_id]
        self.ensure_ledger(event)
        return event

    def ensure_ledger(self, event: dict[str, Any]) -> None:
        event.setdefault(
            "clues",
            {
                TORN_SEED_BAG_CLUE_ID: {
                    "clue_id": TORN_SEED_BAG_CLUE_ID,
                    "location_id": "warehouse",
                    "evidence_id": TORN_SEED_BAG_EVIDENCE_ID,
                    "available": True,
                }
            },
        )
        event.setdefault("evidence_records", {})
        event.setdefault("shared_evidence_ids", [])
        event.setdefault("applied_resolution_effect_ids", [])
        event.setdefault("confronted_causal_claim_ids", [])
        event.setdefault("contextual_offer_version", 1)
        event.setdefault("outcome_presentation_id", None)
        event.setdefault("presentation_ids", [])

    def is_terminal_phase(self, phase: str) -> bool:
        return phase in TERMINAL_PHASES

    def is_terminal(self, world: Any) -> bool:
        return self.is_terminal_phase(str(self.event(world)["phase"]))

    def can_transition(self, current_phase: str, next_phase: str) -> bool:
        if current_phase == next_phase:
            return True
        return next_phase in LEGAL_TRANSITIONS.get(current_phase, frozenset())

    def validate_transition(self, current_phase: str, next_phase: str) -> str | None:
        if next_phase not in MISSING_SEEDS_PHASES:
            return "phase_not_found"
        if self.is_terminal_phase(current_phase) and current_phase != next_phase:
            return "episode_terminal"
        if not self.can_transition(current_phase, next_phase):
            return "illegal_phase_transition"
        return None

    def confrontation_recorded(self, world: Any, causal_claim_id: str) -> bool:
        return causal_claim_id in self.event(world)["confronted_causal_claim_ids"]

    def record_confrontation(self, world: Any, causal_claim_id: str) -> bool:
        confronted = self.event(world)["confronted_causal_claim_ids"]
        if causal_claim_id in confronted:
            return False
        confronted.append(causal_claim_id)
        return True

    def confrontation_has_happened(self, world: Any) -> bool:
        return TOMO_CLAIM_ID in self.event(world)["confronted_causal_claim_ids"]

    def contextual_action(self, world: Any) -> dict[str, Any] | None:
        event = self.event(world)
        clue = event["clues"][TORN_SEED_BAG_CLUE_ID]
        phase = str(event["phase"])
        if self.is_terminal_phase(phase):
            return None
        if phase not in {"confrontation_happened", "suspicion_spread"}:
            return None
        if not self.confrontation_has_happened(world):
            return None
        if world.player.current_location != clue["location_id"]:
            return None
        if not clue["available"]:
            return None
        return {
            "action_id": TORN_SEED_BAG_ACTION_ID,
            "offer_version": int(event["contextual_offer_version"]),
            "location_id": clue["location_id"],
            "label": "Inspect torn seed bag",
            "prompt": "Press E to inspect the torn seed bag near the warehouse shelves.",
            "display_text": "Inspect the torn seed bag",
        }

    def validate_contextual_action(
        self,
        world: Any,
        action_id: str,
        offer_version: int,
    ) -> str | None:
        event = self.event(world)
        if self.is_terminal_phase(str(event["phase"])):
            return "episode_terminal"
        if action_id != TORN_SEED_BAG_ACTION_ID:
            return "contextual_action_not_found"
        if offer_version != int(event["contextual_offer_version"]):
            return "stale_contextual_offer"
        action = self.contextual_action(world)
        if action is None:
            return "contextual_action_not_available"
        return None

    def validate_investigation(self, world: Any, location_id: str) -> str | None:
        event = self.event(world)
        phase = str(event["phase"])
        if self.is_terminal_phase(phase):
            return "episode_terminal"
        if location_id != "warehouse":
            return "clue_not_found"
        if world.player.current_location != "warehouse":
            return "not_reachable"
        clue = event["clues"][TORN_SEED_BAG_CLUE_ID]
        if not clue["available"] or TORN_SEED_BAG_EVIDENCE_ID in event["evidence_records"]:
            return "evidence_already_found"
        if phase not in {"confrontation_happened", "suspicion_spread"}:
            return "clue_not_available"
        if not self.confrontation_has_happened(world):
            return "clue_not_available"
        return None

    def record_evidence_found(
        self,
        world: Any,
        *,
        event_log_id: str,
        provenance_kind: str,
    ) -> dict[str, Any] | None:
        event = self.event(world)
        if TORN_SEED_BAG_EVIDENCE_ID in event["evidence_records"]:
            return None
        clue = event["clues"][TORN_SEED_BAG_CLUE_ID]
        clue["available"] = False
        event["contextual_offer_version"] = int(event["contextual_offer_version"]) + 1
        record = {
            "evidence_id": TORN_SEED_BAG_EVIDENCE_ID,
            "fact_id": TORN_SEED_BAG_FACT_ID,
            "found_location": "warehouse",
            "found_by": "player",
            "found_event_log_id": event_log_id,
            "provenance": {
                "kind": provenance_kind,
                "actor_id": "player",
                "clue_id": TORN_SEED_BAG_CLUE_ID,
                "location_id": "warehouse",
            },
            "status": "held",
        }
        event["evidence_records"][TORN_SEED_BAG_EVIDENCE_ID] = record
        return record

    def evidence_record(self, world: Any, evidence_id: str) -> dict[str, Any] | None:
        return self.event(world)["evidence_records"].get(evidence_id)

    def validate_evidence_share(
        self,
        world: Any,
        *,
        target_id: str | None,
        evidence_id: str,
    ) -> str | None:
        event = self.event(world)
        phase = str(event["phase"])
        if self.is_terminal_phase(phase):
            return "episode_terminal"
        if target_id != RECONCILIATION_RECIPIENT_ID:
            return "invalid_evidence_recipient"
        if evidence_id != TORN_SEED_BAG_EVIDENCE_ID:
            return "evidence_not_found"
        record = self.evidence_record(world, evidence_id)
        if record is None:
            return "evidence_not_found"
        if evidence_id in event["shared_evidence_ids"] or record.get("status") == "shared":
            return "evidence_already_shared"
        if phase != "evidence_found":
            return "semantic_precondition_failed"
        return None

    def record_evidence_shared(self, world: Any, evidence_id: str, event_log_id: str) -> bool:
        event = self.event(world)
        if evidence_id in event["shared_evidence_ids"]:
            return False
        record = self.evidence_record(world, evidence_id)
        if record is None:
            return False
        event["shared_evidence_ids"].append(evidence_id)
        record["status"] = "shared"
        record["shared_event_log_id"] = event_log_id
        return True

    def resolution_effect_id(self, path: str, evidence_id: str | None = None) -> str:
        evidence = evidence_id or "none"
        return f"{self.event_id}:{path}:{evidence}"

    def resolution_effect_applied(
        self,
        world: Any,
        path: str,
        evidence_id: str | None = None,
    ) -> bool:
        effect_id = self.resolution_effect_id(path, evidence_id)
        return effect_id in self.event(world)["applied_resolution_effect_ids"]

    def record_resolution_effect(
        self,
        world: Any,
        path: str,
        evidence_id: str | None = None,
    ) -> bool:
        event = self.event(world)
        effect_id = self.resolution_effect_id(path, evidence_id)
        if effect_id in event["applied_resolution_effect_ids"]:
            return False
        event["applied_resolution_effect_ids"].append(effect_id)
        return True

    def is_episode_action(self, action: Any) -> bool:
        args = action.args
        if args.get("episode_id") == self.event_id:
            return True
        if action.tool_name == "npc_gossip" and args.get("rumor_id") == MISSING_SEEDS_RUMOR_ID:
            return True
        return action.tool_name in {"npc_talk_to", "npc_investigate", "player_share_evidence"} and (
            args.get("topic") == "missing_seeds"
        )

    def validate_queued_action(self, world: Any, action: Any) -> str | None:
        if not self.is_episode_action(action):
            return None
        event = self.event(world)
        phase = str(event["phase"])
        if self.is_terminal_phase(phase):
            return "episode_terminal"

        args = action.args
        if action.tool_name == "npc_move_to":
            return None
        if action.tool_name == "npc_talk_to":
            if args.get("episode_id") != self.event_id:
                return "episode_context_missing"
            social_act = args.get("social_act")
            if social_act not in {CAREFUL_CONFRONTATION, "check_in", "reconcile"}:
                return "social_act_not_found"
            if social_act == CAREFUL_CONFRONTATION:
                causal_claim_id = args.get("causal_claim_id")
                if causal_claim_id != TOMO_CLAIM_ID:
                    return "causal_claim_not_found"
                if self.confrontation_recorded(world, TOMO_CLAIM_ID):
                    return "confrontation_already_applied"
                if phase != "confrontation_pending":
                    return "semantic_precondition_failed"
            return None
        if action.tool_name == "npc_gossip":
            rumor = world.rumors.get(str(args.get("rumor_id")))
            if rumor is not None and rumor.verified_state == "false":
                return "rumor_debunked"
            return None
        if action.tool_name == "npc_investigate":
            if args.get("subject_id") != "warehouse":
                return "clue_not_found"
            if phase not in {"confrontation_happened", "suspicion_spread"}:
                return "semantic_precondition_failed"
            return None
        if action.tool_name == "player_share_evidence":
            return self.validate_evidence_share(
                world,
                target_id=args.get("target_id"),
                evidence_id=str(args.get("evidence_id", TORN_SEED_BAG_EVIDENCE_ID)),
            )
        return None

    def cancel_episode_actions(self, world: Any, reason: str) -> list[str]:
        cancelled: list[str] = []
        for action in world.action_queue.values():
            if action.status not in EPISODE_EXECUTABLE_STATUSES:
                continue
            if not self.is_episode_action(action):
                continue
            action.status = "cancelled"
            action.validator_result = {
                "accepted": False,
                "rejection_code": "episode_resolved",
                "debug_reason": reason,
            }
            cancelled.append(action.action_id)
            world._append_event(
                event_type="action_cancelled",
                actor_id=action.actor_id,
                target_id=action.action_id,
                payload={
                    "action_id": action.action_id,
                    "episode_id": self.event_id,
                    "reason": reason,
                },
            )
        return cancelled

    def objective(self, world: Any) -> str:
        event = self.event(world)
        phase = str(event["phase"])
        if self.is_terminal_phase(phase):
            return "Observe the outcome"
        if not world._player_has_claim_note(TOMO_CLAIM_ID):
            return "Ask Ivo about the missing seeds"
        if not world._npc_has_received_claim("mira", TOMO_CLAIM_ID):
            return "Tell Mira what Ivo said"
        if not self.confrontation_has_happened(world):
            return "Tell Mira what Ivo said"
        if TORN_SEED_BAG_EVIDENCE_ID not in event["evidence_records"]:
            return "Check the Warehouse"
        if TORN_SEED_BAG_EVIDENCE_ID not in event["shared_evidence_ids"]:
            return "Show Mira the evidence"
        return "Observe the outcome"
