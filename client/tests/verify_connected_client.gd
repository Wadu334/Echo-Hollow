extends SceneTree

var failures: Array[String] = []
var world_connection: Node
var saw_protocol_error := false
var saw_location_rejection := false
var saw_mira_movement := false
var saw_consequence_signal := false
var saw_authoritative_dialogue_event := false
var connection_status_history: Array[String] = []
var consequence_signal_counts: Dictionary = {}
var consequence_scene_entry_counts: Dictionary = {}
var movement_key_states: Dictionary = {}
var world_presenter: Node


func _init() -> void:
	node_added.connect(Callable(self, "_on_node_added"))
	call_deferred("_run")


func _run() -> void:
	if OS.get_environment("ECHO_HOLLOW_SERVER_URL").strip_edges().is_empty():
		_fail_and_quit("ECHO_HOLLOW_SERVER_URL must point to the fresh FastAPI test server.")
		return

	var scene_error := change_scene_to_file("res://scenes/main.tscn")
	if scene_error != OK:
		_fail_and_quit("Could not load the main scene.")
		return
	await process_frame
	await process_frame

	world_connection = root.get_node_or_null("WorldConnection")
	world_presenter = root.get_node_or_null("WorldPresenter")
	if world_connection == null:
		_fail_and_quit("WorldConnection autoload is missing.")
		return
	world_connection.connect("world_diff_received", Callable(self, "_on_world_diff"))
	world_connection.connect("client_error", Callable(self, "_on_client_error"))
	world_connection.connect("rumor_consequence_ready", Callable(self, "_on_rumor_consequence"))
	world_connection.connect("connection_status_changed", Callable(self, "_on_connection_status_changed"))
	world_connection.ensure_connected()

	if not await _wait_until(func(): return bool(world_connection.connected), 10.0):
		_fail_and_quit("Godot did not connect to the FastAPI WebSocket.")
		return
	if not await _wait_until(func(): return not world_connection.world_data.is_empty(), 10.0):
		_fail_and_quit("Godot did not receive the initial authoritative world_state.")
		return
	_expect(not str(world_connection.client_session_id).is_empty(), "Expected a client_session_id.")
	print("Connected verification: authoritative session ready.")

	var socket_instance_id: int = world_connection.socket.get_instance_id()
	var main = current_scene
	_expect(main != null and main.name == "Main", "Expected the main scene after connecting.")
	if main == null:
		_finish()
		return
	if not await _wait_until(func(): return main.actor_nodes.has("player"), 3.0):
		_fail_and_quit("Main scene did not build its actor nodes.")
		return
	_expect(
		await _wait_until(func(): return "Ask Ivo" in main.objective_label.text, 3.0),
		"Expected the initial server objective to be visibly rendered."
	)

	world_connection.send_raw_text("{not-json")
	_expect(await _wait_until(func(): return saw_protocol_error, 5.0), "Expected malformed JSON to return client_error.")
	_expect(bool(world_connection.connected), "Malformed JSON must not close the WebSocket.")

	main.player_body.position = Vector2(920, 600)
	world_connection.send_command({
		"type": "player_entered_location",
		"location_id": "not_a_real_location",
	})
	_expect(await _wait_until(func(): return saw_location_rejection, 5.0), "Expected an invalid location rejection diff.")
	var square_center: Vector2 = main.LOCATION_CENTERS["square"]
	_expect(
		await _wait_until(func(): return main.player_body.position.distance_to(square_center) < 1.0, 5.0),
		"Expected the player to snap back to the authoritative Square after rejection."
	)
	_expect(main.local_player_location == "square", "Expected Square to remain the authoritative player location.")

	var initial_mira_memory_count := _visible_memory_count(main, "mira")
	_press_e(main)
	_expect(
		await _wait_until(func(): return _active_dialogue_is("ivo"), 5.0),
		"Expected normal E interaction to open a stateful Ivo conversation."
	)
	await process_frame
	_expect(_active_dialogue_has_choice("ask_about_missing_seeds"), "Expected Ivo to offer the missing-seeds choice.")
	_expect(_press_offered_choice(main, "ask_about_missing_seeds"), "Expected Ivo's offered UI choice to be pressed.")
	_expect(
		await _wait_until(func(): return _player_has_note("ivo_tomo_seed_claim"), 5.0),
		"Expected Ivo's claim to become an authoritative player note."
	)
	_expect(
		await _wait_until(func(): return "Tell Mira" in main.objective_label.text, 3.0),
		"Expected the visible server objective to advance to Tell Mira."
	)
	_press_escape(main)
	await process_frame
	_expect(not main.dialogue_panel.visible, "Expected normal Escape input to close Ivo's long conversation before walking.")

	if not await _walk_to_logical_location(main, "workshop"):
		_fail_and_quit("Expected normal player traversal to move authoritatively to the Workshop.")
		return
	_expect(
		main.LOCATION_RECTS["workshop"].has_point(main.player_body.position),
		"Expected the accepted authoritative Workshop move to preserve the local pixel traversal inside the Workshop."
	)

	_press_e(main)
	_expect(
		await _wait_until(func(): return _active_dialogue_is("mira"), 5.0),
		"Expected normal E interaction to open a stateful Mira conversation."
	)
	await process_frame
	_expect(_active_dialogue_has_choice("share_ivo_claim"), "Expected Mira to offer the Ivo claim handoff.")
	_expect(_press_offered_choice(main, "share_ivo_claim"), "Expected Mira's offered claim handoff choice to be pressed.")
	if not await _wait_until(func(): return _visible_memory_count(main, "mira") > initial_mira_memory_count, 5.0):
		_fail_and_quit("Expected Mira's grouped-memory bubble count to visibly increase after the claim.")
		return

	_expect(
		await _wait_until(func(): return saw_mira_movement, 15.0),
		"Expected actor_movements to carry Mira's validator fallback move."
	)
	_expect(
		await _wait_until(func(): return saw_consequence_signal, 15.0),
		"Expected the authoritative Mira-to-Tomo event to trigger the consequence signal."
	)
	_expect(
		await _wait_until(func(): return current_scene != null and current_scene.name == "RumorConsequence", 10.0),
		"Expected a real SceneTree switch into the rumor consequence scene."
	)
	await process_frame
	_expect(bool(world_connection.connected), "The persistent WebSocket must remain connected in the consequence scene.")
	_expect(
		world_connection.socket.get_instance_id() == socket_instance_id,
		"The consequence scene must reuse the existing WebSocketPeer."
	)
	var first_consequence_payload: Dictionary = world_connection.rumor_consequence_payload
	var first_presentation_id := str(first_consequence_payload.get("presentation_id", ""))
	_expect(_scene_text_contains(str(first_consequence_payload.get("title", ""))), "Expected the server consequence title to be visible.")
	_expect(
		_scene_text_contains(str(first_consequence_payload.get("line", ""))),
		"Expected the server-authored Mira line to be visible."
	)
	_expect(
		_scene_text_contains(str(first_consequence_payload.get("reaction_text", ""))),
		"Expected the server-authored reaction to be visible."
	)
	_expect(
		_scene_text_contains(str(first_consequence_payload.get("relationship_trend_text", ""))),
		"Expected the server-authored relationship trend to be visible."
	)

	_expect(
		await _wait_until(func(): return current_scene != null and current_scene.name == "Main", 10.0),
		"Expected the consequence scene to return to the main scene."
	)
	main = current_scene
	await process_frame
	await physics_frame
	_expect(bool(world_connection.connected), "The WebSocket must remain connected after returning to Main.")
	_expect(
		world_connection.socket.get_instance_id() == socket_instance_id,
		"Returning to Main must not create a second WebSocketPeer."
	)

	var npcs: Dictionary = world_connection.world_data.get("npcs", {})
	var mira: Dictionary = npcs.get("mira", {})
	var mira_location := str(mira.get("current_location", ""))
	_expect(mira_location == "farm", "Expected Mira's authoritative fallback destination to be the Farm.")
	if main != null and main.actor_nodes.has("mira") and main.LOCATION_CENTERS.has(mira_location):
		_expect(
			main.actor_nodes["mira"].position.distance_to(main.LOCATION_CENTERS[mira_location]) < 1.0,
			"Expected Main to restore Mira from the cached authoritative state."
		)
	_expect(str(npcs.get("tomo", {}).get("mood", "")) == "hurt", "Expected the visible consequence to leave Tomo hurt.")
	_expect(saw_authoritative_dialogue_event, "Expected the golden-path dialogue event.")
	_expect(int(consequence_signal_counts.get(first_presentation_id, 0)) == 1, "Expected the first consequence signal exactly once.")
	_expect(int(consequence_scene_entry_counts.get(first_presentation_id, 0)) == 1, "Expected the first consequence scene to be entered exactly once.")
	_expect("Check the Warehouse" in main.objective_label.text, "Expected the visible objective to direct the player to the Warehouse.")

	if not await _walk_to_logical_location(main, "square"):
		_fail_and_quit("Expected the player to return through the Square.")
		return
	if not await _walk_to_logical_location(main, "warehouse"):
		_fail_and_quit("Expected normal traversal to reach the Warehouse.")
		return
	_expect(
		main.player_body.position.distance_to(main.CONTEXTUAL_ACTION_ANCHORS["warehouse"]) > main.CONTEXTUAL_INTERACTION_DISTANCE,
		"Expected the authoritative Warehouse anchor to remain outside the specific clue radius."
	)
	main._update_approach_prompt()
	_expect(not main.approach_label.visible, "Expected no contextual prompt while far from the exact clue.")
	if not await _walk_player_to_pixel(main, main.CONTEXTUAL_ACTION_ANCHORS["warehouse"], 5.0):
		_fail_and_quit("Expected simulated WASD traversal to reach the exact Warehouse clue.")
		return
	main._update_approach_prompt()
	_expect(main.approach_label.visible, "Expected the contextual prompt at the exact Warehouse clue.")
	_expect("torn seed bag" in main.approach_label.text, "Expected the contextual prompt to name the torn seed bag.")
	var cursor_before_disconnect := int(world_connection.last_consumed_event_cursor)
	var socket_before_disconnect: int = world_connection.socket.get_instance_id()
	var session_before_disconnect := str(world_connection.client_session_id)
	var mira_position_before_disconnect: Vector2 = main.actor_nodes["mira"].position
	world_connection.reconnect_attempt = 3
	world_connection.set_process(false)
	_press_e(main)
	await create_timer(0.1).timeout
	world_connection.socket.close(1000, "transient integration drop")
	world_connection.set_process(true)
	_expect(
		await _wait_until(func(): return world_connection.connection_status == "Reconnecting", 5.0),
		"Expected an unexpected transport drop to enter Reconnecting."
	)
	await create_timer(0.4).timeout
	_expect(
		main.actor_nodes["mira"].position.distance_to(mira_position_before_disconnect) < 0.1,
		"Expected disconnected NPCs to remain frozen under backend authority."
	)
	_expect(
		await _wait_until(
			func(): return bool(world_connection.connected) and world_connection.connection_status == "Online",
			12.0
		),
		"Expected capped automatic reconnect to restore Online state."
	)
	_expect(world_connection.socket.get_instance_id() != socket_before_disconnect, "Expected reconnect to create a new transport.")
	_expect(str(world_connection.client_session_id) != session_before_disconnect, "Expected reconnect to receive a new connection session.")
	_expect(
		int(world_connection.last_requested_recovery_cursor) == cursor_before_disconnect,
		"Expected reconnect to request recovery from the last consumed cursor."
	)
	_expect(
		int(world_connection.last_consumed_event_cursor) > cursor_before_disconnect,
		"Expected cursor catch-up to consume authoritative events produced during the drop."
	)
	_expect(int(world_connection.last_recovery_event_count) > 0, "Expected the dropped evidence event in recovery_events.")
	_expect(
		_recovery_contains_evidence("torn_seed_bag"),
		"Expected recovery_events to contain the authoritative torn_seed_bag evidence_found event."
	)
	_expect("Reconnecting" in connection_status_history, "Expected Reconnecting to be visibly reported.")
	_expect("Online" in connection_status_history, "Expected Online to be restored after reconnect.")
	_expect(_player_has_evidence("torn_seed_bag"), "Expected reconnect catch-up plus snapshot to recover the found evidence.")
	main = current_scene
	_expect("Show Mira" in main.objective_label.text, "Expected the recovered visible objective to advance to Show Mira the evidence.")

	var authoritative_npcs: Dictionary = world_connection.world_data.get("npcs", {})
	var authoritative_mira: Dictionary = authoritative_npcs.get("mira", {})
	var recovered_mira_location := str(authoritative_mira.get("current_location", ""))
	if not await _walk_to_logical_location(main, recovered_mira_location):
		_fail_and_quit("Expected normal traversal back to Mira.")
		return
	_press_e(main)
	_expect(
		await _wait_until(func(): return _active_dialogue_is("mira"), 5.0),
		"Expected E to reopen Mira's server conversation after recovery."
	)
	await process_frame
	_expect(_active_dialogue_has_choice("show_torn_seed_bag"), "Expected evidence choice only after authoritative discovery.")
	_expect(_press_offered_choice(main, "show_torn_seed_bag"), "Expected the offered evidence choice to be pressed.")

	_expect(
		await _wait_until(func(): return current_scene != null and current_scene.name == "RumorConsequence", 10.0),
		"Expected a server-driven reconciliation consequence scene."
	)
	var final_payload: Dictionary = world_connection.rumor_consequence_payload
	var final_presentation_id := str(final_payload.get("presentation_id", ""))
	_expect(str(final_payload.get("path", "")) == "reconciled", "Expected the final server outcome path to be reconciled.")
	_expect(_scene_text_contains(str(final_payload.get("title", ""))), "Expected final server outcome title to be visible.")
	_expect(_scene_text_contains(str(final_payload.get("relationship_trend_text", ""))), "Expected final relationship trend to be visible.")
	_expect(not _scene_text_contains("trust 0."), "Expected normal outcome UI to hide exact relationship values.")
	_expect(
		await _wait_until(func(): return current_scene != null and current_scene.name == "Main", 10.0),
		"Expected the final consequence to return safely to Main."
	)
	_expect(int(consequence_signal_counts.get(final_presentation_id, 0)) == 1, "Expected reconciliation consequence exactly once.")
	_expect(int(consequence_scene_entry_counts.get(final_presentation_id, 0)) == 1, "Expected the reconciliation scene to be entered exactly once.")
	await create_timer(1.0).timeout
	_expect(int(consequence_signal_counts.get(final_presentation_id, 0)) == 1, "Expected no replay after returning to Main.")
	_expect(int(consequence_scene_entry_counts.get(final_presentation_id, 0)) == 1, "Expected no duplicate reconciliation scene after returning to Main.")

	var final_world: Dictionary = world_connection.world_data
	var final_event: Dictionary = final_world.get("world_events", {}).get("evt_missing_seeds", {})
	_expect(str(final_event.get("phase", "")) == "resolved_reconciled", "Expected terminal resolved_reconciled authority.")
	_expect(str(final_event.get("resolution_path", "")) == "reconciled", "Expected authoritative reconciled resolution path.")
	_expect(str(final_world.get("npcs", {}).get("tomo", {}).get("mood", "")) == "vindicated", "Expected Tomo's reconciled mood after the final scene.")
	_expect(str(final_world.get("rumors", {}).get("rumor_tomo_took_seeds", {}).get("verified_state", "")) == "false", "Expected the Tomo rumor to be debunked.")

	_finish()


