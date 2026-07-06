# VillageDirector v0

## Purpose

VillageDirector v0 is the deterministic central orchestration layer for Echo Hollow. It coordinates when NPC proposals enter the action queue, but it does not own NPC intention, legality, world mutation, or scenario resolution.

```text
NPC AgentRuntime -> VillageDirector -> Validator -> WorldSimulation -> EpisodeManager
```

## Responsibility Boundaries

### NPC AgentRuntime

`AgentRuntimeV1` is local intention generation. It assembles actor context, retrieves relevant memories, and returns an action proposal. Its proposal-only path must not enqueue actions or mutate world state.

### VillageDirector

`VillageDirector` handles global scheduling:

- approves episode-relevant NPC proposals
- skips duplicate pending actions
- enforces social and gossip pacing budgets
- schedules fallback movement after unavailable-target rejections
- injects deterministic Missing Seeds confrontation beats
- records compact public director traces

The Director must not directly change relationships, write NPC memories, change facts, or resolve events.

### Validator

The validator is the hard legality gate. Every queued tool is validated at execution time. Director approval does not guarantee execution.

### WorldSimulation

`WorldSimulation` is authoritative state mutation. It executes accepted tools and owns actual changes to actors, locations, memories, relationships, rumors, event log entries, and facts.

### EpisodeManager

`MissingSeedsEpisodeManager` owns scenario phase transitions and endings. The Director may enqueue a beat that causes action, but the episode manager decides whether a phase or resolution changes.

### AI / LLM

AI providers remain advisory. No real LLM call is required. Future LLM usage may summarize traces or propose wording, but it must not mutate state, bypass validators, bypass the Director, or resolve scenarios.

## Current Director Decisions

Director decisions are JSON-safe dataclasses:

- `approve`
- `defer`
- `reject`
- `rewrite`
- `fallback`
- `inject_episode_beat`
- `budget_skipped`
- `duplicate_skipped`
- `noop`

Snapshots expose:

- `last_director_trace`
- `director_state`

Relevant event log types include:

- `director_decision`
- `director_fallback_planned`
- `director_episode_beat_injected`
- `director_budget_skipped`
- `director_duplicate_skipped`

## Missing Seeds Behavior

When Mira receives a Missing Seeds memory, her agent proposes a local action such as `npc_talk_to(tomo)`. The Director decides whether to schedule it. If the validator later rejects the talk because Tomo is unavailable, the Director schedules `npc_move_to` plus a retry.

If suspicion has spread too long, the Director may inject a confrontation beat by queueing Mira movement and a Mira-to-Tomo talk action. It does not set the episode phase directly.

## Verification

Run:

```powershell
python -m unittest discover -s backend\tests -v
python backend\scripts\probe_episode.py
```

If Godot is installed:

```powershell
godot_console --headless --path client --script res://tests/verify_client.gd
```
