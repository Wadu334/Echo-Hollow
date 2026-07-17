extends SceneTree

var failures: Array[String] = []


class FakeWorldConnection:
	extends Node
	var connection_status := "Online"
	var contextual_request: Dictionary = {}
	var npc_request := ""

	func send_activate_contextual_action(action_id: String, offer_version: int) -> bool:
		contextual_request = {
			"action_id": action_id,
			"offer_version": offer_version,
		}
		return true

	func send_interact_npc(npc_id: String) -> bool:
		npc_request = npc_id
		return true


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
	var presenter = root.get_node_or_null("WorldPresenter")
	if presenter != null:
		presenter.reset_for_fresh_world()
	var scene := load("res://scenes/main.tscn")
	if scene == null:
		_fail("Could not load main scene.")
		return

	var main = scene.instantiate()
	main.enable_server_connection = false
	root.add_child(main)
	await process_frame
	await physics_frame

	_expect(main.location_nodes.size() == 5, "Expected 5 logical location markers.")
	for location_id in ["square", "tavern", "farm", "workshop", "warehouse"]:
		var marker = main.location_nodes.get(location_id)
		_expect(marker != null and marker.has_node("%s_sign" % location_id), "Expected %s location sign." % location_id)
	_expect(main.actor_nodes.has("player"), "Expected player node.")
	_expect(main.actor_nodes.has("mira"), "Expected Mira node.")
	_expect(main.actor_nodes.has("tomo"), "Expected Tomo node.")
	_expect(main.actor_nodes.has("ivo"), "Expected Ivo node.")

	var player = main.actor_nodes["player"]
	_expect(player is CharacterBody2D, "Expected player to be a CharacterBody2D.")
	_expect(player.has_node("Sprite"), "Expected player sprite.")
	_expect(player.get_node("Sprite").texture != null, "Expected player sprite texture.")

	for npc_id in ["mira", "tomo", "ivo"]:
		var npc = main.actor_nodes[npc_id]
		_expect(npc is CharacterBody2D, "Expected %s to be a CharacterBody2D." % npc_id)
		_expect(npc.has_node("Sprite"), "Expected %s sprite." % npc_id)
		_expect(npc.get_node("Sprite").texture != null, "Expected %s sprite texture." % npc_id)
		_expect(npc.has_node("StateBubble"), "Expected %s state bubble." % npc_id)
		_expect(npc.get_node("StateBubble").visible, "Expected %s state bubble visible." % npc_id)

	_expect(
		player.position.distance_to(main.actor_nodes["ivo"].position) <= main.INTERACTION_DISTANCE,
		"Expected Ivo to be the first talkable NPC near the spawn point."
	)
	main._update_approach_prompt()
	_expect(main.approach_label.visible, "Expected a visible talk prompt near the first NPC.")
	_expect("Ivo" in main.approach_label.text, "Expected the first talk prompt to name Ivo.")

	_expect(main.prop_root.get_child_count() >= 6, "Expected collision props.")
	_expect(main.tile_texture != null, "Expected tile texture.")
	_expect(main.prop_texture != null, "Expected prop texture.")

	player.position = Vector2(420, 345)
	await physics_frame
	var collision = player.move_and_collide(Vector2(80, 0), true)
	_expect(collision != null, "Expected player collision probe against the well.")

	main.bubbles_visible = false
	main._update_bubble_visibility()
	_expect(not main.actor_nodes["mira"].get_node("StateBubble").visible, "Expected bubble toggle to hide Mira state.")
	main.bubbles_visible = true
	main._update_bubble_visibility()
	_expect(main.actor_nodes["mira"].get_node("StateBubble").visible, "Expected bubble toggle to show Mira state.")

	main._update_actor_animation("player", Vector2.RIGHT, 0.2)
	var player_sprite: Sprite2D = player.get_node("Sprite")
	_expect(player_sprite.frame_coords.y == main.DIRECTION_ROWS["right"], "Expected player right animation row.")

	main._update_actor_animation("player", Vector2.UP, 0.2)
	_expect(player_sprite.frame_coords.y == main.DIRECTION_ROWS["up"], "Expected player up animation row.")

	var start_position: Vector2 = player.position
	main._jump_player_to_location("farm")
	await physics_frame
	_expect(main.local_player_location == "farm", "Expected logical jump to farm.")
	_expect(player.position.distance_to(start_position) > 20.0, "Expected player position to change.")

	main._apply_server_message({
		"type": "world_state",
		"data": _world_state(),
	})
	await process_frame
	var player_state: Dictionary = main.world_data.get("player", {})
	_expect(player_state.get("current_location", "") == "square", "Expected server state merge, got %s." % str(player_state))
	_expect(main.local_player_location == "square", "Expected the backend snapshot to own the logical player location.")
	_expect(
		player.position.distance_to(main.LOCATION_CENTERS["square"]) < 1.0,
		"Expected world_state to snap the player to the authoritative logical anchor, got %s." % str(player.position)
	)
	_expect(
		main.actor_nodes["mira"].position.distance_to(main.LOCATION_CENTERS["workshop"]) < 1.0,
		"Expected world_state to snap Mira to the authoritative Workshop."
	)
	_expect("The Missing Seed Pouch" in main.event_label.text, "Expected server event_title to be visible.")
	_expect("Gathering Clues" in main.event_label.text, "Expected server event_phase_text to be visible.")
	_expect("Neighbors are comparing clues." in main.event_label.text, "Expected server village_flow_text to be visible.")
	main._update_status_label()
	_expect("Ask Ivo" in main.objective_label.text, "Expected the server objective to be visible.")

	var mira_bubble_label: Label = main.actor_nodes["mira"].get_node("StateBubble/StateLabel")
	_expect("mem 0" in mira_bubble_label.text, "Expected an empty grouped Mira memory list to show mem 0.")
	var memory_state := _world_state()
	memory_state["memories"]["mira"] = [
		{
			"memory_id": "mem_mira_claim",
			"owner_id": "mira",
			"type": "rumor",
		},
	]
	main._apply_server_message({"type": "world_state", "data": memory_state})
	await process_frame
	_expect("mem 1" in mira_bubble_label.text, "Expected grouped Mira memories to increase the visible bubble count.")

	for objective in [
		"Ask Ivo about the missing seeds",
		"Tell Mira what Ivo said",
		"Check the Warehouse",
		"Show Mira the evidence",
		"Observe the outcome",
	]:
		var objective_state := _world_state()
		objective_state["presentation"]["objective"] = objective
		main._apply_server_message({"type": "world_state", "data": objective_state})
		main._update_status_label()
		_expect(objective in main.objective_label.text, "Expected objective step '%s' to be visible." % objective)

	var contextual_state := _world_state()
	contextual_state["player"]["current_location"] = "warehouse"
	contextual_state["presentation"]["contextual_action"] = {
		"action_id": "inspect_torn_seed_bag",
		"offer_version": 3,
		"label": "Inspect the torn seed bag",
		"prompt": "Press E to inspect the torn seed bag",
		"location_id": "warehouse",
	}
	main._apply_server_message({"type": "world_state", "data": contextual_state})
	await process_frame
	var fake_connection := FakeWorldConnection.new()
	main.world_connection = fake_connection
	main.connected = true
	_expect(main.contextual_marker_nodes["warehouse"].visible, "Expected the offered Warehouse clue to have a visible marker.")
	main._update_approach_prompt()
	_expect(not main.approach_label.visible, "Expected no clue prompt while far from the specific Warehouse marker.")
	main.player_body.position = main.CONTEXTUAL_ACTION_ANCHORS["warehouse"]
	main._update_approach_prompt()
	_expect(main.approach_label.visible, "Expected a Warehouse contextual prompt near the specific clue.")
	_expect("inspect the torn seed bag" in main.approach_label.text, "Expected the contextual prompt to name the exact action.")
	main.actor_nodes["ivo"].position = main.CONTEXTUAL_ACTION_ANCHORS["warehouse"] + Vector2(30, 0)
	_expect(
		str(main._current_interaction().get("kind", "")) == "contextual_action",
		"Expected the closer clue to win when clue and NPC are both candidates."
	)
	main.player_body.position = main.actor_nodes["ivo"].position
	_expect(
		str(main._current_interaction().get("kind", "")) == "npc",
		"Expected the closer NPC to win when clue and NPC are both candidates."
	)
	main.player_body.position = main.CONTEXTUAL_ACTION_ANCHORS["warehouse"]
	main._activate_current_interaction()
	_expect(
		fake_connection.contextual_request == {"action_id": "inspect_torn_seed_bag", "offer_version": 3},
		"Expected E to submit only the server-offered contextual action token."
	)
	main.connected = false
	main.world_connection = null
	fake_connection.free()
	main._apply_server_message({"type": "world_state", "data": _world_state()})

	main._apply_server_message({
		"type": "dialogue_opened",
		"conversation_id": "conv_test_001",
		"offer_version": 1,
		"npc_id": "mira",
		"speaker": "Mira",
		"line": "Good to see you.",
		"choices": [
			{"choice_id": "greet", "text": "Greet"},
			{"choice_id": "ask_about_work", "text": "Ask About Work"},
			{"choice_id": "ask_about_village", "text": "Ask About Village"},
			{"choice_id": "goodbye", "text": "Goodbye"},
		],
	})
	await process_frame
	_expect(main.dialogue_panel.visible, "Expected dialogue panel to open.")
	_expect(main.active_dialogue_npc_id == "mira", "Expected active dialogue NPC.")
	_expect(main.active_conversation_id == "conv_test_001", "Expected the dialogue conversation token.")
	_expect(main.active_offer_version == 1, "Expected the initial offered-choice version.")
	_expect(main.dialogue_choices_box.get_child_count() == 4, "Expected four normal dialogue choices.")

	main._apply_server_message({
		"type": "dialogue_result",
		"conversation_id": "conv_test_001",
		"offer_version": 2,
		"npc_id": "mira",
		"choice_id": "ask_about_work",
		"display_text": "Mira says the workshop is quiet.",
		"choices": [
			{"choice_id": "greet", "text": "Greet"},
			{"choice_id": "goodbye", "text": "Goodbye"},
		],
		"world_diff": _world_state(),
	})
	await process_frame
	_expect(main.toast_label.visible, "Expected toast after dialogue choice.")
	_expect("workshop" in main.dialogue_line_label.text, "Expected dialogue result text in panel.")
	_expect(main.active_offer_version == 2, "Expected the refreshed offered-choice version.")
	_expect(main.dialogue_choices_box.get_child_count() == 2, "Expected refreshed choices from the server.")

	main._apply_server_message({
		"type": "dialogue_result",
		"conversation_id": "conv_test_001",
		"offer_version": 2,
		"npc_id": "mira",
		"choice_id": "goodbye",
		"conversation_closed": true,
		"display_text": "You step back from Mira's workbench.",
		"world_diff": _world_state(),
	})
	await process_frame
	_expect(not main.dialogue_panel.visible, "Expected goodbye to close the dialogue panel.")
	_expect(main.active_dialogue_npc_id == "", "Expected active dialogue NPC to clear after goodbye.")
	_expect(main.active_conversation_id == "", "Expected the conversation token to clear after goodbye.")

	var moved_state := _world_state()
	moved_state["npcs"]["mira"]["current_location"] = "farm"
	moved_state["actor_movements"] = [
		{
			"actor_id": "mira",
			"from_location": "workshop",
			"to_location": "farm",
			"duration_seconds": 0.05,
			"display_text": "Mira is heading to the Farm.",
		},
	]
	main._apply_server_message({
		"type": "world_diff",
		"data": moved_state,
	})
	await create_timer(0.1).timeout
	_expect(
		main.actor_nodes["mira"].position.distance_to(main.LOCATION_CENTERS["farm"]) < 1.0,
		"Expected a valid actor_movement to tween Mira to the authoritative Farm."
	)
	_expect("heading to the Farm" in main.toast_label.text, "Expected movement display text to become a toast.")

	var mismatched_movement := _world_state()
	mismatched_movement["actor_movements"] = [
		{
			"actor_id": "mira",
			"from_location": "farm",
			"to_location": "farm",
			"duration_seconds": 0.05,
		},
	]
	main._apply_server_message({
		"type": "world_diff",
		"data": mismatched_movement,
	})
	await process_frame
	_expect(
		main.actor_nodes["mira"].position.distance_to(main.LOCATION_CENTERS["workshop"]) < 1.0,
		"Expected a movement/auth-location mismatch to snap Mira to the authoritative Workshop."
	)

	var missing_movement := _world_state()
	missing_movement["npcs"]["mira"]["current_location"] = "farm"
	missing_movement["actor_movements"] = []
	main._apply_server_message({
		"type": "world_diff",
		"data": missing_movement,
	})
	await process_frame
	_expect(
		main.actor_nodes["mira"].position.distance_to(main.LOCATION_CENTERS["farm"]) < 1.0,
		"Expected a changed authoritative NPC location without actor_movements to snap to the Farm."
	)

	main.connected = true
	main.has_connected_once = true
	main._tween_actor_to_location("mira", "workshop", {
		"duration_seconds": 0.5,
	})
	await create_timer(0.05).timeout
	var disconnected_mira_position: Vector2 = main.actor_nodes["mira"].position
	main._on_connection_changed(false)
	await create_timer(0.15).timeout
	_expect(
		main.actor_nodes["mira"].position.distance_to(disconnected_mira_position) < 0.1,
		"Expected disconnect to stop an active authoritative NPC tween."
	)
	_expect(not main.actor_tweens.has("mira"), "Expected disconnect to clear Mira's active tween.")

	player.position = Vector2(900, 600)
	main.pending_player_location = "warehouse"
	var intermediate_tick := _world_state()
	intermediate_tick["reason"] = "tick"
	main._apply_server_message({
		"type": "world_diff",
		"data": intermediate_tick,
	})
	await process_frame
	_expect(
		main.pending_player_location == "warehouse",
		"Expected an unrelated tick to preserve the pending player location intent."
	)
	_expect(
		player.position.distance_to(Vector2(900, 600)) < 1.0,
		"Expected an unrelated tick not to snap the player before the location result."
	)

	var rejected_move := _world_state()
	rejected_move["reason"] = "not_reachable"
	main._apply_server_message({
		"type": "world_diff",
		"data": rejected_move,
	})
	await process_frame
	_expect(
		player.position.distance_to(main.LOCATION_CENTERS["square"]) < 1.0,
		"Expected movement rejection to restore the authoritative player position."
	)
	_expect(main.pending_player_location == "", "Expected movement rejection to clear the pending intent.")

	main.pending_rumor_scene = true
	main.scene_transition_started = false
	main._snap_actor_to_location("mira", "farm")
	await process_frame
	_expect(
		not main.pending_rumor_scene and not main.scene_transition_started,
		"Expected an authoritative Mira snap to consume a pending consequence transition safely."
	)

	_expect(load("res://scenes/rumor_consequence.tscn") != null, "Expected the independent rumor consequence scene.")
	_expect(root.has_node("WorldPresenter"), "Expected the persistent WorldPresenter autoload.")
	_expect(root.has_node("WorldConnection"), "Expected the persistent WorldConnection autoload.")
	var connection = root.get_node("WorldConnection")
	var duplicate_diff := _world_state()
	duplicate_diff["reason"] = "tick"
	duplicate_diff["world_minute"] = 480
	connection._reset_session_state()
	_expect(connection._consume_world_diff(duplicate_diff), "Expected the first authoritative diff to be consumed.")
	_expect(
		not connection._consume_world_diff(duplicate_diff),
		"Expected the identical targeted/broadcast world diff to be deduplicated."
	)
	connection.client_session_id = "session_stale"
	connection.active_dialogue = {"conversation_id": "conv_stale"}
	connection.processed_event_log_ids["event_000001"] = true
	connection.rumor_consequence_payload = {"presentation_id": "outcome_stale", "line": "stale"}
	connection.last_consumed_event_cursor = 42
	connection._reset_session_state()
	_expect(connection.client_session_id == "", "Expected reconnect reset to clear the old client session id.")
	_expect(connection.active_dialogue.is_empty(), "Expected reconnect reset to clear stale dialogue state.")
	_expect(connection.processed_event_log_ids.has("event_000001"), "Expected transient reconnect to retain event dedup state.")
	_expect(not connection.rumor_consequence_payload.is_empty(), "Expected transient reconnect to retain pending consequence data.")
	_expect(connection.last_consumed_event_cursor == 42, "Expected transient reconnect to retain the consumed cursor.")
	_expect("after_cursor=42" in connection._connection_url(), "Expected reconnect URL to request cursor catch-up.")
	connection.manual_disconnect_requested = false
	connection.reconnect_attempt = 8
	connection._schedule_reconnect()
	_expect(connection.connection_status == "Reconnecting", "Expected an explicit Reconnecting status.")
	_expect(
		connection.reconnect_delay_remaining <= connection.RECONNECT_MAX_DELAY_SECONDS,
		"Expected exponential reconnect delay to be capped."
	)
	connection.reconnect_scheduled = false
	connection.manual_disconnect_requested = true
	connection.set_process(false)
	main.world_connection = connection
	for status in ["Connecting", "Reconnecting", "Offline"]:
		connection._set_connection_status(status)
		main._update_status_label()
		_expect(status in main.status_label.text, "Expected visible %s connection status." % status)
	main.world_connection = null
	connection._reset_session_state(true)
	connection.has_authoritative_snapshot = true
	connection.has_ever_connected = true
	connection.recovery_in_progress = true
	connection.last_consumed_event_cursor = 10
	connection._set_connection_status("Reconnecting")
	connection._apply_server_message({
		"type": "recovery_events",
		"from_cursor": 10,
		"to_cursor": 11,
		"has_more": true,
		"events": _recovery_events(10, 1),
	})
	var premature_snapshot := _world_state()
	premature_snapshot["event_log_cursor"] = 12
	connection._apply_server_message({
		"type": "world_state",
		"client_session_id": "session_incomplete_recovery",
		"recovery_events": [],
		"data": premature_snapshot,
	})
	_expect(not connection.connected, "Expected a snapshot with a recovery cursor gap not to become Online.")
	_expect(connection.connection_status == "Reconnecting", "Expected incomplete recovery to remain Reconnecting.")
	_expect(connection.last_consumed_event_cursor == 11, "Expected incomplete recovery not to jump to the snapshot cursor.")

	connection._reset_session_state(true)
	connection.has_authoritative_snapshot = true
	connection.has_ever_connected = true
	connection.recovery_in_progress = true
	connection.last_consumed_event_cursor = 10
	connection._set_connection_status("Reconnecting")
	connection._apply_server_message({
		"type": "recovery_events",
		"from_cursor": 10,
		"to_cursor": 510,
		"has_more": true,
		"events": _recovery_events(10, 500),
	})
	_expect(connection.last_consumed_event_cursor == 510, "Expected the first recovery page cursor to be consumed exactly.")
	_expect(not connection.connected, "Expected a partial recovery page not to become Online.")
	connection._apply_server_message({
		"type": "recovery_events",
		"from_cursor": 510,
		"to_cursor": 611,
		"has_more": false,
		"events": _recovery_events(510, 101),
	})
	_expect(connection.last_consumed_event_cursor == 611, "Expected the final recovery page cursor to be consumed exactly.")
	_expect(connection.last_recovery_event_count == 601, "Expected recovery pages to accumulate all 601 events.")
	var complete_snapshot := _world_state()
	complete_snapshot["event_log_cursor"] = 611
	connection._apply_server_message({
		"type": "world_state",
		"client_session_id": "session_complete_recovery",
		"recovery_events": [],
		"data": complete_snapshot,
	})
	_expect(connection.connected, "Expected a fully caught-up recovery snapshot to become Online.")
	_expect(connection.connection_status == "Online", "Expected complete paged recovery to restore Online.")
	_expect(connection.last_consumed_event_cursor == 611, "Expected snapshot application not to skip the recovered cursor.")

	connection.pending_presentation_ack_ids = {
		"pres_still_pending": true,
		"pres_already_removed": true,
	}
	connection.world_data = {
		"pending_presentations": [
			{"presentation_id": "pres_still_pending"},
		],
	}
	connection._reconcile_pending_presentation_acks()
	_expect(
		connection.pending_presentation_ack_ids.has("pres_still_pending"),
		"Expected an unconfirmed server presentation ack to remain queued."
	)
	_expect(
		not connection.pending_presentation_ack_ids.has("pres_already_removed"),
		"Expected snapshot reconciliation to retire an ack already applied by the server."
	)

	if presenter != null:
		presenter.reset_for_fresh_world()
		presenter.ingest_authoritative_events([
			{
				"event_log_id": "elog_without_presentation",
				"type": "npc_dialogue_started",
				"actor_id": "mira",
				"target_id": "tomo",
				"payload": {"topic": "missing_seeds"},
			},
		])
		_expect(
			not presenter.has_pending_consequence(),
			"Expected a bare authority event without a server presentation payload not to synthesize a consequence."
		)
		var outcome := {
			"presentation_id": "pres_reconciled_001",
			"type": "reconciliation_consequence",
			"title": "The Evidence Clears Tomo",
			"line": "The torn seam shows the pouch broke near the Warehouse.",
			"reaction_text": "Tomo exhales as the suspicion lifts.",
			"relationship_trend_text": "Mira and Tomo begin rebuilding trust.",
			"reflection_text": "Mira resolves to check evidence before repeating a claim.",
			"path": "reconciled",
			"event_log_id": "elog_000099",
		}
		_expect(presenter.enqueue_consequence(outcome), "Expected a valid server outcome to queue for presentation.")
		_expect(not presenter.enqueue_consequence(outcome), "Expected the same presentation_id to deduplicate.")
		var consequence_scene = load("res://scenes/rumor_consequence.tscn").instantiate()
		root.add_child(consequence_scene)
		await process_frame
		_expect(_node_text_contains(consequence_scene, "The Evidence Clears Tomo"), "Expected server outcome title in the consequence scene.")
		_expect(_node_text_contains(consequence_scene, "suspicion lifts"), "Expected server reaction text in the consequence scene.")
		_expect(_node_text_contains(consequence_scene, "rebuilding trust"), "Expected a relationship trend instead of exact values.")
		_expect(not _node_text_contains(consequence_scene, "trust 0."), "Expected normal consequence UI to hide exact relationship values.")
		consequence_scene.queue_free()
		await process_frame
		presenter.acknowledge_consequence("pres_reconciled_001")
		_expect(not presenter.enqueue_consequence(outcome), "Expected an acknowledged outcome to remain exactly-once.")

	connection._reset_session_state(true)

	if not failures.is_empty():
		for failure in failures:
			push_error(failure)
		quit(1)
		return
	print("Godot playable client verification passed.")
	quit(0)


