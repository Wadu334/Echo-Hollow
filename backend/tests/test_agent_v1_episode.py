from __future__ import annotations

import unittest

from backend.app.ai_gateway import DeterministicAIProvider
from backend.app.world import WorldSimulation


class AgentV1EpisodeTests(unittest.TestCase):
    def test_action_queue_lifecycle_executes_fallback_and_retry(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")
        world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        self.assertTrue(any(action.tool_name == "npc_talk_to" and action.status == "queued" for action in world.action_queue.values()))

        world.tick()
        self.assertTrue(any(action.tool_name == "npc_talk_to" and action.status == "rejected" for action in world.action_queue.values()))
        self.assertTrue(any(action.tool_name == "npc_move_to" and action.status == "fallback_planned" for action in world.action_queue.values()))

        world.tick()
        world.tick()
        self.assertTrue(any(action.tool_name == "npc_talk_to" and action.status == "executed" for action in world.action_queue.values()))

    def test_npc_move_to_validator_executes_movement(self) -> None:
        world = WorldSimulation()
        world.enqueue_action(
            actor_id="mira",
            tool_name="npc_move_to",
            args={"actor_id": "mira", "location_id": "farm"},
            priority=5,
            reason="test movement",
        )

        world.tick()

        self.assertEqual(world.npcs["mira"].current_location, "farm")
        self.assertEqual(world.last_validator_result["tool_name"], "npc_move_to")
        self.assertTrue(any(event["type"] == "npc_moved" for event in world.events(limit=10)))

    def test_npc_talk_to_writes_memory_for_both_npcs(self) -> None:
        world = WorldSimulation()
        world.enqueue_action(
            actor_id="mira",
            tool_name="npc_move_to",
            args={"actor_id": "mira", "location_id": "farm"},
            priority=5,
            reason="move near Tomo",
        )
        world.tick()
        world.enqueue_action(
            actor_id="mira",
            tool_name="npc_talk_to",
            args={"actor_id": "mira", "target_id": "tomo", "topic": "missing_seeds"},
            priority=5,
            reason="talk to Tomo",
        )

        world.tick()

        memories = world.snapshot()["memories"]
        self.assertTrue(any(memory["topic"] == "missing_seeds" for memory in memories["mira"]))
        self.assertTrue(any(memory["topic"] == "missing_seeds" for memory in memories["tomo"]))

    def test_npc_share_memory_copies_owned_memory(self) -> None:
        world = WorldSimulation()
        source_event_id = world._append_event(
            event_type="test_seed",
            actor_id="mira",
            target_id=None,
            payload={},
        )
        memory = world._write_memory(
            owner_id="mira",
            memory_type="episodic",
            topic="missing_seeds",
            summary="Mira saw scratches near the seed shelf.",
            source_event_log_id=source_event_id,
            truth_state="verified",
        )
        world.enqueue_action(
            actor_id="mira",
            tool_name="npc_move_to",
            args={"actor_id": "mira", "location_id": "farm"},
            priority=5,
            reason="move near Tomo",
        )
        world.tick()
        world.enqueue_action(
            actor_id="mira",
            tool_name="npc_share_memory",
            args={"actor_id": "mira", "target_id": "tomo", "memory_id": memory.memory_id},
            priority=5,
            reason="share clue",
        )

        world.tick()

        tomo_memories = world.snapshot()["memories"]["tomo"]
        self.assertTrue(any("scratches near the seed shelf" in item["summary"] for item in tomo_memories))
        self.assertTrue(any(event["type"] == "npc_memory_shared" for event in world.events(limit=8)))

    def test_resolve_event_is_internal_only_for_clients(self) -> None:
        world = WorldSimulation()

        diff = world.resolve_event("evt_missing_seeds", "reconciled")

        self.assertEqual(diff["reason"], "internal_only")
        self.assertEqual(world.world_events["evt_missing_seeds"]["phase"], "public_problem")

    def test_rejected_talk_to_creates_fallback_move_action(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")
        world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        world.tick()

        actions = world.snapshot()["action_queue"]
        self.assertTrue(any(action["tool_name"] == "npc_talk_to" and action["status"] == "rejected" for action in actions))
        self.assertTrue(any(action["tool_name"] == "npc_move_to" and action["status"] == "fallback_planned" for action in actions))

    def test_rumor_spreads_without_manual_dashboard_gossip(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")

        diff = world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        rumor = diff["rumors"]["rumor_tomo_took_seeds"]
        self.assertIn("mira", rumor["current_holder_ids"])
        self.assertGreaterEqual(rumor["spread_count"], 2)

    def test_evidence_debunks_rumor_and_reconciles_relationship(self) -> None:
        world = self._run_reconciled_path()
        snapshot = world.snapshot()

        self.assertEqual(snapshot["episode_phase"], "resolved_reconciled")
        self.assertEqual(snapshot["rumors"]["rumor_tomo_took_seeds"]["verified_state"], "false")
        self.assertLess(snapshot["rumors"]["rumor_tomo_took_seeds"]["confidence"], 0.2)
        self.assertGreater(snapshot["relationships"]["mira->tomo"]["trust"], 0.5)

    def test_false_accusation_path_reduces_tomo_trust(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")
        world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        world.wait_minutes(95)
        snapshot = world.snapshot()

        self.assertEqual(snapshot["episode_phase"], "resolved_false_accusation")
        self.assertLess(snapshot["relationships"]["tomo->mira"]["trust"], 0.5)
        self.assertIn("falsely_accused", snapshot["npcs"]["tomo"]["status_flags"])

    def test_reflection_changes_mira_future_rumor_response(self) -> None:
        world = self._run_reconciled_path()
        world.share_claim(target_id="mira", claim_id="tomo_took_seeds")
        queued_investigations = [
            action
            for action in world.snapshot()["action_queue"]
            if action["tool_name"] == "npc_investigate" and action["status"] == "queued"
        ]

        self.assertIn("rumor_skepticism", world.npcs["mira"].behavior_modifiers)
        self.assertTrue(queued_investigations)
        self.assertEqual(queued_investigations[-1]["args"]["subject_id"], "warehouse")

    def test_ai_gateway_deterministic_provider_returns_valid_schema(self) -> None:
        provider = DeterministicAIProvider()

        proposal = provider.propose_action(
            {
                "actor": {"npc_id": "mira", "behavior_modifiers": []},
                "triggering_memory": {"memory_id": "mem_1", "target_id": "tomo"},
            }
        )

        self.assertEqual(proposal.tool_name, "npc_talk_to")
        self.assertEqual(proposal.actor_id, "mira")
        self.assertIn("target_id", proposal.args)
        self.assertEqual(proposal.source_memory_ids, ["mem_1"])

    def _run_reconciled_path(self) -> WorldSimulation:
        world = WorldSimulation()
        world.move_player("workshop")
        world.share_claim(target_id="mira", claim_id="tomo_took_seeds")
        for _ in range(3):
            world.tick()
        world.move_player("square")
        world.move_player("farm")
        world.move_player("warehouse")
        world.investigate("warehouse")
        world.move_player("square")
        world.move_player("farm")
        world.player_share_evidence(target_id="mira", evidence_id="torn_seed_bag")
        return world


if __name__ == "__main__":
    unittest.main()
