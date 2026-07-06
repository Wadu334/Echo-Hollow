# Project Guidance

## Agent Architecture Rules

- Do not let an LLM or the VillageDirector mutate world state directly.
- All world changes must go through validated tools.
- `AgentRuntimeV1` proposes local NPC intent.
- `VillageDirector` schedules, skips duplicates, applies budgets, and plans fallback actions.
- Validators approve or reject queued tools at execution time.
- `WorldSimulation` executes accepted tools and owns authoritative state mutation.
- `MissingSeedsEpisodeManager` owns scenario phase changes and endings.
- Tests must not require network access or API keys.
- Keep deterministic behavior as the default.

## Development Rules

- Inspect the active call path before changing behavior.
- Keep changes focused and incremental.
- Avoid circular imports; use dataclasses and JSON-safe `to_dict()` payloads for shared traces.
- Preserve FastAPI, WebSocket, dashboard, and Godot client compatibility unless a task explicitly asks otherwise.
- Run focused backend tests after changing simulation, Director, or agent code.