func _on_world_diff(diff: Dictionary) -> void:
	var reason := str(diff.get("reason", ""))
	if reason in ["location_not_found", "not_reachable", "invalid_location"]:
		saw_location_rejection = true
	var movements = diff.get("actor_movements", [])
	if typeof(movements) != TYPE_ARRAY:
		return
	for movement_value in movements:
		if typeof(movement_value) != TYPE_DICTIONARY:
			continue
		if str(movement_value.get("actor_id", "")) == "mira" and str(movement_value.get("to_location", "")) == "farm":
			saw_mira_movement = true


func _on_client_error(message: Dictionary) -> void:
	if str(message.get("error", message.get("code", ""))) == "malformed_json":
		saw_protocol_error = true


func _on_rumor_consequence(payload: Dictionary) -> void:
	saw_consequence_signal = true
	var presentation_id := str(payload.get("presentation_id", ""))
	if not presentation_id.is_empty():
		consequence_signal_counts[presentation_id] = int(consequence_signal_counts.get(presentation_id, 0)) + 1
	var event: Dictionary = payload.get("event", {})
	saw_authoritative_dialogue_event = (
		saw_authoritative_dialogue_event
		or (
			str(event.get("type", "")) == "npc_dialogue_started"
			and str(event.get("actor_id", "")) == "mira"
			and str(event.get("target_id", "")) == "tomo"
		)
		or (
			str(payload.get("type", "")) == "rumor_consequence"
			and str(payload.get("path", "")) == "careful_confrontation"
			and not str(payload.get("event_log_id", "")).is_empty()
		)
	)


