# AI Agent Village Implementation Pack

This pack converts the research PDF into actionable implementation stages.

For the current implementation snapshot, start with `current-state.md`.

## Document Map

- `specs/00-mvp-stage-plan.md`: scope, milestones, technical direction.
- `specs/01-product-prd.md`: product promise, UX, loop, risks.
- `specs/02-world-simulation-spec.md`: authoritative world model and realtime flow.
- `specs/03-memory-rumor-spec.md`: memory layers, rumor propagation, reflection.
- `specs/04-tool-validator-spec.md`: action tools, validation rules, rejection codes.
- `specs/05-scenario-content-spec.md`: first playable event chain and NPC content.
- `specs/06-ai-invocation-spec.md`: when and how to call LLMs safely.
- `specs/07-development-method-resources.md`: build method, team/resource needs, testing strategy.
- `specs/08-agent-v0-implementation.md`: deterministic agent loop notes and borrowed agent patterns.
- `specs/10-village-director-v0.md`: Director orchestration, pacing, fallback, and phase boundaries.
- `specs/12-playable-world-backend-support.md`: backend contracts for a future Stardew-like Godot client.
- `specs/13-playable-world-client-v0.md`: Godot WASD movement, imported pixel-cute assets, collision props, NPC routines, and agent state bubbles.
- `specs/14-playable-world-v1-goal.md`: next playable loop goal, UX copy direction, and acceptance criteria.
- `specs/15-playable-world-v2-rumor-handoff.md`: connection-scoped dialogue, authoritative movement reconciliation, rumor handoff, and the visible Mira-to-Tomo consequence.
- `specs/16-playable-world-v2-1-evidence-closure.md`: explicit phase graph, Warehouse contextual evidence, offered-choice reconciliation, terminal integrity, cursor recovery, and acceptance evidence.

## Recommended Build Order

Completed foundation:

1. Backend world skeleton.
2. World state models.
3. WebSocket world sync.
4. Godot display client.
5. NPC schedules.
6. Event log, memory, relationships, rumors, and validators.
7. Missing Seeds episode paths.
8. Deterministic AgentRuntime.
9. VillageDirector orchestration.
10. Playable backend command support.
11. Godot Playable World v0 with local WASD movement, collision props, NPC patrol visuals, and deterministic state bubbles.
12. Playable World v1 ordinary conversation UI and player-facing feedback.
13. Playable World v2 Ivo-to-Mira rumor handoff, stateful choices, backend-authored movement, and visible agent consequence.

Current verified increment:

14. Playable World v2.1 Warehouse evidence closure, irreversible outcomes,
    semantic action validation, server-authored reconciliation presentation,
    and transient connection recovery. The 2026-07-17 automated record passes
    backend, branch-coverage, Godot offline, recovery, and three fresh-server
    connected runs.

Recommended next build order:

1. Complete a visible operator playtest of provenance, contextual prompt
   priority, recovery status, and outcome wording with normal `WASD`/`E`
   controls; the first desktop-control attempt was interrupted.
2. Add a compact optional debug overlay for world, conversation, and Director state.
3. Add persistence after the connected playable loop feels reliable.
4. Add LLM texture only after deterministic play remains stable.

## Minimal Runtime Resources

### Local Development

- Python 3.11+.
- FastAPI.
- Uvicorn.
- Godot stable version.

Current deterministic prototype does not require Postgres, pgvector, or an OpenAI API key.

### Later Persistence Target

Postgres + JSONB + pgvector remain good later targets once persistence and semantic memory retrieval become real requirements.

### Do Not Add Yet

- Voice.
- 3D engine work.
- LangGraph.
- CrewAI.
- Complex multi-agent orchestration platform.
- UGC systems.

## Current External References

- Godot 2D documentation: https://docs.godotengine.org/en/stable/tutorials/2d/index.html
- FastAPI WebSocket documentation: https://fastapi.tiangolo.com/advanced/websockets/
- OpenAI Agents SDK guide: https://developers.openai.com/api/docs/guides/agents
- OpenAI Responses API reference: https://developers.openai.com/api/reference/responses/overview
- PostgreSQL JSON documentation: https://www.postgresql.org/docs/current/datatype-json.html
- pgvector repository: https://github.com/pgvector/pgvector
- Steamworks content survey: https://partner.steamgames.com/doc/gettingstarted/contentsurvey
- AI Town architecture: https://github.com/a16z-infra/ai-town/blob/main/ARCHITECTURE.md
- Generative Agents paper: https://arxiv.org/abs/2304.03442

## Immediate Next Step

Preserve the verified v2.1 evidence and recovery slice:

```text
Ivo rumor -> offered choice -> Mira memory -> validated fallback movement
-> accepted Mira/Tomo talk -> Warehouse contextual clue
-> Mira evidence choice -> terminal reconciliation outcome
-> cursor recovery -> exactly-once visible consequence
```

Use `backend/scripts/verify_connected_godot.py` for a fresh, repeatable
Godot-to-FastAPI run, and use the commands, manual procedure, and final result
record in `specs/16-playable-world-v2-1-evidence-closure.md`. Keep future work
incremental: do not add a general cutscene framework, persistence, or LLM
dialogue until the deterministic connected loop remains stable under long-run,
replay, and transient-disconnect checks.
