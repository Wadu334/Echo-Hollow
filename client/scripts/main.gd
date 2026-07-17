extends Node2D

const VIEWPORT_SIZE := Vector2(960, 640)
const WORLD_SIZE := Vector2(960, 672)
const TILE_SIZE := 48
const TILE_SOURCE_MARGIN := 2
const TILE_SOURCE_SIZE := TILE_SIZE - TILE_SOURCE_MARGIN * 2
const SPRITE_CELL_SIZE := 128
const PLAYER_SPEED := 150.0
const NPC_SPEED := 56.0
const INTERACTION_DISTANCE := 72.0
const CONTEXTUAL_INTERACTION_DISTANCE := 52.0

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

const LOCATION_NAMES := {
	"square": "Square",
	"tavern": "Tavern",
	"farm": "Farm",
	"workshop": "Workshop",
	"warehouse": "Warehouse",
}

const LOCATION_CENTERS := {
	"square": Vector2(480, 300),
	"tavern": Vector2(176, 210),
	"farm": Vector2(790, 430),
	"workshop": Vector2(230, 500),
	"warehouse": Vector2(760, 180),
}

const CONTEXTUAL_ACTION_ANCHORS := {
	"warehouse": Vector2(840, 230),
}

const LOCATION_RECTS := {
	"square": Rect2(300, 210, 360, 260),
	"tavern": Rect2(70, 80, 220, 230),
	"farm": Rect2(640, 330, 260, 250),
	"workshop": Rect2(90, 420, 280, 210),
	"warehouse": Rect2(650, 70, 250, 210),
}

const LOCATION_LABEL_OFFSETS := {
	"square": Vector2(-54, -98),
	"tavern": Vector2(-52, -116),
	"farm": Vector2(-34, -118),
	"workshop": Vector2(-66, -110),
	"warehouse": Vector2(-74, -118),
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
	"gggggggggggggggggggg",
	"gggddggggggggggddggg",
	"ggddddggggggggddddgg",
	"ggddddddggggddddddgg",
	"gggddddddggddddddggg",
	"ggggddddssssddddgggg",
	"gggggdddssssdddggggg",
	"ggggddddssssddddgggg",
	"gggdddddssssdddddggg",
	"ggddddddssssddddddgg",
	"ggddddgggddgggddddgg",
	"gggddggggddggggddggg",
	"gggggggggddggggggggg",
	"gggggggggddggggggggg",
]

const NPC_ROUTINES := {
	"mira": [
		Vector2(230, 500),
		Vector2(285, 462),
		Vector2(315, 525),
		Vector2(165, 520),
	],
	"tomo": [
		Vector2(805, 430),
		Vector2(740, 365),
		Vector2(670, 430),
		Vector2(790, 505),
	],
	"ivo": [
		Vector2(540, 330),
		Vector2(585, 300),
		Vector2(535, 395),
		Vector2(455, 310),
	],
}

