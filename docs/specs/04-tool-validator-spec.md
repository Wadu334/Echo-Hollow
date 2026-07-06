# Tool And Validator Spec

## 1. Purpose

Tools are the only way agent decisions can change the world.

LLM and planner output must be treated as proposals. The validator decides whether a proposal is legal, safe, and consistent with world state.

## 2. Tool Proposal Envelope

```json
{
  "proposal_id": "act_7781",
  "world_id": "demo_world_001",
  "actor_id": "mira",
  "intent": "investigate",
  "tool_name": "talk_to",
  "args": {
    "target_id": "ivo",
    "topic": "missing_seeds"
  },
  "reason": "Mira heard conflicting reports about Ivo being near the warehouse.",
  "source_memory_ids": ["mem_1021"],
  "source_event_log_ids": ["elog_000120"],
  "requires_validation": true
}
```

## 3. Validator Result

```json
{
  "proposal_id": "act_7781",
  "accepted": true,
  "rejection_code": null,
  "applied_event_log_ids": ["elog_000123"],
  "public_feedback": "Mira walks toward the tavern to ask Ivo about the warehouse.",
  "debug_reason": "Actor and target are reachable; topic is active; cooldown passed."
}
```

## 4. Common Validation Rules

All tools must check:

- actor exists
- actor is active
- actor is not locked by another action
- target exists if required
- location is reachable if required
- action cooldown has passed
- event prerequisites are satisfied
- tool is allowed for actor type
- content is safe
- mutation has an event source

## 5. Tool List

### move_to(location_id)

Move actor to a reachable location.

Args:

```json
{
  "location_id": "tavern"
}
```

Validation:

- location exists
- path exists
- destination capacity available
- actor is not busy
- movement cooldown passed

World effects:

- update actor location
- emit movement event
- trigger perception for occupants

Deterministic:

- Yes.

LLM needed:

- No.

### talk_to(target_id, topic)

Start dialogue with nearby target.

Args:

```json
{
  "target_id": "ivo",
  "topic": "missing_seeds"
}
```

Validation:

- target is in same location or valid communication channel exists
- both actors available
- topic is known or discoverable
- dialogue cooldown passed

World effects:

- create dialogue session
- write event log
- optionally write episodic memory after dialogue

Deterministic:

- Partly.

LLM needed:

- For natural language and ambiguous social wording.

### share_memory(target_id, memory_id, framing)

Share a known memory or claim with another actor.

Args:

```json
{
  "target_id": "mira",
  "memory_id": "mem_player_003",
  "framing": "Tomo denied taking the seeds and said Ivo was near the warehouse."
}
```

Validation:

- actor owns or legitimately knows the memory
- target is available
- memory is shareable
- content is safe
- source chain can be recorded

World effects:

- target receives episodic or rumor memory
- source chain updates
- relationship may change

Deterministic:

- Validation and state write are deterministic.

LLM needed:

- Optional for phrasing.

### gossip(target_id, rumor_payload)

Spread uncertain information.

Args:

```json
{
  "target_id": "ivo",
  "rumor_payload": {
    "rumor_id": "rumor_missing_seeds_01",
    "framed_content": "Mira thinks Tomo may know more about the missing seeds."
  }
}
```

Validation:

- rumor exists
- rumor is not expired
- actor currently holds rumor
- target does not already know equivalent rumor at equal or higher confidence
- propagation cooldown passed
- distortion remains within allowed bounds

World effects:

- write rumor memory to target
- update spread count
- update confidence/distortion
- emit social perception event

Deterministic:

- Propagation scoring and state changes are deterministic.

LLM needed:

- Optional for wording.

### investigate(subject)

Investigate a location, object, or NPC.

Args:

```json
{
  "subject_type": "location",
  "subject_id": "warehouse",
  "topic": "missing_seeds"
}
```

Validation:

- actor is at required location
- subject is investigable
- event phase allows investigation
- clue has not already been exhausted unless repeatable

World effects:

- reveal evidence
- update event facts
- write episodic memory

Deterministic:

- Yes.

LLM needed:

- No for discovery; optional for descriptive text.

### work(job_slot)

Execute normal scheduled work.

Args:

```json
{
  "job_slot": "mira_morning_workshop"
}
```

Validation:

- schedule slot active
- actor at required location or can move there
- no higher-priority event override

World effects:

- set current action
- optionally produce minor world resource/event

Deterministic:

- Yes.

LLM needed:

- No.

### rest(rest_type)

Recover need values.

Args:

```json
{
  "rest_type": "short_break"
}
```

Validation:

- actor available
- valid location
- rest cooldown passed

World effects:

- update needs
- update current action

Deterministic:

- Yes.

LLM needed:

- No.

### update_relationship(target_id, deltas, source)

Change social state.

Args:

```json
{
  "target_id": "tomo",
  "deltas": {
    "trust": -0.08,
    "affinity": -0.04
  },
  "source_event_log_id": "elog_000120"
}
```

Validation:

- source event exists
- delta is within allowed range
- actor and target relationship exists or can be initialized
- repeated application is idempotency-safe

World effects:

- update social memory
- write relationship event

Deterministic:

- Yes.

LLM needed:

- No.

## 6. Rejection Codes

- `actor_not_found`
- `target_not_found`
- `location_not_found`
- `not_reachable`
- `target_unavailable`
- `actor_busy`
- `cooldown_active`
- `event_prerequisite_missing`
- `unsafe_content`
- `unknown_world_fact`
- `memory_not_owned`
- `rumor_expired`
- `duplicate_information`
- `delta_out_of_bounds`

## 7. LLM Structured Output Contract

When LLM suggests an action, it must output:

```json
{
  "intent": "talk_to",
  "tool_name": "talk_to",
  "args": {
    "target_id": "ivo",
    "topic": "missing_seeds"
  },
  "confidence": 0.72,
  "reason": "Ivo is socially central and was mentioned in a conflicting report.",
  "fallback_if_rejected": "Mira keeps working but stays suspicious."
}
```

The planner may discard low-confidence proposals before validation.

## 8. Safety Rules

- LLM cannot invent new locations, NPCs, evidence, or event facts.
- LLM cannot modify relationship values directly.
- LLM cannot directly set event resolution.
- LLM cannot create tool names outside the whitelist.
- Player-provided claims must be stored as claims unless verified by world evidence.

## 9. Test Requirements

- Invalid tool names are rejected.
- A movement proposal to disconnected location is rejected.
- A conversation with an absent NPC is rejected.
- A rumor cannot spread if cooldown is active.
- Relationship deltas outside bounds are rejected.
- LLM-proposed unknown fact does not enter world facts.

