extends Node

signal connection_changed(connected: bool)
signal connection_status_changed(status: String)
signal world_state_received(data: Dictionary)
signal world_diff_received(data: Dictionary)
signal authoritative_events_received(events: Array)
signal authoritative_resync_completed(cursor: int)
signal dialogue_opened(message: Dictionary)
signal dialogue_result(message: Dictionary)
signal dialogue_rejected(message: Dictionary)
signal interaction_denied(message: Dictionary)
signal client_error(message: Dictionary)
signal rumor_consequence_ready(payload: Dictionary)

const DEFAULT_SERVER_URL := "ws://127.0.0.1:8000/ws/world/demo_world_001"
const RECONNECT_BASE_DELAY_SECONDS := 0.25
const RECONNECT_MAX_DELAY_SECONDS := 4.0

var socket: WebSocketPeer = WebSocketPeer.new()
var connected := false
var connection_requested := false
var transport_open := false
var connection_status := "Offline"
var manual_disconnect_requested := true
var has_ever_connected := false
var reconnect_attempt := 0
var reconnect_delay_remaining := 0.0
var reconnect_scheduled := false
var client_session_id := ""
var world_data: Dictionary = {}
var last_world_diff: Dictionary = {}
var active_dialogue: Dictionary = {}
var processed_event_log_ids: Dictionary = {}
var rumor_consequence_payload: Dictionary = {}
var last_world_diff_signature := ""
var server_url := DEFAULT_SERVER_URL
var last_consumed_event_cursor := 0
var last_requested_recovery_cursor := 0
var last_recovery_event_count := 0
var last_recovery_events: Array = []
var has_authoritative_snapshot := false
var recovery_in_progress := false
var pending_presentation_ack_ids: Dictionary = {}
var sent_ack_ids_this_session: Dictionary = {}
var world_presenter: Node


func _ready() -> void:
	var configured_url := OS.get_environment("ECHO_HOLLOW_SERVER_URL").strip_edges()
	if not configured_url.is_empty():
		server_url = configured_url
	world_presenter = get_node_or_null("/root/WorldPresenter")
	if world_presenter != null:
		var consequence_callable := Callable(self, "_on_presenter_consequence_ready")
		if not world_presenter.is_connected("consequence_ready", consequence_callable):
			world_presenter.connect("consequence_ready", consequence_callable)
	set_process(false)


func ensure_connected() -> void:
	var state := socket.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN or state == WebSocketPeer.STATE_CONNECTING:
		return
	manual_disconnect_requested = false
	reconnect_scheduled = false
	_start_connection(has_ever_connected)


func _start_connection(is_reconnect: bool) -> void:
	_reset_transport_session()
	socket = WebSocketPeer.new()
	recovery_in_progress = has_authoritative_snapshot or last_consumed_event_cursor > 0
	last_recovery_event_count = 0
	last_recovery_events = []
	if world_presenter != null:
		world_presenter.set_delivery_paused(true)
	_set_connection_status("Reconnecting" if is_reconnect else "Connecting")
	last_requested_recovery_cursor = last_consumed_event_cursor
	var error := socket.connect_to_url(_connection_url())
	if error != OK:
		connection_requested = false
		emit_signal("client_error", {
			"type": "client_error",
			"error": "connection_failed",
			"display_text": "Could not connect to the Echo Hollow world server.",
		})
		_schedule_reconnect()
		return

	connection_requested = true
	set_process(true)


func disconnect_from_server() -> void:
	manual_disconnect_requested = true
	reconnect_scheduled = false
	reconnect_delay_remaining = 0.0
	if socket.get_ready_state() in [WebSocketPeer.STATE_OPEN, WebSocketPeer.STATE_CONNECTING]:
		socket.close()
	connection_requested = false
	if connected:
		connected = false
		emit_signal("connection_changed", false)
	_reset_transport_session()
	_set_connection_status("Offline")
	if world_presenter != null:
		world_presenter.set_delivery_paused(false)
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


