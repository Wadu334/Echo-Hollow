from __future__ import annotations

import asyncio
import unittest

from backend.app.main import WorldHub
from backend.app.world import WorldSimulation


class CapturingHub(WorldHub):
    def __init__(self, world: WorldSimulation) -> None:
        super().__init__(world)
        self.messages: list[dict] = []

    async def broadcast(self, message: dict) -> None:
        self.messages.append(message)


class PlayableWorldBackendTests(unittest.TestCase):
    def test_player_entered_location_updates_player_current_location(self) -> None:
        world = WorldSimulation()

        diff = world.player_entered_location("tavern")

        self.assertEqual(diff["reason"], "player_moved")
        self.assertEqual(diff["player"]["current_location"], "tavern")

    def test_player_interact_npc_denies_when_not_nearby(self) -> None:
        world = WorldSimulation()

        response = world.player_interact_npc("mira", "talk")

        self.assertEqual(response["type"], "interaction_denied")
        self.assertEqual(response["reason"], "not_nearby")
        self.assertEqual(response["display_text"], "Mira is not close enough right now.")

    def test_player_interact_npc_opens_dialogue_when_same_location(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")

        response = world.player_interact_npc("mira", "talk")

        self.assertEqual(response["type"], "dialogue_opened")
        self.assertEqual(response["npc_id"], "mira")
        self.assertEqual(response["speaker"], "Mira")
        self.assertIn("seed pouch", response["line"])
        self.assertIn({"choice_id": "offer_help", "text": "Offer Help"}, response["choices"])

    def test_dialogue_choice_offer_help_writes_mira_memory(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")

        response = world.dialogue_choice("mira", "offer_help")

        self.assertEqual(response["type"], "dialogue_result")
        self.assertEqual(response["toast"], "Mira remembers your offer to help.")
        memories = response["world_diff"]["memories"]["mira"]
        self.assertTrue(any("offered to help" in memory["summary"] for memory in memories))

    def test_dialogue_choice_ask_about_cat_creates_helpful_note_and_toast(self) -> None:
        world = WorldSimulation()
        world.move_player("tavern")

        response = world.dialogue_choice("ivo", "ask_about_cat")

        self.assertEqual(response["toast"], "Ivo remembers a cat near the Warehouse.")
        self.assertTrue(any(note["note_id"] == "cat_near_warehouse" for note in response["world_diff"]["player"]["notes"]))
        self.assertTrue(any(event["type"] == "player_note_added" for event in world.events(limit=5)))

    def test_actor_movement_diff_appears_when_npc_move_to_executes(self) -> None:
        world = WorldSimulation()
        world.enqueue_action(
            actor_id="mira",
            tool_name="npc_move_to",
            args={"actor_id": "mira", "location_id": "farm"},
            priority=5,
            reason="test movement",
        )

        diff = world.tick()

        self.assertEqual(diff["actor_movements"][0]["actor_id"], "mira")
        self.assertEqual(diff["actor_movements"][0]["from_location"], "workshop")
        self.assertEqual(diff["actor_movements"][0]["to_location"], "farm")
        self.assertEqual(diff["actor_movements"][0]["display_text"], "Mira is heading to the Farm.")

    def test_presentation_maps_internal_phase_to_cozy_display_text(self) -> None:
        world = WorldSimulation()
        world.world_events["evt_missing_seeds"]["phase"] = "evidence_found"

        presentation = world.snapshot()["presentation"]

        self.assertEqual(presentation["event_title"], "The Missing Seed Pouch")
        self.assertEqual(presentation["event_phase_text"], "A Clue Found")
        self.assertIn("useful clue", presentation["village_flow_text"])

    def test_forbidden_terms_are_not_present_in_presentation_strings(self) -> None:
        world = WorldSimulation()
        forbidden_terms = ["rumor", "gossip", "accuse", "suspicion", "manipulate", "confront"]

        for phase in [
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
        ]:
            world.world_events["evt_missing_seeds"]["phase"] = phase
            presentation = world.snapshot()["presentation"]
            combined = " ".join(
                [
                    presentation["event_title"],
                    presentation["event_phase_text"],
                    presentation["village_flow_text"],
                    *presentation["toasts"],
                ]
            ).lower()
            for term in forbidden_terms:
                self.assertNotIn(term, combined)

    def test_websocket_handler_supports_playable_dialogue_command(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")
        hub = CapturingHub(world)

        response = asyncio.run(
            hub.handle_message(
                {
                    "type": "player_interact_npc",
                    "npc_id": "mira",
                    "interaction": "talk",
                }
            )
        )

        self.assertEqual(response["type"], "dialogue_opened")
        self.assertEqual(hub.messages[-1]["type"], "dialogue_opened")

    def test_websocket_handler_broadcasts_dialogue_choice_world_diff(self) -> None:
        world = WorldSimulation()
        world.move_player("tavern")
        hub = CapturingHub(world)

        response = asyncio.run(
            hub.handle_message(
                {
                    "type": "dialogue_choice",
                    "npc_id": "ivo",
                    "choice_id": "ask_about_cat",
                }
            )
        )

        self.assertEqual(response["type"], "dialogue_result")
        self.assertEqual(hub.messages[0]["type"], "dialogue_result")
        self.assertEqual(hub.messages[1]["type"], "world_diff")


if __name__ == "__main__":
    unittest.main()
