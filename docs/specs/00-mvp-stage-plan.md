# AI Agent Village MVP Stage Plan

## 1. Stage Objective

Build a playable first-stage prototype of an AI Agent village game.

The prototype should prove one core product claim:

> The village remembers player actions, spreads information between NPCs, and turns internal memory changes into visible world consequences.

This stage is not trying to prove large-scale autonomous NPC society, voice-driven NPCs, 3D production quality, or long-term live operations. It is a narrow vertical slice for validating the game loop and the agent architecture.

## 2. MVP Scope

### In Scope

- 2D top-down village.
- 1 playable player character.
- 3 core NPCs.
- 5 locations.
- 1 core event chain: `missing_seeds`.
- Text-based player-to-NPC dialogue.
- Limited NPC-to-NPC automatic dialogue.
- Layered memory:
  - episodic memory
  - social memory
  - rumor memory
  - semantic memory
  - reflection memory
- Relationship state:
  - trust
  - affinity
  - fear
  - debt
- Rumor propagation with confidence, source chain, distortion, and verification state.
- Server-authoritative world simulation.
- WebSocket state sync.
- Tool validation for all world mutations.
- Debug views for world events, NPC goals, memories, validator decisions, and AI calls.

### Out Of Scope

- 3D world.
- Voice generation.
- Multiplayer.
- More than one village.
- 10+ autonomous NPCs.
- Procedural map generation.
- Player-created NPCs or events.
- Fully free-form world mutation by LLM.
- LangGraph or CrewAI as the primary game runtime.
- Steam release build polish.

## 3. Success Criteria

The MVP is successful when a tester can complete a 10 minute loop where:

1. The player hears or causes a claim about the missing seeds.
2. At least one NPC stores the claim as memory.
3. The claim spreads to another NPC.
4. The second NPC changes dialogue or behavior because of the claim.
5. The player can discover evidence.
6. The evidence updates the event state from rumor to verified fact.
7. Relationships change because of the event outcome.
8. A later NPC action reads the changed memory or relationship state.

The prototype must remain playable if an LLM request times out. In that case, the system should fall back to deterministic behavior or simple template text.

## 4. Technical Direction

Recommended stack:

- Engine: Godot.
- Backend: Python + FastAPI.
- Realtime: WebSocket.
- Database: Postgres + JSONB + pgvector.
- AI: OpenAI Responses API or Agents SDK for dialogue, structured action proposals, and reasoning.
- Runtime planning: custom lightweight planner.
- NPC execution: schedule + utility score + small GOAP/BT/FSM layer.
- Deployment model: one simulation worker per world.

The world simulation is the source of truth. LLM output is advisory until converted into structured tool calls and accepted by validators.

## 5. Architecture Principle

Use this boundary throughout implementation:

- Deterministic systems own time, locations, pathing, cooldowns, resource changes, relationship arithmetic, quest state, and event state.
- LLM systems own natural language, ambiguous social interpretation, complex dialogue framing, and candidate action proposals.
- Validators own permission to mutate world state.
- Memory writer owns durable memory records.
- Async jobs own summaries, embeddings, reflections, and compression.

## 6. First Development Milestones

### Week 1: World Skeleton

- Godot map with 5 locations.
- Player movement.
- Backend project skeleton.
- World clock.
- WebSocket connection.
- Basic event log.

Acceptance:

- Client can connect to backend.
- Backend emits world time and player location updates.
- No LLM integration yet.

### Week 2: NPC Schedule

- NPC definitions.
- Fixed daily schedules.
- Location occupancy.
- Basic pathing or direct location transitions.

Acceptance:

- 3 NPCs move through their schedules.
- Location changes are server-authored.
- Client displays NPC location/status.

### Week 3: Dialogue And Relationships

- Player-to-NPC text dialogue.
- Simple local template fallback.
- Relationship values.
- Dialogue log.

Acceptance:

- Player can talk to nearby NPC.
- Dialogue can update a relationship field through a validated event.

### Week 4: Memory

- Episodic memory write.
- Social memory update.
- Basic memory retrieval.
- NPC-to-NPC conversation trigger.

Acceptance:

- A player statement is stored and later retrieved in a different interaction.

### Week 5: Rumor Engine

- Rumor object.
- Propagation scoring.
- Distortion and confidence update.
- Source chain tracking.

Acceptance:

- A rumor can move from one NPC to another and change form within bounded rules.

### Week 6: Missing Seeds Event

- Event facts.
- Evidence discovery.
- Three resolution paths.
- Relationship consequences.

Acceptance:

- Player can resolve, escalate, or manipulate the event.

### Week 7: Reflection And Behavior Change

- Reflection job.
- Long-term behavior flag.
- Relationship UI.
- Debug panel.

Acceptance:

- An NPC changes later behavior because of reflection or social memory.

### Week 8: Stabilization

- Prompt reduction.
- Caching.
- Timeout fallback.
- Safety filtering.
- Demo packaging.

Acceptance:

- Low-concurrency demo runs without blocking on LLM latency.

## 7. Required Core Specs

The first implementation batch is defined by:

- `01-product-prd.md`
- `02-world-simulation-spec.md`
- `03-memory-rumor-spec.md`
- `04-tool-validator-spec.md`
- `05-scenario-content-spec.md`

These specs are intentionally written before code so implementation can stay scoped and testable.