const NPC_BUBBLES := {
	"mira": {
		"mood": "steady",
		"memory": "wood",
		"rumor": "village",
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

var connected := false
var has_connected_once := false
var world_data: Dictionary = {}
var actor_nodes: Dictionary = {}
var actor_state: Dictionary = {}
var actor_tweens: Dictionary = {}
var authoritative_actor_locations: Dictionary = {}
var location_nodes: Dictionary = {}
var location_positions: Dictionary = {}
var contextual_marker_nodes: Dictionary = {}
var npc_state: Dictionary = {}
var bubbles_visible := true
var enable_server_connection := true
var debug_controls_enabled := false
var local_player_location := "square"
var pending_player_location := ""
var last_interaction_text := "Walk up to a villager and press E to talk."
var active_dialogue_npc_id := ""
var active_conversation_id := ""
var active_offer_version := 0
var toast_timer := 0.0
var scene_transition_started := false
var pending_rumor_scene := false

var player_body: CharacterBody2D
var tile_texture: Texture2D
var prop_texture: Texture2D
var world_connection: Node
var world_presenter: Node

@onready var world_root := Node2D.new()
@onready var tile_root := Node2D.new()
@onready var prop_root := Node2D.new()
@onready var actor_root := Node2D.new()
@onready var location_root := Node2D.new()
@onready var ui_layer := CanvasLayer.new()
@onready var status_label := Label.new()
@onready var objective_label := Label.new()
@onready var hint_label := Label.new()
@onready var event_label := RichTextLabel.new()
@onready var approach_label := Label.new()
@onready var toast_label := Label.new()
@onready var dialogue_panel := PanelContainer.new()
@onready var dialogue_title_label := Label.new()
@onready var dialogue_line_label := Label.new()
@onready var dialogue_choices_box := VBoxContainer.new()


func _ready() -> void:
	debug_controls_enabled = OS.get_environment("ECHO_HOLLOW_DEBUG_CONTROLS").strip_edges().to_lower() in ["1", "true", "yes"]
	_load_textures()
	_build_world_scene()
	_build_static_ui()
	_spawn_player()
	_spawn_npcs()
	_update_bubble_visibility()
	_bind_world_presenter()
	if enable_server_connection:
		_bind_world_connection()
		_attempt_server_connection()
	else:
		status_label.text = "Echo Hollow | Offline Demo | Square"
		objective_label.text = "Server sync is disabled for verification."


func _physics_process(delta: float) -> void:
	_update_player_movement(delta)
	_update_npc_routines(delta)
	_update_player_location()
	_update_status_label()
	_update_approach_prompt()
	_update_toast(delta)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if dialogue_panel.visible:
			match event.keycode:
				KEY_ESCAPE:
					_close_dialogue()
				KEY_1, KEY_2, KEY_3, KEY_4:
					_choose_dialogue_by_number(event.keycode - KEY_1)
			return

		match event.keycode:
			KEY_F11:
				_toggle_fullscreen()
			KEY_B:
				bubbles_visible = not bubbles_visible
				_update_bubble_visibility()
			KEY_E:
				_activate_current_interaction()
			KEY_1:
				if debug_controls_enabled:
					_jump_player_to_location("square")
			KEY_2:
				if debug_controls_enabled:
					_jump_player_to_location("tavern")
			KEY_3:
				if debug_controls_enabled:
					_jump_player_to_location("farm")
			KEY_4:
				if debug_controls_enabled:
					_jump_player_to_location("workshop")
			KEY_5:
				if debug_controls_enabled:
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
	if world_connection == null:
		status_label.text = "Echo Hollow | Offline Demo | Square"
		objective_label.text = "Persistent world connection is unavailable."
		return
	status_label.text = "Echo Hollow | Connecting | Square"
	objective_label.text = "Connecting to the village server..."
	world_connection.ensure_connected()


func _bind_world_presenter() -> void:
	world_presenter = get_node_or_null("/root/WorldPresenter")
	if world_presenter == null:
		return
	var presentation_callable := Callable(self, "_on_presentation_changed")
	if not world_presenter.is_connected("presentation_changed", presentation_callable):
		world_presenter.connect("presentation_changed", presentation_callable)
	if world_presenter.has_pending_consequence():
		call_deferred("_on_rumor_consequence_ready", world_presenter.peek_next_consequence())


func _bind_world_connection() -> void:
	world_connection = get_node_or_null("/root/WorldConnection")
	if world_connection == null:
		return
	_connect_world_signal("connection_changed", "_on_connection_changed")
	_connect_world_signal("connection_status_changed", "_on_connection_status_changed")
	_connect_world_signal("world_state_received", "_on_world_state_received")
	_connect_world_signal("world_diff_received", "_on_world_diff_received")
	_connect_world_signal("dialogue_opened", "_on_dialogue_opened")
	_connect_world_signal("dialogue_result", "_on_dialogue_result")
	_connect_world_signal("dialogue_rejected", "_on_dialogue_rejected")
	_connect_world_signal("interaction_denied", "_on_interaction_denied")
	_connect_world_signal("client_error", "_on_client_error")
	_connect_world_signal("rumor_consequence_ready", "_on_rumor_consequence_ready")

	connected = bool(world_connection.connected)
	if connected:
		has_connected_once = true
	var cached_world: Dictionary = world_connection.world_data
	if not cached_world.is_empty():
		_on_world_state_received(cached_world)


func _connect_world_signal(signal_name: StringName, method_name: StringName) -> void:
	var callable := Callable(self, method_name)
	if not world_connection.is_connected(signal_name, callable):
		world_connection.connect(signal_name, callable)


func _on_connection_changed(is_connected: bool) -> void:
	connected = is_connected
	if connected:
		has_connected_once = true
		_freeze_local_npcs()
		var cached_world: Dictionary = world_connection.world_data
		if not cached_world.is_empty():
			_on_world_state_received(cached_world)
	elif has_connected_once:
		_freeze_local_npcs()
		_close_dialogue()


func _on_connection_status_changed(_status: String) -> void:
	_update_status_label()


func _on_presentation_changed(_presentation: Dictionary) -> void:
	_update_contextual_markers()
	_update_status_label()
	_render_events(world_data.get("latest_events", []))


func _on_world_state_received(data: Dictionary) -> void:
	world_data = data.duplicate(true)
	if world_presenter != null:
		world_presenter.ingest_world_data(world_data)
	_reconcile_authoritative_world({}, true)


func _on_world_diff_received(diff: Dictionary) -> void:
	if world_connection != null:
		world_data = world_connection.world_data.duplicate(true)
	else:
		_merge_world_diff(diff)
		if world_presenter != null:
			world_presenter.ingest_world_data(world_data)
	_reconcile_authoritative_world(diff, false)


func _on_dialogue_opened(message: Dictionary) -> void:
	last_interaction_text = "%s says: %s" % [message.get("speaker", "Villager"), message.get("line", "")]
	_show_dialogue(message)


func _on_dialogue_result(message: Dictionary) -> void:
	last_interaction_text = str(message.get("display_text", message.get("toast", "Choice noted.")))
	_show_dialogue_result(message)


func _on_dialogue_rejected(message: Dictionary) -> void:
	var text := str(message.get("display_text", "That conversation choice is no longer available."))
	_show_toast(text)
	if message.has("conversation_id") and message.has("offer_version") and message.has("choices"):
		_show_dialogue(message)
	else:
		_close_dialogue()


func _on_interaction_denied(message: Dictionary) -> void:
	last_interaction_text = str(message.get("display_text", "Not close enough."))
	_show_toast(last_interaction_text)


func _on_client_error(message: Dictionary) -> void:
	_show_toast(str(message.get("display_text", message.get("error", "Village server error."))))


func _on_rumor_consequence_ready(_payload: Dictionary) -> void:
	if scene_transition_started:
		return
	if actor_tweens.has("mira"):
		pending_rumor_scene = true
		return
	scene_transition_started = true
	call_deferred("_open_rumor_consequence_scene")


func _open_rumor_consequence_scene() -> void:
	if world_presenter != null:
		var consequence_payload: Dictionary = world_presenter.begin_next_consequence()
		if consequence_payload.is_empty():
			scene_transition_started = false
			pending_rumor_scene = false
			return
	if world_connection == null:
		scene_transition_started = false
		pending_rumor_scene = false
		return
	_close_dialogue()
	var error := get_tree().change_scene_to_file("res://scenes/rumor_consequence.tscn")
	if error != OK:
		scene_transition_started = false
		_show_toast("The rumor consequence scene could not be opened.")


func _build_world_scene() -> void:
	add_child(world_root)
	world_root.add_child(tile_root)
	world_root.add_child(location_root)
	world_root.add_child(prop_root)
	world_root.add_child(actor_root)

	_build_tile_ground()
	_build_location_markers()
	_build_contextual_markers()
	_build_props()


func _build_tile_ground() -> void:
	for y in MAP_ROWS.size():
		var row: String = MAP_ROWS[y]
		for x in row.length():
			var key := row[x]
			var map_cell := Vector2i(x, y)
			_add_tile(map_cell, _tile_atlas_for(key, map_cell))


func _tile_atlas_for(key: String, map_cell: Vector2i) -> Vector2i:
	var jitter: int = abs(map_cell.x * 17 + map_cell.y * 31) % 9
	if key == "g" and jitter == 0:
		return TILE_ATLAS["f"]
	if key == "g" and jitter == 4:
		return TILE_ATLAS["m"]
	if key == "d" and jitter == 2:
		return TILE_ATLAS["r"]
	if key == "s" and jitter == 5:
		return TILE_ATLAS["c"]
	return TILE_ATLAS.get(key, TILE_ATLAS["g"])


func _add_tile(map_cell: Vector2i, atlas_cell: Vector2i) -> void:
	var tile := Sprite2D.new()
	tile.texture = tile_texture
	tile.region_enabled = true
	var region_origin := Vector2(
		atlas_cell.x * TILE_SIZE + TILE_SOURCE_MARGIN,
		atlas_cell.y * TILE_SIZE + TILE_SOURCE_MARGIN
	)
	tile.region_rect = Rect2(region_origin, Vector2(TILE_SOURCE_SIZE, TILE_SOURCE_SIZE))
	tile.position = Vector2(map_cell.x * TILE_SIZE + TILE_SIZE / 2, map_cell.y * TILE_SIZE + TILE_SIZE / 2)
	tile.scale = Vector2(
		float(TILE_SIZE) / float(TILE_SOURCE_SIZE),
		float(TILE_SIZE) / float(TILE_SOURCE_SIZE)
	)
	tile.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	tile_root.add_child(tile)


func _toggle_fullscreen() -> void:
	var mode := DisplayServer.window_get_mode()
	if mode == DisplayServer.WINDOW_MODE_FULLSCREEN or mode == DisplayServer.WINDOW_MODE_EXCLUSIVE_FULLSCREEN:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	else:
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)


func _build_location_markers() -> void:
	for location_id in LOCATION_CENTERS.keys():
		var marker := Node2D.new()
		marker.name = "%s_location" % location_id
		marker.position = LOCATION_CENTERS[location_id]
		location_root.add_child(marker)
		location_nodes[location_id] = marker
		location_positions[location_id] = LOCATION_CENTERS[location_id]
		_add_location_sign(location_id, marker)


func _add_location_sign(location_id: String, marker: Node2D) -> void:
	var sign := Node2D.new()
	sign.name = "%s_sign" % location_id
	sign.position = LOCATION_LABEL_OFFSETS.get(location_id, Vector2(-54, -96))
	marker.add_child(sign)

	var bg := ColorRect.new()
	bg.color = Color(0.10, 0.12, 0.11, 0.62)
	bg.size = Vector2(118, 26)
	bg.position = Vector2.ZERO
	sign.add_child(bg)

	var label := Label.new()
	label.text = LOCATION_NAMES.get(location_id, location_id.capitalize())
	label.size = bg.size
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 12)
	label.add_theme_color_override("font_color", Color(1.0, 0.96, 0.82, 1.0))
	label.add_theme_color_override("font_outline_color", Color(0.0, 0.0, 0.0, 0.8))
	label.add_theme_constant_override("outline_size", 2)
	sign.add_child(label)


