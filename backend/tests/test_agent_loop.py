from __future__ import annotations

import unittest

from backend.app.world import WorldSimulation


class AgentLoopTests(unittest.TestCase):
    def test_share_claim_requires_same_location(self) -> None:
        world = WorldSimulation()

        diff = world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        self.assertEqual(diff["reason"], "target_unavailable")
        self.assertEqual(diff["latest_events"][-1]["type"], "tool_rejected")
        self.assertEqual(diff["last_validator_result"]["tool_name"], "share_memory")

    def test_share_claim_writes_memory_and_runs_agent_loop(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")

        diff = world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        self.assertEqual(diff["reason"], "memory_shared")
        self.assertEqual(world.world_events["evt_missing_seeds"]["phase"], "conflicting_claims")
        self.assertIn("mira", diff["memories"])
        self.assertTrue(any(memory["type"] == "episodic" for memory in diff["memories"]["mira"]))
        self.assertTrue(any(memory["type"] == "rumor" for memory in diff["memories"]["mira"]))
        self.assertLess(diff["relationships"]["mira->tomo"]["trust"], 0.5)
        self.assertEqual(diff["last_agent_trace"]["decision"], "action_proposed")
        self.assertEqual(diff["last_agent_trace"]["tool_proposal"]["tool_name"], "npc_talk_to")
        self.assertEqual(diff["last_director_trace"]["decisions"][-1]["decision_type"], "approve")
        self.assertTrue(any(action["tool_name"] == "npc_talk_to" for action in diff["action_queue"]))
        event_types = [event["type"] for event in world.events(limit=10)]
        self.assertIn("memory_written", event_types)
        self.assertIn("relationship_changed", event_types)
        self.assertIn("agent_action_planned", event_types)

    def test_observe_writes_perception_memory_for_nearby_npc(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")

        diff = world.observe()

        self.assertEqual(diff["reason"], "player_observed")
        self.assertIn("mira", diff["memories"])
        self.assertTrue(any(memory["topic"] == "player_presence" for memory in diff["memories"]["mira"]))

    def test_talk_to_writes_dialogue_memory_when_nearby(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")

        diff = world.talk_to(target_id="mira", topic="missing_seeds")

        self.assertEqual(diff["reason"], "dialogue_started")
        self.assertIn("mira", diff["memories"])
        self.assertTrue(any(memory["topic"] == "missing_seeds" for memory in diff["memories"]["mira"]))

    def test_investigate_warehouse_verifies_evidence_fact(self) -> None:
        world = WorldSimulation()
        world.move_player("warehouse")

        diff = world.investigate("warehouse")

        self.assertEqual(diff["reason"], "evidence_found")
        event = diff["world_events"]["evt_missing_seeds"]
        self.assertEqual(event["phase"], "evidence_found")
        torn_seed_fact = next(fact for fact in event["facts"] if fact["fact_id"] == "fact_torn_seed_bag")
        self.assertTrue(torn_seed_fact["verified"])
        self.assertIn("player", diff["memories"])

    def test_gossip_spreads_existing_rumor_between_npcs(self) -> None:
        world = WorldSimulation()
        for _ in range(4 * 60):
            world.tick()
        world.move_player("tavern")
        world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        diff = world.gossip(actor_id="mira", target_id="tomo", rumor_id="rumor_tomo_took_seeds")

        self.assertEqual(diff["reason"], "rumor_spread")
        rumor = diff["rumors"]["rumor_tomo_took_seeds"]
        self.assertIn("tomo", rumor["current_holder_ids"])
        self.assertGreaterEqual(rumor["spread_count"], 3)
        self.assertTrue(any(memory["type"] == "rumor" for memory in diff["memories"]["tomo"]))


if __name__ == "__main__":
    unittest.main()
