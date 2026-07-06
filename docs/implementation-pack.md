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

Recommended next build order:

1. Implement Godot WASD player controller.
2. Add collision and logical location trigger areas.
3. Add proximity NPC interaction and dialogue UI.
4. Tween NPCs from `actor_movements`.
5. Add HUD presentation and toast display.
6. Add debug overlay for world/Director state.
7. Add persistence after the playable loop feels good.
8. Add LLM texture only after deterministic play remains stable.

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

Do not integrate LLM until the playable loop is stable without it.