func _world_state() -> Dictionary:
	return {
		"world_id": "demo_world_001",
		"time": "day 1 08:00",
		"event_log_cursor": 1,
		"locations": {
			"square": _location("square", "Square", 480, 340),
			"tavern": _location("tavern", "Tavern", 176, 210),
			"farm": _location("farm", "Farm", 790, 430),
			"workshop": _location("workshop", "Workshop", 230, 500),
			"warehouse": _location("warehouse", "Warehouse", 760, 180),
		},
		"player": {
			"player_id": "player",
			"current_location": "square",
		},
		"npcs": {
			"mira": _npc("mira", "Mira", "workshop", "steady"),
			"tomo": _npc("tomo", "Tomo", "farm", "guarded"),
			"ivo": _npc("ivo", "Ivo", "square", "warm"),
		},
		"memories": {
			"mira": [],
			"tomo": [],
			"ivo": [],
		},
		"rumors": {},
		"latest_events": [
			{
				"world_time": "day 1 08:00",
				"type": "test_event",
			},
		],
		"presentation": {
			"event_title": "The Missing Seed Pouch",
			"event_phase_text": "Gathering Clues",
			"village_flow_text": "Neighbors are comparing clues.",
			"objective": "Ask Ivo about the missing seeds",
			"contextual_action": null,
			"toasts": [],
		},
		"pending_presentations": [],
	}


func _recovery_events(from_cursor: int, count: int) -> Array:
	var events: Array = []
	for offset in count:
		events.append({
			"event_log_id": "elog_recovery_%06d" % (from_cursor + offset + 1),
			"type": "recovery_probe",
			"actor_id": null,
			"target_id": null,
			"payload": {"offset": offset},
		})
	return events


func _location(location_id: String, label: String, x: int, y: int) -> Dictionary:
	return {
		"location_id": location_id,
		"name": label,
		"position": {
			"x": x,
			"y": y,
		},
		"current_occupants": [],
	}


func _npc(npc_id: String, label: String, location_id: String, mood: String) -> Dictionary:
	return {
		"npc_id": npc_id,
		"name": label,
		"current_location": location_id,
		"current_action": "test",
		"current_goal": "test_goal",
		"mood": mood,
	}


func _expect(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)


func _node_text_contains(node: Node, fragment: String) -> bool:
	for child in node.find_children("*", "Label", true, false):
		if fragment in str(child.text):
			return true
	return false


func _fail(message: String) -> void:
	failures.append(message)
	for failure in failures:
		push_error(failure)
	quit(1)
