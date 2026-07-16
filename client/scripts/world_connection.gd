extends Node

signal connection_changed(connected: bool)
signal world_state_received(data: Dictionary)
signal world_diff_received(data: Dictionary)
signal dialogue_opened(message: Dictionary)
signal dialogue_result(message: Dictionary)
signal dialogue_rejected(message: Dictionary)
signal interaction_denied(message: Dictionary)
signal client_error(message: Dictionary)
signal rumor_consequence_ready(payload: Dictionary)

const DEFAULT_SERVER_URL := "ws://127.0.0.1:8000/ws/world/demo_world_001"

var socket: WebSocketPeer = WebSocketPeer.new()
var connected := false
var connection_requested := false
var client_session_id := ""
var world_data: Dictionary = {}
var last_world_diff: Dictionary = {}
var active_dialogue: Dictionary = {}
var processed_event_log_ids: Dictionary = {}
var rumor_consequence_payload: Dictionary = {}
var last_world_diff_signature := ""
var server_url := DEFAULT_SERVER_URL


func _ready() -> void:
	var configured_url := OS.get_environment("ECHO_HOLLOW_SERVER_URL").strip_edges()
	if not configured_url.is_empty():
		server_url = configured_url
	set_process(false)


func ensure_connected() -> void:
	var state := socket.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN or state == WebSocketPeer.STATE_CONNECTING:
		return

	_reset_session_state()
	socket = WebSocketPeer.new()
	var error := socket.connect_to_url(server_url)
	if error != OK:
		connection_requested = false
		emit_signal("client_error", {
			"type": "client_error",
			"error": "connection_failed",
			"display_text": "Could not connect to the Echo Hollow world server.",
		})
		return

	connection_requested = true
	set_process(true)


func disconnect_from_server() -> void:
	if socket.get_ready_state() in [WebSocketPeer.STATE_OPEN, WebSocketPeer.STATE_CONNECTING]:
		socket.close()
	connection_requested = false
	if connected:
		connected = false
		emit_signal("connection_changed", false)
	_reset_session_state()
	set_process(false)


func send_command(payload: Dictionary) -> bool:
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return false
	return socket.send_text(JSON.stringify(payload)) == OK


func send_raw_text(payload: String) -> bool:
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return false
	return socket.send_text(payload) == OK


func send_location_intent(location_id: String) -> bool:
	return send_command({
		"type": "player_entered_location",
		"location_id": location_id,
	})


func send_interact_npc(npc_id: String) -> bool:
	return send_command({
		"type": "player_interact_npc",
		"npc_id": npc_id,
		"interaction": "talk",
	})


func send_dialogue_choice(choice_id: String) -> bool:
	var conversation_id := str(active_dialogue.get("conversation_id", ""))
	if conversation_id.is_empty() or not active_dialogue.has("offer_version"):
		return false
	return send_command({
		"type": "dialogue_choice",
		"conversation_id": conversation_id,
		"offer_version": int(active_dialogue.get("offer_version", 0)),
		"choice_id": choice_id,
	})


func clear_rumor_consequence() -> void:
	rumor_consequence_payload = {}


func _process(_delta: float) -> void:
	socket.poll()
	var state := socket.get_ready_state()

	if state == WebSocketPeer.STATE_OPEN and not connected:
		connected = true
		connection_requested = false
		emit_signal("connection_changed", true)
	elif state == WebSocketPeer.STATE_CLOSED:
		var should_notify := connected or connection_requested
		connected = false
		connection_requested = false
		if should_notify:
			emit_signal("connection_changed", false)
		_reset_session_state()
		set_process(false)

	while socket.get_available_packet_count() > 0:
		var packet := socket.get_packet().get_string_from_utf8()
		var parsed = JSON.parse_string(packet)
		if typeof(parsed) != TYPE_DICTIONARY:
			emit_signal("client_error", {
				"type": "client_error",
				"error": "invalid_server_message",
				"display_text": "The village server sent an unreadable message.",
			})
			continue
		_apply_server_message(parsed)


func _apply_server_message(message: Dictionary) -> void:
	var message_type := str(message.get("type", ""))
	match message_type:
		"world_state":
			var state_data = message.get("data", {})
			if typeof(state_data) != TYPE_DICTIONARY:
				return
			var next_session_id := str(message.get("client_session_id", ""))
			if next_session_id != client_session_id:
				_reset_session_state()
			client_session_id = next_session_id
			world_data = (state_data as Dictionary).duplicate(true)
			emit_signal("world_state_received", world_data)
			_seed_processed_event_ids(world_data.get("latest_events", []))
		"world_diff":
			var diff_data = message.get("data", {})
			if typeof(diff_data) != TYPE_DICTIONARY:
				return
			_consume_world_diff(diff_data)
		"dialogue_opened":
			active_dialogue = _dialogue_state_from_message(message)
			emit_signal("dialogue_opened", message)
		"dialogue_result":
			var result_diff = message.get("world_diff", {})
			if typeof(result_diff) == TYPE_DICTIONARY and not (result_diff as Dictionary).is_empty():
				_consume_world_diff(result_diff)
			_update_dialogue_after_result(message)
			emit_signal("dialogue_result", message)
		"dialogue_rejected":
			_update_dialogue_after_rejection(message)
			emit_signal("dialogue_rejected", message)
		"interaction_denied":
			emit_signal("interaction_denied", message)
		"client_error":
			emit_signal("client_error", message)


