from __future__ import annotations

import unittest

from backend.app.missing_seeds import (
    CAREFUL_CONFRONTATION,
    LEGAL_TRANSITIONS,
    MISSING_SEEDS_PHASES,
    TOMO_CLAIM_ID,
    TORN_SEED_BAG_EVIDENCE_ID,
)
from backend.app.world import WorldSimulation


class PlayableWorldV21IntegrityTests(unittest.TestCase):
    def _reach_confrontation(self, world: WorldSimulation) -> None:
        world.move_player("workshop")
        shared = world.share_claim("mira", TOMO_CLAIM_ID)
        self.assertEqual(shared["reason"], "memory_shared")
        for _ in range(3):
            world.tick()
        self.assertTrue(world.missing_seeds.confrontation_has_happened(world))
        self.assertIn(
            world.world_events["evt_missing_seeds"]["phase"],
            {"confrontation_happened", "suspicion_spread"},
        )

    def _find_evidence(self, world: WorldSimulation) -> None:
        self._reach_confrontation(world)
        world.move_player("square")
        at_warehouse = world.move_player("warehouse")
        action = at_warehouse["presentation"]["contextual_action"]
        self.assertIsNotNone(action)
        found = world.activate_contextual_action(
            action["action_id"],
            action["offer_version"],
        )
        self.assertEqual(found["reason"], "evidence_found")

    def _resolve_reconciled(self, world: WorldSimulation) -> None:
        self._find_evidence(world)
        world.move_player("farm")
        resolved = world.player_share_evidence("mira", TORN_SEED_BAG_EVIDENCE_ID)
        self.assertEqual(resolved["reason"], "evidence_shared")
        self.assertEqual(world.world_events["evt_missing_seeds"]["phase"], "resolved_reconciled")

    def test_phase_graph_is_explicit_and_terminal_phases_have_no_outgoing_edges(self) -> None:
        self.assertEqual(set(LEGAL_TRANSITIONS), set(MISSING_SEEDS_PHASES))
        for phase in {
            "resolved_reconciled",
            "resolved_false_accusation",
            "resolved_player_manipulated",
        }:
            self.assertEqual(LEGAL_TRANSITIONS[phase], frozenset())

        world = WorldSimulation()
        self.assertFalse(world.episode_manager.set_phase(world, "evidence_found"))
        self.assertEqual(world.world_events["evt_missing_seeds"]["phase"], "public_problem")

    def test_terminal_phase_cannot_reopen_or_reapply_resolution(self) -> None:
        world = WorldSimulation()
        self._resolve_reconciled(world)
        event = world.world_events["evt_missing_seeds"]
        baseline = self._stable_outcome_state(world)
        resolution_events = self._event_count(world, "event_resolved")

        reopened = world.episode_manager.set_phase(world, "resolution_pending")
        replay = world.player_share_evidence("mira", TORN_SEED_BAG_EVIDENCE_ID)

        self.assertFalse(reopened)
        self.assertEqual(replay["reason"], "episode_terminal")
        self.assertEqual(event["phase"], "resolved_reconciled")
        self.assertEqual(event["resolution_path"], "reconciled")
        self.assertEqual(self._stable_outcome_state(world), baseline)
        self.assertEqual(self._event_count(world, "event_resolved"), resolution_events)

    def test_wrong_location_investigation_never_discovers_evidence(self) -> None:
        world = WorldSimulation()
        self._reach_confrontation(world)

        wrong_subject = world.investigate("workshop")
        remote_warehouse = world.investigate("warehouse")

        self.assertEqual(wrong_subject["reason"], "clue_not_found")
        self.assertEqual(remote_warehouse["reason"], "not_reachable")
        self.assertIsNone(world.missing_seeds.evidence_record(world, TORN_SEED_BAG_EVIDENCE_ID))
        self.assertEqual(self._event_count(world, "evidence_found"), 0)

    def test_repeated_investigation_is_stable_and_preserves_provenance(self) -> None:
        world = WorldSimulation()
        self._reach_confrontation(world)
        world.move_player("square")
        at_warehouse = world.move_player("warehouse")
        action = at_warehouse["presentation"]["contextual_action"]

        first = world.activate_contextual_action(action["action_id"], action["offer_version"])
        replay = world.activate_contextual_action(action["action_id"], action["offer_version"])
        debug_replay = world.investigate("warehouse")

        self.assertEqual(first["reason"], "evidence_found")
        self.assertEqual(replay["reason"], "stale_contextual_offer")
        self.assertEqual(debug_replay["reason"], "evidence_already_found")
        self.assertEqual(self._event_count(world, "evidence_found"), 1)
        self.assertEqual(
            sum(memory.type == "evidence" and memory.owner_id == "player" for memory in world.memories.values()),
            1,
        )
        record = world.player.evidence[0]
        self.assertEqual(record["evidence_id"], TORN_SEED_BAG_EVIDENCE_ID)
        self.assertEqual(record["fact_id"], "fact_torn_seed_bag")
        self.assertEqual(record["found_location"], "warehouse")
        self.assertEqual(record["provenance"]["kind"], "contextual_action")
        self.assertEqual(record["provenance"]["clue_id"], "clue_torn_seed_bag")

    def test_wrong_evidence_recipient_is_rejected_without_side_effects(self) -> None:
        world = WorldSimulation()
        self._find_evidence(world)
        world.move_player("farm")
        baseline_memories = len(world.memories)
        baseline = self._stable_outcome_state(world)

        rejected = world.player_share_evidence("tomo", TORN_SEED_BAG_EVIDENCE_ID)

        self.assertEqual(rejected["reason"], "invalid_evidence_recipient")
        self.assertEqual(len(world.memories), baseline_memories)
        self.assertEqual(self._event_count(world, "evidence_shared"), 0)
        self.assertEqual(self._stable_outcome_state(world), baseline)
        self.assertEqual(world.world_events["evt_missing_seeds"]["phase"], "evidence_found")

    def test_repeated_evidence_share_applies_resolution_once(self) -> None:
        world = WorldSimulation()
        self._find_evidence(world)
        world.move_player("farm")

        accepted = world.player_share_evidence("mira", TORN_SEED_BAG_EVIDENCE_ID)
        baseline = self._stable_outcome_state(world)
        memory_count = len(world.memories)
        replay = world.player_share_evidence("mira", TORN_SEED_BAG_EVIDENCE_ID)

        self.assertEqual(accepted["reason"], "evidence_shared")
        self.assertEqual(replay["reason"], "episode_terminal")
        self.assertEqual(self._stable_outcome_state(world), baseline)
        self.assertEqual(len(world.memories), memory_count)
        self.assertEqual(self._event_count(world, "evidence_shared"), 1)
        self.assertEqual(self._event_count(world, "event_resolved"), 1)
        self.assertEqual(
            sum(memory.type == "reflection" and memory.owner_id == "mira" for memory in world.memories.values()),
            1,
        )

    def test_resolution_cancels_queued_fallback_and_retry_actions(self) -> None:
        world = WorldSimulation()
        self._find_evidence(world)
        queued_ids = [
            world.enqueue_action(
                actor_id="mira",
                tool_name="npc_move_to",
                args={
                    "actor_id": "mira",
                    "location_id": "square",
                    "episode_id": "evt_missing_seeds",
                    "causal_claim_id": TOMO_CLAIM_ID,
                },
                priority=5,
                execute_after_minute=world.world_minute + 10,
                status="fallback_planned",
                reason="stale fallback",
            ),
            world.enqueue_action(
                actor_id="mira",
                tool_name="npc_talk_to",
                args={
                    "actor_id": "mira",
                    "target_id": "tomo",
                    "topic": "missing_seeds",
                    "episode_id": "evt_missing_seeds",
                    "social_act": "check_in",
                    "causal_claim_id": TOMO_CLAIM_ID,
                },
                priority=4,
                execute_after_minute=world.world_minute + 11,
                reason="stale retry",
            ),
            world.enqueue_action(
                actor_id="mira",
                tool_name="npc_gossip",
                args={
                    "actor_id": "mira",
                    "target_id": "ivo",
                    "rumor_id": "rumor_tomo_took_seeds",
                    "episode_id": "evt_missing_seeds",
                },
                priority=3,
                execute_after_minute=world.world_minute + 12,
                reason="stale queued rumor",
            ),
        ]
        world.move_player("farm")

        world.player_share_evidence("mira", TORN_SEED_BAG_EVIDENCE_ID)

        self.assertTrue(all(world.action_queue[action_id].status == "cancelled" for action_id in queued_ids))
        world.wait_minutes(20)
        self.assertTrue(all(world.action_queue[action_id].status == "cancelled" for action_id in queued_ids))
        cancelled_events = {
            event["target_id"]
            for event in world.events(limit=200)
            if event["type"] == "action_cancelled"
        }
        self.assertTrue(set(queued_ids).issubset(cancelled_events))

    def test_debunked_rumor_cannot_spread_or_write_memory(self) -> None:
        world = WorldSimulation()
        self._resolve_reconciled(world)
        world.enqueue_action(
            actor_id="ivo",
            tool_name="npc_move_to",
            args={"actor_id": "ivo", "location_id": "farm"},
            priority=9,
            reason="move for semantic test",
        )
        world.tick()
        rumor_before = world.rumors["rumor_tomo_took_seeds"].to_dict()
        memories_before = len(world.memories)

        rejected = world.gossip("ivo", "mira", "rumor_tomo_took_seeds")

        self.assertEqual(rejected["reason"], "rumor_debunked")
        self.assertEqual(world.rumors["rumor_tomo_took_seeds"].to_dict(), rumor_before)
        self.assertEqual(len(world.memories), memories_before)

    def test_same_causal_claim_cannot_trigger_second_confrontation(self) -> None:
        world = WorldSimulation()
        self._reach_confrontation(world)
        baseline = self._stable_outcome_state(world)
        dialogue_count = self._event_count(world, "npc_dialogue_started")
        presentation_count = len(world.pending_presentations)
        phase = world.world_events["evt_missing_seeds"]["phase"]
        action_id = world.enqueue_action(
            actor_id="mira",
            tool_name="npc_talk_to",
            args={
                "actor_id": "mira",
                "target_id": "tomo",
                "topic": "missing_seeds",
                "episode_id": "evt_missing_seeds",
                "social_act": CAREFUL_CONFRONTATION,
                "causal_claim_id": TOMO_CLAIM_ID,
            },
            priority=9,
            reason="replayed causal claim",
        )

        world.tick()

        self.assertEqual(world.action_queue[action_id].status, "rejected")
        self.assertEqual(
            world.action_queue[action_id].validator_result["rejection_code"],
            "confrontation_already_applied",
        )
        self.assertEqual(world.world_events["evt_missing_seeds"]["phase"], phase)
        self.assertEqual(self._stable_outcome_state(world), baseline)
        self.assertEqual(self._event_count(world, "npc_dialogue_started"), dialogue_count)
        self.assertEqual(len(world.pending_presentations), presentation_count)

    def test_missing_social_act_rejected_and_check_in_is_not_accusation(self) -> None:
        world = WorldSimulation()
        world._change_npc_location("mira", "farm", "test_setup")
        world._npc_schedule_locks["mira"] = world.world_minute + 10
        baseline_relationship = world.relationships["tomo->mira"].to_dict()
        baseline_moods = (world.npcs["mira"].mood, world.npcs["tomo"].mood)
        missing_intent_id = world.enqueue_action(
            actor_id="mira",
            tool_name="npc_talk_to",
            args={
                "actor_id": "mira",
                "target_id": "tomo",
                "topic": "missing_seeds",
                "episode_id": "evt_missing_seeds",
            },
            priority=9,
            reason="missing social act",
        )
        world.tick()
        self.assertEqual(
            world.action_queue[missing_intent_id].validator_result["rejection_code"],
            "social_act_not_found",
        )

        check_in_id = world.enqueue_action(
            actor_id="mira",
            tool_name="npc_talk_to",
            args={
                "actor_id": "mira",
                "target_id": "tomo",
                "topic": "missing_seeds",
                "episode_id": "evt_missing_seeds",
                "social_act": "check_in",
            },
            priority=8,
            reason="neutral check in",
        )
        world.tick()

        self.assertEqual(world.action_queue[check_in_id].status, "executed")
        self.assertEqual(world.relationships["tomo->mira"].to_dict(), baseline_relationship)
        self.assertEqual((world.npcs["mira"].mood, world.npcs["tomo"].mood), baseline_moods)
        self.assertFalse(world.missing_seeds.confrontation_has_happened(world))

    def test_reconciled_outcome_is_stable_for_more_than_300_world_minutes(self) -> None:
        world = WorldSimulation()
        self._resolve_reconciled(world)
        baseline = self._stable_outcome_state(world)
        world.enqueue_action(
            actor_id="mira",
            tool_name="npc_talk_to",
            args={
                "actor_id": "mira",
                "target_id": "tomo",
                "topic": "missing_seeds",
                "episode_id": "evt_missing_seeds",
                "social_act": CAREFUL_CONFRONTATION,
                "causal_claim_id": TOMO_CLAIM_ID,
            },
            priority=9,
            reason="post-terminal replay",
        )

        world.wait_minutes(301)

        self.assertEqual(self._stable_outcome_state(world), baseline)

    def test_false_accusation_terminal_is_stable_for_more_than_300_world_minutes(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")
        world.share_claim("mira", TOMO_CLAIM_ID)
        world.wait_minutes(185)
        self.assertEqual(world.world_events["evt_missing_seeds"]["phase"], "resolved_false_accusation")
        baseline = self._stable_outcome_state(world)
        world.enqueue_action(
            actor_id="mira",
            tool_name="npc_gossip",
            args={
                "actor_id": "mira",
                "target_id": "ivo",
                "rumor_id": "rumor_tomo_took_seeds",
                "episode_id": "evt_missing_seeds",
            },
            priority=9,
            reason="post-terminal rumor replay",
        )

        world.wait_minutes(301)

        self.assertEqual(self._stable_outcome_state(world), baseline)

    def test_normal_server_offered_path_exposes_objectives_evidence_and_outcomes(self) -> None:
        world = WorldSimulation()
        objectives = [world.snapshot()["presentation"]["objective"]]

        ivo = world.player_interact_npc("ivo", client_session_id="session")
        world.dialogue_choice(
            ivo["conversation_id"],
            ivo["offer_version"],
            "ask_about_missing_seeds",
            client_session_id="session",
        )
        objectives.append(world.snapshot()["presentation"]["objective"])
        world.move_player("workshop")
        mira = world.player_interact_npc("mira", client_session_id="session")
        world.dialogue_choice(
            mira["conversation_id"],
            mira["offer_version"],
            "share_ivo_claim",
            client_session_id="session",
        )
        for _ in range(3):
            world.tick()
        objectives.append(world.snapshot()["presentation"]["objective"])
        world.move_player("square")
        warehouse = world.move_player("warehouse")
        contextual = warehouse["presentation"]["contextual_action"]
        self.assertEqual(contextual["action_id"], "inspect_torn_seed_bag_clue")
        self.assertIn("label", contextual)
        self.assertIn("prompt", contextual)
        world.activate_contextual_action(contextual["action_id"], contextual["offer_version"])
        objectives.append(world.snapshot()["presentation"]["objective"])
        world.move_player("farm")
        mira_with_evidence = world.player_interact_npc("mira", client_session_id="session")
        self.assertIn(
            "show_torn_seed_bag",
            {choice["choice_id"] for choice in mira_with_evidence["choices"]},
        )
        world.dialogue_choice(
            mira_with_evidence["conversation_id"],
            mira_with_evidence["offer_version"],
            "show_torn_seed_bag",
            client_session_id="session",
        )
        objectives.append(world.snapshot()["presentation"]["objective"])

        self.assertEqual(
            objectives,
            [
                "Ask Ivo about the missing seeds",
                "Tell Mira what Ivo said",
                "Check the Warehouse",
                "Show Mira the evidence",
                "Observe the outcome",
            ],
        )
        presentations = world.snapshot()["pending_presentations"]
        self.assertEqual(
            {item["type"] for item in presentations},
            {"rumor_consequence", "reconciliation_consequence"},
        )
        required_fields = {
            "presentation_id",
            "type",
            "title",
            "line",
            "reaction_text",
            "relationship_trend_text",
            "reflection_text",
            "path",
            "event_log_id",
        }
        self.assertTrue(all(required_fields.issubset(item) for item in presentations))
        self.assertTrue(all("trust" not in item for item in presentations))

    def test_pending_presentation_ack_and_event_cursor_recovery_are_stable(self) -> None:
        world = WorldSimulation()
        cursor = world.snapshot()["event_log_cursor"]
        self._reach_confrontation(world)
        confrontation_id = "presentation_evt_missing_seeds_careful_confrontation"
        self.assertIn(confrontation_id, world.pending_presentations)
        recovery = world.events_after(cursor)
        self.assertTrue(any(event["type"] == "npc_dialogue_started" for event in recovery))

        acknowledged = world.ack_presentation(confrontation_id)
        replay = world.ack_presentation(confrontation_id)

        self.assertEqual(acknowledged["reason"], "presentation_acknowledged")
        self.assertEqual(replay["reason"], "presentation_not_found")
        self.assertNotIn(confrontation_id, world.pending_presentations)

    @staticmethod
    def _event_count(world: WorldSimulation, event_type: str) -> int:
        return sum(event["type"] == event_type for event in world.events(limit=200))

    @staticmethod
    def _stable_outcome_state(world: WorldSimulation) -> tuple[object, ...]:
        event = world.world_events["evt_missing_seeds"]
        rumor = world.rumors["rumor_tomo_took_seeds"]
        return (
            event["phase"],
            event["resolution_path"],
            world.relationships["mira->tomo"].to_dict(),
            world.relationships["tomo->mira"].to_dict(),
            world.npcs["tomo"].mood,
            rumor.verified_state,
            rumor.confidence,
            tuple(rumor.current_holder_ids),
            rumor.spread_count,
        )


if __name__ == "__main__":
    unittest.main()