func _build_contextual_markers() -> void:
	for location_id in CONTEXTUAL_ACTION_ANCHORS.keys():
		var marker := Node2D.new()
		marker.name = "%s_contextual_clue" % location_id
		marker.position = CONTEXTUAL_ACTION_ANCHORS[location_id]
		marker.visible = false
		location_root.add_child(marker)
		contextual_marker_nodes[location_id] = marker

		var diamond := Polygon2D.new()
		diamond.polygon = PackedVector2Array([
			Vector2(0, -9),
			Vector2(9, 0),
			Vector2(0, 9),
			Vector2(-9, 0),
		])
		diamond.color = Color(1.0, 0.78, 0.30, 0.92)
		marker.add_child(diamond)

		var label := Label.new()
		label.name = "ClueLabel"
		label.text = "Clue"
		label.position = Vector2(-80, -34)
		label.size = Vector2(160, 20)
		label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		label.add_theme_font_size_override("font_size", 11)
		label.add_theme_color_override("font_color", Color(1.0, 0.92, 0.68, 1.0))
		label.add_theme_color_override("font_outline_color", Color(0.0, 0.0, 0.0, 0.9))
		label.add_theme_constant_override("outline_size", 3)
		marker.add_child(label)


func _update_contextual_markers() -> void:
	for marker_value in contextual_marker_nodes.values():
		(marker_value as Node2D).visible = false
	if world_presenter == null:
		return
	var action: Dictionary = world_presenter.current_contextual_action()
	var location_id := str(action.get("location_id", ""))
	if str(action.get("action_id", "")).is_empty() or not contextual_marker_nodes.has(location_id):
		return
	var marker: Node2D = contextual_marker_nodes[location_id]
	marker.visible = true
	var label: Label = marker.get_node("ClueLabel")
	label.text = str(action.get("label", "Clue"))


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
	status_label.text = "Echo Hollow | Local | Square"
	ui_layer.add_child(status_label)

	objective_label.position = Vector2(16, 34)
	objective_label.add_theme_font_size_override("font_size", 13)
	objective_label.text = "Next: Walk up to a villager and press E to talk."
	ui_layer.add_child(objective_label)

	hint_label.position = Vector2(16, 606)
	hint_label.add_theme_font_size_override("font_size", 14)
	hint_label.text = "WASD move | E interact | B bubbles | F11 fullscreen"
	if debug_controls_enabled:
		hint_label.text += " | 1-5 debug jump"
	ui_layer.add_child(hint_label)

	event_label.position = Vector2(676, 18)
	event_label.size = Vector2(270, 190)
	event_label.bbcode_enabled = true
	event_label.add_theme_font_size_override("normal_font_size", 13)
	event_label.text = "[b]Village[/b]\nTalk with villagers and learn who they are.\nNext: Press E near a villager."
	ui_layer.add_child(event_label)

	approach_label.position = Vector2(300, 558)
	approach_label.size = Vector2(360, 28)
	approach_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	approach_label.add_theme_font_size_override("font_size", 15)
	approach_label.add_theme_color_override("font_color", Color(1.0, 0.96, 0.82, 1.0))
	approach_label.add_theme_color_override("font_outline_color", Color(0.0, 0.0, 0.0, 0.9))
	approach_label.add_theme_constant_override("outline_size", 4)
	approach_label.visible = false
	ui_layer.add_child(approach_label)

	toast_label.position = Vector2(290, 92)
	toast_label.size = Vector2(380, 42)
	toast_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	toast_label.add_theme_font_size_override("font_size", 14)
	toast_label.add_theme_color_override("font_color", Color(1.0, 0.98, 0.88, 1.0))
	toast_label.add_theme_color_override("font_outline_color", Color(0.0, 0.0, 0.0, 0.9))
	toast_label.add_theme_constant_override("outline_size", 4)
	toast_label.visible = false
	ui_layer.add_child(toast_label)

	_build_dialogue_ui()


