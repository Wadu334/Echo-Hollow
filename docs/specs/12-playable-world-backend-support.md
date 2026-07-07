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
  "line": "Good to see you. I am checking the workshop list before the afternoon.",
  "choices": [
    { "choice_id": "greet", "text": "Greet" },
    { "choice_id": "ask_about_work", "text": "Ask About Work" },
    { "choice_id": "ask_about_village", "text": "Ask About Village" },
    { "choice_id": "goodbye", "text": "Goodbye" }
  ]
}
```

### `dialogue_choice`

Applies deterministic MVP dialogue feedback and may return a `world_diff`.

```json
{ "type": "dialogue_choice", "npc_id": "ivo", "choice_id": "ask_about_village" }
```

Current default v1 dialogue choices are normal conversation topics:

- `greet`
- `ask_about_work`
- `ask_about_village`
- `goodbye`

Missing Seeds-specific choices and Agent-driven follow-up actions are intentionally not the default playable path for v1. They should be layered in after normal NPC conversation feels good.

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
