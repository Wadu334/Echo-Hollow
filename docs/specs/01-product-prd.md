# Product PRD: AI Agent Village MVP

## 1. Product Definition

AI Agent Village is a small 2D social simulation game where NPCs remember player actions, spread information, update relationships, and change behavior inside a persistent village.

The first MVP is a playable vertical slice, not a full commercial game.

## 2. Product Promise

The player should feel:

- "The village remembers what I said."
- "NPCs talk to each other when I am not directly involved."
- "A rumor can become a social consequence."
- "Evidence and player intervention can change how the village judges people."

## 3. Target Experience

The MVP should be understandable within 10 minutes:

1. The player enters a village.
2. A public event is active: the shared seed bag is missing.
3. The player hears conflicting accounts from NPCs.
4. The player repeats or withholds information.
5. NPCs react to what they hear.
6. Information spreads.
7. The player discovers evidence.
8. The village updates its beliefs and relationships.
9. The player sees a changed behavior or dialogue caused by the earlier chain.

## 4. Core Loop

### Observe

The player sees NPC location, visible mood, recent public events, and village rumors.

### Intervene

The player talks, asks questions, shares claims, investigates locations, or chooses who to help.

### Diffuse

NPCs convert events into memories, select whether to share them, and propagate claims through social channels.

### Return

The world exposes consequences through changed dialogue, changed trust, refused help, new investigation behavior, or event resolution.

## 5. MVP User Stories

- As a player, I can walk around the village and approach NPCs.
- As a player, I can ask an NPC about the current event.
- As a player, I can tell one NPC what another NPC said.
- As a player, I can inspect the warehouse and find evidence.
- As a player, I can see that an NPC's opinion changed because of what they heard.
- As a player, I can resolve the seed event in more than one way.
- As a developer, I can inspect why an NPC chose an action.
- As a developer, I can inspect which memories were retrieved for a dialogue or decision.

## 6. NPC Cast

### Mira

- Role: carpenter.
- Social role: order-focused executor.
- Personality: disciplined, suspicious, low tolerance for disorder.
- Drama function: likely to treat incomplete information as actionable evidence.

### Tomo

- Role: farmer.
- Social role: practical victim.
- Personality: hardworking, sensitive, defensive under accusation.
- Drama function: easily harmed by rumor and public suspicion.

### Ivo

- Role: tavern keeper.
- Social role: social hub.
- Personality: outwardly warm, image-conscious, socially opportunistic.
- Drama function: rumor amplifier and reputation broker.

## 7. Locations

- Square: public notice, accidental meetings, public rumor spread.
- Tavern: social hub and gossip center.
- Farm: Tomo's work location and source of practical stakes.
- Workshop: Mira's work location and order-focused dialogue.
- Warehouse: evidence location for the missing seeds event.

## 8. Main Event: Missing Seeds

Village seed supplies are missing. NPCs have partial and conflicting information.

Known initial fact:

- The shared seed bag is missing.

Initial uncertain claims:

- Tomo may have taken it.
- Ivo may have been near the warehouse late at night.
- Mira believes the community should act quickly.

Possible outcomes:

- Misunderstanding escalates: Tomo is socially punished.
- Investigation clears Tomo: relationships recover.
- Player manipulates blame: short-term favor with one NPC, long-term trust loss with another.

## 9. UI Requirements

### Main View

- Top-down village map.
- Player character.
- NPCs with compact status indicators.
- Interactive location highlights.

### Side Panel

- Current time.
- Current location.
- Recent events.
- Active village rumors.

### Interaction Bar

- Text input.
- Contextual action buttons:
  - talk
  - ask
  - share
  - investigate
  - leave

### NPC Panel

- Known facts.
- Relationship trend.
- Recent public memory summary.
- Current mood/status.

### Debug Panel

Required for development builds:

- NPC current goal.
- Last action proposal.
- Validator result.
- Retrieved memory ids.
- Last LLM call latency and fallback state.

## 10. Non-Goals

- The MVP does not need beautiful art.
- The MVP does not need voice.
- The MVP does not need broad procedural content.
- The MVP does not need arbitrary player commands that mutate the world.
- The MVP does not need to simulate every NPC every second.

## 11. Product Risks

### Weak Consequences

If memory does not visibly affect behavior, players will read the game as a chatbot.

Mitigation:

- Every important memory must have at least one possible external behavior consequence.

### LLM Latency

If NPCs pause for multiple seconds without feedback, the simulation feels broken.

Mitigation:

- Give immediate deterministic response.
- Complete richer wording asynchronously.
- Use fallback text on timeout.

### Cost Growth

If every action uses LLM reasoning, the game becomes too expensive.

Mitigation:

- Use LLM only for dialogue, ambiguous social reasoning, and candidate action proposals.
- Use rules for schedule, pathing, cooldowns, and propagation eligibility.

### Content Safety

Runtime-generated text must be bounded.

Mitigation:

- Input filtering.
- Output moderation or safety classifier.
- Tool whitelist.
- World fact whitelist.

## 12. MVP Done Definition

The PRD is satisfied when a tester can play the missing seeds sequence end-to-end and see at least one NPC behavior change caused by a stored memory or rumor.

