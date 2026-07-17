# Echo Hollow Current State

## One-Line Summary

Echo Hollow is now a deterministic AI-native village prototype with a FastAPI
world server, a connected Godot client, stateful NPC dialogue, and one visible
rumor-to-agent consequence path. Playable World v2.1 extends that slice through
Warehouse evidence, a server-offered Mira reconciliation choice, terminal
outcome integrity, and recoverable presentation delivery.

No real LLM/API call is required for the current demo.

## Acceptance Status

The Playable World v2 baseline is established. The final v2.1 automated record
passes backend regressions, branch coverage, Godot offline checks, the full
connected evidence path, transient recovery, and three fresh-server runs. A
visible manual operator pass was attempted but stopped when desktop control was
cancelled; the reproducible connected harness still exercises the no-debug
`E`/`Escape`/`WASD` path. The authoritative checklist is
`specs/16-playable-world-v2-1-evidence-closure.md`.

## Current Architecture

```text
Godot Client
  -> WorldConnection Autoload
  -> strict WebSocket commands
  -> WorldSimulation
  -> focused Missing Seeds rules/service
  -> AgentRuntimeV1 proposal
  -> VillageDirector scheduling
  -> Validator legality gate
  -> WorldSimulation execution
  -> MissingSeedsEpisodeManager phase/resolution
  -> world_diff / dialogue payload / pending presentation
  -> WorldPresenter / Godot UI
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
- Focused Missing Seeds rules own clue availability, terminal guards,
  idempotency, confrontation causality, and execution-time semantic checks.
- `WorldPresenter` owns contextual prompt and consequence delivery state so
  recovery and outcome logic do not accumulate in `main.gd`.
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

The normal v2.1 Godot path is:

- Ivo gives the player a sourced Tomo seed-pouch claim.
- The player hands that claim to Mira through a stateful dialogue choice.
- Mira receives memory and AgentRuntime proposes a follow-up.
- Rejected remote NPC talk creates Director fallback movement plus retry.
- Mira's accepted retry with Tomo opens a visible consequence scene in Godot.
- Presentation directs the player to the Warehouse.
- `E` activates the concrete clue only while it is authoritatively offered.
- The first discovery writes structured torn-bag evidence with Warehouse
  provenance; repeats are stable no-ops or rejections.
- Mira alone offers the evidence choice after all server preconditions hold.
- The choice debunks the rumor and resolves the episode once.
- The server-authored outcome carries reaction, relationship trend, and
  reflection text for Godot presentation.

The Missing Seeds phase graph is explicit and every `resolved_*` phase is
terminal. Resolution cancels or invalidates incompatible queued, fallback, and
retry actions. A debunked rumor cannot gain holders, confidence, or spread; the
same causal claim cannot create a second Mira/Tomo confrontation.

The backend may still expose dashboard or direct-call investigation and
evidence helpers for diagnosis. Those helpers are not the normal Godot route
and do not satisfy playable acceptance.

### Playable Backend Support

The normal Godot command surface includes:

- `player_entered_location`
- `player_interact_npc`
- `dialogue_choice`
- `activate_contextual_action`
- `ack_presentation`

`investigate_location`, `player_share_evidence`, `wait_minutes`,
`run_village_step`, dashboard actions, and direct simulation methods are debug
or regression surfaces. Godot does not use them to choose an arbitrary evidence
id, location, or recipient.

Snapshots and diffs include:

- `presentation`
- `presentation.objective`
- `presentation.contextual_action`
- `pending_presentations`
- `actor_movements`
- location `visual_anchor`
- location `interaction_radius`

## Client State

The Godot client keeps the Playable World v2 connected baseline and adds the
v2.1 presentation/recovery boundary:

- `WorldConnection` owns one WebSocket across scene changes and caches the latest authoritative state.
- `ECHO_HOLLOW_SERVER_URL` overrides the default local world socket.
- The main scene still supports offline visual and headless checks without opening a socket.
- While connected, local area crossing sends intent; only a backend state or diff commits logical location.
- NPC local patrol stops after connection and backend-authored location changes are tweened from `actor_movements`.
- Missing or contradictory movement metadata falls back to an authoritative snap.
- Rejected player movement snaps the player back to the backend location.
- Dialogue UI stores `conversation_id` and `offer_version` and submits only currently offered choices.
- `E` resolves one clearly named target: a nearby NPC or the current
  server-offered contextual clue.
- `event_title`, `event_phase_text`, `village_flow_text`, and `objective` are
  rendered from backend presentation state.
- Grouped memories are counted per owner in NPC bubbles; the connected test must
  prove Mira's visible count changes after the claim handoff.
- Player-facing relationships use qualitative trend text; exact values remain
  in debug state.
- A server-authored pending presentation, not a bare dialogue event, triggers a
  real change to `rumor_consequence.tscn`.
- Consequence scenes consume normalized server outcome payloads instead of
  rebuilding every beat from hard-coded phase branches.
- Returning to the main scene reapplies the latest cached world state.
- Unexpected disconnects show `Reconnecting`, retry with capped exponential
  backoff, retain the last event cursor, request ordered 500-event recovery
  pages after that cursor, and then apply a full snapshot only after the
  recovered cursor exactly reaches the snapshot cursor.
- Pending presentations are deduplicated and acknowledged by
  `presentation_id`, providing exactly-once visible delivery across live and
  recovered messages.
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
    "objective": "Check the Warehouse",
    "contextual_action": {
      "action_id": "inspect_torn_seed_bag_clue",
      "offer_version": 1,
      "location_id": "warehouse",
      "prompt": "Press E to inspect the torn seed bag near the warehouse shelves."
    },
    "toasts": []
  }
}
```

