# AI Agent Village Implementation Pack

This pack converts the research PDF into the first actionable implementation stage.

## Document Map

- `specs/00-mvp-stage-plan.md`: scope, milestones, technical direction.
- `specs/01-product-prd.md`: product promise, UX, loop, risks.
- `specs/02-world-simulation-spec.md`: authoritative world model and realtime flow.
- `specs/03-memory-rumor-spec.md`: memory layers, rumor propagation, reflection.
- `specs/04-tool-validator-spec.md`: action tools, validation rules, rejection codes.
- `specs/05-scenario-content-spec.md`: first playable event chain and NPC content.
- `specs/06-ai-invocation-spec.md`: when and how to call LLMs safely.
- `specs/07-development-method-resources.md`: build method, team/resource needs, testing strategy.

## Recommended Build Order

1. Create backend skeleton.
2. Create world state models.
3. Create WebSocket world sync.
4. Create Godot map and player movement.
5. Add NPC schedules.
6. Add dialogue session and event log.
7. Add memory writer and retrieval.
8. Add rumor engine.
9. Add missing seeds scenario.
10. Add LLM calls only after deterministic loop is working.

## Minimal Runtime Resources

### Local Development

- Python 3.11+.
- FastAPI.
- Uvicorn.
- Postgres 16+.
- pgvector.
- Godot stable version.
- OpenAI API key.

### Optional Early Simplification

For the first local prototype, Postgres can be delayed behind repository interfaces and replaced temporarily by SQLite or JSON files. Do this only if the team needs speed. The real architecture should keep Postgres + JSONB + pgvector as the target.

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

Start implementation with the deterministic loop:

```text
world clock -> event log -> WebSocket world_diff -> Godot display
```

Do not integrate LLM until the world can already move time, place NPCs, accept player intents, and record event log entries.