func _on_connection_status_changed(status: String) -> void:
	connection_status_history.append(status)


func _on_node_added(node: Node) -> void:
	if node == null or node.name != "RumorConsequence":
		return
	if world_presenter == null:
		world_presenter = root.get_node_or_null("WorldPresenter")
	if world_presenter == null:
		return
	var payload: Dictionary = world_presenter.peek_next_consequence()
	var presentation_id := str(payload.get("presentation_id", ""))
	if presentation_id.is_empty():
		return
	consequence_scene_entry_counts[presentation_id] = int(consequence_scene_entry_counts.get(presentation_id, 0)) + 1


func _press_e(main) -> void:
	var event := InputEventKey.new()
	event.keycode = KEY_E
	event.pressed = true
	main._unhandled_input(event)


func _press_escape(main) -> void:
	var event := InputEventKey.new()
	event.keycode = KEY_ESCAPE
	event.pressed = true
	main._unhandled_input(event)


func _press_offered_choice(main, choice_id: String) -> bool:
	var choices = world_connection.active_dialogue.get("choices", [])
	if typeof(choices) != TYPE_ARRAY:
		return false
	for index in choices.size():
		var choice = choices[index]
		if typeof(choice) == TYPE_DICTIONARY and str(choice.get("choice_id", "")) == choice_id:
			main._choose_dialogue_by_number(index)
			return true
	return false


