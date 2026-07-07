extends Node2D

const SERVER_URL := "ws://127.0.0.1:8000/ws/world/demo_world_001"

const VIEWPORT_SIZE := Vector2(960, 640)
const WORLD_SIZE := Vector2(960, 672)
const TILE_SIZE := 48
const SPRITE_CELL_SIZE := 128
const PLAYER_SPEED := 150.0
const NPC_SPEED := 56.0
const INTERACTION_DISTANCE := 72.0

const ASSET_ROOT := "res://assets/playable_world_v0"
const PLAYER_SHEET := ASSET_ROOT + "/sprites/player_walk_4dir_4frame.png"
const MIRA_SHEET := ASSET_ROOT + "/sprites/mira_walk_4dir_4frame.png"
const TOMO_SHEET := ASSET_ROOT + "/sprites/tomo_walk_4dir_4frame.png"
const IVO_SHEET := ASSET_ROOT + "/sprites/ivo_walk_4dir_4frame.png"
const TILESET_IMAGE := ASSET_ROOT + "/tiles/ground_path_tileset_48.png"
const PROP_ATLAS := ASSET_ROOT + "/props/collision_props.png"

const DIRECTION_ROWS := {
	"down": 0,
	"up": 1,
	"left": 2,
	"right": 3,
}

const ACTOR_SHEETS := {
	"player": PLAYER_SHEET,
	"mira": MIRA_SHEET,
	"tomo": TOMO_SHEET,
	"ivo": IVO_SHEET,
}

const ACTOR_NAMES := {
	"player": "Player",
	"mira": "Mira",
	"tomo": "Tomo",
	"ivo": "Ivo",
}

const LOCATION_CENTERS := {
	"square": Vector2(480, 340),
	"tavern": Vector2(176, 210),
	"farm": Vector2(790, 430),
	"workshop": Vector2(230, 500),
	"warehouse": Vector2(760, 180),
}

const LOCATION_RECTS := {
	"square": Rect2(300, 210, 360, 260),
	"tavern": Rect2(70, 80, 220, 230),
	"farm": Rect2(640, 330, 260, 250),
	"workshop": Rect2(90, 420, 280, 210),
	"warehouse": Rect2(650, 70, 250, 210),
}

const TILE_ATLAS := {
	"g": Vector2i(0, 0),
	"d": Vector2i(1, 0),
	"s": Vector2i(2, 0),
	"f": Vector2i(3, 0),
	"p": Vector2i(0, 1),
	"r": Vector2i(1, 1),
	"c": Vector2i(2, 1),
	"m": Vector2i(7, 7),
}

const MAP_ROWS := [
	"ggggggggddddgggggggg",
	"gggggggddddddggggggg",
	"gggddddddssddddddggg",
	"ggddddddssssddddddgg",
	"gddddssssssssddddddg",
	"ddddssssssssssdddddd",
	"ddddssssssssssdddddd",
	"gddddssssssssddddddg",
	"ggddddddssssddddddgg",
	"gggddddddssddddddggg",
	"gggggddddddddddggggg",
	"ggggggggddddgggggggg",
	"gggggggggddggggggggg",
	"gggggggggddggggggggg",
]

const NPC_ROUTINES := {
	"mira": [
		Vector2(230, 500),
		Vector2(315, 450),
		Vector2(420, 395),
		Vector2(350, 505),
	],
	"tomo": [
		Vector2(805, 430),
		Vector2(740, 365),
		Vector2(670, 430),
		Vector2(790, 505),
	],
	"ivo": [
		Vector2(176, 210),
		Vector2(255, 285),
		Vector2(405, 320),
		Vector2(210, 345),
	],
}

const NPC_BUBBLES := {
	"mira": {
		"mood": "steady",
		"memory": "wood",
		"rumor": "seed",
		"relationship": "+trust",
	},
	"tomo": {
		"mood": "guarded",
		"memory": "field",
		"rumor": "pouch",
		"relationship": "?trust",
	},
	"ivo": {
		"mood": "warm",
		"memory": "tavern",
		"rumor": "cat",
		"relationship": "+care",
	},
}

var socket := WebSocketPeer.new()
var connected := false
var world_data: Dictionary = {}
var actor_nodes: Dictionary = {}
var actor_state: Dictionary = {}
var location_nodes: Dictionary = {}
var location_positions: Dictionary = {}
var npc_state: Dictionary = {}
var bubbles_visible := true
var enable_server_connection := true
var local_player_location := "square"
var last_interaction_text := "Press E near a villager. Press B to toggle agent bubbles."

var player_body: CharacterBody2D
var tile_texture: Texture2D
var prop_texture: Texture2D

