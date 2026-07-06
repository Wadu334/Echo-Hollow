from __future__ import annotations

import unittest

from backend.app.world import WorldSimulation


class GodotClientContractTests(unittest.TestCase):
    def test_world_snapshot_contains_all_fields_used_by_godot_client(self) -> None:
        world = WorldSimulation()
        snapshot = world.snapshot()

        self.assertIsInstance(snapshot["time"], str)
        self.assertIsInstance(snapshot["event_log_cursor"], int)

        for location in snapshot["locations"].values():
            self.assertIn("name", location)
            self.assertIn("position", location)
            self.assertIsInstance(location["position"]["x"], int)
            self.assertIsInstance(location["position"]["y"], int)
            self.assertIsInstance(location["current_occupants"], list)

        player = snapshot["player"]
        self.assertIn(player["current_location"], snapshot["locations"])

        for npc in snapshot["npcs"].values():
            self.assertIn("name", npc)
            self.assertIn(npc["current_location"], snapshot["locations"])
            self.assertIn("current_action", npc)
            self.assertIn("current_goal", npc)
            self.assertIn("mood", npc)

    def test_world_diff_contains_all_fields_used_by_godot_client_after_player_move(self) -> None:
        world = WorldSimulation()
        diff = world.move_player("tavern")

        for key in ["locations", "player", "npcs", "latest_events", "time", "event_log_cursor"]:
            self.assertIn(key, diff)
        self.assertEqual(diff["reason"], "player_moved")
        self.assertEqual(diff["player"]["current_location"], "tavern")
        self.assertEqual(diff["latest_events"][-1]["type"], "player_moved")

    def test_agent_fields_are_available_to_clients(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")
        diff = world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

        for key in [
            "memories",
            "relationships",
            "rumors",
            "world_events",
            "last_validator_result",
            "last_agent_trace",
        ]:
            self.assertIn(key, diff)
        self.assertIn("mira", diff["memories"])
        self.assertIn("mira->tomo", diff["relationships"])
        self.assertEqual(diff["last_agent_trace"]["decision"], "investigate_missing_seeds")


if __name__ == "__main__":
    unittest.main()