func _walk_to_logical_location(main, location_id: String) -> bool:
	if main == null or not main.LOCATION_CENTERS.has(location_id):
		return false
	print("Connected verification: simulated WASD toward ", location_id, ".")
	var start_location := _authoritative_player_location()
	if start_location == "square" and location_id == "workshop":
		var east_of_well := Vector2(560.0, main.player_body.position.y)
		var south_corridor := Vector2(560.0, 500.0)
		if not await _walk_player_to_pixel(main, east_of_well, 3.0):
			_release_movement_keys()
			return false
		if not await _walk_player_to_pixel(main, south_corridor, 5.0):
			_release_movement_keys()
			return false
	var target: Vector2 = main.LOCATION_CENTERS[location_id]
	var deadline := Time.get_ticks_msec() + 10000
	while Time.get_ticks_msec() < deadline and _authoritative_player_location() != location_id:
		_drive_player_with_wasd(main, target)
		await physics_frame
	_release_movement_keys()
	if _authoritative_player_location() != location_id:
		print("Connected verification: WASD failed for ", location_id, " at ", main.player_body.position, ", authority=", _authoritative_player_location())
		return false
	if location_id == "square" and main.player_body.position.y > 380.0:
		var east_of_well_return := Vector2(560.0, main.player_body.position.y)
		if not await _walk_player_to_pixel(main, east_of_well_return, 3.0):
			return false
		if not await _walk_player_to_pixel(main, Vector2(560.0, 300.0), 4.0):
			return false
	if not await _walk_player_to_pixel(main, target, 5.0):
		print("Connected verification: authority reached ", location_id, " but WASD could not reach its interaction center from ", main.player_body.position)
		return false
	var inside_authoritative_area: bool = main.LOCATION_RECTS[location_id].has_point(main.player_body.position)
	print("Connected verification: WASD reached ", location_id, ", inside_area=", inside_authoritative_area)
	return inside_authoritative_area


