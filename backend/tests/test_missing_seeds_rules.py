from __future__ import annotations

import unittest

from backend.app.missing_seeds import (
    CAREFUL_CONFRONTATION,
    MISSING_SEEDS_EVENT_ID,
    TOMO_CLAIM_ID,
    TORN_SEED_BAG_ACTION_ID,
    TORN_SEED_BAG_EVIDENCE_ID,
)
from backend.app.world import WorldSimulation


class MissingSeedsRulesTests(unittest.TestCase):
    def test_transition_validation_reports_unknown_illegal_and_terminal_edges(self) -> None:
        world = WorldSimulation()
        rules = world.missing_seeds

        self.assertIsNone(rules.validate_transition("public_problem", "public_problem"))
        self.assertEqual(
            rules.validate_transition("public_problem", "not_a_phase"),
            "phase_not_found",
        )
        self.assertEqual(
            rules.validate_transition("public_problem", "evidence_found"),
            "illegal_phase_transition",
        )
        self.assertEqual(
            rules.validate_transition("resolved_reconciled", "resolution_pending"),
            "episode_terminal",
        )
        with self.assertRaises(ValueError):
            world.episode_manager.set_phase(world, "not_a_phase")

    def test_contextual_action_rejections_are_stable(self) -> None:
        world = WorldSimulation()
        rules = world.missing_seeds

        self.assertEqual(
            rules.validate_contextual_action(world, "wrong", 1),
            "contextual_action_not_found",
        )
        self.assertEqual(
            rules.validate_contextual_action(world, TORN_SEED_BAG_ACTION_ID, 2),
            "stale_contextual_offer",
        )
        self.assertEqual(
            rules.validate_contextual_action(world, TORN_SEED_BAG_ACTION_ID, 1),
            "contextual_action_not_available",
        )
        world.world_events[MISSING_SEEDS_EVENT_ID]["phase"] = "resolved_reconciled"
        self.assertEqual(
            rules.validate_contextual_action(world, TORN_SEED_BAG_ACTION_ID, 1),
            "episode_terminal",
        )
        self.assertIsNone(rules.contextual_action(world))

    def test_evidence_ledger_rejects_missing_duplicate_and_wrong_phase_operations(self) -> None:
        world = WorldSimulation()
        rules = world.missing_seeds
        world.move_player("warehouse")

        self.assertEqual(rules.validate_investigation(world, "warehouse"), "clue_not_available")
        self.assertEqual(
            rules.validate_evidence_share(
                world,
                target_id="tomo",
                evidence_id=TORN_SEED_BAG_EVIDENCE_ID,
            ),
            "invalid_evidence_recipient",
        )
        self.assertEqual(
            rules.validate_evidence_share(world, target_id="mira", evidence_id="invented"),
            "evidence_not_found",
        )
        self.assertEqual(
            rules.validate_evidence_share(
                world,
                target_id="mira",
                evidence_id=TORN_SEED_BAG_EVIDENCE_ID,
            ),
            "evidence_not_found",
        )
        record = rules.record_evidence_found(
            world,
            event_log_id="elog_test",
            provenance_kind="test",
        )
        self.assertIsNotNone(record)
        self.assertIsNone(
            rules.record_evidence_found(
                world,
                event_log_id="elog_duplicate",
                provenance_kind="test",
            )
        )
        self.assertEqual(
            rules.validate_evidence_share(
                world,
                target_id="mira",
                evidence_id=TORN_SEED_BAG_EVIDENCE_ID,
            ),
            "semantic_precondition_failed",
        )
        self.assertFalse(rules.record_evidence_shared(world, "invented", "elog_missing"))
        self.assertTrue(
            rules.record_evidence_shared(
                world,
                TORN_SEED_BAG_EVIDENCE_ID,
                "elog_shared",
            )
        )
        self.assertFalse(
            rules.record_evidence_shared(
                world,
                TORN_SEED_BAG_EVIDENCE_ID,
                "elog_replay",
            )
        )
        self.assertEqual(
            rules.validate_evidence_share(
                world,
                target_id="mira",
                evidence_id=TORN_SEED_BAG_EVIDENCE_ID,
            ),
            "evidence_already_shared",
        )

    def test_causal_and_resolution_ledgers_are_at_most_once(self) -> None:
        world = WorldSimulation()
        rules = world.missing_seeds

        self.assertTrue(rules.record_confrontation(world, TOMO_CLAIM_ID))
        self.assertFalse(rules.record_confrontation(world, TOMO_CLAIM_ID))
        self.assertTrue(rules.confrontation_recorded(world, TOMO_CLAIM_ID))
        self.assertTrue(
            rules.record_resolution_effect(
                world,
                "reconciled",
                TORN_SEED_BAG_EVIDENCE_ID,
            )
        )
        self.assertTrue(
            rules.resolution_effect_applied(
                world,
                "reconciled",
                TORN_SEED_BAG_EVIDENCE_ID,
            )
        )
        self.assertFalse(
            rules.record_resolution_effect(
                world,
                "reconciled",
                TORN_SEED_BAG_EVIDENCE_ID,
            )
        )

    def test_queued_action_semantic_failures_are_checked_before_spatial_execution(self) -> None:
        world = WorldSimulation()

        missing_context = self._enqueue_talk(
            world,
            {"actor_id": "mira", "target_id": "tomo", "topic": "missing_seeds"},
        )
        missing_causal = self._enqueue_talk(
            world,
            {
                "actor_id": "mira",
                "target_id": "tomo",
                "topic": "missing_seeds",
                "episode_id": MISSING_SEEDS_EVENT_ID,
                "social_act": CAREFUL_CONFRONTATION,
            },
        )
        wrong_phase = self._enqueue_talk(
            world,
            {
                "actor_id": "mira",
                "target_id": "tomo",
                "topic": "missing_seeds",
                "episode_id": MISSING_SEEDS_EVENT_ID,
                "social_act": CAREFUL_CONFRONTATION,
                "causal_claim_id": TOMO_CLAIM_ID,
            },
        )
        wrong_subject_id = world.enqueue_action(
            actor_id="mira",
            tool_name="npc_investigate",
            args={
                "actor_id": "mira",
                "subject_id": "square",
                "episode_id": MISSING_SEEDS_EVENT_ID,
            },
            priority=1,
            reason="wrong subject",
        )
        early_investigation_id = world.enqueue_action(
            actor_id="mira",
            tool_name="npc_investigate",
            args={
                "actor_id": "mira",
                "subject_id": "warehouse",
                "episode_id": MISSING_SEEDS_EVENT_ID,
            },
            priority=1,
            reason="wrong phase",
        )
        wrong_evidence_recipient_id = world.enqueue_action(
            actor_id="player",
            tool_name="player_share_evidence",
            args={
                "actor_id": "player",
                "target_id": "tomo",
                "evidence_id": TORN_SEED_BAG_EVIDENCE_ID,
                "episode_id": MISSING_SEEDS_EVENT_ID,
            },
            priority=1,
            reason="wrong evidence recipient",
        )
        world.rumors["rumor_tomo_took_seeds"].verified_state = "false"
        debunked_gossip_id = world.enqueue_action(
            actor_id="ivo",
            tool_name="npc_gossip",
            args={
                "actor_id": "ivo",
                "target_id": "mira",
                "rumor_id": "rumor_tomo_took_seeds",
                "episode_id": MISSING_SEEDS_EVENT_ID,
            },
            priority=1,
            reason="debunked rumor",
        )

        self.assertEqual(
            world._validate_action(world.action_queue[missing_context])["rejection_code"],
            "episode_context_missing",
        )
        self.assertEqual(
            world._validate_action(world.action_queue[missing_causal])["rejection_code"],
            "causal_claim_not_found",
        )
        self.assertEqual(
            world._validate_action(world.action_queue[wrong_phase])["rejection_code"],
            "semantic_precondition_failed",
        )
        self.assertEqual(
            world._validate_action(world.action_queue[wrong_subject_id])["rejection_code"],
            "clue_not_found",
        )
        self.assertEqual(
            world._validate_action(world.action_queue[early_investigation_id])["rejection_code"],
            "semantic_precondition_failed",
        )
        self.assertEqual(
            world._validate_action(world.action_queue[wrong_evidence_recipient_id])["rejection_code"],
            "invalid_evidence_recipient",
        )
        self.assertEqual(
            world._validate_action(world.action_queue[debunked_gossip_id])["rejection_code"],
            "rumor_debunked",
        )

    @staticmethod
    def _enqueue_talk(world: WorldSimulation, args: dict[str, str]) -> str:
        return world.enqueue_action(
            actor_id="mira",
            tool_name="npc_talk_to",
            args=args,
            priority=1,
            reason="semantic validation test",
        )


if __name__ == "__main__":
    unittest.main()