func _build_dialogue_ui() -> void:
	dialogue_panel.position = Vector2(210, 414)
	dialogue_panel.size = Vector2(540, 176)
	dialogue_panel.visible = false
	ui_layer.add_child(dialogue_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 14)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 14)
	margin.add_theme_constant_override("margin_bottom", 12)
	dialogue_panel.add_child(margin)

	var layout := VBoxContainer.new()
	layout.add_theme_constant_override("separation", 7)
	margin.add_child(layout)

	dialogue_title_label.add_theme_font_size_override("font_size", 16)
	dialogue_title_label.add_theme_color_override("font_color", Color(0.18, 0.13, 0.08, 1.0))
	layout.add_child(dialogue_title_label)

	dialogue_line_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	dialogue_line_label.add_theme_font_size_override("font_size", 13)
	dialogue_line_label.add_theme_color_override("font_color", Color(0.20, 0.16, 0.12, 1.0))
	layout.add_child(dialogue_line_label)

	dialogue_choices_box.add_theme_constant_override("separation", 5)
	layout.add_child(dialogue_choices_box)


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
	if dialogue_panel.visible:
		player_body.velocity = Vector2.ZERO
		_update_actor_animation("player", Vector2.ZERO, delta)
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
	if connected or has_connected_once:
		return
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


