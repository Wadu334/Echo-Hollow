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

Recommended next build order:

1. Add polished dialogue UI choices.
2. Add visible logical location trigger areas and interaction affordances.
3. Tween NPCs from backend `actor_movements`.
4. Add HUD presentation and toast display.
5. Add debug overlay for world/Director state.
6. Add persistence after the playable loop feels good.
7. Add LLM texture only after deterministic play remains stable.

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

Build the playable Godot client layer:

```text
WASD movement -> trigger logical locations -> interact with NPCs -> dialogue choices -> world_diff/presentation feedback
```

The first WASD/collision/NPC-state slice now exists. Continue with dialogue choices, richer location triggers, and backend-driven NPC tweening. Do not integrate LLM until the playable loop is stable without it.
