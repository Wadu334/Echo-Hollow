# Playable World v1 Goal

## Goal

Turn the current playable village slice into a comfortable NPC conversation prototype.

This phase should not push the player through the Missing Seeds main event yet. The first priority is the ordinary moment-to-moment experience:

```text
walk around -> approach a villager -> start a conversation -> choose a topic -> receive a clear response
```

Agent-driven actions, quest consequences, rumor spread, and event escalation should be layered in after basic NPC dialogue feels understandable and pleasant.

## Player Experience Target

A first-time tester should understand that the current build is a village conversation prototype, not a quest-completion build.

The game should guide the player through a short social loop:

1. Start in the village.
2. Find a first talkable NPC near the starting point.
3. Walk up to Mira, Tomo, or Ivo.
4. Press `E` to talk.
5. Read a small dialogue panel.
6. Choose a simple topic.
7. See a short response or toast.
8. Leave the conversation and talk to someone else.

The player should not need to know about backend phases, action queues, world diffs, or scenario internals.

## Scope

### Must Build

- Dialogue box with NPC name, line, and selectable choices.
- Choice submission through the existing WebSocket dialogue command path.
- Friendly fallback choices for normal conversation:
  - greet
  - ask about work
  - ask about the village
  - say goodbye
- Clear approach prompt when the player is near an NPC.
- A first talkable NPC near the player spawn.
- Toast or compact feedback after a dialogue choice.
- HUD copy that tells the player to talk to villagers instead of pushing a main quest.
- Friendly event labels instead of raw event ids.

### Should Build

- Small relationship or familiarity hint after repeated conversations.
- NPC bubbles that summarize player-facing state in plain language:
  - mood
  - current activity
  - short social hint
- Conversation close and re-open behavior that feels predictable.
- Optional debug overlay for backend details.

### Do Not Build Yet

- Missing Seeds quest progression as the main player path.
- Warehouse investigation flow.
- Evidence sharing flow.
- Agent-driven NPC actions after dialogue.
- Rumor propagation as a required player-facing loop.
- LLM dialogue generation.
- New NPCs or locations.
- Persistence.
- Big art overhaul.

## Later Agent Action Layer

After normal NPC dialogue works, add a second layer:

```text
dialogue choice -> memory or intent -> AgentRuntime proposal -> VillageDirector scheduling -> validated action -> visible NPC response
```

That later layer can include:

- NPC movement from `actor_movements`.
- NPC follow-up actions after conversations.
- Rumor spread.
- Relationship shifts.
- Missing Seeds investigation and evidence sharing.
- Main event consequences.

## UX Copy Direction

Use calm player-facing language before debug language.

Good:

- "Next: Talk to a villager."
- "Press E to talk to Mira."
- "Mira is thinking about repairs."
- "Tomo seems busy but willing to talk."
- "Ivo shares a village rumor."

Avoid making the default HUD feel like a quest log for this phase:

- "Find the torn seed bag."
- "Share evidence with Mira."
- "Resolve Missing Seeds."

Avoid exposing raw implementation terms in the default HUD:

- `public_problem`
- `world_diff`
- `npc_schedule_changed`
- `action_queue`
- `deterministic placeholder`

Debug terms can stay in an optional debug overlay.

## Acceptance Criteria

Playable World v1 is done when a tester can complete this path without external instructions:

1. Walk near Mira, Tomo, or Ivo.
2. See a clear talk prompt.
3. Press `E` to open a dialogue panel.
4. Choose at least one normal conversation option.
5. See the NPC response and a small feedback message.
6. Close the dialogue.
7. Repeat with another NPC.

The build should feel like the foundation of a social village game, even before quests and agent actions are added.

## First Implementation Slice

Build this first:

```text
Dialogue UI + normal conversation choices
NPC approach prompt
Toast feedback
Friendly HUD objective text
```

This is the shortest path from the current v0 client to a readable player-facing prototype.