@onready var world_root := Node2D.new()
@onready var prop_root := Node2D.new()
@onready var actor_root := Node2D.new()
@onready var location_root := Node2D.new()
@onready var ui_layer := CanvasLayer.new()
@onready var status_label := Label.new()
@onready var hint_label := Label.new()
@onready var event_label := RichTextLabel.new()


func _ready() -> void:
	_load_textures()
	_build_world_scene()
	_build_static_ui()
	_spawn_player()
	_spawn_npcs()
	_update_bubble_visibility()
	if enable_server_connection:
		_attempt_server_connection()
	else:
		status_label.text = "Playable local mode. WebSocket disabled for verification."


func _physics_process(delta: float) -> void:
	_poll_socket()
	_update_player_movement(delta)
	_update_npc_routines(delta)
	_update_player_location()
	_update_status_label()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_B:
				bubbles_visible = not bubbles_visible
				_update_bubble_visibility()
			KEY_E:
				_interact_with_nearest_npc()
			KEY_1:
				_jump_player_to_location("square")
			KEY_2:
				_jump_player_to_location("tavern")
			KEY_3:
				_jump_player_to_location("farm")
			KEY_4:
				_jump_player_to_location("workshop")
			KEY_5:
				_jump_player_to_location("warehouse")


func _load_textures() -> void:
	tile_texture = _load_png_texture(TILESET_IMAGE)
	prop_texture = _load_png_texture(PROP_ATLAS)


func _load_png_texture(res_path: String) -> Texture2D:
	var image := Image.new()
	var err := image.load(ProjectSettings.globalize_path(res_path))
	if err != OK:
		push_error("Could not load PNG texture %s: %s" % [res_path, err])
		return null
	return ImageTexture.create_from_image(image)


func _attempt_server_connection() -> void:
	var err := socket.connect_to_url(SERVER_URL)
	if err != OK:
		status_label.text = "Playable local mode. WebSocket connect failed: %s" % err
	else:
		status_label.text = "Playable local mode. Connecting to world server..."


func _poll_socket() -> void:
	socket.poll()
	var state := socket.get_ready_state()
	if state == WebSocketPeer.STATE_OPEN and not connected:
		connected = true
	elif state == WebSocketPeer.STATE_CLOSED and connected:
		connected = false

	while socket.get_available_packet_count() > 0:
		var packet := socket.get_packet().get_string_from_utf8()
		var parsed = JSON.parse_string(packet)
		if typeof(parsed) == TYPE_DICTIONARY:
			_apply_server_message(parsed)


func _build_world_scene() -> void:
	add_child(world_root)
	world_root.add_child(location_root)
	world_root.add_child(prop_root)
	world_root.add_child(actor_root)

	_build_tile_ground()
	_build_location_markers()
	_build_props()


func _build_tile_ground() -> void:
	for y in MAP_ROWS.size():
		var row: String = MAP_ROWS[y]
		for x in row.length():
			var key := row[x]
			_add_tile(Vector2i(x, y), TILE_ATLAS.get(key, TILE_ATLAS["g"]))


