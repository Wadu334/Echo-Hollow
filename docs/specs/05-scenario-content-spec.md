# Scenario Content Spec: Missing Seeds

## 1. Purpose

This scenario is the first vertical slice. It must prove the game can turn memory and rumor into visible consequences.

The scenario should be small enough to implement quickly but rich enough to support three different endings.

## 2. Scenario Summary

The shared village seed bag is missing. Mira wants order restored, Tomo is vulnerable to blame, and Ivo is a social hub with incomplete information. The player can escalate suspicion, investigate evidence, or manipulate the outcome.

## 3. Cast

### Mira

```json
{
  "npc_id": "mira",
  "name": "Mira",
  "role": "carpenter",
  "home_location": "workshop",
  "personality": {
    "orderliness": 0.88,
    "warmth": 0.42,
    "suspicion": 0.63,
    "sociability": 0.35
  },
  "goals": [
    { "goal_id": "maintain_order", "priority": 0.8 },
    { "goal_id": "finish_repairs", "priority": 0.6 }
  ]
}
```

Behavior notes:

- Prefers verified order but is impatient when public resources are threatened.
- More likely to investigate or accuse when rumor confidence rises.
- Reflection should reduce future accusation tendency if she is proven wrong.

### Tomo

```json
{
  "npc_id": "tomo",
  "name": "Tomo",
  "role": "farmer",
  "home_location": "farm",
  "personality": {
    "orderliness": 0.62,
    "warmth": 0.50,
    "suspicion": 0.36,
    "sociability": 0.28
  },
  "goals": [
    { "goal_id": "protect_farm", "priority": 0.85 },
    { "goal_id": "avoid_public_shame", "priority": 0.7 }
  ]
}
```

Behavior notes:

- Defensive when accused.
- Trust drops quickly toward people who spread blame.
- Helps the player later if cleared.

### Ivo

```json
{
  "npc_id": "ivo",
  "name": "Ivo",
  "role": "tavern_keeper",
  "home_location": "tavern",
  "personality": {
    "orderliness": 0.45,
    "warmth": 0.66,
    "suspicion": 0.48,
    "sociability": 0.82
  },
  "goals": [
    { "goal_id": "protect_reputation", "priority": 0.75 },
    { "goal_id": "keep_business_running", "priority": 0.65 }
  ]
}
```

Behavior notes:

- Shares information easily.
- Protects image when implicated.
- Can refuse service or favors when relationships fall.

## 4. Locations

### square

- Public notice board.
- Starting point.
- Public rumor spread bonus: `+0.05`.

### tavern

- Ivo's location.
- Gossip spread bonus: `+0.10`.
- Dialogue availability high.

### farm

- Tomo's work location.
- Evidence context for why seeds matter.

### workshop

- Mira's work location.
- Order-related dialogue.

### warehouse

- Evidence location.
- Contains clue: torn seed bag.

## 5. Initial World Facts

```json
[
  {
    "fact_id": "fact_seed_bag_missing",
    "content": "The shared seed bag is missing.",
    "verified": true,
    "public": true
  },
  {
    "fact_id": "fact_ivo_near_warehouse",
    "content": "Ivo was near the warehouse late last night.",
    "verified": false,
    "public": false
  },
  {
    "fact_id": "fact_torn_seed_bag",
    "content": "The seed bag was torn open near the warehouse.",
    "verified": false,
    "public": false
  }
]
```

## 6. Initial Rumors

```json
[
  {
    "rumor_id": "rumor_tomo_took_seeds",
    "topic": "missing_seeds",
    "content": "Tomo may have taken the public seed bag.",
    "source_chain": ["ivo"],
    "confidence": 0.32,
    "distortion_level": 0.18,
    "verified_state": "unknown",
    "current_holder_ids": ["mira", "ivo"]
  }
]
```

## 7. Event Phases

### phase_1_public_problem

Trigger:

- Game starts.

Player-facing state:

- Notice board says the seed bag is missing.

NPC state:

- Mira is tense.
- Tomo is worried.
- Ivo is talkative but evasive.

### phase_2_conflicting_claims

Trigger:

- Player talks to at least two NPCs about missing seeds.

Possible claims:

- Mira says Tomo had access to the seeds.
- Tomo denies taking them and mentions Ivo near the warehouse.
- Ivo suggests Tomo may be under pressure.

### phase_3_social_spread

Trigger:

- Player shares one claim or NPC propagates rumor.

World effects:

- Rumor holder count increases.
- Trust shifts.
- Mira may choose to confront Tomo or Ivo.

### phase_4_evidence

Trigger:

- Player investigates warehouse.

Evidence:

- Torn seed bag found near a storage corner.
- Optional text: marks suggest an animal or accidental tear, not theft.

World effects:

- `fact_torn_seed_bag.verified = true`
- suspicion toward Tomo can be reduced if player shares evidence.

### phase_5_resolution

Trigger:

- Player shares evidence or allows rumor to escalate long enough.

Resolution path selected:

- `clear_tomo`
- `accuse_tomo`
- `shift_blame_to_ivo`

## 8. Resolution Paths

### clear_tomo

Requirements:

- Player discovers torn seed bag.
- Player shares evidence with Mira or Ivo.
- Tomo rumor is debunked.

Effects:

- Mira trust toward Tomo increases.
- Tomo trust toward player increases.
- Mira reflection created: investigate before accusing.
- Ivo may apologize or minimize role.

### accuse_tomo

Requirements:

- Rumor confidence about Tomo exceeds threshold.
- Evidence is not discovered or not shared.
- Mira confronts Tomo.

Effects:

- Mira trust toward Tomo decreases.
- Tomo stress increases.
- Tomo may avoid tavern or square.
- Player loses Tomo trust if they spread accusation.

### shift_blame_to_ivo

Requirements:

- Player repeatedly frames Ivo as suspicious.
- Ivo near warehouse claim spreads.
- Evidence is incomplete or ambiguous.

Effects:

- Mira suspicion toward Ivo increases.
- Ivo trust toward player decreases if manipulation is detected.
- Player may gain short-term Tomo trust.
- Later reflection can mark player as unreliable if contradictions are found.

## 9. Key Dialogue Beats

Dialogue should be generated or templated from structured context. The following are content targets, not mandatory exact lines.

### Mira Opening

- She worries public supplies are missing.
- She wants a quick answer.
- She suspects someone with access.

### Tomo Defense

- He denies taking seeds.
- He feels judged.
- He mentions Ivo was near the warehouse late.

### Ivo Gossip

- He says he only heard things.
- He implies Tomo was desperate.
- He protects his own reputation.

### Evidence Reveal

- The warehouse clue weakens the theft interpretation.
- NPCs should treat evidence differently from rumor.

## 10. Behavior Consequences

At least one consequence must become visible:

- Mira walks to confront Ivo.
- Tomo refuses to speak openly with the player.
- Ivo refuses service/favor to Tomo.
- Mira apologizes or changes future investigation behavior.
- A rumor appears in the side panel and later changes state to debunked or confirmed.

## 11. Required Debug Traces

Every scenario run should make these inspectable:

- Which memories were created.
- Which rumor spread event fired.
- Which relationship deltas applied.
- Which validator checks passed or failed.
- Which event phase is active.
- Which evidence facts are verified.

## 12. Scenario Done Definition

This scenario is done when all three resolution paths can be triggered by different player choices and each path causes at least one visible NPC behavior or relationship consequence.

