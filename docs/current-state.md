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

The current Godot client now has a local Playable World v1 baseline:

- `WASD` moves a `CharacterBody2D` player in the village square.
- Player animation changes by facing direction: down, up, left, and right.
- Pixel-cute assets are imported under `client/assets/playable_world_v0/`.
- Major props have simple collision: well, noticeboard, crate, bench, fence, and lamp.
- Mira, Tomo, and Ivo spawn as NPCs with deterministic patrol/idle routines.
- Ivo starts near the player in the Square so the first interaction is immediately discoverable.
- Major locations have in-world labels: Square, Tavern, Farm, Workshop, and Warehouse.
- The tile map uses a central-square path network, small atlas variations, and clipped tile regions to reduce the debug-grid look.
- NPCs show lightweight deterministic state bubbles for mood, memory, rumor, and relationship placeholders.
- `E` opens a dialogue panel with normal conversation topics when the player is close enough.
- Normal v1 dialogue choices are `greet`, `ask_about_work`, `ask_about_village`, and `goodbye`.
- Dialogue choices show a player-facing response and toast.
- `B` toggles state bubbles.
- `F11` toggles fullscreen.
- Number keys `1-5` still jump to logical locations for debugging and backend contract checks.
- Headless verification passes.

The backend is still not a per-frame coordinate server. Godot owns movement, collision, animation, camera, and local visual coordinates. The backend owns logical location, interactions, memory, relationships, rumors, Director scheduling, episode state, and event log.

## Public Contracts

### Dialogue Opened

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
- Godot headless prints `Godot playable client verification passed.`

## Current Limitations

- No database persistence yet.
- No real LLM integration yet.
- Backend does not simulate per-frame coordinates by design.
- Dialogue is deterministic MVP content and still needs a polished choice UI.
- NPC state bubbles currently use deterministic placeholder text until connected to richer memory, rumor, relationship, and Director summaries.
- NPC backend movement diffs are not yet tweened into local paths.

## Recommended Next Goal

Implement Playable World v1 as a normal NPC conversation prototype. See `docs/specs/14-playable-world-v1-goal.md`.

First build:

- Dialogue box and choice UI backed by `dialogue_choice`.
- Normal conversation topics such as greeting, work, village, and goodbye.
- NPC approach prompts and predictable conversation close/re-open behavior.
- Toast and HUD feedback in player-facing language.

Then build:

- Missing Seeds investigation and evidence sharing.
- Agent-driven follow-up actions after conversations.
- NPC visual tweening from backend `actor_movements`.
- Compact memory, rumor, relationship, and Director summaries in NPC bubbles.
- Optional debug overlay for `world_diff`, Director trace, and action queue.
