# Playable World Backend Support v0

## Purpose

This slice prepares Echo Hollow for a Stardew-like Godot client without turning the backend into a per-frame coordinate server.

```text
Godot: WASD, collision, smooth movement, camera, visual NPC tweening
Backend: logical location, interactions, memory, relationships, Director, episode state
```

The backend remains deterministic and does not call an LLM.

## WebSocket Commands

### `player_entered_location`

Godot sends this when the player's local collider enters a logical location area.

```json
{ "type": "player_entered_location", "location_id": "workshop" }
```

The backend reuses `move_player(location_id)` and emits a normal `world_diff`.

### `player_interact_npc`

Opens deterministic dialogue if the player and NPC share the same logical location.

```json
{ "type": "player_interact_npc", "npc_id": "mira", "interaction": "talk" }
```

Invalid interactions return:

```json
{
  "type": "interaction_denied",
  "reason": "not_nearby",
  "display_text": "Mira is not close enough right now."
}
```

Valid interactions return:

```json
{
  "type": "dialogue_opened",
  "npc_id": "mira",
  "speaker": "Mira",
  "line": "Thanks for helping me look for the seed pouch.",
  "choices": [
    { "choice_id": "offer_help", "text": "Offer Help" }
  ]
}
```

### `dialogue_choice`

Applies deterministic MVP effects and may return a `world_diff`.

```json
{ "type": "dialogue_choice", "npc_id": "ivo", "choice_id": "ask_about_cat" }
```

Current effects:

- Mira `offer_help`: writes a warm memory for Mira.
- Tomo `ask_what_he_saw`: adds a player note about the warehouse door.
- Ivo `ask_about_cat`: adds a player note about a cat near the Warehouse.

### Other Playable Commands

- `investigate_location`: logical investigation alias for playable clients.
- `wait_minutes`: advances simulation time.
- `run_village_step`: runs one autonomous village step for an actor.

Existing command types remain supported.

## Actor Movement Diffs

When an NPC logical move action executes, diffs include `actor_movements` so Godot can tween the actor visually.

```json
{
  "actor_movements": [
    {
      "actor_id": "mira",
      "from_location": "workshop",
      "to_location": "farm",
      "duration_seconds": 4.0,
      "display_text": "Mira is heading to the Farm."
    }
  ]
}
```

The backend still changes only logical location. Godot chooses the path, animation, and interpolation.

## Presentation Object

Snapshots and diffs include cozy presentation text:

```json
{
  "presentation": {
    "event_title": "The Missing Seed Pouch",
    "event_phase_text": "Gathering Clues",
    "village_flow_text": "Neighbors are comparing small clues and trying to be fair.",
    "toasts": []
  }
}
```

Internal phase names remain unchanged. Presentation text avoids harsh debug terms and is safe for a player-facing HUD.

## Location Visual Metadata

Location payloads include optional client hints:

```json
{
  "visual_anchor": { "x": 480, "y": 260 },
  "interaction_radius": 96
}
```

Godot can ignore these and keep hand-authored map coordinates if needed.

## Verification

Run:

```powershell
python -m unittest discover -s backend\tests -v
python backend\scripts\probe_episode.py
```

Godot headless verification is still:

```powershell
godot_console --headless --path client --script res://tests/verify_client.gd
```
