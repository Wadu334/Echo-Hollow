# Godot Client

This is the current Godot 4.x playable client for Echo Hollow.

## Current Slice

Playable World v1 baseline is a local Godot scene with:

- WASD player movement.
- 4-direction player walking animation.
- camera follow.
- village tile/prop art with location labels and a central path network.
- simple collision for major props.
- Mira, Tomo, and Ivo as deterministic NPCs.
- Ivo starts near the player as the first talkable NPC.
- a dialogue panel for normal NPC conversation choices.
- toast feedback after dialogue choices.
- lightweight agent state bubbles above NPCs.

The client can run without the backend. When the backend server is available, it also connects to:

```text
ws://127.0.0.1:8000/ws/world/demo_world_001
```

## Controls

- `WASD`: move player.
- `E`: talk to the nearest NPC.
- `B`: toggle NPC state bubbles.
- `F11`: toggle fullscreen.
- `1`: jump to Square.
- `2`: jump to Tavern.
- `3`: jump to Farm.
- `4`: jump to Workshop.
- `5`: jump to Warehouse.

Number keys are debug helpers for logical location and backend contract checks. Normal play should use WASD.

## Asset Contract

Runtime assets live under:

```text
res://assets/playable_world_v0/
```

Sprite sheets:

- `sprites/player_walk_4dir_4frame.png`
- `sprites/mira_walk_4dir_4frame.png`
- `sprites/tomo_walk_4dir_4frame.png`
- `sprites/ivo_walk_4dir_4frame.png`

Each character sheet is `512x512`, transparent PNG, `4 columns x 4 rows`, with `128x128` cells.

Rows:

1. `down`
2. `up`
3. `left`
4. `right`

Map and prop assets:

- `tiles/ground_path_tileset_48.png`
- `props/collision_props.png`

## Runtime Contract

The client can consume backend WebSocket messages:

- `world_state`
- `world_diff`
- `dialogue_opened`
- `dialogue_result`
- `interaction_denied`

The backend stays authoritative for logical state. Godot owns local movement, collision, animation, camera, and visual coordinates.

When connected, the playable client sends:

```json
{ "type": "player_entered_location", "location_id": "workshop" }
```

and:

```json
{ "type": "player_interact_npc", "npc_id": "mira", "interaction": "talk" }
```

## Verification

```powershell
Godot_v4.7-stable_win64_console.exe --headless --path client --script res://tests/verify_client.gd
```

Expected output:

```text
Godot playable client verification passed.
```