func _freeze_local_npcs() -> void:
	for npc_id in ["mira", "tomo", "ivo"]:
		if actor_tweens.has(npc_id):
			var existing_tween: Tween = actor_tweens[npc_id]
			if existing_tween != null and existing_tween.is_valid():
				existing_tween.kill()
			actor_tweens.erase(npc_id)
		var body: CharacterBody2D = actor_nodes.get(npc_id, null)
		if body == null:
			continue
		body.velocity = Vector2.ZERO
		_update_actor_animation(npc_id, Vector2.ZERO, 0.0)


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
			if connected:
				if local_player_location != location_id and pending_player_location != location_id:
					pending_player_location = location_id
					_send_location_entered(location_id)
			elif local_player_location != location_id:
				local_player_location = location_id
			return


func _jump_player_to_location(location_id: String) -> void:
	if not LOCATION_CENTERS.has(location_id):
		return
	player_body.position = LOCATION_CENTERS[location_id]
	if connected:
		if pending_player_location != location_id:
			pending_player_location = location_id
			_send_location_entered(location_id)
	else:
		local_player_location = location_id


func _update_bubble_visibility() -> void:
	for actor_id in actor_nodes.keys():
		if actor_id == "player":
			continue
		var node: Node = actor_nodes[actor_id]
		if node.has_node("StateBubble"):
			node.get_node("StateBubble").visible = bubbles_visible


func _interact_with_nearest_npc() -> void:
	_activate_current_interaction()


func _activate_current_interaction() -> void:
	var interaction := _current_interaction()
	var interaction_kind := str(interaction.get("kind", ""))
	if interaction_kind == "npc":
		var npc_id := str(interaction.get("npc_id", ""))
		last_interaction_text = "Opening conversation with %s..." % ACTOR_NAMES.get(npc_id, npc_id.capitalize())
		_send_interact_npc(npc_id)
		return
	if interaction_kind == "contextual_action":
		var action_id := str(interaction.get("action_id", ""))
		var offer_version := int(interaction.get("offer_version", 0))
		last_interaction_text = str(interaction.get("label", "Checking this clue..."))
		_send_activate_contextual_action(action_id, offer_version)
		return
	last_interaction_text = "Move closer to a villager or an available clue, then press E."
	_show_toast(last_interaction_text)


func _update_status_label() -> void:
	var connection_text := "Offline"
	if world_connection != null:
		connection_text = str(world_connection.connection_status)
	elif not enable_server_connection:
		connection_text = "Offline Demo"
	status_label.text = "Echo Hollow | %s | %s" % [
		connection_text,
		_pretty_location(local_player_location),
	]
	var objective := _server_objective()
	if objective.is_empty():
		objective = _current_player_prompt()
	objective_label.text = "Next: %s" % objective


func _nearest_talkable_npc_id() -> String:
	if player_body == null:
		return ""
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
	if nearest_distance <= INTERACTION_DISTANCE:
		return nearest_id
	return ""


func _update_approach_prompt() -> void:
	if dialogue_panel.visible:
		approach_label.visible = false
		return
	var interaction := _current_interaction()
	if interaction.is_empty():
		approach_label.visible = false
		return
	approach_label.text = str(interaction.get("prompt", "Press E to interact"))
	approach_label.visible = true


func _current_interaction() -> Dictionary:
	if has_connected_once and not connected:
		return {}
	var nearest_id := _nearest_talkable_npc_id()
	var npc_candidate: Dictionary = {}
	var npc_distance := INF
	if not nearest_id.is_empty():
		npc_distance = player_body.position.distance_to(actor_nodes[nearest_id].position)
		npc_candidate = {
			"kind": "npc",
			"npc_id": nearest_id,
			"distance": npc_distance,
			"prompt": "Press E to talk to %s" % ACTOR_NAMES.get(nearest_id, nearest_id.capitalize()),
		}

	var contextual_candidate: Dictionary = {}
	if world_presenter != null and connected:
		var action: Dictionary = world_presenter.current_contextual_action()
		var action_id := str(action.get("action_id", ""))
		var offered_location := str(action.get("location_id", ""))
		if (
			not action_id.is_empty()
			and action.has("offer_version")
			and offered_location == local_player_location
			and CONTEXTUAL_ACTION_ANCHORS.has(offered_location)
		):
			var contextual_distance := player_body.position.distance_to(CONTEXTUAL_ACTION_ANCHORS[offered_location])
			if contextual_distance <= CONTEXTUAL_INTERACTION_DISTANCE:
				contextual_candidate = {
					"kind": "contextual_action",
					"action_id": action_id,
					"offer_version": int(action.get("offer_version", 0)),
					"label": str(action.get("label", "Inspect the clue")),
					"distance": contextual_distance,
					"prompt": str(action.get("prompt", "Press E to %s" % str(action.get("label", "inspect the clue")).to_lower())),
				}

	if not contextual_candidate.is_empty() and (
		npc_candidate.is_empty() or float(contextual_candidate["distance"]) < npc_distance
	):
		return contextual_candidate
	return npc_candidate


