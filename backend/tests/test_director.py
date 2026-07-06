from __future__ import annotations

import unittest

from backend.app.agent_runtime import AgentRuntimeDecision
from backend.app.ai_schemas import AIActionProposal
from backend.app.director import DirectorConfig, VillageDirector
from backend.app.world import WorldSimulation


class VillageDirectorTests(unittest.TestCase):
    def test_director_approves_episode_relevant_action(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")

        diff = world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        self.assertEqual(diff["last_agent_trace"]["decision"], "action_proposed")
        self.assertEqual(diff["last_director_trace"]["decisions"][-1]["decision_type"], "approve")
        self.assertTrue(any(action["tool_name"] == "npc_talk_to" for action in diff["action_queue"]))

    def test_agent_runtime_propose_step_does_not_enqueue(self) -> None:
        world = WorldSimulation()
        source_event_id = world._append_event("test_memory_source", "player", "mira", {})
        memory = world._write_memory(
            owner_id="mira",
            memory_type="episodic",
            topic="missing_seeds",
            summary="Player says Tomo may have taken the seeds.",
            source_event_log_id=source_event_id,
            truth_state="unverified",
            target_id="tomo",
        )
        queue_size = len(world.action_queue)

        decision = world.agent_runtime.propose_step(world, "mira", memory)

        self.assertEqual(decision.decision, "action_proposed")
        self.assertEqual(len(world.action_queue), queue_size)

    def test_director_creates_fallback_after_target_unavailable(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")
        world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        world.tick()

        self.assertEqual(world.last_director_trace["decisions"][-1]["decision_type"], "fallback")
        actions = world.snapshot()["action_queue"]
        self.assertTrue(any(action["tool_name"] == "npc_move_to" and action["status"] == "fallback_planned" for action in actions))
        self.assertTrue(any(action["tool_name"] == "npc_talk_to" and action["status"] == "queued" for action in actions))

    def test_director_skips_duplicate_action(self) -> None:
        world = WorldSimulation()
        proposal = self._proposal("npc_talk_to", {"actor_id": "mira", "target_id": "tomo", "topic": "missing_seeds"}, 7)
        first = self._decision("mira", proposal)
        second = self._decision("mira", proposal)

        approved = world.director.review_agent_decision(world, first)
        duplicate = world.director.review_agent_decision(world, second)

        self.assertEqual(approved.decision_type, "approve")
        self.assertEqual(duplicate.decision_type, "duplicate_skipped")
        pending_talks = [
            action for action in world.action_queue.values()
            if action.tool_name == "npc_talk_to" and action.args.get("target_id") == "tomo"
        ]
        self.assertEqual(len(pending_talks), 1)

    def test_director_respects_gossip_budget(self) -> None:
        world = WorldSimulation()
        world.director = VillageDirector(DirectorConfig(max_gossip_spread_per_day=1))
        first = self._decision(
            "mira",
            self._proposal("npc_gossip", {"actor_id": "mira", "target_id": "ivo", "rumor_id": "rumor_tomo_took_seeds"}, 4),
        )
        second = self._decision(
            "mira",
            self._proposal("npc_gossip", {"actor_id": "mira", "target_id": "tomo", "rumor_id": "rumor_tomo_took_seeds"}, 4),
        )

        approved = world.director.review_agent_decision(world, first)
        skipped = world.director.review_agent_decision(world, second)

        self.assertEqual(approved.decision_type, "approve")
        self.assertEqual(skipped.decision_type, "budget_skipped")

    def test_director_does_not_control_routine_schedule(self) -> None:
        world = WorldSimulation()

        for _ in range(4 * 60):
            world.tick()

        self.assertEqual(world.npcs["mira"].current_location, "tavern")
        self.assertTrue(any(event["type"] == "npc_schedule_changed" for event in world.events(limit=20)))

    def test_director_injects_confrontation_beat(self) -> None:
        world = WorldSimulation()
        event = world.world_events["evt_missing_seeds"]
        event["phase"] = "suspicion_spread"
        event["phase_started_minute"] = world.world_minute - 46

        queued_ids = world.director.on_tick(world)

        self.assertEqual(world.last_director_trace["decisions"][-1]["decision_type"], "inject_episode_beat")
        self.assertEqual(len(queued_ids), 2)
        actions = world.snapshot()["action_queue"]
        self.assertTrue(any(action["tool_name"] == "npc_move_to" and action["actor_id"] == "mira" for action in actions))
        self.assertTrue(any(action["tool_name"] == "npc_talk_to" and action["args"].get("target_id") == "tomo" for action in actions))

    def test_snapshot_exposes_director_trace(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")
        world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        snapshot = world.snapshot()

        self.assertIn("last_director_trace", snapshot)
        self.assertIn("director_state", snapshot)
        self.assertEqual(snapshot["last_director_trace"]["decisions"][-1]["decision_type"], "approve")

    def test_reconciled_episode_path_still_works_with_director(self) -> None:
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

        snapshot = world.snapshot()

        self.assertEqual(snapshot["episode_phase"], "resolved_reconciled")
        self.assertEqual(snapshot["world_events"]["evt_missing_seeds"]["resolution_path"], "reconciled")
        self.assertTrue(any(memory["type"] == "reflection" for memory in snapshot["memories"]["mira"]))

    def _proposal(self, tool_name: str, args: dict[str, object], priority: int) -> AIActionProposal:
        return AIActionProposal(
            tool_name=tool_name,
            actor_id=str(args["actor_id"]),
            args=args,
            priority=priority,
            reason="test proposal",
        )

    def _decision(self, actor_id: str, proposal: AIActionProposal) -> AgentRuntimeDecision:
        return AgentRuntimeDecision(
            actor_id=actor_id,
            decision="action_proposed",
            context={"world_minute": 480},
            steps=[],
            tool_proposal=proposal,
            queued_action_id=None,
            public_reason=proposal.reason,
        )


if __name__ == "__main__":
    unittest.main()
