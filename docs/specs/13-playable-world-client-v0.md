# Playable World Client v0

## Purpose

This slice turns the Godot client from a location-debug display into a small local playable village scene.

```text
Godot: WASD, collision, sprite animation, local NPC routine visuals, state bubbles
Backend: logical location, dialogue, memory, rumor, relationship, Director, episode state
```

No LLM call is required for this milestone.

## Imported Assets

Finalized pixel-cute assets are copied under:

```text
client/assets/playable_world_v0/
```

Sprite sheets:

- `sprites/player_walk_4dir_4frame.png`
- `sprites/mira_walk_4dir_4frame.png`
- `sprites/tomo_walk_4dir_4frame.png`
- `sprites/ivo_walk_4dir_4frame.png`

Map and prop assets:

- `tiles/ground_path_tileset_48.png`
- `props/collision_props.png`

Source moodboard assets remain under `moodboards/` and are not referenced by runtime code.

## Sprite Sheet Layout

Each character sheet is:

- `512x512`
- transparent PNG
- `4 columns x 4 rows`
- `128x128` per cell

Rows are fixed:

1. `down`
2. `up`
3. `left`
4. `right`

Columns are walk frames `0-3`. Idle currently uses frame `0` for the current facing direction.

## Controls

- `WASD`: local player movement.
- `E`: interact with the nearest NPC if close enough.
- `B`: toggle deterministic agent state bubbles.
- `1-5`: jump to logical locations for debug and backend contract checks.

## Local World Rules

Godot owns the local play feel:

- `CharacterBody2D` player movement.
- Directional walking animation.
- Camera follow.
- Collision against major props.
- Hand-authored local coordinates.
- Simple deterministic NPC patrol loops.
- Lightweight NPC state bubbles for mood, memory, rumor, and relationship placeholders.

The current collision props are:

- well
- noticeboard
- crate
- bench
- fence
- lamp

## Backend Integration Points

The playable client keeps the backend boundary from `12-playable-world-backend-support.md`.

When the player enters a logical area, Godot sends:

```json
{ "type": "player_entered_location", "location_id": "workshop" }
```

When the player interacts with an NPC, Godot sends:

```json
{ "type": "player_interact_npc", "npc_id": "mira", "interaction": "talk" }
```

The backend may respond with:

- `world_state`
- `world_diff`
- `dialogue_opened`
- `interaction_denied`

`VillageDirector` remains deterministic and global. It can schedule logical NPC actions and expose traces, but it does not mutate per-frame visual coordinates.

## Verification

Run:

```powershell
Godot_v4.7-stable_win64_console.exe --headless --path client --script res://tests/verify_client.gd
```

The verification checks:

- main scene loads;
- player, Mira, Tomo, and Ivo spawn as `CharacterBody2D`;
- sprite textures are loaded from runtime PNG assets;
- collision props exist;
- the player collision probe hits the well;
- agent state bubbles can be hidden and shown;
- directional animation rows switch correctly;
- server state can still merge into the client state.

## Known Next Steps

- Add proper dialogue UI choices.
- Add location trigger areas with visual debug toggles.
- Tween NPCs from backend `actor_movements`.
- Add a compact presentation/toast HUD.
- Replace placeholder bubble text with real memory, rumor, relationship, and Director trace summaries.
