from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CLIENT = ROOT / "client"


class GodotProjectFileTests(unittest.TestCase):
    def test_project_points_to_main_scene(self) -> None:
        project = (CLIENT / "project.godot").read_text(encoding="utf-8")

        self.assertIn('config/name="Echo Hollow MVP"', project)
        self.assertIn('run/main_scene="res://scenes/main.tscn"', project)

    def test_main_scene_loads_main_script(self) -> None:
        scene = (CLIENT / "scenes" / "main.tscn").read_text(encoding="utf-8")

        self.assertIn('path="res://scripts/main.gd"', scene)
        self.assertIn('[node name="Main" type="Node2D"]', scene)

    def test_main_script_uses_expected_world_socket_and_location_keys(self) -> None:
        script = (CLIENT / "scripts" / "main.gd").read_text(encoding="utf-8")

        self.assertIn('ws://127.0.0.1:8000/ws/world/demo_world_001', script)
        for key in ["KEY_1", "KEY_2", "KEY_3", "KEY_4", "KEY_5"]:
            self.assertIn(key, script)
        for location_id in ["square", "tavern", "farm", "workshop", "warehouse"]:
            self.assertIn(f'"{location_id}"', script)


if __name__ == "__main__":
    unittest.main()
