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

Playable WebSocket commands:

- `player_entered_location`: Godot notifies the backend that the player entered a logical area.
- `player_interact_npc`: opens deterministic NPC dialogue when the player and NPC share a logical location.
- `dialogue_choice`: applies deterministic choice effects and returns a toast plus optional `world_diff`.
- `investigate_location`: logical investigation alias for playable clients.
- `wait_minutes`: advances world time.
- `run_village_step`: asks the VillageDirector/AgentRuntime path to run one autonomous step.

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
`docs/specs/15-playable-world-v2-rumor-handoff.md` for the complete contract.

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
python -m unittest discover -s backend\tests
python backend\scripts\probe_episode.py
python backend\scripts\probe_websocket.py
python backend\scripts\verify_connected_godot.py --godot "<Godot console path>"
```

`probe_websocket.py` expects the backend server to be running;
`probe_episode.py` runs the deterministic simulation in-process. The connected
Godot verification starts and stops its own fresh Uvicorn process.

## Godot Headless Verification

If Godot 4.x is available:

```powershell
godot_console --headless --path client --quit --verbose
godot_console --headless --path client --script res://tests/verify_client.gd
python backend\scripts\verify_connected_godot.py --godot "godot_console"
```

The first command confirms the project and main scene load. The second runs the
offline client display contract. The third runs a real Godot-to-FastAPI
WebSocket check, including authoritative reconciliation and the consequence
scene transition.

## Godot Client

Open `client/project.godot` in Godot 4.x and run the main scene.

Controls:

- `WASD`: move player
- `E`: interact with nearest NPC
- `B`: toggle NPC state bubbles
- `1-5`: jump to logical locations for debugging

The client connects by default to:

```text
ws://127.0.0.1:8000/ws/world/demo_world_001
```

Override the URL with `ECHO_HOLLOW_SERVER_URL`.