func _update_toast(delta: float) -> void:
	if toast_timer <= 0.0:
		return
	toast_timer -= delta
	if toast_timer <= 0.0:
		toast_label.visible = false


func _show_toast(text: String) -> void:
	toast_label.text = text
	toast_label.visible = true
	toast_timer = 3.0


func _apply_server_message(message: Dictionary) -> void:
	var payload = message.get("data", {})
	if message.get("type") == "world_state":
		if typeof(payload) == TYPE_DICTIONARY:
			_on_world_state_received(payload)
	elif message.get("type") == "world_diff":
		if typeof(payload) == TYPE_DICTIONARY:
			_merge_world_diff(payload)
			_reconcile_authoritative_world(payload, false)
	elif message.get("type") == "dialogue_opened":
		_on_dialogue_opened(message)
	elif message.get("type") == "dialogue_result":
		var result_diff = message.get("world_diff", {})
		if typeof(result_diff) == TYPE_DICTIONARY:
			_merge_world_diff(result_diff)
			_reconcile_authoritative_world(result_diff, false)
		_on_dialogue_result(message)
	elif message.get("type") == "dialogue_rejected":
		_on_dialogue_rejected(message)
	elif message.get("type") == "interaction_denied":
		_on_interaction_denied(message)
	elif message.get("type") == "client_error":
		_on_client_error(message)
	else:
		return

	_sync_bubbles_from_world()
	_render_events(world_data.get("latest_events", []))


func _show_dialogue(message: Dictionary) -> void:
	active_dialogue_npc_id = str(message.get("npc_id", ""))
	active_conversation_id = str(message.get("conversation_id", ""))
	active_offer_version = int(message.get("offer_version", 0))
	dialogue_title_label.text = str(message.get("speaker", "Villager"))
	dialogue_line_label.text = str(message.get("line", "Hello."))
	_rebuild_dialogue_choices(message.get("choices", []))
	dialogue_panel.visible = true
	approach_label.visible = false


func _show_dialogue_result(message: Dictionary) -> void:
	var text := str(message.get("display_text", message.get("toast", "Choice noted.")))
	dialogue_line_label.text = text
	_show_toast(text)
	if bool(message.get("conversation_closed", false)) or str(message.get("choice_id", "")) in ["goodbye", "share_ivo_claim"]:
		_close_dialogue()
		return
	if message.has("conversation_id"):
		active_conversation_id = str(message.get("conversation_id", active_conversation_id))
	if message.has("offer_version"):
		active_offer_version = int(message.get("offer_version", active_offer_version))
	elif message.has("next_offer_version"):
		active_offer_version = int(message.get("next_offer_version", active_offer_version))
	if message.has("choices"):
		_rebuild_dialogue_choices(message.get("choices", []))


func _rebuild_dialogue_choices(choices: Variant) -> void:
	for child in dialogue_choices_box.get_children():
		child.queue_free()
	if typeof(choices) != TYPE_ARRAY:
		return
	for index in choices.size():
		var choice = choices[index]
		if typeof(choice) != TYPE_DICTIONARY:
			continue
		var choice_id := str(choice.get("choice_id", ""))
		var text := str(choice.get("text", choice_id.capitalize()))
		var button := Button.new()
		button.text = "%d. %s" % [index + 1, text]
		button.focus_mode = Control.FOCUS_NONE
		button.custom_minimum_size = Vector2(0, 28)
		button.pressed.connect(_on_dialogue_choice_pressed.bind(choice_id))
		dialogue_choices_box.add_child(button)


func _on_dialogue_choice_pressed(choice_id: String) -> void:
	_send_dialogue_choice(choice_id)


func _choose_dialogue_by_number(index: int) -> void:
	if index < 0 or index >= dialogue_choices_box.get_child_count():
		return
	var button = dialogue_choices_box.get_child(index)
	if button is Button:
		(button as Button).emit_signal("pressed")


func _close_dialogue() -> void:
	dialogue_panel.visible = false
	active_dialogue_npc_id = ""
	active_conversation_id = ""
	active_offer_version = 0
	last_interaction_text = "Walk up to a villager and press E to talk."


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
		"pending_presentations",
	]:
		if diff.has(key):
			world_data[key] = diff[key]


