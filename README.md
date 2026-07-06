# Echo Hollow

Echo Hollow is the first-stage MVP skeleton for a deterministic AI Agent village game.

This repository currently proves the non-LLM foundation:

- server-authoritative world clock
- event log
- five village locations
- player location updates
- three scheduled NPCs
- WebSocket world sync
- Godot 2D display project
- deterministic Agent v0 loop
- memory, relationship, rumor, and validator state
- missing-seeds claim -> memory -> agent trace -> relationship consequence

LLM dialogue is intentionally not connected yet. The current agent loop is deterministic so the gameplay spine can be tested before model integration.

## Project Layout

- `backend/app/`: FastAPI world server.
- `backend/tests/`: deterministic world simulation tests.
- `backend/scripts/probe_websocket.py`: small WebSocket probe.
- `client/`: Godot 4.x client project.
- `docs/`: planning and implementation specs.

## Backend Setup

Use Python 3.11+.

```powershell
cd "C:\Users\guoxi\Documents\Echo Hollow"
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

The dashboard includes Agent Tool buttons. For example, move the player to Workshop, then use `Tell Mira: Tomo rumor` to trigger:

```text
player claim -> Mira memory -> AgentLoop context -> tool proposal -> validator -> relationship change -> event log
```

## Backend Verification

```powershell
python -m unittest discover -s backend\tests
python backend\scripts\probe_websocket.py
```

The probe expects the backend server to be running.

## Godot Headless Verification

If Godot 4.x is available:

```powershell
godot_console --headless --path client --quit --verbose
godot_console --headless --path client --script res://tests/verify_client.gd
```

The first command confirms the project and main scene load. The second command runs a small client display contract test inside Godot.

## Godot Client

Open `client/project.godot` in Godot 4.x and run the main scene.

Controls:

- `1`: move player to Square
- `2`: move player to Tavern
- `3`: move player to Farm
- `4`: move player to Workshop
- `5`: move player to Warehouse

The client connects to:

```text
ws://127.0.0.1:8000/ws/world/demo_world_001
```
