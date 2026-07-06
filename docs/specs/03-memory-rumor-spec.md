# Memory And Rumor Spec

## 1. Purpose

Memory is the core game system. It is not just chat history. Memory must explain why NPCs behave differently later.

Every important memory should support at least one downstream use:

- dialogue context
- relationship update
- rumor propagation
- event progression
- behavior change
- reflection

## 2. Memory Types

### Episodic Memory

Personal record of something experienced.

Used for:

- "What happened to me?"
- "Who told me this?"
- "Where did I hear it?"

### Semantic Memory

Stable knowledge summarized from multiple memories or verified facts.

Used for:

- "What do I know to be generally true?"
- "What has been confirmed?"

### Social Memory

Relationship-specific state.

Used for:

- trust
- affinity
- fear
- debt
- secrets
- perceived reliability

### Rumor Memory

Unverified or socially transmitted information.

Used for:

- gossip
- suspicion
- false belief
- distorted propagation

### Reflection Memory

Higher-level conclusion generated after important events or day-end processing.

Used for:

- long-term bias
- changed routine
- changed future decision weighting

## 3. Common Memory Fields

```json
{
  "memory_id": "mem_1021",
  "world_id": "demo_world_001",
  "owner_id": "mira",
  "type": "episodic",
  "created_at_world_time": "09:10",
  "created_at_real_time": "2026-07-03T06:10:00Z",
  "location_id": "square",
  "participants": ["mira", "player"],
  "topic": "missing_seeds",
  "summary": "Player said Tomo denied taking the seeds and mentioned Ivo was near the warehouse.",
  "structured": {},
  "importance": 0.71,
  "emotional_valence": -0.24,
  "truth_state": "unverified",
  "source_event_log_id": "elog_000120",
  "embedding_status": "pending"
}
```

## 4. Truth State

Allowed values:

- `verified`
- `unverified`
- `disputed`
- `debunked`
- `fictional_or_invalid`

World facts and event-critical claims must come from the database, not free model invention.

## 5. Episodic Memory Schema

```json
{
  "type": "episodic",
  "structured": {
    "event_type": "heard_claim",
    "speaker_id": "player",
    "claim_target_id": "ivo",
    "claim": "Ivo was near the warehouse late last night.",
    "direct_experience": false
  }
}
```

Write timing:

- Immediately after conversation.
- Immediately after visible event.
- Immediately after investigation.
- Immediately after accepted tool action.

## 6. Social Memory Schema

```json
{
  "memory_id": "soc_mira_tomo",
  "type": "social",
  "owner_id": "mira",
  "target_id": "tomo",
  "trust": 0.42,
  "affinity": 0.36,
  "fear": 0.08,
  "debt": 0,
  "reliability_score": 0.50,
  "last_updated_by": "elog_000121"
}
```

Social memory is both a memory and a gameplay stat. Changes must be bounded.

Recommended MVP relationship delta range:

- minor event: `0.01` to `0.04`
- meaningful rumor: `0.05` to `0.10`
- verified betrayal/help: `0.10` to `0.25`

## 7. Rumor Schema

```json
{
  "rumor_id": "rumor_missing_seeds_01",
  "world_id": "demo_world_001",
  "topic": "missing_seeds",
  "content": "Tomo may have taken the public seed bag.",
  "source_chain": ["ivo", "mira"],
  "current_holder_ids": ["mira"],
  "confidence": 0.41,
  "distortion_level": 0.22,
  "verified_state": "unknown",
  "spread_count": 2,
  "created_from_event_log_id": "elog_000080",
  "ttl_world_minutes": 360
}
```

Allowed `verified_state` values:

- `unknown`
- `confirmed`
- `debunked`

## 8. Rumor Propagation

Propagation flow:

1. Event creates episodic memory.
2. Importance and emotional valence are scored.
3. If above threshold, memory becomes propagation candidate.
4. Candidate is scored against personality, relationship, location, and topic relevance.
5. If score passes threshold, NPC proposes `gossip` or `share_memory`.
6. Validator checks proximity, cooldown, target availability, and content bounds.
7. Target receives rumor memory.
8. Confidence and distortion update.
9. Relationship changes may be applied.

## 9. Propagation Score

Suggested MVP formula:

```text
score =
  importance * 0.30
  + abs(emotional_valence) * 0.20
  + speaker_sociability * 0.15
  + relationship_affinity * 0.10
  + topic_relevance * 0.15
  + location_gossip_modifier * 0.10
  - cooldown_penalty
```

Default threshold: `0.55`.

## 10. Distortion Rules

Each propagation may increase distortion:

- low trust source: `+0.05`
- high stress speaker: `+0.05`
- tavern/location gossip modifier: `+0.03`
- direct witness: `-0.08`
- verified evidence attached: `-0.20`

Distortion must be capped between `0.0` and `1.0`.

LLM may rewrite rumor wording, but must preserve structured fields. It cannot change verified facts.

## 11. Confidence Rules

Confidence changes:

- direct witness: `+0.25`
- trusted source: `+0.10`
- multiple independent sources: `+0.20`
- conflicting evidence: `-0.25`
- debunking evidence: set `verified_state = debunked`
- confirming evidence: set `verified_state = confirmed`

Confidence must be capped between `0.0` and `1.0`.

## 12. Memory Retrieval

Retriever input:

- actor id
- topic
- current location
- participants
- recent event ids
- candidate action type

Retriever output should include:

- recent episodic memories
- relevant social memory
- active rumors
- verified event facts
- high-importance reflections

MVP retrieval can combine:

- structured query by owner/topic/participants
- recency score
- importance score
- optional vector similarity through pgvector

## 13. Reflection

Reflection should not run in the realtime path.

Run reflection when:

- an event resolves
- a relationship changes significantly
- day ends
- an NPC experiences repeated related memories

Reflection output:

```json
{
  "memory_id": "refl_mira_001",
  "type": "reflection",
  "owner_id": "mira",
  "topic": "judgment",
  "summary": "Mira realizes she acted too quickly on incomplete information about Tomo.",
  "behavior_modifiers": {
    "investigate_before_accuse": 0.20,
    "trust_tomo_recovery": 0.12
  },
  "source_memory_ids": ["mem_1021", "mem_1088", "soc_mira_tomo"]
}
```

## 14. Safety Constraints

- Memory summaries must not invent world facts.
- Critical facts must reference event ids or evidence ids.
- Runtime-generated text must be filtered before becoming memory.
- Player claims are stored as claims, not facts.
- Rumors must preserve source chain.

## 15. Test Requirements

- Player claim writes episodic memory.
- NPC-to-NPC gossip writes target rumor memory.
- Debunked rumor does not upgrade to semantic memory.
- Verified evidence can update rumor state to confirmed or debunked.
- Relationship delta references source memory or event.
- Reflection does not block realtime interaction.