func _walk_player_to_pixel(main, target: Vector2, timeout_seconds: float) -> bool:
	if main == null or main.player_body == null:
		return false
	var deadline := Time.get_ticks_msec() + int(timeout_seconds * 1000.0)
	while Time.get_ticks_msec() < deadline and main.player_body.position.distance_to(target) > 5.0:
		_drive_player_with_wasd(main, target)
		await physics_frame
	_release_movement_keys()
	return main.player_body.position.distance_to(target) <= 5.0


func _drive_player_with_wasd(main, target: Vector2) -> void:
	var delta: Vector2 = target - main.player_body.position
	var horizontal := absf(delta.x) > 4.0
	_set_movement_key(KEY_A, horizontal and delta.x < 0.0)
	_set_movement_key(KEY_D, horizontal and delta.x > 0.0)
	_set_movement_key(KEY_W, not horizontal and delta.y < 0.0)
	_set_movement_key(KEY_S, not horizontal and delta.y > 0.0)


func _set_movement_key(keycode: Key, pressed: bool) -> void:
	if bool(movement_key_states.get(keycode, false)) == pressed:
		return
	movement_key_states[keycode] = pressed
	var event := InputEventKey.new()
	event.keycode = keycode
	event.physical_keycode = keycode
	event.pressed = pressed
	Input.parse_input_event(event)


