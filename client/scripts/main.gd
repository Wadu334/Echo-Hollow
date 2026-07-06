extends Node2D

const SERVER_URL := "ws://127.0.0.1:8000/ws/world/demo_world_001"
const ACTOR_COLORS := {
	"player": Color(0.20, 0.65, 1.0),
	"mira": Color(0.95, 0.45, 0.35),
	"tomo": Color(0.30, 0.75, 0.35),
	"ivo": Color(0.95, 0.75, 0.25),
}

var socket := WebSocketPeer.new()
var location_nodes: Dictionary = {}
var actor_nodes: Dictionary = {}
var location_positions: Dictionary = {}
var world_data: Dictionary = {}
var connected := false

@onready var status_label := Label.new()
@onready var event_label := RichTextLabel.new()


func _ready() -> void:
	_build_static_ui()
	var err := socket.connect_to_url(SERVER_URL)
	if err != OK:
		status_label.text = "WebSocket connect failed: %s" % err
	else:
		status_label.text = "Connecting to world server..."


func _process(_delta: float) -> void:
	socket.poll()
	var state := socket.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN and not connected:
		connected = true
		status_label.text = "Connected. Number keys 1-5 move the player."
	elif state == WebSocketPeer.STATE_CLOSED and connected:
		connected = false
		status_label.text = "Disconnected from world server."

	while socket.get_available_packet_count() > 0:
		var packet := socket.get_packet().get_string_from_utf8()
		var parsed = JSON.parse_string(packet)
		if typeof(parsed) == TYPE_DICTIONARY:
			_apply_server_message(parsed)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var location_id := ""
		match event.keycode:
			KEY_1:
				location_id = "square"
			KEY_2:
				location_id = "tavern"
			KEY_3:
				location_id = "farm"
			KEY_4:
				location_id = "workshop"
			KEY_5:
				location_id = "warehouse"
		if location_id != "":
			_send_move(location_id)


func _build_static_ui() -> void:
	var background := ColorRect.new()
	background.color = Color(0.10, 0.13, 0.12)
	background.size = Vector2(960, 640)
	add_child(background)

	status_label.position = Vector2(24, 18)
	status_label.add_theme_font_size_override("font_size", 18)
	status_label.text = "Starting..."
	add_child(status_label)

	event_label.position = Vector2(650, 24)
	event_label.size = Vector2(280, 560)
	event_label.bbcode_enabled = true
	event_label.add_theme_font_size_override("normal_font_size", 14)
	add_child(event_label)

	_create_hint_label()


func _create_hint_label() -> void:
	var hints := Label.new()
	hints.position = Vector2(24, 580)
	hints.text = "1 Square  2 Tavern  3 Farm  4 Workshop  5 Warehouse"
	hints.add_theme_font_size_override("font_size", 16)
	add_child(hints)


func _apply_server_message(message: Dictionary) -> void:
	var payload = message.get("data", {})
	if typeof(payload) != TYPE_DICTIONARY:
		return

	if message.get("type") == "world_state":
		world_data = payload
	elif message.get("type") == "world_diff":
		_merge_world_diff(payload)
	else:
		return

	_render_world()


func _merge_world_diff(diff: Dictionary) -> void:
	for key in [
		"locations",
		"player",
		"npcs",
		"latest_events",
		"time",
		"event_log_cursor",
		"world_events",
		"episode_phase",
		"action_queue",
		"memories",
		"relationships",
		"rumors",
		"last_validator_result",
		"last_agent_trace",
		"last_relationship_change",
	]:
		if diff.has(key):
			world_data[key] = diff[key]


func _render_world() -> void:
	var time_text = world_data.get("time", "unknown time")
	var cursor = world_data.get("event_log_cursor", 0)
	status_label.text = "%s | event log #%s | keys 1-5 move player" % [time_text, cursor]

	_render_locations(world_data.get("locations", {}))
	_render_actors()
	_render_events(world_data.get("latest_events", []))


func _render_locations(locations: Dictionary) -> void:
	for location_id in locations.keys():
		var location: Dictionary = locations[location_id]
		var pos_data: Dictionary = location.get("position", {"x": 100, "y": 100})
		var pos := Vector2(pos_data.get("x", 100), pos_data.get("y", 100))
		location_positions[location_id] = pos

		if not location_nodes.has(location_id):
			var box := ColorRect.new()
			box.color = Color(0.22, 0.27, 0.24)
			box.position = pos - Vector2(62, 32)
			box.size = Vector2(124, 64)
			add_child(box)

			var label := Label.new()
			label.name = "Label"
			label.position = Vector2(8, 8)
			label.add_theme_font_size_override("font_size", 14)
			box.add_child(label)
			location_nodes[location_id] = box

		var node: ColorRect = location_nodes[location_id]
		var label: Label = node.get_node("Label")
		var occupants: Array = location.get("current_occupants", [])
		label.text = "%s\n%s" % [location.get("name", location_id), _join_strings(occupants)]


