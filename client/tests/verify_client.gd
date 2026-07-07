extends SceneTree

var failures: Array[String] = []


func _init() -> void:
	call_deferred("_run")


func _run() -> void:
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
			"ivo": _npc("ivo", "Ivo", "tavern", "warm"),
		},
		"latest_events": [
			{
				"world_time": "day 1 08:00",
				"type": "test_event",
			},
		],
		"presentation": {
			"event_phase_text": "Gathering clues",
		},
	}


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


func _fail(message: String) -> void:
	failures.append(message)
	for failure in failures:
		push_error(failure)
	quit(1)
