# Echo Hollow

Echo Hollow is the first-stage MVP skeleton for a deterministic AI Agent village game.

This repository currently proves the non-LLM foundation:

- server-authoritative world clock
- event log
- five village locations
- player location updates
- three scheduled NPCs
- WebSocket world sync
- Godot 2D playable client with WASD movement, local collision, backend-authored NPC movement, and state bubbles
- connection-scoped, stateful dialogue choices with replay protection
- deterministic Agent v1 loop
- VillageDirector v0 orchestration layer
- memory, relationship, rumor, and validator state
- Ivo rumor -> player claim -> Mira memory -> Agent proposal -> Director fallback -> visible consequence scene
- Playable World v2.1 evidence-closure contract: Warehouse clue -> Mira offered choice -> server-authored reconciliation outcome

LLM dialogue is intentionally not connected yet. The current agent and director loops are deterministic so the gameplay spine can be tested before model integration.

## Agent Architecture

Echo Hollow separates local NPC autonomy from global orchestration:

```text
NPC AgentRuntime -> VillageDirector -> Validator -> WorldSimulation -> EpisodeManager
```

- `AgentRuntimeV1` assembles context and proposes local NPC intent.
- `VillageDirector` approves, skips duplicates, applies pacing budgets, schedules fallback movement, and injects episode beats.
- Validators are the hard legality gate for every tool execution.
- `WorldSimulation` is the only authority that mutates actor locations, memories, relationships, rumors, event logs, and facts.
- `MissingSeedsEpisodeManager` owns scenario phase transitions and final endings.
- Focused Missing Seeds rules own clue availability, terminal guards,
  idempotency, causal-confrontation checks, and resolution compatibility.
- AI/LLM providers are advisory only and are disabled by default.

The Director is not a God Agent. It does not change relationships, write NPC memories, create facts, or resolve events directly. It only schedules validated actions and records compact public traces.

## Project Layout

- `backend/app/`: FastAPI world server.
- `backend/tests/`: deterministic world simulation tests.
- `backend/scripts/probe_websocket.py`: small WebSocket probe.
- `client/`: Godot 4.x client project.
- `docs/`: planning and implementation specs.

## Documentation Map

- `docs/current-state.md`: current implementation snapshot and next recommended goal.
- `docs/implementation-pack.md`: staged build map from research blueprint to implementation.
- `docs/specs/10-village-director-v0.md`: Director orchestration contract.
- `docs/specs/12-playable-world-backend-support.md`: playable backend WebSocket and payload contracts.
- `docs/specs/13-playable-world-client-v0.md`: Godot playable client, imported assets, movement, collision, NPC routines, and state bubbles.
- `docs/specs/14-playable-world-v1-goal.md`: ordinary NPC conversation goal and player-facing UX baseline.
- `docs/specs/15-playable-world-v2-rumor-handoff.md`: stateful rumor handoff, authoritative movement reconciliation, and visible agent consequence.
- `docs/specs/16-playable-world-v2-1-evidence-closure.md`: explicit episode graph, evidence closure, terminal integrity, recovery, and final acceptance evidence.

## Backend Setup

Use Python 3.11+.

```powershell
cd "C:\Echo Hollow"
python -m pip install -r backend\requirements-dev.txt
python -m uvicorn backend.app.main:app --reload
```

The server listens on `http://127.0.0.1:8000`.

Useful endpoints:

- `GET /` live world dashboard
- `GET /health`
- `GET /api/world/demo_world_001`
- `GET /api/world/demo_world_001/events`
- `GET /api/world/demo_world_001/agent`
- `WS /ws/world/demo_world_001`

## Playable World Backend Support

The backend is intentionally not a per-frame coordinate server. Godot owns WASD input, collision, smooth movement, camera feel, and visual coordinates. The backend stays authoritative for logical location, interactions, memory, relationships, Director scheduling, episode state, and event logs.

Normal Godot play uses these WebSocket commands:

- `player_entered_location`: Godot notifies the backend that the player entered a logical area.
- `player_interact_npc`: opens deterministic NPC dialogue when the player and NPC share a logical location.
- `dialogue_choice`: applies deterministic choice effects and returns a toast plus optional `world_diff`.
- `activate_contextual_action`: activates the Warehouse clue currently offered
  by authoritative presentation state; the client supplies no evidence or
  recipient id.
- `ack_presentation`: acknowledges an exactly-once consequence after it is shown.

Dashboard buttons, direct simulation calls, `wait_minutes`, `run_village_step`,
raw `investigate_location`, and arbitrary `player_share_evidence` payloads are
debug or regression surfaces. They do **not** count as proof that the normal
Godot path is playable.

Dialogue responses now carry a connection-owned conversation and offered-choice
version:

