from __future__ import annotations

import unittest

from backend.app.world import WorldSimulation


class WorldSimulationTests(unittest.TestCase):
    def test_initial_snapshot_contains_required_mvp_state(self) -> None:
        world = WorldSimulation()
        snapshot = world.snapshot()

        self.assertEqual(snapshot["world_id"], "demo_world_001")
        self.assertEqual(snapshot["player"]["current_location"], "square")
        self.assertEqual(set(snapshot["npcs"].keys()), {"mira", "tomo", "ivo"})
        self.assertEqual(snapshot["npcs"]["ivo"]["current_location"], "square")
        self.assertEqual(set(snapshot["locations"].keys()), {"square", "tavern", "farm", "workshop", "warehouse"})
        self.assertIn("evt_missing_seeds", snapshot["active_events"])
        self.assertGreaterEqual(snapshot["event_log_cursor"], 1)

    def test_tick_advances_time_and_writes_schedule_events(self) -> None:
        world = WorldSimulation()

        for _ in range(4 * 60):
            diff = world.tick()

        self.assertEqual(diff["minute_of_day"], 12 * 60)
        self.assertEqual(diff["npcs"]["mira"]["current_location"], "tavern")
        self.assertEqual(diff["npcs"]["tomo"]["current_location"], "tavern")
        self.assertTrue(any(event["type"] == "npc_schedule_changed" for event in world.events(limit=20)))

    def test_player_movement_is_validated_by_location_graph(self) -> None:
        world = WorldSimulation()

        accepted = world.move_player("tavern")
        self.assertEqual(accepted["reason"], "player_moved")
        self.assertEqual(accepted["player"]["current_location"], "tavern")

        rejected = world.move_player("workshop")
        self.assertEqual(rejected["reason"], "not_reachable")
        self.assertEqual(rejected["player"]["current_location"], "tavern")
        self.assertEqual(rejected["latest_events"][-1]["type"], "client_action_rejected")

    def test_event_log_cursor_increases_on_tick_and_player_action(self) -> None:
        world = WorldSimulation()
        start_cursor = world.snapshot()["event_log_cursor"]
        world.move_player("farm")
        after_move_cursor = world.snapshot()["event_log_cursor"]
        world.tick()
        after_tick_cursor = world.snapshot()["event_log_cursor"]

        self.assertGreater(after_move_cursor, start_cursor)
        self.assertGreaterEqual(after_tick_cursor, after_move_cursor)


if __name__ == "__main__":
    unittest.main()