func _reconcile_authoritative_world(diff: Dictionary, force_snap: bool) -> void:
	var player_data = world_data.get("player", {})
	if typeof(player_data) == TYPE_DICTIONARY:
		var authoritative_player_location := str(player_data.get("current_location", local_player_location))
		var previous_player_location := str(authoritative_actor_locations.get("player", ""))
		var rejection_reason := str(diff.get("reason", ""))
		var location_rejected := rejection_reason in [
			"not_reachable",
			"location_not_found",
			"invalid_location",
		]
		var player_move_resolved := rejection_reason == "player_moved"
		var pending_was_accepted := (
			player_move_resolved
			and not pending_player_location.is_empty()
			and pending_player_location == authoritative_player_location
		)
		var should_snap_player := force_snap or previous_player_location.is_empty()
		if location_rejected:
			should_snap_player = true
		elif player_move_resolved and not pending_player_location.is_empty() and not pending_was_accepted:
			should_snap_player = true
		elif previous_player_location != authoritative_player_location and pending_player_location.is_empty():
			should_snap_player = true
		if should_snap_player:
			_snap_actor_to_location("player", authoritative_player_location)
		if force_snap or location_rejected or player_move_resolved:
			pending_player_location = ""
		local_player_location = authoritative_player_location
		authoritative_actor_locations["player"] = authoritative_player_location

	var movements_by_actor: Dictionary = {}
	var actor_movements = diff.get("actor_movements", [])
	if typeof(actor_movements) == TYPE_ARRAY:
		for movement_value in actor_movements:
			if typeof(movement_value) != TYPE_DICTIONARY:
				continue
			var movement: Dictionary = movement_value
			var movement_actor_id := str(movement.get("actor_id", ""))
			if movement_actor_id in ["mira", "tomo", "ivo"]:
				movements_by_actor[movement_actor_id] = movement

	var npcs = world_data.get("npcs", {})
	if typeof(npcs) == TYPE_DICTIONARY:
		for npc_id in ["mira", "tomo", "ivo"]:
			var npc_data: Dictionary = npcs.get(npc_id, {})
			var authoritative_location := str(npc_data.get("current_location", ""))
			if authoritative_location.is_empty() or not LOCATION_CENTERS.has(authoritative_location):
				continue
			var previous_location := str(authoritative_actor_locations.get(npc_id, ""))
			var movement: Dictionary = movements_by_actor.get(npc_id, {})
			if force_snap or previous_location.is_empty():
				_snap_actor_to_location(npc_id, authoritative_location)
			elif not movement.is_empty():
				if str(movement.get("to_location", "")) == authoritative_location:
					_tween_actor_to_location(npc_id, authoritative_location, movement)
					var display_text := str(movement.get("display_text", ""))
					if not display_text.is_empty():
						_show_toast(display_text)
				else:
					_snap_actor_to_location(npc_id, authoritative_location)
			elif previous_location != authoritative_location:
				_snap_actor_to_location(npc_id, authoritative_location)
			authoritative_actor_locations[npc_id] = authoritative_location

	if not active_dialogue_npc_id.is_empty() and typeof(npcs) == TYPE_DICTIONARY:
		var active_npc: Dictionary = npcs.get(active_dialogue_npc_id, {})
		if str(active_npc.get("current_location", "")) != local_player_location:
			_close_dialogue()

	_sync_bubbles_from_world()
	_render_events(world_data.get("latest_events", []))


func _snap_actor_to_location(actor_id: String, location_id: String) -> void:
	if not actor_nodes.has(actor_id) or not LOCATION_CENTERS.has(location_id):
		return
	if actor_tweens.has(actor_id):
		var existing_tween: Tween = actor_tweens[actor_id]
		if existing_tween != null and existing_tween.is_valid():
			existing_tween.kill()
		actor_tweens.erase(actor_id)
	var body: CharacterBody2D = actor_nodes[actor_id]
	body.position = LOCATION_CENTERS[location_id]
	body.velocity = Vector2.ZERO
	_on_actor_motion_settled(actor_id)


func _tween_actor_to_location(actor_id: String, location_id: String, movement: Dictionary) -> void:
	if not actor_nodes.has(actor_id) or not LOCATION_CENTERS.has(location_id):
		return
	if actor_tweens.has(actor_id):
		var existing_tween: Tween = actor_tweens[actor_id]
		if existing_tween != null and existing_tween.is_valid():
			existing_tween.kill()
	var body: CharacterBody2D = actor_nodes[actor_id]
	var target_position: Vector2 = LOCATION_CENTERS[location_id]
	var direction := target_position - body.position
	var duration := clampf(float(movement.get("duration_seconds", 0.4)), 0.05, 6.0)
	body.velocity = Vector2.ZERO
	_update_actor_animation(actor_id, direction.normalized(), 0.1)
	var tween := create_tween()
	tween.set_trans(Tween.TRANS_SINE)
	tween.set_ease(Tween.EASE_IN_OUT)
	tween.tween_property(body, "position", target_position, duration)
	tween.finished.connect(_on_actor_tween_finished.bind(actor_id))
	actor_tweens[actor_id] = tween


func _on_actor_tween_finished(actor_id: String) -> void:
	actor_tweens.erase(actor_id)
	_on_actor_motion_settled(actor_id)


