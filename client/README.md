# Godot Client

This is the current Godot 4.x display client for the deterministic world server.

## Runtime Contract

The client expects the backend WebSocket to emit:

- `world_state`
- `world_diff`
- `dialogue_opened`
- `dialogue_result`
- `interaction_denied`

The payload fields consumed by `scripts/main.gd` are covered by `backend/tests/test_client_contract.py`.

## Controls

- `1`: Square
- `2`: Tavern
- `3`: Farm
- `4`: Workshop
- `5`: Warehouse

Each key sends:

```json
{
  "type": "move_player",
  "location_id": "tavern"
}
```

## Next Playable Client Contract

The backend now supports the logical messages needed for a Stardew-like client:

- `player_entered_location`
- `player_interact_npc`
- `dialogue_choice`
- `investigate_location`
- `wait_minutes`
- `run_village_step`

Godot should own WASD movement, collision, camera, local coordinates, animation, and NPC tweening. The backend owns logical location, interactions, memory, Director scheduling, and episode state.

## Current Verification Note

Godot headless verification has passed with Godot 4.7 in this environment:

```powershell
godot_console --headless --path client --script res://tests/verify_client.gd
```

Manual visual QA should still be done by opening `project.godot` in Godot 4.x.