func _add_tile(map_cell: Vector2i, atlas_cell: Vector2i) -> void:
	var tile := Sprite2D.new()
	tile.texture = tile_texture
	tile.region_enabled = true
	tile.region_rect = Rect2(atlas_cell.x * TILE_SIZE, atlas_cell.y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
	tile.position = Vector2(map_cell.x * TILE_SIZE + TILE_SIZE / 2, map_cell.y * TILE_SIZE + TILE_SIZE / 2)
	tile.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	world_root.add_child(tile)


func _build_location_markers() -> void:
	for location_id in LOCATION_CENTERS.keys():
		var marker := Node2D.new()
		marker.name = "%s_location" % location_id
		marker.position = LOCATION_CENTERS[location_id]
		location_root.add_child(marker)
		location_nodes[location_id] = marker
		location_positions[location_id] = LOCATION_CENTERS[location_id]


func _build_props() -> void:
	_add_prop("well", Rect2(0, 0, 256, 256), Vector2(480, 365), Vector2(76, 58), Vector2(0, -20), 0.46)
	_add_prop("noticeboard", Rect2(256, 0, 256, 256), Vector2(395, 250), Vector2(84, 24), Vector2(0, -20), 0.44)
	_add_prop("crate", Rect2(512, 0, 256, 256), Vector2(665, 410), Vector2(54, 40), Vector2(0, -18), 0.36)
	_add_prop("bench", Rect2(0, 256, 256, 256), Vector2(585, 250), Vector2(92, 30), Vector2(0, -18), 0.40)
	_add_prop("fence", Rect2(256, 256, 256, 256), Vector2(750, 555), Vector2(128, 36), Vector2(0, -18), 0.45)
	_add_prop("lamp", Rect2(512, 256, 256, 256), Vector2(565, 160), Vector2(26, 28), Vector2(0, -14), 0.42)
	_add_prop("farm_crate", Rect2(512, 0, 256, 256), Vector2(815, 500), Vector2(54, 40), Vector2(0, -18), 0.34)
	_add_prop("workshop_bench", Rect2(0, 256, 256, 256), Vector2(230, 565), Vector2(92, 30), Vector2(0, -18), 0.36)


func _add_prop(prop_id: String, region: Rect2, anchor: Vector2, collision_size: Vector2, collision_offset: Vector2, scale_value: float) -> void:
	var body := StaticBody2D.new()
	body.name = prop_id
	body.position = anchor
	prop_root.add_child(body)

	var sprite := Sprite2D.new()
	sprite.texture = prop_texture
	sprite.region_enabled = true
	sprite.region_rect = region
	sprite.scale = Vector2(scale_value, scale_value)
	sprite.position = Vector2(0, -region.size.y * scale_value / 2.0)
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	body.add_child(sprite)

	var shape := CollisionShape2D.new()
	var rect := RectangleShape2D.new()
	rect.size = collision_size
	shape.shape = rect
	shape.position = collision_offset
	body.add_child(shape)


func _build_static_ui() -> void:
	add_child(ui_layer)

	status_label.position = Vector2(16, 12)
	status_label.add_theme_font_size_override("font_size", 15)
	status_label.text = "Playable local mode."
	ui_layer.add_child(status_label)

	hint_label.position = Vector2(16, 606)
	hint_label.add_theme_font_size_override("font_size", 14)
	hint_label.text = "WASD move | E interact | B bubbles | 1-5 jump logical locations"
	ui_layer.add_child(hint_label)

	event_label.position = Vector2(690, 18)
	event_label.size = Vector2(252, 180)
	event_label.bbcode_enabled = true
	event_label.add_theme_font_size_override("normal_font_size", 13)
	event_label.text = "[b]Village[/b]\nAgent bubbles are deterministic placeholders."
	ui_layer.add_child(event_label)


func _spawn_player() -> void:
	player_body = _create_actor("player", LOCATION_CENTERS["square"], true)
	actor_root.add_child(player_body)
	actor_nodes["player"] = player_body

	var camera := Camera2D.new()
	camera.name = "FollowCamera"
	camera.enabled = true
	camera.position_smoothing_enabled = true
	camera.position_smoothing_speed = 8.0
	camera.limit_left = 0
	camera.limit_top = 0
	camera.limit_right = int(WORLD_SIZE.x)
	camera.limit_bottom = int(WORLD_SIZE.y)
	player_body.add_child(camera)


func _spawn_npcs() -> void:
	for npc_id in ["mira", "tomo", "ivo"]:
		var start_position: Vector2 = NPC_ROUTINES[npc_id][0]
		var npc := _create_actor(npc_id, start_position, false)
		actor_root.add_child(npc)
		actor_nodes[npc_id] = npc
		npc_state[npc_id] = {
			"target_index": 1,
			"wait_timer": 0.8,
		}


func _create_actor(actor_id: String, start_position: Vector2, is_player: bool) -> CharacterBody2D:
	var body := CharacterBody2D.new()
	body.name = actor_id
	body.position = start_position
	body.collision_layer = 1 if is_player else 2
	body.collision_mask = 1

	var collision := CollisionShape2D.new()
	var shape := RectangleShape2D.new()
	shape.size = Vector2(28, 18) if actor_id != "ivo" else Vector2(36, 20)
	collision.shape = shape
	collision.position = Vector2(0, -10)
	body.add_child(collision)

	var sprite := Sprite2D.new()
	sprite.name = "Sprite"
	sprite.texture = _load_png_texture(ACTOR_SHEETS[actor_id])
	sprite.hframes = 4
	sprite.vframes = 4
	sprite.frame_coords = Vector2i(0, DIRECTION_ROWS["down"])
	sprite.position = Vector2(0, -40)
	sprite.scale = Vector2(0.62, 0.62)
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	body.add_child(sprite)

	var name_label := Label.new()
	name_label.name = "NameLabel"
	name_label.text = ACTOR_NAMES.get(actor_id, actor_id)
	name_label.position = Vector2(-28, 4)
	name_label.add_theme_font_size_override("font_size", 11)
	body.add_child(name_label)

	if actor_id != "player":
		var bubble := _create_state_bubble(actor_id)
		bubble.name = "StateBubble"
		bubble.position = Vector2(-54, -118)
		body.add_child(bubble)

	actor_state[actor_id] = {
		"direction": "down",
		"walk_time": 0.0,
		"moving": false,
	}
	return body


func _create_state_bubble(actor_id: String) -> Node2D:
	var data: Dictionary = NPC_BUBBLES.get(actor_id, {})
	var bubble := Node2D.new()

	var bg := ColorRect.new()
	bg.color = Color(1.0, 0.94, 0.80, 0.88)
	bg.size = Vector2(108, 50)
	bg.position = Vector2.ZERO
	bubble.add_child(bg)

	var label := Label.new()
	label.name = "StateLabel"
	label.position = Vector2(8, 5)
	label.add_theme_font_size_override("font_size", 9)
	label.text = "%s | %s\n%s | %s" % [
		data.get("mood", "calm"),
		data.get("memory", "memory"),
		data.get("rumor", "rumor"),
		data.get("relationship", "+trust"),
	]
	bubble.add_child(label)
	return bubble


func _update_player_movement(delta: float) -> void:
	if player_body == null:
		return

	var input_vector := Vector2.ZERO
	if Input.is_key_pressed(KEY_W):
		input_vector.y -= 1.0
	if Input.is_key_pressed(KEY_S):
		input_vector.y += 1.0
	if Input.is_key_pressed(KEY_A):
		input_vector.x -= 1.0
	if Input.is_key_pressed(KEY_D):
		input_vector.x += 1.0

	if input_vector.length() > 1.0:
		input_vector = input_vector.normalized()

	player_body.velocity = input_vector * PLAYER_SPEED
	player_body.move_and_slide()
	player_body.position.x = clampf(player_body.position.x, 24.0, WORLD_SIZE.x - 24.0)
	player_body.position.y = clampf(player_body.position.y, 80.0, WORLD_SIZE.y - 18.0)
	_update_actor_animation("player", input_vector, delta)


func _update_npc_routines(delta: float) -> void:
	for npc_id in NPC_ROUTINES.keys():
		var body: CharacterBody2D = actor_nodes.get(npc_id, null)
		if body == null:
			continue

		var state: Dictionary = npc_state.get(npc_id, {})
		var wait_timer: float = state.get("wait_timer", 0.0)
		if wait_timer > 0.0:
			wait_timer -= delta
			state["wait_timer"] = wait_timer
			npc_state[npc_id] = state
			body.velocity = Vector2.ZERO
			_update_actor_animation(npc_id, Vector2.ZERO, delta)
			continue

		var route: Array = NPC_ROUTINES[npc_id]
		var target_index: int = state.get("target_index", 0)
		var target: Vector2 = route[target_index]
		var delta_to_target := target - body.position
		if delta_to_target.length() < 4.0:
			state["target_index"] = (target_index + 1) % route.size()
			state["wait_timer"] = 1.2
			npc_state[npc_id] = state
			body.velocity = Vector2.ZERO
			_update_actor_animation(npc_id, Vector2.ZERO, delta)
			continue

		var movement := delta_to_target.normalized()
		body.velocity = movement * NPC_SPEED
		body.move_and_slide()
		_update_actor_animation(npc_id, movement, delta)


func _update_actor_animation(actor_id: String, movement: Vector2, delta: float) -> void:
	var body: CharacterBody2D = actor_nodes.get(actor_id, null)
	if body == null:
		return
	var sprite: Sprite2D = body.get_node("Sprite")
	var state: Dictionary = actor_state.get(actor_id, {})
	var direction: String = state.get("direction", "down")
	var moving := movement.length() > 0.01

	if moving:
		if absf(movement.x) > absf(movement.y):
			direction = "right" if movement.x > 0.0 else "left"
		else:
			direction = "down" if movement.y > 0.0 else "up"
		state["walk_time"] = float(state.get("walk_time", 0.0)) + delta
	else:
		state["walk_time"] = 0.0

	state["direction"] = direction
	state["moving"] = moving
	actor_state[actor_id] = state

	var frame := int(floor(float(state.get("walk_time", 0.0)) * 8.0)) % 4 if moving else 0
	sprite.frame_coords = Vector2i(frame, DIRECTION_ROWS[direction])


func _update_player_location() -> void:
	if player_body == null:
		return
	for location_id in LOCATION_RECTS.keys():
		var rect: Rect2 = LOCATION_RECTS[location_id]
		if rect.has_point(player_body.position):
			if local_player_location != location_id:
				local_player_location = location_id
				_send_location_entered(location_id)
			return


func _jump_player_to_location(location_id: String) -> void:
	if not LOCATION_CENTERS.has(location_id):
		return
	player_body.position = LOCATION_CENTERS[location_id]
	local_player_location = location_id
	_send_location_entered(location_id)


func _update_bubble_visibility() -> void:
	for actor_id in actor_nodes.keys():
		if actor_id == "player":
			continue
		var node: Node = actor_nodes[actor_id]
		if node.has_node("StateBubble"):
			node.get_node("StateBubble").visible = bubbles_visible


func _interact_with_nearest_npc() -> void:
	var nearest_id := ""
	var nearest_distance := INF
	for npc_id in ["mira", "tomo", "ivo"]:
		var npc: Node2D = actor_nodes.get(npc_id, null)
		if npc == null:
			continue
		var distance := player_body.position.distance_to(npc.position)
		if distance < nearest_distance:
			nearest_distance = distance
			nearest_id = npc_id

	if nearest_id == "" or nearest_distance > INTERACTION_DISTANCE:
		last_interaction_text = "No villager is close enough."
		return

	last_interaction_text = "Talking with %s." % ACTOR_NAMES[nearest_id]
	_send_interact_npc(nearest_id)


func _update_status_label() -> void:
	var connection_text := "online" if connected else "local"
	status_label.text = "Echo Hollow Playable v0 | %s | location: %s | %s" % [
		connection_text,
		local_player_location,
		last_interaction_text,
	]


func _apply_server_message(message: Dictionary) -> void:
	var payload = message.get("data", {})
	if typeof(payload) != TYPE_DICTIONARY:
		return

	if message.get("type") == "world_state":
		world_data = payload
	elif message.get("type") == "world_diff":
		_merge_world_diff(payload)
	elif message.get("type") == "dialogue_opened":
		last_interaction_text = "%s: %s" % [message.get("speaker", "Villager"), message.get("line", "")]
	elif message.get("type") == "interaction_denied":
		last_interaction_text = str(message.get("display_text", "Not close enough."))
	else:
		return

	_sync_bubbles_from_world()
	_render_events(world_data.get("latest_events", []))


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
		"last_director_trace",
		"director_state",
		"last_relationship_change",
		"actor_movements",
		"presentation",
	]:
		if diff.has(key):
			world_data[key] = diff[key]