func _dialogue_state_from_message(message: Dictionary) -> Dictionary:
	return {
		"conversation_id": str(message.get("conversation_id", "")),
		"offer_version": int(message.get("offer_version", 0)),
		"npc_id": str(message.get("npc_id", "")),
		"choices": message.get("choices", []),
	}


func _update_dialogue_after_result(message: Dictionary) -> void:
	if bool(message.get("conversation_closed", false)):
		active_dialogue = {}
		return

	if message.has("conversation_id"):
		active_dialogue["conversation_id"] = str(message.get("conversation_id", ""))
	if message.has("npc_id"):
		active_dialogue["npc_id"] = str(message.get("npc_id", ""))
	if message.has("offer_version"):
		active_dialogue["offer_version"] = int(message.get("offer_version", 0))
	elif message.has("next_offer_version"):
		active_dialogue["offer_version"] = int(message.get("next_offer_version", 0))
	if message.has("choices"):
		active_dialogue["choices"] = message.get("choices", [])


func _update_dialogue_after_rejection(message: Dictionary) -> void:
	if message.has("conversation_id") and message.has("offer_version") and message.has("choices"):
		active_dialogue = _dialogue_state_from_message(message)
		return
	active_dialogue = {}


func _merge_world_diff(diff: Dictionary) -> void:
	last_world_diff = diff.duplicate(true)
	for key in diff.keys():
		world_data[key] = diff[key]


func _consume_world_diff(diff: Dictionary) -> bool:
	var signature := _world_diff_signature(diff)
	if not signature.is_empty() and signature == last_world_diff_signature:
		return false
	last_world_diff_signature = signature
	_merge_world_diff(diff)
	emit_signal("world_diff_received", last_world_diff)
	_process_authoritative_events(last_world_diff.get("latest_events", []))
	return true


func _world_diff_signature(diff: Dictionary) -> String:
	if not diff.has("event_log_cursor") or not diff.has("reason"):
		return ""
	return "%s|%s|%s|%s" % [
		str(diff.get("world_id", "")),
		str(diff.get("world_minute", "")),
		str(diff.get("event_log_cursor", "")),
		str(diff.get("reason", "")),
	]


func _reset_session_state() -> void:
	client_session_id = ""
	active_dialogue = {}
	processed_event_log_ids.clear()
	rumor_consequence_payload = {}
	last_world_diff = {}
	last_world_diff_signature = ""


func _process_authoritative_events(events: Variant) -> void:
	if typeof(events) != TYPE_ARRAY:
		return
	for event_value in events:
		if typeof(event_value) != TYPE_DICTIONARY:
			continue
		var event: Dictionary = event_value
		var event_log_id := str(event.get("event_log_id", ""))
		if event_log_id.is_empty() or processed_event_log_ids.has(event_log_id):
			continue
		processed_event_log_ids[event_log_id] = true
		if not _is_rumor_consequence_event(event):
			continue
		rumor_consequence_payload = _build_rumor_consequence_payload(event)
		emit_signal("rumor_consequence_ready", rumor_consequence_payload)


func _seed_processed_event_ids(events: Variant) -> void:
	if typeof(events) != TYPE_ARRAY:
		return
	for event_value in events:
		if typeof(event_value) != TYPE_DICTIONARY:
			continue
		var event_log_id := str(event_value.get("event_log_id", ""))
		if not event_log_id.is_empty():
			processed_event_log_ids[event_log_id] = true


func _is_rumor_consequence_event(event: Dictionary) -> bool:
	if str(event.get("type", "")) != "npc_dialogue_started":
		return false
	if str(event.get("actor_id", "")) != "mira" or str(event.get("target_id", "")) != "tomo":
		return false
	var payload = event.get("payload", {})
	return typeof(payload) == TYPE_DICTIONARY and str(payload.get("topic", "")) == "missing_seeds"


func _build_rumor_consequence_payload(event: Dictionary) -> Dictionary:
	var event_payload: Dictionary = event.get("payload", {})
	var npcs: Dictionary = world_data.get("npcs", {})
	var tomo: Dictionary = npcs.get("tomo", {})
	var relationships: Dictionary = world_data.get("relationships", {})
	var relationship: Dictionary = relationships.get("tomo->mira", {})
	return {
		"event": event.duplicate(true),
		"line": str(event_payload.get("line", "Mira asks Tomo about the missing seeds.")),
		"tomo_mood": str(tomo.get("mood", "hurt")),
		"relationship": relationship.duplicate(true),
	}
