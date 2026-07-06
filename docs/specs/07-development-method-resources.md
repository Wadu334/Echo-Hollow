# Development Method And Resources

## 1. Development Method

Use vertical-slice development.

The first slice should prove:

```text
player input -> event log -> memory write -> NPC reaction -> visible consequence
```

Do not start with broad agent infrastructure. Start with the smallest deterministic game loop that can later accept AI proposals.

## 2. Build Order

### Phase 1: Deterministic World

- Backend app skeleton.
- World clock.
- Event log.
- Static locations.
- Player intents.
- WebSocket state sync.

Exit criteria:

- Client receives world time and location state from server.

### Phase 2: NPC Runtime

- NPC definitions.
- Schedules.
- Location transitions.
- Basic relationship state.
- Debug panel.

Exit criteria:

- NPCs act without LLM.

### Phase 3: Interaction And Memory

- Player-to-NPC dialogue shell.
- Memory writer.
- Memory retrieval.
- Social memory updates.

Exit criteria:

- A player statement is stored and affects later dialogue context.

### Phase 4: Rumor And Event Chain

- Rumor propagation.
- Evidence facts.
- Missing seeds phase machine.
- Three resolution paths.

Exit criteria:

- Information spreads and changes the event outcome.

### Phase 5: AI Enhancement

- Add LLM dialogue.
- Add structured action proposals.
- Add async summaries and reflections.
- Add safety and fallback.

Exit criteria:

- LLM improves texture, but the scenario remains playable without it.

## 3. Team Roles

### Minimum Solo-Friendly Setup

One full-stack developer can build the MVP if using placeholder art and simple UI.

Required competencies:

- Python backend.
- Realtime WebSocket basics.
- Godot 2D basics.
- LLM API integration.
- Game systems thinking.

### Small Team Setup

Recommended:

- 1 backend/AI engineer.
- 1 Godot/client engineer.
- 1 systems/narrative designer.
- 1 part-time UI or pixel artist.

## 4. Software Resources

### Required

- Godot stable version.
- Python 3.11+.
- FastAPI.
- Uvicorn.
- Postgres.
- pgvector.
- OpenAI API access.
- Git.

### Recommended Dev Libraries

- Pydantic for data contracts.
- SQLAlchemy or SQLModel for persistence.
- Alembic for migrations once schema stabilizes.
- pytest for backend tests.
- ruff for linting/formatting.

Do not add production dependencies until a concrete need appears.

## 5. Infrastructure Resources

### Local MVP

- Local Postgres.
- Local FastAPI server.
- Godot editor.
- `.env` file for API keys.

### Demo Server

- 1 small cloud VM or container service.
- Managed Postgres or Docker Postgres.
- Reverse proxy with WebSocket support.
- Basic logging and error monitoring.

### Scaling Assumption

Use one simulation worker per active world. Do not design for massive concurrency in the first stage.

## 6. Content Resources

Minimum:

- 1 small top-down tilemap.
- 1 player sprite.
- 3 NPC sprites.
- 5 location labels/interiors or map zones.
- Simple dialogue UI.
- Status icons or text labels.

Use placeholder assets until the loop is proven.

## 7. AI And Cost Controls

Controls required before public demo:

- per-session AI call budget
- per-NPC autonomous call cooldown
- prompt context size limit
- response timeout
- fallback templates
- cached embeddings
- async reflection queue

Cost should be measured per 10 minute session.

## 8. Testing Strategy

### Unit Tests

- validator accepts/rejects tools correctly
- relationship deltas are bounded
- rumor confidence/distortion stays capped
- event phase transitions require prerequisites

### Simulation Tests

- replay event log
- run missing seeds path to each ending
- simulate LLM timeout
- simulate invalid player claim

### Manual Playtest Checklist

- Does a memory visibly affect behavior?
- Can player understand what changed?
- Is the UI showing enough state without exposing debug internals?
- Does the game continue when AI is slow?
- Does the rumor feel socially plausible?

## 9. Documentation Gates

Before coding a feature, the team should know:

- What state object it changes.
- Which tool or system owns the mutation.
- Which validator rule protects it.
- Which visible player consequence proves it works.
- Which test proves it did not regress.

## 10. First Implementation Task

Create the backend world skeleton:

```text
FastAPI app
WorldState model
EventLog model
WorldClock service
WebSocket /ws/world/{world_id}
tick loop that emits world_diff
```

No LLM is needed for this task.

