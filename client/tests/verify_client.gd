extends SceneTree


func _initialize() -> void:
	var scene := load("res://scenes/main.tscn")
	if scene == null:
		_fail("Could not load main scene.")
		return

	var main = scene.instantiate()
	root.add_child(main)
	await process_frame

	main._apply_server_message({
		"type": "world_state",
		"data": _world_state("square", 1),
	})
	await process_frame

	_expect(main.location_nodes.size() == 5, "Expected 5 location nodes.")
	_expect(main.actor_nodes.has("player"), "Expected player node.")
	_expect(main.actor_nodes.has("mira"), "Expected Mira node.")
	_expect(main.actor_nodes.has("tomo"), "Expected Tomo node.")
	_expect(main.actor_nodes.has("ivo"), "Expected Ivo node.")

	main._apply_server_message({
		"type": "world_diff",
		"data": _world_state("tavern", 2),
	})
	await process_frame

	_expect(main.world_data["player"]["current_location"] == "tavern", "Expected player at tavern.")
	var expected_position: Vector2 = main.location_positions["tavern"] + Vector2(-28, -42)
	var actual_position: Vector2 = main.actor_nodes["player"].position
	_expect(actual_position.distance_to(expected_position) < 0.01, "Expected player node to move to tavern.")

	print("Godot client verification passed.")
	quit(0)


func _world_state(player_location: String, cursor: int) -> Dictionary:
	var locations := {
		"square": _location("square", "Square", 420, 240, ["player"] if player_location == "square" else []),
		"tavern": _location("tavern", "Tavern", 170, 150, ["player", "ivo"] if player_location == "tavern" else ["ivo"]),
		"farm": _location("farm", "Farm", 690, 160, ["tomo"]),
		"workshop": _location("workshop", "Workshop", 190, 440, ["mira"]),
		"warehouse": _location("warehouse", "Warehouse", 670, 430, []),
	}
	return {
		"world_id": "demo_world_001",
		"time": "day 1 08:%02d" % cursor,
		"event_log_cursor": cursor,
		"locations": locations,
		"player": {
			"player_id": "player",
			"current_location": player_location,
		},
		"npcs": {
			"mira": _npc("mira", "Mira", "workshop"),
			"tomo": _npc("tomo", "Tomo", "farm"),
			"ivo": _npc("ivo", "Ivo", "tavern"),
		},
		"latest_events": [
			{
				"world_time": "day 1 08:%02d" % cursor,
				"type": "test_event",
			},
		],
	}


func _location(location_id: String, label: String, x: int, y: int, occupants: Array) -> Dictionary:
	return {
		"location_id": location_id,
		"name": label,
		"position": {
			"x": x,
			"y": y,
		},
		"current_occupants": occupants,
	}


func _npc(npc_id: String, label: String, location_id: String) -> Dictionary:
	return {
		"npc_id": npc_id,
		"name": label,
		"current_location": location_id,
		"current_action": "test",
		"current_goal": "test_goal",
		"mood": "neutral",
	}


func _expect(condition: bool, message: String) -> void:
	if not condition:
		_fail(message)


func _fail(message: String) -> void:
	push_error(message)
	quit(1)
