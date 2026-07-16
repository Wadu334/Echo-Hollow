# Godot Client

This is the current Godot 4.x playable client for Echo Hollow.

## Current Slice

Playable World v2 keeps the local playable scene and adds a connected vertical
slice with:

- WASD player movement.
- 4-direction player walking animation.
- camera follow.
- village tile/prop art with location labels and a central path network.
- simple collision for major props.
- Mira, Tomo, and Ivo as deterministic NPCs while offline.
- Ivo starts near the player as the first talkable NPC.
- server-generated dialogue choices with conversation and offer tokens.
- toast feedback after dialogue choices.
- lightweight agent state bubbles above NPCs.
- backend-authored NPC movement reconciliation while connected.
- a standalone Mira/Tomo rumor-consequence scene.

The client can run without the backend. `WorldConnection` owns the persistent
WebSocket when the main scene calls `ensure_connected()`. The default URL is:

```text
ws://127.0.0.1:8000/ws/world/demo_world_001
```

Override it with `ECHO_HOLLOW_SERVER_URL`.

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
- `dialogue_rejected`
- `interaction_denied`
- `client_error`

While connected, the backend is authoritative for player and NPC logical
locations. Godot owns local movement, collision, animation, tweening, camera,
scene changes, and visual coordinates.

When connected, the playable client sends:

```json
{ "type": "player_entered_location", "location_id": "workshop" }
```

and:

```json
{ "type": "player_interact_npc", "npc_id": "mira", "interaction": "talk" }
```

Dialogue choices echo the server offer:

```json
{
  "type": "dialogue_choice",
  "conversation_id": "conv_000001",
  "offer_version": 1,
  "choice_id": "share_ivo_claim"
}
```

## Verification

```powershell
Godot_v4.7-stable_win64_console.exe --headless --path client --script res://tests/verify_client.gd
.\.venv\Scripts\python.exe backend\scripts\verify_connected_godot.py `
  --godot "C:\path\to\Godot_v4.7-stable_win64_console.exe"
```

Expected output:

```text
Godot playable client verification passed.
Godot connected client verification passed.
```
