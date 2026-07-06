# Echo Hollow Current State

## One-Line Summary

Echo Hollow is now a deterministic AI-native village prototype with a FastAPI world server, VillageDirector orchestration, a Missing Seeds episode loop, and backend support for a future Stardew-like Godot client.

No real LLM/API call is required for the current demo.

## Current Architecture

```text
Godot Client
  -> WebSocket commands
  -> WorldSimulation
  -> AgentRuntimeV1 proposal
  -> VillageDirector scheduling
  -> Validator legality gate
  -> WorldSimulation execution
  -> MissingSeedsEpisodeManager phase/resolution
  -> world_diff / dialogue payload / presentation text
```

### Responsibility Boundaries

- Godot owns WASD input, collision, camera, smooth movement, animation, and local visual coordinates.
- Backend owns logical location, NPC interactions, memory, relationships, rumors, action queue, Director scheduling, episode state, and event log.
- `AgentRuntimeV1` proposes local NPC intent and does not mutate world state in `propose_step`.
- `VillageDirector` approves, skips duplicates, applies pacing budgets, plans fallback movement, and injects episode beats.
- Validators are the hard legality gate before tool execution.
- `WorldSimulation` is the only authority that executes accepted world mutations.
- `MissingSeedsEpisodeManager` owns phase transitions and endings.
- AI providers remain advisory and deterministic by default.

## Implemented Capabilities

### Deterministic Village Core

- Server-authoritative world clock.
- Five logical locations.
- Three scheduled NPCs.
- Event log, memory, relationship, and rumor state.
- WebSocket `world_state` and `world_diff` sync.
- Dashboard at `GET /`.

### Agent And Director

- Agent context assembly and proposal-only runtime.
- Action queue with validation-time execution.
- Director approval, duplicate skipping, social/gossip pacing, fallback planning, and Missing Seeds episode beat injection.
- Public traces:
  - `last_agent_trace`
  - `last_director_trace`
  - `director_state`

### Missing Seeds Episode

Current episode paths include:

- Player shares a Tomo seed-pouch claim with Mira.
- Mira receives memory and Director schedules follow-up.
- Rejected NPC talk can create fallback movement plus retry.
- Player can find torn seed bag evidence.
- Player can share evidence with Mira.
- Episode can resolve into reconciliation or misunderstanding paths.
- Reflection memory can alter Mira's future handling.

### Playable Backend Support

The backend now supports the logical commands needed by a future playable 2D client:

- `player_entered_location`
- `player_interact_npc`
- `dialogue_choice`
- `investigate_location`
- `wait_minutes`
- `run_village_step`

Snapshots and diffs include:

- `presentation`
- `actor_movements`
- location `visual_anchor`
- location `interaction_radius`

## Client State

The current Godot client is still a simple display client:

- number keys `1-5` move the player between logical locations
- actors are drawn at location anchors
- side panel shows episode/action/relationship information
- headless verification passes

The backend is ready for the next client pass, but WASD movement, collision, camera follow, NPC tweening, dialogue box UI, HUD, and debug overlay still need to be implemented in Godot.

## Public Contracts

### Dialogue Opened

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

### Interaction Denied

```json
{
  "type": "interaction_denied",
  "reason": "not_nearby",
  "display_text": "Mira is not close enough right now."
}
```

### Actor Movement Diff

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

### Presentation

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

## Verification

Current verification commands:

```powershell
python -m unittest discover -s backend\tests -v
python backend\scripts\probe_episode.py
godot_console --headless --path client --script res://tests/verify_client.gd
```

Expected current result:

- backend tests pass
- `probe_episode.py` reaches `resolved_reconciled`
- Godot headless prints `Godot client verification passed.`

## Current Limitations

- No database persistence yet.
- No real LLM integration yet.
- Godot client does not yet have WASD movement or collision.
- Backend does not simulate per-frame coordinates by design.
- Dialogue is deterministic MVP content.
- Visual assets are placeholders.

## Recommended Next Goal

Implement Godot Playable Client v0:

- WASD `CharacterBody2D` player movement.
- Collision and location trigger areas.
- Send `player_entered_location` when entering logical regions.
- Proximity interaction key for NPCs.
- Dialogue box and choice UI.
- Tween NPCs from `actor_movements`.
- HUD for `presentation` and toasts.
- Debug overlay for `world_diff`, Director trace, and action queue.
