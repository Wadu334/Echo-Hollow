extends SceneTree

var failures: Array[String] = []
var world_connection: Node
var saw_protocol_error := false
var saw_location_rejection := false
var saw_mira_movement := false
var saw_consequence_signal := false
var saw_authoritative_dialogue_event := false


func _init() -> void:
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
	if world_connection == null:
		_fail_and_quit("WorldConnection autoload is missing.")
		return
	world_connection.connect("world_diff_received", Callable(self, "_on_world_diff"))
	world_connection.connect("client_error", Callable(self, "_on_client_error"))
	world_connection.connect("rumor_consequence_ready", Callable(self, "_on_rumor_consequence"))
	world_connection.ensure_connected()

	if not await _wait_until(func(): return bool(world_connection.connected), 10.0):
		_fail_and_quit("Godot did not connect to the FastAPI WebSocket.")
		return
	if not await _wait_until(func(): return not world_connection.world_data.is_empty(), 10.0):
		_fail_and_quit("Godot did not receive the initial authoritative world_state.")
		return
	_expect(not str(world_connection.client_session_id).is_empty(), "Expected a client_session_id.")

	var socket_instance_id: int = world_connection.socket.get_instance_id()
	var main = current_scene
	_expect(main != null and main.name == "Main", "Expected the main scene after connecting.")
	if main == null:
		_finish()
		return
	if not await _wait_until(func(): return main.actor_nodes.has("player"), 3.0):
		_fail_and_quit("Main scene did not build its actor nodes.")
		return

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

	world_connection.send_interact_npc("ivo")
	_expect(
		await _wait_until(func(): return _active_dialogue_is("ivo"), 5.0),
		"Expected a stateful Ivo conversation."
	)
	_expect(_active_dialogue_has_choice("ask_about_missing_seeds"), "Expected Ivo to offer the missing-seeds choice.")
	_expect(world_connection.send_dialogue_choice("ask_about_missing_seeds"), "Expected Ivo choice request to be sent.")
	_expect(
		await _wait_until(func(): return _player_has_note("ivo_tomo_seed_claim"), 5.0),
		"Expected Ivo's claim to become an authoritative player note."
	)

	world_connection.send_location_intent("workshop")
	_expect(
		await _wait_until(func(): return _authoritative_player_location() == "workshop", 5.0),
		"Expected the backend to move the player to the Workshop."
	)
	_expect(
		await _wait_until(
			func(): return main.player_body.position.distance_to(main.LOCATION_CENTERS["workshop"]) < 1.0,
			5.0
		),
		"Expected an externally accepted logical move to reconcile the player at the Workshop."
	)

	world_connection.send_interact_npc("mira")
	_expect(
		await _wait_until(func(): return _active_dialogue_is("mira"), 5.0),
		"Expected a stateful Mira conversation."
	)
	_expect(_active_dialogue_has_choice("share_ivo_claim"), "Expected Mira to offer the Ivo claim handoff.")
	_expect(world_connection.send_dialogue_choice("share_ivo_claim"), "Expected Mira claim handoff request to be sent.")

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
	var consequence_payload: Dictionary = world_connection.rumor_consequence_payload
	_expect(_scene_text_contains("A Rumor Reaches Tomo"), "Expected the consequence title to be visible.")
	_expect(
		_scene_text_contains(str(consequence_payload.get("line", ""))),
		"Expected the server-authored Mira line to be visible."
	)
	_expect(_scene_text_contains("Tomo looks hurt"), "Expected Tomo's authoritative hurt mood to be visible.")
	_expect(_scene_text_contains("Tomo → Mira"), "Expected the relationship summary to be visible.")

	var cutscene_cursor_before := int(world_connection.world_data.get("event_log_cursor", 0))
	_expect(
		world_connection.send_command({"type": "observe"}),
		"Expected to send a command while the consequence scene owns the SceneTree."
	)
	_expect(
		await _wait_until(
			func():
				return (
					current_scene != null
					and current_scene.name == "RumorConsequence"
					and int(world_connection.world_data.get("event_log_cursor", 0)) > cutscene_cursor_before
				),
			1.25
		),
		"Expected the Autoload to consume a world diff while the consequence scene was active."
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
	var event: Dictionary = payload.get("event", {})
	saw_authoritative_dialogue_event = (
		str(event.get("type", "")) == "npc_dialogue_started"
		and str(event.get("actor_id", "")) == "mira"
		and str(event.get("target_id", "")) == "tomo"
	)


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