```json
{
  "type": "dialogue_opened",
  "conversation_id": "conv_...",
  "offer_version": 1,
  "npc_id": "mira",
  "speaker": "Mira",
  "line": "Thanks for helping me look for the seed pouch.",
  "choices": [
    { "choice_id": "offer_help", "text": "Offer Help" }
  ]
}
```

Choice submissions must echo `conversation_id`, `offer_version`, and
`choice_id`. The server rejects stale, replayed, cross-session, or unoffered
choices without mutating the world. See
`docs/specs/15-playable-world-v2-rumor-handoff.md` for the conversation contract
and `docs/specs/16-playable-world-v2-1-evidence-closure.md` for the evidence
choice and terminal-outcome contract.

World diffs may include:

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
  ],
  "presentation": {
    "event_title": "The Missing Seed Pouch",
    "event_phase_text": "Gathering Clues",
    "village_flow_text": "Neighbors are comparing small clues and trying to be fair.",
    "objective": "Check the Warehouse",
    "toasts": []
  }
}
```

The Godot client retains offline visual-test support. While connected, the
backend is the only authority for player and NPC logical locations; Godot sends
movement intent and owns only local pixels, collision, animation, tweening, and
presentation. A persistent `WorldConnection` Autoload keeps the socket alive
through the rumor-consequence scene. The number keys remain debug helpers for
logical location checks. See `docs/current-state.md` for the current capability
map.

For v2.1, `WorldConnection` retains its last consumed event cursor across an
unexpected transport loss, reconnects with capped exponential backoff, requests
events after that cursor in ordered pages of at most 500 entries, and then
applies a full authoritative snapshot. Each recovery page carries
`from_cursor`, `to_cursor`, and `has_more`; the client becomes `Online` only
when the consumed cursor exactly matches the snapshot cursor. A persistent
presenter deduplicates pending consequences by `presentation_id`, so the
reconciliation scene is neither lost nor shown twice after recovery.

The dashboard includes Agent Tool buttons. For example, move the player to Workshop, then use `Tell Mira: Tomo rumor` to trigger:

```text
player claim -> Mira memory -> AgentRuntime proposal -> VillageDirector approval -> action queue -> validator -> event log
```

Director state is visible in world snapshots and the agent endpoint:

```text
last_director_trace
director_state
```

## Backend Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v

.\.venv\Scripts\python.exe -m coverage erase
.\.venv\Scripts\python.exe -m coverage run --branch --source=backend.app `
  -m unittest discover -s backend\tests -v
.\.venv\Scripts\python.exe -m coverage report --show-missing
```

Coverage is branch-aware because the new Missing Seeds rejection and no-op
branches are part of the acceptance contract. Do not infer v2.1 completion from
the previous 67-test baseline alone. The final v2.1 run passes 89 tests with
80% total branch coverage; `missing_seeds.py` is 95%, `protocol.py` is 98%,
`director.py` is 86%, `world.py` is 83%, and `episode.py` is 82%.

## Godot Headless Verification

If Godot 4.x is available:

```powershell
godot_console --headless --path client --quit --verbose
godot_console --headless --path client --script res://tests/verify_client.gd
.\.venv\Scripts\python.exe backend\scripts\verify_connected_godot.py `
  --godot "godot_console"
```

The first command confirms the project and main scene load. The second runs the
offline client display contract. The third runs a real Godot-to-FastAPI
WebSocket check, including authoritative reconciliation and the consequence
scene transition. The final v2.1 connected scenario also completes the
Warehouse evidence path, catches up the named `torn_seed_bag` evidence event
after a transient disconnect, and proves each presentation scene enters once.

Fresh-world repeatability requires three independent harness processes:

```powershell
.\.venv\Scripts\python.exe backend\scripts\verify_connected_godot.py `
  --godot "godot_console" --runs 3 --godot-timeout 120
```

The harness starts and stops a new Uvicorn process for every run. The final
2026-07-17 record passed all three fresh servers; details are in
`docs/specs/16-playable-world-v2-1-evidence-closure.md`.

## Godot Client

Open `client/project.godot` in Godot 4.x and run the main scene.

Controls:

- `WASD`: move player
- `E`: interact with the clearly named nearby NPC or current contextual clue
- `B`: toggle NPC state bubbles
- `1-5`: jump to logical locations only when
  `ECHO_HOLLOW_DEBUG_CONTROLS=1`

The client connects by default to:

```text
ws://127.0.0.1:8000/ws/world/demo_world_001
```

Override the URL with `ECHO_HOLLOW_SERVER_URL`.

The no-debug acceptance path is:

```text
Ask Ivo -> Tell Mira -> Check the Warehouse
-> Show Mira the evidence -> Observe the outcome
```

Use only `WASD`, `E`, and server-provided choices. Do not use the dashboard,
number-key jumps, or raw WebSocket commands. The complete manual procedure and
final automated verification record are in
`docs/specs/16-playable-world-v2-1-evidence-closure.md`.
