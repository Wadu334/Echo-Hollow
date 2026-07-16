# Echo Hollow Current State

## One-Line Summary

Echo Hollow is now a deterministic AI-native village prototype with a FastAPI
world server, a connected Godot client, stateful NPC dialogue, and one visible
rumor-to-agent consequence path.

No real LLM/API call is required for the current demo.

## Current Architecture

```text
Godot Client
  -> WorldConnection Autoload
  -> strict WebSocket commands
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
- While connected, the backend owns the player's and NPCs' logical locations.
- Godot sends location intent and reconciles pixels from authoritative snapshots, diffs, and `actor_movements`.
- Backend owns NPC interactions, conversation sessions, offered choices, memory, relationships, rumors, action queue, Director scheduling, episode state, and event log.
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
- Strict WebSocket command parsing with recoverable `client_error` responses.
- Connection-scoped `client_session_id`.
- WebSocket `world_state` and `world_diff` sync.
- Dashboard at `GET /`.

### Stateful Dialogue

- One open conversation per connected client.
- Server-generated choices derived from current world state.
- `conversation_id` and monotonic `offer_version` on every choice.
- Stable rejection of cross-session, closed, stale, replayed, and unoffered choices.
- Ivo offers the sourced Tomo claim once; Mira offers the handoff only while it remains actionable.
- Moving the player or conversation NPC invalidates the affected conversation.

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

- Ivo gives the player a sourced Tomo seed-pouch claim.
- The player hands that claim to Mira through a stateful dialogue choice.
- Mira receives memory and AgentRuntime proposes a follow-up.
- Rejected remote NPC talk creates Director fallback movement plus retry.
- Mira's accepted retry with Tomo opens a visible consequence scene in Godot.
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

The Godot client now has a Playable World v2 connected baseline:

- `WorldConnection` owns one WebSocket across scene changes and caches the latest authoritative state.
- `ECHO_HOLLOW_SERVER_URL` overrides the default local world socket.
- The main scene still supports offline visual and headless checks without opening a socket.
- While connected, local area crossing sends intent; only a backend state or diff commits logical location.
- NPC local patrol stops after connection and backend-authored location changes are tweened from `actor_movements`.
- Missing or contradictory movement metadata falls back to an authoritative snap.
- Rejected player movement snaps the player back to the backend location.
- Dialogue UI stores `conversation_id` and `offer_version` and submits only currently offered choices.
- The Mira-to-Tomo `npc_dialogue_started` event triggers a real change to `rumor_consequence.tscn`.
- The consequence scene reuses the persistent connection and shows the server-authored line, Tomo mood, and relationship summary.
- Returning to the main scene reapplies the latest cached world state.
- Existing WASD, collision, animation, camera, approach prompt, toast, bubbles, fullscreen, and debug location controls remain.

The backend remains a logical simulation, not a per-frame coordinate server.
Godot owns play feel and presentation; connected logical state always
reconciles to the backend.

## Public Contracts

### Dialogue Opened

```json
{
  "type": "dialogue_opened",
  "conversation_id": "conv_000001",
  "offer_version": 1,
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

### Dialogue Choice

```json
{
  "type": "dialogue_choice",
  "conversation_id": "conv_000001",
  "offer_version": 1,
  "choice_id": "share_ivo_claim"
}
```

### Dialogue Rejected

```json
{
  "type": "dialogue_rejected",
  "reason": "stale_offer",
  "conversation_id": "conv_000001",
  "offer_version": 2,
  "display_text": "Those dialogue choices are no longer current."
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
python backend\scripts\verify_connected_godot.py --godot "<Godot console path>"
```

Expected current result:

- backend tests pass
- `probe_episode.py` reaches `resolved_reconciled`
- Godot headless prints `Godot playable client verification passed.`
- connected verification prints `Godot connected client verification passed.`
- the harness exits after terminating its temporary Uvicorn process

## Current Limitations

- No database persistence yet.
- No real LLM integration yet.
- Backend does not simulate per-frame coordinates by design.
- Dialogue and consequence content remain deterministic MVP templates.
- Actor movement uses location-anchor tweening, not pathfinding.
- The consequence scene is specific to the Mira/Tomo rumor path, not a general cutscene engine.
- The current connection model is one player/world and has no multiplayer controller lease.

## Recommended Next Goal

Stabilize Playable World v2 before broadening content:

- playtest the Ivo-to-Mira handoff for clarity without debug knowledge
- make movement tween timing and rejection feedback feel natural
- expose compact provenance wording in the consequence scene
- preserve deterministic replay and strict offered-choice validation

Do not add persistence or LLM dialogue until this connected vertical slice
remains reliable under repeated runs. See
`docs/specs/15-playable-world-v2-rumor-handoff.md`.
