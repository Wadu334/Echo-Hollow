from __future__ import annotations

import asyncio
import unittest

from backend.app.main import WorldHub
from backend.app.protocol import ProtocolError, parse_client_message, validate_client_payload
from backend.app.world import WorldSimulation


class FakeWebSocket:
    def __init__(self) -> None:
        self.accepted = False
        self.messages: list[dict] = []

    async def accept(self) -> None:
        self.accepted = True

    async def send_json(self, message: dict) -> None:
        self.messages.append(message)


class BlockingFakeWebSocket(FakeWebSocket):
    def __init__(self) -> None:
        super().__init__()
        self.block_next_send = False
        self.send_started = asyncio.Event()
        self.release_send = asyncio.Event()

    async def send_json(self, message: dict) -> None:
        if self.block_next_send:
            self.block_next_send = False
            self.send_started.set()
            await self.release_send.wait()
        await super().send_json(message)


class CapturingHub(WorldHub):
    def __init__(self, world: WorldSimulation) -> None:
        super().__init__(world)
        self.broadcasts: list[dict] = []

    async def broadcast(self, message: dict) -> None:
        self.broadcasts.append(message)


class ProtocolTests(unittest.TestCase):
    def test_parser_rejects_malformed_json_and_non_object_payloads(self) -> None:
        for text, expected_code in [
            ("{", "malformed_json"),
            ("[]", "payload_not_object"),
        ]:
            with self.subTest(text=text):
                with self.assertRaises(ProtocolError) as context:
                    parse_client_message(text)
                self.assertEqual(context.exception.code, expected_code)

    def test_validator_rejects_missing_wrong_type_and_unsupported_messages(self) -> None:
        cases = [
            ({}, "missing_field", "type"),
            ({"type": "wait_minutes", "minutes": "30"}, "invalid_field_type", "minutes"),
            ({"type": "wait_minutes", "minutes": True}, "invalid_field_type", "minutes"),
            ({"type": "not_real"}, "unsupported_message_type", "type"),
        ]
        for payload, expected_code, expected_field in cases:
            with self.subTest(payload=payload):
                with self.assertRaises(ProtocolError) as context:
                    validate_client_payload(payload)
                self.assertEqual(context.exception.code, expected_code)
                self.assertEqual(context.exception.field, expected_field)

    def test_existing_optional_command_defaults_remain_compatible(self) -> None:
        self.assertEqual(
            validate_client_payload({"type": "share_claim", "target_id": "mira"})["claim_id"],
            "tomo_took_seeds",
        )
        self.assertEqual(
            validate_client_payload(
                {
                    "type": "gossip",
                    "actor_id": "mira",
                    "target_id": "ivo",
                }
            )["rumor_id"],
            "rumor_tomo_took_seeds",
        )
        self.assertEqual(
            validate_client_payload({"type": "wait_minutes"})["minutes"],
            30,
        )

    def test_contextual_action_and_presentation_ack_require_strict_fields(self) -> None:
        self.assertEqual(
            validate_client_payload(
                {
                    "type": "activate_contextual_action",
                    "action_id": "inspect_torn_seed_bag_clue",
                    "offer_version": 1,
                }
            )["offer_version"],
            1,
        )
        self.assertEqual(
            validate_client_payload(
                {
                    "type": "ack_presentation",
                    "presentation_id": "presentation_1",
                }
            )["presentation_id"],
            "presentation_1",
        )
        for payload, field in [
            ({"type": "activate_contextual_action", "action_id": "x"}, "offer_version"),
            ({"type": "ack_presentation", "presentation_id": 1}, "presentation_id"),
        ]:
            with self.subTest(payload=payload):
                with self.assertRaises(ProtocolError) as context:
                    validate_client_payload(payload)
                self.assertEqual(context.exception.field, field)

    def test_legacy_dialogue_choice_is_explicitly_rejected(self) -> None:
        with self.assertRaises(ProtocolError) as context:
            validate_client_payload(
                {
                    "type": "dialogue_choice",
                    "npc_id": "ivo",
                    "choice_id": "greet",
                }
            )

        error = context.exception
        self.assertEqual(error.code, "missing_conversation_id")
        self.assertEqual(error.to_message()["type"], "dialogue_rejected")

    def test_bad_message_is_targeted_and_does_not_mutate_or_close_session(self) -> None:
        world = WorldSimulation()
        hub = CapturingHub(world)
        websocket = FakeWebSocket()
        start_cursor = world.snapshot()["event_log_cursor"]

        result = asyncio.run(
            hub.handle_text(
                "{",
                websocket=websocket,
                client_session_id="session_a",
            )
        )
        cursor_after_bad_message = world.snapshot()["event_log_cursor"]
        valid_result = asyncio.run(
            hub.handle_text(
                '{"type":"move_player","location_id":"tavern"}',
                websocket=websocket,
                client_session_id="session_a",
            )
        )

        self.assertEqual(result["type"], "client_error")
        self.assertEqual(result["code"], "malformed_json")
        self.assertEqual(cursor_after_bad_message, start_cursor)
        self.assertEqual(valid_result["reason"], "player_moved")
        self.assertEqual(hub.broadcasts[-1]["type"], "world_diff")

    def test_connect_assigns_session_id_in_initial_world_state(self) -> None:
        world = WorldSimulation()
        hub = CapturingHub(world)
        websocket = FakeWebSocket()

        client_session_id = asyncio.run(hub.connect(websocket))

        self.assertTrue(websocket.accepted)
        self.assertEqual(websocket.messages[0]["type"], "world_state")
        self.assertEqual(websocket.messages[0]["client_session_id"], client_session_id)
        self.assertTrue(client_session_id.startswith("session_"))
        self.assertEqual(websocket.messages[0]["recovery_events"], [])

    def test_connect_after_cursor_returns_recovery_events_before_snapshot_consumption(self) -> None:
        world = WorldSimulation()
        cursor = world.snapshot()["event_log_cursor"]
        world.move_player("tavern")
        hub = CapturingHub(world)
        websocket = FakeWebSocket()

        asyncio.run(hub.connect(websocket, after_cursor=cursor))

        recovery = websocket.messages[0]
        state = websocket.messages[1]
        self.assertEqual(recovery["type"], "recovery_events")
        self.assertEqual(recovery["from_cursor"], cursor)
        self.assertEqual(recovery["to_cursor"], cursor + 1)
        self.assertFalse(recovery["has_more"])
        self.assertEqual(recovery["events"][0]["type"], "player_moved")
        self.assertEqual(state["type"], "world_state")
        self.assertEqual(state["recovery_events"], [])
        self.assertEqual(state["data"]["event_log_cursor"], world.snapshot()["event_log_cursor"])

    def test_connect_pages_more_than_five_hundred_recovery_events_without_a_cursor_gap(self) -> None:
        world = WorldSimulation()
        cursor = world.snapshot()["event_log_cursor"]
        for index in range(1201):
            world._append_event(
                event_type="recovery_probe",
                actor_id=None,
                target_id=None,
                payload={"index": index},
            )
        snapshot_cursor = world.snapshot()["event_log_cursor"]
        hub = CapturingHub(world)
        websocket = FakeWebSocket()

        asyncio.run(hub.connect(websocket, after_cursor=cursor))

        pages = websocket.messages[:-1]
        state = websocket.messages[-1]
        self.assertEqual([len(page["events"]) for page in pages], [500, 500, 201])
        self.assertEqual([page["has_more"] for page in pages], [True, True, False])
        expected_from = cursor
        recovered_indexes: list[int] = []
        for page in pages:
            self.assertEqual(page["type"], "recovery_events")
            self.assertEqual(page["from_cursor"], expected_from)
            self.assertEqual(page["to_cursor"], expected_from + len(page["events"]))
            expected_from = page["to_cursor"]
            recovered_indexes.extend(event["payload"]["index"] for event in page["events"])
        self.assertEqual(expected_from, snapshot_cursor)
        self.assertEqual(recovered_indexes, list(range(1201)))
        self.assertEqual(state["type"], "world_state")
        self.assertEqual(state["data"]["event_log_cursor"], snapshot_cursor)

    def test_disconnect_closes_that_sessions_open_conversation(self) -> None:
        world = WorldSimulation()
        hub = CapturingHub(world)
        websocket = FakeWebSocket()

        async def scenario() -> tuple[str, str]:
            client_session_id = await hub.connect(websocket)
            opened = await hub.handle_message(
                {
                    "type": "player_interact_npc",
                    "npc_id": "ivo",
                    "interaction": "talk",
                },
                websocket=websocket,
                client_session_id=client_session_id,
            )
            await hub.disconnect(websocket)
            return client_session_id, opened["conversation_id"]

        client_session_id, conversation_id = asyncio.run(scenario())

        self.assertNotIn(client_session_id, world._open_conversation_by_client)
        self.assertEqual(world.conversations[conversation_id].status, "closed")
        self.assertEqual(world.conversations[conversation_id].close_reason, "client_disconnected")

    def test_dialogue_is_targeted_but_embedded_world_diff_is_broadcast(self) -> None:
        world = WorldSimulation()
        hub = WorldHub(world)
        requester = FakeWebSocket()
        observer = FakeWebSocket()

        async def scenario() -> None:
            requester_session = await hub.connect(requester)
            await hub.connect(observer)
            requester.messages.clear()
            observer.messages.clear()
            opened = await hub.handle_message(
                {
                    "type": "player_interact_npc",
                    "npc_id": "ivo",
                    "interaction": "talk",
                },
                websocket=requester,
                client_session_id=requester_session,
            )
            await hub.handle_message(
                {
                    "type": "dialogue_choice",
                    "conversation_id": opened["conversation_id"],
                    "offer_version": opened["offer_version"],
                    "choice_id": "greet",
                },
                websocket=requester,
                client_session_id=requester_session,
            )

        asyncio.run(scenario())

        self.assertEqual(
            [message["type"] for message in requester.messages],
            ["dialogue_opened", "dialogue_result", "world_diff"],
        )
        self.assertEqual(
            [message["type"] for message in observer.messages],
            ["world_diff"],
        )
        self.assertTrue(
            requester.messages[1]["world_diff"]["presentation"]["toasts"],
        )
        self.assertEqual(
            observer.messages[0]["data"]["presentation"]["toasts"],
            [],
        )

    def test_state_mutation_and_delivery_are_serialized_across_tick(self) -> None:
        world = WorldSimulation()
        world.minute_of_day = 11 * 60 + 59
        hub = WorldHub(world)
        requester = BlockingFakeWebSocket()
        observer = FakeWebSocket()

        async def scenario() -> bool:
            requester_session = await hub.connect(requester)
            await hub.connect(observer)
            requester.messages.clear()
            observer.messages.clear()
            opened = await hub.handle_message(
                {
                    "type": "player_interact_npc",
                    "npc_id": "ivo",
                    "interaction": "talk",
                },
                websocket=requester,
                client_session_id=requester_session,
            )
            requester.messages.clear()
            observer.messages.clear()

            requester.block_next_send = True
            choice_task = asyncio.create_task(
                hub.handle_message(
                    {
                        "type": "dialogue_choice",
                        "conversation_id": opened["conversation_id"],
                        "offer_version": opened["offer_version"],
                        "choice_id": "greet",
                    },
                    websocket=requester,
                    client_session_id=requester_session,
                )
            )
            await asyncio.wait_for(requester.send_started.wait(), timeout=1.0)
            tick_task = asyncio.create_task(hub.tick())
            await asyncio.sleep(0)
            tick_was_blocked = not tick_task.done()
            requester.release_send.set()
            await asyncio.gather(choice_task, tick_task)
            return tick_was_blocked

        tick_was_blocked = asyncio.run(scenario())

        self.assertTrue(tick_was_blocked)
        observer_diffs = [
            message["data"]
            for message in observer.messages
            if message["type"] == "world_diff"
        ]
        self.assertEqual(
            [diff["world_minute"] for diff in observer_diffs],
            [11 * 60 + 59, 12 * 60],
        )
        self.assertEqual(
            observer_diffs[0]["npcs"]["mira"]["current_location"],
            "workshop",
        )
        self.assertEqual(
            observer_diffs[1]["npcs"]["mira"]["current_location"],
            "tavern",
        )


if __name__ == "__main__":
    unittest.main()