func _sync_bubbles_from_world() -> void:
	var npcs = world_data.get("npcs", {})
	if typeof(npcs) != TYPE_DICTIONARY:
		return

	for npc_id in ["mira", "tomo", "ivo"]:
		if not actor_nodes.has(npc_id):
			continue
		var npc_data: Dictionary = npcs.get(npc_id, {})
		var bubble: Node = actor_nodes[npc_id].get_node_or_null("StateBubble")
		if bubble == null:
			continue
		var label: Label = bubble.get_node("StateLabel")
		var local_data: Dictionary = NPC_BUBBLES.get(npc_id, {})
		label.text = "%s | %s\n%s | %s" % [
			npc_data.get("mood", local_data.get("mood", "calm")),
			local_data.get("memory", "memory"),
			local_data.get("rumor", "rumor"),
			local_data.get("relationship", "+trust"),
		]


func _render_events(events: Array) -> void:
	var phase := str(world_data.get("episode_phase", "-"))
	var presentation: Dictionary = world_data.get("presentation", {})
	var lines: Array[String] = [
		"[b]Village[/b]",
		str(presentation.get("event_phase_text", "Playable local slice")),
		"Phase: %s" % phase,
		"Latest: %s" % _latest_action_summary(),
		"",
		"[b]Events[/b]",
	]
	for event in events.slice(maxi(0, events.size() - 4), events.size()):
		if typeof(event) == TYPE_DICTIONARY:
			lines.append("%s  %s" % [event.get("world_time", ""), event.get("type", "")])
	event_label.text = "\n".join(lines)


func _latest_action_summary() -> String:
	var actions = world_data.get("action_queue", [])
	if typeof(actions) != TYPE_ARRAY or actions.is_empty():
		return "-"
	var latest_action = actions[actions.size() - 1]
	if typeof(latest_action) != TYPE_DICTIONARY:
		return "-"
	return "%s %s" % [latest_action.get("status", "-"), latest_action.get("tool_name", "-")]


func _send_location_entered(location_id: String) -> void:
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return
	socket.send_text(JSON.stringify({
		"type": "player_entered_location",
		"location_id": location_id,
	}))


func _send_interact_npc(npc_id: String) -> void:
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		return
	socket.send_text(JSON.stringify({
		"type": "player_interact_npc",
		"npc_id": npc_id,
		"interaction": "talk",
	}))