func _render_actors() -> void:
	var actors := {}
	var player = world_data.get("player", {})
	if typeof(player) == TYPE_DICTIONARY:
		actors["player"] = {
			"name": "Player",
			"location": player.get("current_location", "square"),
			"offset": Vector2(-28, -42),
		}

	var npcs = world_data.get("npcs", {})
	if typeof(npcs) == TYPE_DICTIONARY:
		var index := 0
		for npc_id in npcs.keys():
			var npc: Dictionary = npcs[npc_id]
			actors[npc_id] = {
				"name": npc.get("name", npc_id),
				"location": npc.get("current_location", "square"),
				"offset": Vector2(-6 + index * 18, 36),
			}
			index += 1

	for actor_id in actors.keys():
		var actor: Dictionary = actors[actor_id]
		var location_id = actor.get("location", "square")
		if not location_positions.has(location_id):
			continue

		if not actor_nodes.has(actor_id):
			actor_nodes[actor_id] = _create_actor_node(actor_id, actor.get("name", actor_id))

		var node: Node2D = actor_nodes[actor_id]
		node.position = location_positions[location_id] + actor.get("offset", Vector2.ZERO)


func _create_actor_node(actor_id: String, display_name: String) -> Node2D:
	var root := Node2D.new()
	var marker := ColorRect.new()
	marker.color = ACTOR_COLORS.get(actor_id, Color.WHITE)
	marker.size = Vector2(14, 14)
	marker.position = Vector2(-7, -7)
	root.add_child(marker)

	var label := Label.new()
	label.text = display_name
	label.position = Vector2(-20, 10)
	label.add_theme_font_size_override("font_size", 12)
	root.add_child(label)
	add_child(root)
	return root


func _render_events(events: Array) -> void:
	var phase: String = str(world_data.get("episode_phase", "-"))
	if phase == "-" and world_data.has("world_events"):
		var event_data: Dictionary = world_data["world_events"].get("evt_missing_seeds", {})
		if typeof(event_data) == TYPE_DICTIONARY:
			phase = str(event_data.get("phase", "-"))

	var lines: Array[String] = [
		"[b]Episode[/b]",
		"Phase: %s" % phase,
		"Latest action: %s" % _latest_action_summary(),
		"Relationship: %s" % _latest_relationship_summary(),
		"",
		"[b]Recent Events[/b]",
	]
	for event in events:
		if typeof(event) == TYPE_DICTIONARY:
			lines.append("%s  %s" % [event.get("world_time", ""), event.get("type", "")])
	var trace = world_data.get("last_agent_trace", null)
	if typeof(trace) == TYPE_DICTIONARY:
		lines.append("")
		lines.append("[b]Agent[/b]")
		lines.append("%s: %s" % [trace.get("actor_id", "-"), trace.get("decision", "-")])
	event_label.text = "\n".join(lines)


func _latest_action_summary() -> String:
	var actions = world_data.get("action_queue", [])
	if typeof(actions) != TYPE_ARRAY or actions.is_empty():
		return "-"
	var latest_action = actions[actions.size() - 1]
	if typeof(latest_action) != TYPE_DICTIONARY:
		return "-"
	return "%s %s" % [latest_action.get("status", "-"), latest_action.get("tool_name", "-")]


func _latest_relationship_summary() -> String:
	var change = world_data.get("last_relationship_change", null)
	if typeof(change) != TYPE_DICTIONARY:
		return "-"
	return "%s->%s trust %s" % [
		change.get("owner_id", "-"),
		change.get("target_id", "-"),
		change.get("trust", "-"),
	]


func _send_move(location_id: String) -> void:
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		status_label.text = "Cannot move: WebSocket is not connected."
		return
	var payload := {
		"type": "move_player",
		"location_id": location_id,
	}
	socket.send_text(JSON.stringify(payload))


func _join_strings(values: Array) -> String:
	var text_values: PackedStringArray = []
	for value in values:
		text_values.append(str(value))
	return ", ".join(text_values)