func _release_movement_keys() -> void:
	for keycode in [KEY_W, KEY_A, KEY_S, KEY_D]:
		_set_movement_key(keycode, false)


func _visible_memory_count(main, npc_id: String) -> int:
	if main == null or not main.actor_nodes.has(npc_id):
		return -1
	var label: Label = main.actor_nodes[npc_id].get_node("StateBubble/StateLabel")
	var marker := label.text.find("mem ")
	if marker < 0:
		return -1
	var suffix := label.text.substr(marker + 4)
	return int(suffix.get_slice(" ", 0))


func _active_dialogue_is(npc_id: String) -> bool:
	return str(world_connection.active_dialogue.get("npc_id", "")) == npc_id


func _active_dialogue_has_choice(choice_id: String) -> bool:
	var choices = world_connection.active_dialogue.get("choices", [])
	if typeof(choices) != TYPE_ARRAY:
		return false
	for choice_value in choices:
		if typeof(choice_value) == TYPE_DICTIONARY and str(choice_value.get("choice_id", "")) == choice_id:
			return true
	return false


func _player_has_note(note_id: String) -> bool:
	var player: Dictionary = world_connection.world_data.get("player", {})
	var notes = player.get("notes", [])
	if typeof(notes) != TYPE_ARRAY:
		return false
	for note_value in notes:
		if typeof(note_value) == TYPE_DICTIONARY and str(note_value.get("note_id", "")) == note_id:
			return true
	return false


func _player_has_evidence(evidence_id: String) -> bool:
	var player: Dictionary = world_connection.world_data.get("player", {})
	var evidence = player.get("evidence", [])
	if typeof(evidence) != TYPE_ARRAY:
		return false
	for evidence_value in evidence:
		if typeof(evidence_value) == TYPE_DICTIONARY and str(evidence_value.get("evidence_id", "")) == evidence_id:
			return true
	return false


func _recovery_contains_evidence(evidence_id: String) -> bool:
	for event_value in world_connection.last_recovery_events:
		if typeof(event_value) != TYPE_DICTIONARY:
			continue
		var event: Dictionary = event_value
		if str(event.get("type", "")) != "evidence_found":
			continue
		var payload = event.get("payload", {})
		if typeof(payload) == TYPE_DICTIONARY and str(payload.get("evidence_id", "")) == evidence_id:
			return true
	return false


func _authoritative_player_location() -> String:
	var player: Dictionary = world_connection.world_data.get("player", {})
	return str(player.get("current_location", ""))


func _scene_text_contains(fragment: String) -> bool:
	if current_scene == null or fragment.is_empty():
		return false
	for node in current_scene.find_children("*", "Label", true, false):
		if fragment in str(node.text):
			return true
	return false


func _wait_until(predicate: Callable, timeout_seconds: float) -> bool:
	var deadline := Time.get_ticks_msec() + int(timeout_seconds * 1000.0)
	while Time.get_ticks_msec() < deadline:
		if bool(predicate.call()):
			return true
		await process_frame
		await create_timer(0.01).timeout
	return bool(predicate.call())


func _expect(condition: bool, message: String) -> void:
	if not condition:
		failures.append(message)


func _fail_and_quit(message: String) -> void:
	failures.append(message)
	_finish()


func _finish() -> void:
	if not failures.is_empty():
		for failure in failures:
			push_error(failure)
		quit(1)
		return
	print("Godot connected client verification passed.")
	quit(0)
