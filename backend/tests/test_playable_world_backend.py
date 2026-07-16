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


class FakeWebSocket:
    def __init__(self) -> None:
        self.messages: list[dict] = []

    async def send_json(self, message: dict) -> None:
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
        self.assertEqual(response["offer_version"], 1)
        self.assertTrue(response["conversation_id"].startswith("conv_"))
        self.assertEqual(response["npc_id"], "mira")
        self.assertEqual(response["speaker"], "Mira")
        self.assertIn("workshop", response["line"])
        self.assertIn({"choice_id": "greet", "text": "Greet"}, response["choices"])
        self.assertIn({"choice_id": "ask_about_work", "text": "Ask About Work"}, response["choices"])
        self.assertIn({"choice_id": "ask_about_village", "text": "Ask About Village"}, response["choices"])
        self.assertIn({"choice_id": "goodbye", "text": "Goodbye"}, response["choices"])

    def test_normal_dialogue_choice_returns_player_facing_feedback(self) -> None:
        world = WorldSimulation()
        world.move_player("workshop")
        opened = world.player_interact_npc("mira", "talk")

        response = world.dialogue_choice(
            opened["conversation_id"],
            opened["offer_version"],
            "ask_about_work",
        )

        self.assertEqual(response["type"], "dialogue_result")
        self.assertEqual(response["offer_version"], 2)
        self.assertFalse(response["conversation_closed"])
        self.assertEqual(response["toast"], "Mira says the workshop is quiet, which is exactly how she likes it.")
        self.assertEqual(response["display_text"], response["toast"])
        self.assertEqual(response["world_diff"]["reason"], "dialogue_choice")

    def test_all_playable_npcs_expose_normal_conversation_choices(self) -> None:
        locations = {"mira": "workshop", "tomo": "farm", "ivo": "square"}

        for npc_id, location_id in locations.items():
            world = WorldSimulation()
            world.move_player(location_id)
            response = world.player_interact_npc(npc_id, "talk")
            choice_ids = {choice["choice_id"] for choice in response["choices"]}
            self.assertTrue(
                {"greet", "ask_about_work", "ask_about_village", "goodbye"}.issubset(choice_ids),
            )
            if npc_id == "ivo":
                self.assertIn("ask_about_missing_seeds", choice_ids)

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
        websocket = FakeWebSocket()

        response = asyncio.run(
            hub.handle_message(
                {
                    "type": "player_interact_npc",
                    "npc_id": "mira",
                    "interaction": "talk",
                },
                websocket=websocket,
                client_session_id="session_a",
            )
        )

        self.assertEqual(response["type"], "dialogue_opened")
        self.assertEqual(websocket.messages[-1]["type"], "dialogue_opened")
        self.assertEqual(hub.messages, [])

    def test_websocket_handler_broadcasts_dialogue_choice_world_diff(self) -> None:
        world = WorldSimulation()
        world.move_player("square")
        hub = CapturingHub(world)
        websocket = FakeWebSocket()
        opened = asyncio.run(
            hub.handle_message(
                {
                    "type": "player_interact_npc",
                    "npc_id": "ivo",
                    "interaction": "talk",
                },
                websocket=websocket,
                client_session_id="session_a",
            )
        )
        websocket.messages.clear()

        response = asyncio.run(
            hub.handle_message(
                {
                    "type": "dialogue_choice",
                    "conversation_id": opened["conversation_id"],
                    "offer_version": opened["offer_version"],
                    "choice_id": "ask_about_village",
                },
                websocket=websocket,
                client_session_id="session_a",
            )
        )

        self.assertEqual(response["type"], "dialogue_result")
        self.assertEqual(websocket.messages[0]["type"], "dialogue_result")
        self.assertEqual(hub.messages[0]["type"], "world_diff")


if __name__ == "__main__":
    unittest.main()
