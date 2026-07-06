# Godot Client

This is a Godot 4.x display client for the deterministic MVP world server.

## Runtime Contract

The client expects the backend WebSocket to emit:

- `world_state`
- `world_diff`

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

## Current Verification Note

The project files are ready for Godot 4.x, but this environment did not have a local Godot executable available. Backend protocol compatibility is covered by automated tests; final visual QA should be done by opening `project.godot` in Godot 4.x.