### Contextual Action

```json
{
  "type": "activate_contextual_action",
  "action_id": "inspect_torn_seed_bag_clue",
  "offer_version": 1
}
```

The server rechecks authoritative location, phase, availability, and version.
The client supplies no evidence, fact, or recipient id.

### Outcome Presentation

```json
{
  "presentation_id": "present_...",
  "type": "reconciliation_consequence",
  "path": "reconciled",
  "title": "The Rumor Is Put Right",
  "line": "Mira tells Tomo the torn bag changes what everyone thought happened.",
  "reaction_text": "Tomo looks relieved, though the accusation still stings.",
  "relationship_trend_text": "Tomo and Mira are beginning to rebuild trust.",
  "reflection_text": "Mira resolves to check evidence before repeating a claim."
}
```

### Reconnect Recovery

The client reconnects with `after_cursor=<last_consumed_event_cursor>`. The
server sends ordered `recovery_events` pages before `world_state`. Every page
contains `from_cursor`, `to_cursor`, `has_more`, and at most 500 events. The
client accumulates pages without skipping its cursor and remains `Reconnecting`
unless its consumed cursor exactly equals the following snapshot cursor.
Repeated live, recovered, and pending copies converge on one visible
consequence because the presenter deduplicates by `presentation_id`.

## Verification

Run the following against the final worktree:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v

.\.venv\Scripts\python.exe -m coverage erase
.\.venv\Scripts\python.exe -m coverage run --branch --source=backend.app `
  -m unittest discover -s backend\tests -v
.\.venv\Scripts\python.exe -m coverage report --show-missing

Godot_v4.7-stable_win64_console.exe --headless --path client `
  --script res://tests/verify_client.gd

.\.venv\Scripts\python.exe backend\scripts\verify_connected_godot.py `
  --godot "<Godot console path>" --runs 3 --godot-timeout 120
```

Required evidence:

- previous 67 backend tests remain green and all v2.1 integrity regressions pass;
- branch coverage reports the new rules and failure branches;
- offline Godot verifies contextual prompt, presentation, objective sequence,
  grouped-memory bubble, connection state, and outcome UI;
- connected Godot completes the full Warehouse reconciliation path;
- a connected transient-disconnect test proves cursor catch-up,
  authoritative resync, and exactly-once consequence delivery;
- the full connected acceptance passes from a fresh server three times.

Current automated record (2026-07-17): **Pass.** All 89 backend tests pass,
total branch coverage is 80% (`missing_seeds.py` 95%), offline Godot reports
`Godot playable client verification passed.`, and three independent connected
servers report `Godot connected client verification passed.` The manual
no-debug procedure and the interrupted visible-operator note are recorded in
`specs/16-playable-world-v2-1-evidence-closure.md`.

## Current Limitations

- No database persistence yet.
- No real LLM integration yet.
- Backend does not simulate per-frame coordinates by design.
- Dialogue and consequence content remain deterministic MVP templates.
- Actor movement uses location-anchor tweening, not pathfinding.
- The presenter is reusable for this slice but is not a general cutscene engine.
- The current connection model is one player/world and has no multiplayer controller lease.
- No save exists; recovery covers a transient WebSocket loss while the server
  process and in-memory world remain alive, not a server restart.

## Completion Gate

Do not start persistence, multiplayer, or LLM dialogue work until the v2.1
record shows the complete no-debug evidence path, terminal long-run stability,
transient recovery, coverage, and three independent fresh-server passes. See
`specs/16-playable-world-v2-1-evidence-closure.md`.