func _on_actor_motion_settled(actor_id: String) -> void:
	_update_actor_animation(actor_id, Vector2.ZERO, 0.0)
	if actor_id == "mira" and pending_rumor_scene and not scene_transition_started:
		pending_rumor_scene = false
		scene_transition_started = true
		call_deferred("_open_rumor_consequence_scene")


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
		var memory_count := 0
		var memories_value = world_data.get("memories", {})
		if typeof(memories_value) == TYPE_DICTIONARY:
			var owner_memories = (memories_value as Dictionary).get(npc_id, [])
			if typeof(owner_memories) == TYPE_ARRAY:
				memory_count = (owner_memories as Array).size()
			elif typeof(owner_memories) == TYPE_DICTIONARY:
				memory_count = (owner_memories as Dictionary).size()
		var rumor_count := 0
		var rumors: Dictionary = world_data.get("rumors", {})
		for rumor_value in rumors.values():
			if typeof(rumor_value) != TYPE_DICTIONARY:
				continue
			var holders = rumor_value.get("current_holder_ids", [])
			if typeof(holders) == TYPE_ARRAY and npc_id in holders:
				rumor_count += 1
		label.text = "%s | %s\n%s | %s" % [
			npc_data.get("mood", "calm"),
			npc_data.get("current_action", "idle"),
			"mem %d" % memory_count,
			"rumor %d" % rumor_count,
		]


func _render_events(events: Array) -> void:
	var presentation_data: Dictionary = world_data.get("presentation", {})
	if world_presenter != null and not world_presenter.presentation.is_empty():
		presentation_data = world_presenter.presentation
	var title := str(presentation_data.get("event_title", "Village"))
	var phase_text := str(presentation_data.get("event_phase_text", "Village Day"))
	var flow_text := str(presentation_data.get("village_flow_text", "Talk with villagers and learn who they are."))
	var objective := str(presentation_data.get("objective", "")).strip_edges()
	var toasts = presentation_data.get("toasts", [])
	var lines: Array[String] = [
		"[b]%s[/b]" % title,
		phase_text,
		flow_text,
	]
	if not objective.is_empty():
		lines.append("Next: %s" % objective)
	if typeof(toasts) == TYPE_ARRAY and not toasts.is_empty():
		lines.append("Update: %s" % str(toasts[toasts.size() - 1]))
	lines.append("")
	lines.append("[b]Recent[/b]")
	for event in events.slice(maxi(0, events.size() - 4), events.size()):
		if typeof(event) == TYPE_DICTIONARY:
			lines.append("%s  %s" % [
				event.get("world_time", ""),
				_event_display_label(str(event.get("type", ""))),
			])
	event_label.text = "\n".join(lines)


func _current_player_prompt() -> String:
	if dialogue_panel.visible:
		return "Choose a topic, or press Esc to close the conversation."
	var interaction := _current_interaction()
	if not interaction.is_empty():
		return str(interaction.get("prompt", "Press E to interact")).trim_prefix("Press E to ").capitalize()
	var player = world_data.get("player", {})
	if typeof(player) == TYPE_DICTIONARY:
		var notes = player.get("notes", [])
		if typeof(notes) == TYPE_ARRAY and not notes.is_empty():
			return "You learned something new. Talk to another villager."
	return "Walk up to a villager and press E to talk."


func _server_objective() -> String:
	if world_presenter != null:
		var presenter_objective := str(world_presenter.objective_text()).strip_edges()
		if not presenter_objective.is_empty():
			return presenter_objective
	var presentation_data = world_data.get("presentation", {})
	if typeof(presentation_data) == TYPE_DICTIONARY:
		return str(presentation_data.get("objective", "")).strip_edges()
	return ""


func _event_display_label(event_type: String) -> String:
	match event_type:
		"world_started":
			return "The village day begins."
		"player_moved":
			return "You changed location."
		"player_interacted_npc":
			return "Conversation started."
		"dialogue_choice_selected":
			return "You answered."
		"player_note_added":
			return "You learned something new."
		"memory_written":
			return "Someone remembered something."
		"relationship_changed":
			return "A relationship shifted."
		"rumor_spread":
			return "A rumor spread."
		"npc_schedule_changed":
			return "A villager changed plans."
		"evidence_found":
			return "Something interesting was found."
		_:
			return event_type.replace("_", " ").capitalize()


func _pretty_location(location_id: String) -> String:
	match location_id:
		"square":
			return "Square"
		"tavern":
			return "Tavern"
		"farm":
			return "Farm"
		"workshop":
			return "Workshop"
		"warehouse":
			return "Warehouse"
		_:
			return location_id.capitalize()


func _send_location_entered(location_id: String) -> void:
	if world_connection == null or not connected:
		return
	world_connection.send_location_intent(location_id)


func _send_interact_npc(npc_id: String) -> void:
	if world_connection == null or not connected:
		_show_toast("Village server is not connected yet.")
		return
	world_connection.send_interact_npc(npc_id)


func _send_activate_contextual_action(action_id: String, offer_version: int) -> void:
	if world_connection == null or not connected:
		_show_toast("Village server is not connected yet.")
		return
	if not world_connection.send_activate_contextual_action(action_id, offer_version):
		_show_toast("That interaction is no longer available.")


func _send_dialogue_choice(choice_id: String) -> void:
	if active_dialogue_npc_id == "" or active_conversation_id == "":
		return
	if world_connection == null or not connected:
		_show_toast("Village server is not connected yet.")
		return
	world_connection.send_command({
		"type": "dialogue_choice",
		"conversation_id": active_conversation_id,
		"offer_version": active_offer_version,
		"choice_id": choice_id,
	})
