extends Node2D

const VIEWPORT_SIZE := Vector2(960, 640)
const ASSET_ROOT := "res://assets/playable_world_v0"
const MIRA_SHEET := ASSET_ROOT + "/sprites/mira_walk_4dir_4frame.png"
const TOMO_SHEET := ASSET_ROOT + "/sprites/tomo_walk_4dir_4frame.png"

var world_connection: Node
var world_presenter: Node
var presentation_id := ""
var elapsed := 0.0
var duration_seconds := 3.5
var returning_to_main := false


func _ready() -> void:
	world_connection = get_node_or_null("/root/WorldConnection")
	world_presenter = get_node_or_null("/root/WorldPresenter")
	if world_connection == null or world_presenter == null:
		call_deferred("_return_to_main")
		return

	var configured_duration := OS.get_environment("ECHO_HOLLOW_CUTSCENE_DURATION").strip_edges()
	if not configured_duration.is_empty():
		duration_seconds = maxf(0.05, float(configured_duration))

	var payload: Dictionary = world_presenter.begin_next_consequence()
	if payload.is_empty():
		payload = world_connection.rumor_consequence_payload
	presentation_id = str(payload.get("presentation_id", ""))
	if payload.is_empty() or presentation_id.is_empty():
		call_deferred("_return_to_main")
		return
	_build_scene(payload)


func _process(delta: float) -> void:
	elapsed += delta
	if elapsed >= duration_seconds:
		_return_to_main()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode in [KEY_SPACE, KEY_ESCAPE]:
			_return_to_main()


func _build_scene(payload: Dictionary) -> void:
	var background := ColorRect.new()
	background.color = Color(0.08, 0.07, 0.09, 1.0)
	background.size = VIEWPORT_SIZE
	add_child(background)

	var glow := ColorRect.new()
	glow.color = Color(0.35, 0.18, 0.16, 0.28)
	glow.position = Vector2(120, 100)
	glow.size = Vector2(720, 430)
	add_child(glow)

	_add_actor(MIRA_SHEET, Vector2(335, 390), false)
	_add_actor(TOMO_SHEET, Vector2(625, 390), true)

	var ui := CanvasLayer.new()
	add_child(ui)

	var title := Label.new()
	title.text = str(payload.get("title", "Village Consequence"))
	title.position = Vector2(250, 72)
	title.size = Vector2(460, 50)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 28)
	title.add_theme_color_override("font_color", Color(1.0, 0.88, 0.66, 1.0))
	ui.add_child(title)

	var line := Label.new()
	line.text = "\"%s\"" % str(payload.get("line", ""))
	line.position = Vector2(190, 148)
	line.size = Vector2(580, 92)
	line.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	line.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	line.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	line.add_theme_font_size_override("font_size", 17)
	line.add_theme_color_override("font_color", Color(0.96, 0.91, 0.84, 1.0))
	ui.add_child(line)

	var reaction := Label.new()
	reaction.text = str(payload.get("reaction_text", ""))
	reaction.position = Vector2(190, 452)
	reaction.size = Vector2(580, 44)
	reaction.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	reaction.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	reaction.add_theme_font_size_override("font_size", 16)
	reaction.add_theme_color_override("font_color", Color(0.90, 0.70, 0.68, 1.0))
	ui.add_child(reaction)

	var relationship_label := Label.new()
	relationship_label.text = str(payload.get("relationship_trend_text", ""))
	relationship_label.position = Vector2(190, 500)
	relationship_label.size = Vector2(580, 28)
	relationship_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	relationship_label.add_theme_font_size_override("font_size", 14)
	relationship_label.add_theme_color_override("font_color", Color(0.76, 0.78, 0.80, 1.0))
	ui.add_child(relationship_label)

	var reflection_text := str(payload.get("reflection_text", "")).strip_edges()
	if not reflection_text.is_empty():
		var reflection := Label.new()
		reflection.text = reflection_text
		reflection.position = Vector2(190, 532)
		reflection.size = Vector2(580, 42)
		reflection.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		reflection.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		reflection.add_theme_font_size_override("font_size", 13)
		reflection.add_theme_color_override("font_color", Color(0.82, 0.82, 0.76, 1.0))
		ui.add_child(reflection)

	var hint := Label.new()
	hint.text = "Space / Esc to continue"
	hint.position = Vector2(350, 588)
	hint.size = Vector2(260, 24)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 12)
	hint.add_theme_color_override("font_color", Color(0.58, 0.58, 0.62, 1.0))
	ui.add_child(hint)


func _add_actor(sheet_path: String, position_value: Vector2, face_left: bool) -> void:
	var sprite := Sprite2D.new()
	sprite.texture = _load_png_texture(sheet_path)
	sprite.hframes = 4
	sprite.vframes = 4
	sprite.frame_coords = Vector2i(0, 2 if face_left else 3)
	sprite.position = position_value
	sprite.scale = Vector2(1.15, 1.15)
	sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	add_child(sprite)


func _load_png_texture(res_path: String) -> Texture2D:
	var image := Image.new()
	var error := image.load(ProjectSettings.globalize_path(res_path))
	if error != OK:
		push_error("Could not load PNG texture %s: %s" % [res_path, error])
		return null
	return ImageTexture.create_from_image(image)


func _return_to_main() -> void:
	if returning_to_main:
		return
	returning_to_main = true
	var error := get_tree().change_scene_to_file("res://scenes/main.tscn")
	if error != OK:
		returning_to_main = false
		return
	if world_connection != null and not presentation_id.is_empty():
		world_connection.ack_presentation(presentation_id)
