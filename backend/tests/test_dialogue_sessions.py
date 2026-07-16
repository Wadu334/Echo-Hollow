from __future__ import annotations

import unittest

from backend.app.world import WorldSimulation


class DialogueSessionTests(unittest.TestCase):
    def test_only_one_open_conversation_per_session_and_closed_history_is_bounded(self) -> None:
        world = WorldSimulation()
        previous_conversation_id = ""
        for _ in range(70):
            opened = world.player_interact_npc("ivo", client_session_id="session_a")
            previous_conversation_id = opened["conversation_id"]
            world.dialogue_choice(
                opened["conversation_id"],
                opened["offer_version"],
                "goodbye",
                client_session_id="session_a",
            )

        closed = [
            conversation
            for conversation in world.conversations.values()
            if conversation.status == "closed"
        ]
        self.assertLessEqual(len(closed), 64)
        self.assertEqual(world.conversations[previous_conversation_id].close_reason, "choice:goodbye")
        self.assertNotIn("session_a", world._open_conversation_by_client)

    def test_closed_history_is_pruned_by_close_order_not_creation_order(self) -> None:
        world = WorldSimulation()
        early_opened = world.player_interact_npc("ivo", client_session_id="session_early")
        later_conversation_ids: list[str] = []

        for index in range(64):
            opened = world.player_interact_npc(
                "ivo",
                client_session_id=f"session_later_{index}",
            )
            later_conversation_ids.append(opened["conversation_id"])
            world.dialogue_choice(
                opened["conversation_id"],
                opened["offer_version"],
                "goodbye",
                client_session_id=f"session_later_{index}",
            )

        world.dialogue_choice(
            early_opened["conversation_id"],
            early_opened["offer_version"],
            "goodbye",
            client_session_id="session_early",
        )

        self.assertIn(early_opened["conversation_id"], world.conversations)
        self.assertEqual(
            world.conversations[early_opened["conversation_id"]].status,
            "closed",
        )
        self.assertNotIn(later_conversation_ids[0], world.conversations)
        self.assertIn(later_conversation_ids[-1], world.conversations)

    def test_ivo_claim_changes_future_offers_and_stale_offer_is_rejected(self) -> None:
        world = WorldSimulation()
        opened = world.player_interact_npc("ivo", client_session_id="session_a")
        initial_choice_ids = {choice["choice_id"] for choice in opened["choices"]}

        result = world.dialogue_choice(
            opened["conversation_id"],
            opened["offer_version"],
            "ask_about_missing_seeds",
            client_session_id="session_a",
        )
        event_cursor = world.snapshot()["event_log_cursor"]
        replay = world.dialogue_choice(
            opened["conversation_id"],
            opened["offer_version"],
            "ask_about_missing_seeds",
            client_session_id="session_a",
        )

        self.assertIn("ask_about_missing_seeds", initial_choice_ids)
        self.assertEqual(result["offer_version"], 2)
        self.assertNotIn(
            "ask_about_missing_seeds",
            {choice["choice_id"] for choice in result["choices"]},
        )
        self.assertEqual(
            world.player.notes[-1],
            {
                "note_id": "ivo_tomo_seed_claim",
                "title": "Ivo's Seed Claim",
                "text": "Ivo says Tomo may have taken the public seed bag.",
                "claim_id": "tomo_took_seeds",
                "source_actor_id": "ivo",
            },
        )
        self.assertEqual(replay["reason"], "stale_offer")
        self.assertEqual(world.snapshot()["event_log_cursor"], event_cursor)

    def test_resolved_episode_does_not_offer_missing_seed_claim_choices(self) -> None:
        world = WorldSimulation()
        world.world_events["evt_missing_seeds"]["phase"] = "resolved_reconciled"
        ivo_opened = world.player_interact_npc("ivo", client_session_id="session_a")
        world.player.notes.append(
            {
                "note_id": "ivo_tomo_seed_claim",
                "title": "Ivo's Seed Claim",
                "text": "Ivo says Tomo may have taken the public seed bag.",
                "claim_id": "tomo_took_seeds",
                "source_actor_id": "ivo",
            }
        )
        world.move_player("workshop")
        mira_opened = world.player_interact_npc("mira", client_session_id="session_a")

        self.assertNotIn(
            "ask_about_missing_seeds",
            {choice["choice_id"] for choice in ivo_opened["choices"]},
        )
        self.assertNotIn(
            "share_ivo_claim",
            {choice["choice_id"] for choice in mira_opened["choices"]},
        )

    def test_session_choice_and_interaction_validations_are_ordered(self) -> None:
        world = WorldSimulation()
        opened = world.player_interact_npc(
            "ivo",
            client_session_id="session_a",
        )

        mismatch = world.dialogue_choice(
            opened["conversation_id"],
            opened["offer_version"],
            "greet",
            client_session_id="session_b",
        )
        invalid_choice = world.dialogue_choice(
            opened["conversation_id"],
            opened["offer_version"],
            "not_offered",
            client_session_id="session_a",
        )
        world.npcs["ivo"].status_flags.append("uninteractable")
        invalidated = world.dialogue_choice(
            opened["conversation_id"],
            opened["offer_version"],
            "greet",
            client_session_id="session_a",
        )
        closed = world.dialogue_choice(
            opened["conversation_id"],
            opened["offer_version"],
            "greet",
            client_session_id="session_a",
        )

        self.assertEqual(mismatch["reason"], "session_mismatch")
        self.assertEqual(invalid_choice["reason"], "choice_not_offered")
        self.assertEqual(invalidated["reason"], "interaction_invalidated")
        self.assertEqual(closed["reason"], "conversation_closed")

    def test_authoritative_player_or_npc_movement_closes_open_conversation(self) -> None:
        world = WorldSimulation()
        ivo_opened = world.player_interact_npc("ivo", client_session_id="session_a")

        world.move_player("tavern")
        after_player_move = world.dialogue_choice(
            ivo_opened["conversation_id"],
            ivo_opened["offer_version"],
            "greet",
            client_session_id="session_a",
        )
        world.move_player("square")
        new_ivo_opened = world.player_interact_npc("ivo", client_session_id="session_a")
        world._change_npc_location("ivo", "tavern", "test")
        after_npc_move = world.dialogue_choice(
            new_ivo_opened["conversation_id"],
            new_ivo_opened["offer_version"],
            "greet",
            client_session_id="session_a",
        )

        self.assertEqual(after_player_move["reason"], "conversation_closed")
        self.assertEqual(after_npc_move["reason"], "conversation_closed")

    def test_stateful_claim_choice_cannot_be_applied_twice_across_sessions(self) -> None:
        world = WorldSimulation()
        ivo_opened = world.player_interact_npc("ivo", client_session_id="session_ivo")
        world.dialogue_choice(
            ivo_opened["conversation_id"],
            ivo_opened["offer_version"],
            "ask_about_missing_seeds",
            client_session_id="session_ivo",
        )
        world.move_player("workshop")
        mira_a = world.player_interact_npc("mira", client_session_id="session_a")
        mira_b = world.player_interact_npc("mira", client_session_id="session_b")

        accepted = world.dialogue_choice(
            mira_a["conversation_id"],
            mira_a["offer_version"],
            "share_ivo_claim",
            client_session_id="session_a",
        )
        duplicate = world.dialogue_choice(
            mira_b["conversation_id"],
            mira_b["offer_version"],
            "share_ivo_claim",
            client_session_id="session_b",
        )

        memory_shared_events = [
            event
            for event in world.events(limit=100)
            if event["type"] == "memory_shared"
            and event["target_id"] == "mira"
            and event["payload"].get("claim_id") == "tomo_took_seeds"
        ]
        proposed_talk_actions = [
            action
            for action in world.action_queue.values()
            if action.actor_id == "mira"
            and action.tool_name == "npc_talk_to"
            and action.args.get("target_id") == "tomo"
        ]

        self.assertTrue(accepted["conversation_closed"])
        self.assertEqual(duplicate["reason"], "conversation_closed")
        self.assertEqual(len(memory_shared_events), 1)
        self.assertEqual(len(proposed_talk_actions), 1)

    def test_stateful_choice_is_rechecked_after_external_world_change(self) -> None:
        world = WorldSimulation()
        ivo_opened = world.player_interact_npc("ivo", client_session_id="session_ivo")
        world.dialogue_choice(
            ivo_opened["conversation_id"],
            ivo_opened["offer_version"],
            "ask_about_missing_seeds",
            client_session_id="session_ivo",
        )
        world.move_player("workshop")
        mira_opened = world.player_interact_npc("mira", client_session_id="session_mira")

        world.share_claim("mira", "tomo_took_seeds")
        rejected = world.dialogue_choice(
            mira_opened["conversation_id"],
            mira_opened["offer_version"],
            "share_ivo_claim",
            client_session_id="session_mira",
        )

        memory_shared_events = [
            event
            for event in world.events(limit=100)
            if event["type"] == "memory_shared"
            and event["target_id"] == "mira"
            and event["payload"].get("claim_id") == "tomo_took_seeds"
        ]
        self.assertEqual(rejected["reason"], "choice_not_offered")
        self.assertEqual(len(memory_shared_events), 1)

    def test_ivo_to_mira_golden_path_reaches_visible_validator_consequence(self) -> None:
        world = WorldSimulation()
        ivo_opened = world.player_interact_npc("ivo", client_session_id="session_a")
        world.dialogue_choice(
            ivo_opened["conversation_id"],
            ivo_opened["offer_version"],
            "ask_about_missing_seeds",
            client_session_id="session_a",
        )
        world.move_player("workshop")
        mira_opened = world.player_interact_npc("mira", client_session_id="session_a")
        self.assertIn(
            "share_ivo_claim",
            {choice["choice_id"] for choice in mira_opened["choices"]},
        )

        shared = world.dialogue_choice(
            mira_opened["conversation_id"],
            mira_opened["offer_version"],
            "share_ivo_claim",
            client_session_id="session_a",
        )
        memory_shared_event = next(
            event
            for event in reversed(world.events(limit=30))
            if event["type"] == "memory_shared"
        )

        self.assertTrue(shared["conversation_closed"])
        self.assertEqual(memory_shared_event["payload"]["source_actor_id"], "ivo")
        self.assertEqual(memory_shared_event["payload"]["source_note_id"], "ivo_tomo_seed_claim")
        self.assertTrue(
            any(
                "Ivo's claim" in memory["summary"]
                for memory in shared["world_diff"]["memories"]["mira"]
            )
        )
        self.assertEqual(shared["world_diff"]["last_agent_trace"]["decision"], "action_proposed")
        self.assertEqual(
            shared["world_diff"]["last_director_trace"]["decisions"][-1]["decision_type"],
            "approve",
        )

        first_tick = world.tick()
        rejected_talk = next(
            action
            for action in world.action_queue.values()
            if action.tool_name == "npc_talk_to" and action.status == "rejected"
        )
        self.assertEqual(rejected_talk.validator_result["rejection_code"], "target_unavailable")
        self.assertEqual(world.last_director_trace["decisions"][-1]["decision_type"], "fallback")
        self.assertEqual(first_tick["actor_movements"], [])

        movement_tick = world.tick()
        movement = movement_tick["actor_movements"][0]
        self.assertEqual(movement["actor_id"], "mira")
        self.assertEqual(movement["from_location"], "workshop")
        self.assertEqual(movement["to_location"], "farm")

        world.tick()
        final_snapshot = world.snapshot()
        visible_event = next(
            event
            for event in reversed(world.events(limit=30))
            if event["type"] == "npc_dialogue_started"
        )
        self.assertEqual(visible_event["actor_id"], "mira")
        self.assertEqual(visible_event["target_id"], "tomo")
        self.assertEqual(visible_event["payload"]["topic"], "missing_seeds")
        self.assertEqual(final_snapshot["npcs"]["mira"]["mood"], "stern")
        self.assertEqual(final_snapshot["npcs"]["tomo"]["mood"], "hurt")
        self.assertLess(final_snapshot["relationships"]["tomo->mira"]["trust"], 0.5)

        before_replay = (
            len(world.memories),
            len(world.action_queue),
            world.snapshot()["event_log_cursor"],
        )
        replay = world.dialogue_choice(
            mira_opened["conversation_id"],
            mira_opened["offer_version"],
            "share_ivo_claim",
            client_session_id="session_a",
        )
        after_replay = (
            len(world.memories),
            len(world.action_queue),
            world.snapshot()["event_log_cursor"],
        )
        self.assertEqual(replay["reason"], "conversation_closed")
        self.assertEqual(after_replay, before_replay)


if __name__ == "__main__":
    unittest.main()