func send_activate_contextual_action(action_id: String, offer_version: int) -> bool:
	if action_id.is_empty():
		return false
	return send_command({
		"type": "activate_contextual_action",
		"action_id": action_id,
		"offer_version": offer_version,
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


func ack_presentation(presentation_id: String) -> bool:
	if presentation_id.is_empty():
		return false
	var requires_server_ack := true
	if world_presenter != null:
		var payload: Dictionary = world_presenter.peek_next_consequence()
		if str(payload.get("presentation_id", "")) == presentation_id:
			requires_server_ack = bool(payload.get("requires_server_ack", true))
		world_presenter.acknowledge_consequence(presentation_id)
	rumor_consequence_payload = {}
	if not requires_server_ack:
		return true
	pending_presentation_ack_ids[presentation_id] = true
	return _send_presentation_ack(presentation_id)


func _process(delta: float) -> void:
	if reconnect_scheduled:
		reconnect_delay_remaining -= delta
		if reconnect_delay_remaining <= 0.0:
			reconnect_scheduled = false
			_start_connection(true)
		return

	socket.poll()
	var state := socket.get_ready_state()

	if state == WebSocketPeer.STATE_OPEN and not connected:
		if not transport_open:
			transport_open = true
			connection_requested = false
	elif state == WebSocketPeer.STATE_CLOSED:
		var should_notify := connected or connection_requested or transport_open
		connected = false
		connection_requested = false
		if should_notify:
			emit_signal("connection_changed", false)
		_reset_transport_session()
		if manual_disconnect_requested:
			_set_connection_status("Offline")
			set_process(false)
		else:
			_schedule_reconnect()
		return

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
				_reset_transport_session()
			client_session_id = next_session_id
			var recovery_events = message.get("recovery_events", [])
			if typeof(recovery_events) == TYPE_ARRAY and not (recovery_events as Array).is_empty():
				# Compatibility with a pre-pagination server. Treat the embedded
				# events as one contiguous page and still require it to reach the
				# snapshot cursor before the client may become Online.
				_append_recovery_events(recovery_events)
				last_consumed_event_cursor += (recovery_events as Array).size()
			var snapshot_cursor := int((state_data as Dictionary).get(
				"event_log_cursor",
				last_consumed_event_cursor
			))
			if recovery_in_progress and last_consumed_event_cursor != snapshot_cursor:
				_reject_incomplete_recovery(snapshot_cursor)
				return
			world_data = (state_data as Dictionary).duplicate(true)
			_reconcile_pending_presentation_acks()
			_ingest_presenter_world_data()
			emit_signal("world_state_received", world_data)
			if has_authoritative_snapshot:
				_process_authoritative_events(world_data.get("latest_events", []))
			else:
				_seed_processed_event_ids(world_data.get("latest_events", []))
			has_authoritative_snapshot = true
			last_consumed_event_cursor = maxi(
				last_consumed_event_cursor,
				int(world_data.get("event_log_cursor", last_consumed_event_cursor))
			)
			recovery_in_progress = false
			reconnect_attempt = 0
			var became_authoritatively_ready := not connected
			connected = true
			has_ever_connected = true
			_set_connection_status("Online")
			if became_authoritatively_ready:
				emit_signal("connection_changed", true)
			if world_presenter != null:
				world_presenter.set_delivery_paused(false)
			emit_signal("authoritative_resync_completed", last_consumed_event_cursor)
			_flush_pending_presentation_acks()
		"recovery_events", "world_recovery":
			_consume_recovery_page(message)
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
	_ingest_presenter_world_data()


func _consume_world_diff(diff: Dictionary) -> bool:
	var signature := _world_diff_signature(diff)
	if not signature.is_empty() and signature == last_world_diff_signature:
		return false
	last_world_diff_signature = signature
	_merge_world_diff(diff)
	_confirm_presentation_acks(last_world_diff)
	emit_signal("world_diff_received", last_world_diff)
	_process_authoritative_events(last_world_diff.get("latest_events", []))
	last_consumed_event_cursor = maxi(
		last_consumed_event_cursor,
		int(last_world_diff.get("event_log_cursor", last_consumed_event_cursor))
	)
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


func _reset_session_state(clear_recovery_state: bool = false) -> void:
	_reset_transport_session()
	if not clear_recovery_state:
		return
	last_consumed_event_cursor = 0
	last_requested_recovery_cursor = 0
	last_recovery_event_count = 0
	last_recovery_events = []
	has_authoritative_snapshot = false
	processed_event_log_ids.clear()
	rumor_consequence_payload = {}
	pending_presentation_ack_ids.clear()
	sent_ack_ids_this_session.clear()
	world_data = {}
	if world_presenter != null:
		world_presenter.reset_for_fresh_world()


func _reset_transport_session() -> void:
	transport_open = false
	client_session_id = ""
	active_dialogue = {}
	last_world_diff = {}
	last_world_diff_signature = ""
	sent_ack_ids_this_session.clear()


func _process_authoritative_events(events: Variant) -> void:
	if typeof(events) != TYPE_ARRAY:
		return
	var fresh_events: Array = []
	for event_value in events:
		if typeof(event_value) != TYPE_DICTIONARY:
			continue
		var event: Dictionary = event_value
		var event_log_id := str(event.get("event_log_id", ""))
		if event_log_id.is_empty() or processed_event_log_ids.has(event_log_id):
			continue
		processed_event_log_ids[event_log_id] = true
		fresh_events.append(event.duplicate(true))
	if fresh_events.is_empty():
		return
	emit_signal("authoritative_events_received", fresh_events)
	if world_presenter != null:
		world_presenter.ingest_authoritative_events(fresh_events)


func _consume_recovery_page(message: Dictionary) -> bool:
	var events = message.get("events", message.get("recovery_events", []))
	if typeof(events) != TYPE_ARRAY:
		_reject_recovery_page("Recovery events must be an array.")
		return false
	var page_from_cursor := int(message.get("from_cursor", last_consumed_event_cursor))
	var page_to_cursor := int(message.get(
		"to_cursor",
		page_from_cursor + (events as Array).size()
	))
	if page_from_cursor != last_consumed_event_cursor:
		_reject_recovery_page("Recovery page did not start at the consumed cursor.")
		return false
	if page_to_cursor != page_from_cursor + (events as Array).size():
		_reject_recovery_page("Recovery page cursor range did not match its events.")
		return false
	_append_recovery_events(events)
	last_consumed_event_cursor = page_to_cursor
	recovery_in_progress = true
	return true


func _append_recovery_events(events: Variant) -> void:
	if typeof(events) != TYPE_ARRAY:
		return
	for event_value in events:
		last_recovery_events.append(event_value.duplicate(true) if typeof(event_value) == TYPE_DICTIONARY else event_value)
	last_recovery_event_count = last_recovery_events.size()
	_process_authoritative_events(events)


func _reject_recovery_page(display_text: String) -> void:
	emit_signal("client_error", {
		"type": "client_error",
		"error": "invalid_recovery_page",
		"display_text": display_text,
	})
	if socket.get_ready_state() in [WebSocketPeer.STATE_OPEN, WebSocketPeer.STATE_CONNECTING]:
		socket.close(1011, "invalid recovery page")


func _reject_incomplete_recovery(snapshot_cursor: int) -> void:
	emit_signal("client_error", {
		"type": "client_error",
		"error": "incomplete_recovery",
		"display_text": "Recovery cursor did not match the authoritative snapshot cursor.",
		"consumed_cursor": last_consumed_event_cursor,
		"snapshot_cursor": snapshot_cursor,
	})
	if socket.get_ready_state() in [WebSocketPeer.STATE_OPEN, WebSocketPeer.STATE_CONNECTING]:
		socket.close(1011, "incomplete recovery")



func _seed_processed_event_ids(events: Variant) -> void:
	if typeof(events) != TYPE_ARRAY:
		return
	for event_value in events:
		if typeof(event_value) != TYPE_DICTIONARY:
			continue
		var event_log_id := str(event_value.get("event_log_id", ""))
		if not event_log_id.is_empty():
			processed_event_log_ids[event_log_id] = true


func _connection_url() -> String:
	if last_consumed_event_cursor <= 0:
		return server_url
	var separator := "&" if "?" in server_url else "?"
	return "%s%safter_cursor=%d" % [server_url, separator, last_consumed_event_cursor]


func _set_connection_status(next_status: String) -> void:
	if connection_status == next_status:
		return
	connection_status = next_status
	emit_signal("connection_status_changed", connection_status)


func _schedule_reconnect() -> void:
	if manual_disconnect_requested:
		_set_connection_status("Offline")
		set_process(false)
		return
	reconnect_attempt += 1
	reconnect_delay_remaining = minf(
		RECONNECT_BASE_DELAY_SECONDS * pow(2.0, float(reconnect_attempt - 1)),
		RECONNECT_MAX_DELAY_SECONDS
	)
	reconnect_scheduled = true
	_set_connection_status("Reconnecting")
	set_process(true)


func _ingest_presenter_world_data() -> void:
	if world_presenter != null:
		world_presenter.ingest_world_data(world_data)


func _on_presenter_consequence_ready(payload: Dictionary) -> void:
	rumor_consequence_payload = payload.duplicate(true)
	emit_signal("rumor_consequence_ready", rumor_consequence_payload)


func _send_presentation_ack(presentation_id: String) -> bool:
	if not connected or sent_ack_ids_this_session.has(presentation_id):
		return false
	var sent := send_command({
		"type": "ack_presentation",
		"presentation_id": presentation_id,
	})
	if sent:
		sent_ack_ids_this_session[presentation_id] = true
	return sent


func _flush_pending_presentation_acks() -> void:
	if not connected:
		return
	for presentation_id_value in pending_presentation_ack_ids.keys():
		_send_presentation_ack(str(presentation_id_value))


func _confirm_presentation_acks(diff: Dictionary) -> void:
	var events = diff.get("latest_events", [])
	if typeof(events) != TYPE_ARRAY:
		return
	for event_value in events:
		if typeof(event_value) != TYPE_DICTIONARY or str(event_value.get("type", "")) != "presentation_acknowledged":
			continue
		var payload = event_value.get("payload", {})
		if typeof(payload) != TYPE_DICTIONARY:
			continue
		var presentation_id := str(payload.get("presentation_id", ""))
		pending_presentation_ack_ids.erase(presentation_id)
		sent_ack_ids_this_session.erase(presentation_id)


func _reconcile_pending_presentation_acks() -> void:
	if not world_data.has("pending_presentations"):
		return
	var server_pending = world_data.get("pending_presentations", [])
	if typeof(server_pending) != TYPE_ARRAY:
		return
	var server_pending_ids: Dictionary = {}
	for value in server_pending:
		if typeof(value) == TYPE_DICTIONARY:
			var presentation_id := str(value.get("presentation_id", ""))
			if not presentation_id.is_empty():
				server_pending_ids[presentation_id] = true
	for presentation_id_value in pending_presentation_ack_ids.keys():
		var presentation_id := str(presentation_id_value)
		if server_pending_ids.has(presentation_id):
			continue
		pending_presentation_ack_ids.erase(presentation_id)
		sent_ack_ids_this_session.erase(presentation_id)
