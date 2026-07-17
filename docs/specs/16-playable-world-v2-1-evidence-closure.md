# Playable World v2.1: Evidence Closure, Outcome Integrity, And Recovery

## Status

This document is the acceptance contract for Playable World v2.1. It describes
the intended production path and the evidence required to call the slice
complete. The final automated verification record was produced on 2026-07-17
against the final pre-commit `main` worktree. The visible manual operator pass
was interrupted when desktop control was cancelled and is recorded separately
rather than reported as passing.

## Goal

Starting from a fresh world, a player must be able to complete the Missing Seeds
reconciliation using only normal Godot controls and choices offered by the
server:

```text
Ask Ivo
-> carry Ivo's sourced Tomo claim
-> tell Mira
-> Mira remembers it
-> AgentRuntime proposes a social follow-up
-> VillageDirector schedules legal movement and retry
-> Mira and Tomo show a visible social consequence
-> check the Warehouse
-> press E on the concrete clue
-> carry torn seed bag evidence
-> show Mira the server-offered evidence choice
-> debunk the Tomo rumor
-> show the server-authored reconciliation outcome
```

The accepted run must not use the dashboard, number-key location jumps, raw
WebSocket messages, or debug action buttons.

## Normal Play Versus Debug Surfaces

The same backend may expose diagnostic operations, but those operations are not
evidence that the Godot path is playable.

| Surface | Intended use | Counts as playable acceptance |
|---|---|---|
| Godot `WASD` | Pixel movement and logical-area intent | Yes |
| Godot `E` near an NPC | Open a server-owned conversation | Yes |
| Godot `E` on the Warehouse clue | Submit the currently offered contextual action | Yes |
| A button generated from `dialogue_opened.choices` | Submit its `conversation_id`, `offer_version`, and `choice_id` | Yes |
| Dashboard action buttons | Inspect or force backend/debug behavior | No |
| Number keys `1-5` | Debug-only location jumps | No |
| `probe_episode.py` or direct `WorldSimulation` calls | Deterministic backend diagnosis | No |
| Raw `investigate_location`, `player_share_evidence`, or arbitrary target payloads | Protocol/debug regression checks only | No |

The playable evidence handoff never lets the client choose an arbitrary evidence
recipient. Mira appears as a choice only when the server has verified every
precondition.

## Architecture Boundary

The existing authority model remains in force:

```text
Godot input/presentation
-> strict WebSocket protocol
-> WorldSimulation command boundary
-> Missing Seeds rules/service
-> AgentRuntime proposal
-> VillageDirector scheduling
-> Validator execution-time check
-> WorldSimulation mutation
-> EpisodeManager transition/outcome
-> authoritative state, events, and presentation
```

- `AgentRuntimeV1` proposes intent; it does not mutate the world.
- `VillageDirector` schedules, deduplicates, budgets, and plans fallback actions;
  it does not apply relationship, rumor, memory, or phase effects.
- Validators recheck both location and episode semantics immediately before
  execution.
- `WorldSimulation` executes accepted tools and owns authoritative mutations.
- `MissingSeedsEpisodeManager` owns phase transitions and terminal outcomes.
- Episode-specific clue, resolution, confrontation, and rumor rules belong in a
  focused Missing Seeds rules/service module rather than accumulating in the
  general world loop.
- Godot presentation, contextual interaction, consequence queuing, and recovery
  deduplication belong in a presenter/controller rather than one growing
  `main.gd` branch.

The inactive legacy `backend/app/agent.py` must be removed, migrated, or marked
deprecated with no ambiguity about the active runtime path. The active agent
runtime remains `backend/app/agent_runtime.py`.

## Explicit Phase Transition Graph

The Missing Seeds episode uses a whitelist graph. `set_phase` must reject any
edge not listed here, even if the destination is otherwise a known phase.

| Current phase | Legal next phases |
|---|---|
| `public_problem` | `conflicting_claims` |
| `conflicting_claims` | `confrontation_pending`, `suspicion_spread`, `resolved_false_accusation` |
| `confrontation_pending` | `confrontation_happened`, `suspicion_spread`, `resolved_false_accusation` |
| `suspicion_spread` | `confrontation_pending`, `confrontation_happened`, `evidence_found`, `resolved_false_accusation` |
| `confrontation_happened` | `suspicion_spread`, `evidence_found`, `resolved_false_accusation` |
| `evidence_found` | `resolution_pending` |
| `resolution_pending` | `resolved_reconciled`, `resolved_player_manipulated` |
| `resolved_reconciled` | none |
| `resolved_false_accusation` | none |
| `resolved_player_manipulated` | none |

Entering the current phase again is an idempotent no-op, not a second phase
effect. Every `resolved_*` phase is irreversible. Investigation, evidence share,
ticks, queued actions, fallbacks, retries, stale choices, and direct/debug calls
must not reopen a terminal episode.

`resolved_player_manipulated` remains a modelled terminal state but is not a
playable v2.1 ending.

## Outcome Integrity And At-Most-Once Rules

The following are business invariants, not UI conventions:

1. A concrete clue may be discovered at most once.
2. The same `evidence_id` may resolve the same episode at most once.
3. A resolution path's relationship, mood, reflection, rumor, and event effects
   may be applied at most once.
4. The same causal claim may create at most one Mira-to-Tomo confrontation.
5. A rejected, stale, replayed, wrong-recipient, wrong-location, or duplicate
   request may append a rejection audit event, but it must not change business
   state.
6. Resolving the episode cancels or invalidates all incompatible queued,
   fallback, and retry actions for that episode.
7. An action that was legal when queued must still pass episode semantic checks
   at execution time.
8. A rumor whose `verified_state` is `false` cannot gain holders, spread count,
   distortion, or confidence.
9. A `missing_seeds` conversation is not automatically an accusation. The
   queued action carries a validated social act or intent such as
   `ask_for_clarification`, `confront_claim`, or `reconcile_with_evidence`.

Recommended stable rejection or no-op reasons are:

- `not_reachable`
- `clue_not_found`
- `clue_not_available`
- `evidence_already_found`
- `evidence_not_found`
- `invalid_evidence_recipient`
- `evidence_already_shared`
- `episode_terminal`
- `semantic_precondition_failed`
- `rumor_debunked`
- `stale_contextual_offer`
- existing conversation reasons such as `stale_offer` and
  `choice_not_offered`

Exact wire strings must be locked by tests once selected. More important than
the spelling is that every failure is stable, observable, and free of business
side effects.

## Warehouse Contextual Evidence

### Availability

The torn seed bag is discoverable only when all of these are true:

- the player is authoritatively at `warehouse`;
- the Missing Seeds episode is in a phase where the clue is relevant;
- the concrete Warehouse clue is still available;
- the player has not already discovered `torn_seed_bag`;
- the episode is not terminal.

Godot receives the currently offered action from backend presentation state. A
representative payload is:

```json
{
  "presentation": {
    "objective": "Check the Warehouse",
    "contextual_action": {
      "action_id": "inspect_torn_seed_bag_clue",
      "offer_version": 1,
      "location_id": "warehouse",
      "prompt": "Press E to inspect the torn seed bag near the warehouse shelves."
    }
  }
}
```

Godot submits only the offered identifier and version:

```json
{
  "type": "activate_contextual_action",
  "action_id": "inspect_torn_seed_bag_clue",
  "offer_version": 1
}
```

The server rechecks location, phase, availability, and version. It does not
trust a client-supplied evidence id, fact id, location, or recipient.

### Authoritative Evidence Record

The first accepted investigation writes a structured record equivalent to:

```json
{
  "evidence_id": "torn_seed_bag",
  "fact_id": "fact_torn_seed_bag",
  "found_location": "warehouse",
  "found_by": "player",
  "found_event_log_id": "log_...",
  "provenance": {
    "kind": "contextual_interaction",
    "actor_id": "player",
    "clue_id": "clue_torn_seed_bag",
    "location_id": "warehouse"
  },
  "status": "held"
}
```

The corresponding fact, player evidence inventory or memory, and event log must
refer to the same identifiers. Repeating the investigation returns a stable
no-op or rejection and creates no second evidence/memory/business event.

## Mira Evidence Choice And Reconciliation

Mira offers `show_torn_seed_bag` only when:

- the player owns the authoritative `torn_seed_bag` record;
- the episode is awaiting a resolution and is not terminal;
- the player and Mira are authoritatively co-located and can interact;
- Mira is the configured reconciliation recipient;
- this evidence has not already been shared for this episode.

The player submits the ordinary conversation token and offered choice. The
client does not submit `target_id: "mira"` as an unrestricted evidence command.
Before any of those conditions is true, Mira must not offer the choice. Tomo and
Ivo must not offer it in v2.1.

An accepted choice:

1. records the evidence handoff once;
2. moves through `resolution_pending` by a legal graph edge;
3. debunks `rumor_tomo_took_seeds`;
4. applies relationship and mood effects once;
5. writes Mira's reflection once;
6. invalidates incompatible episode actions;
7. enters `resolved_reconciled` once;
8. emits one server-authored outcome presentation.

## Player-Facing Presentation

Backend presentation fields must be rendered, not merely transported:

- `event_title`
- `event_phase_text`
- `village_flow_text`
- `objective`
- current `contextual_action.prompt`, when available
- pending consequence/outcome payloads

The objective sequence for the accepted path is:

```text
Ask Ivo
-> Tell Mira
-> Check the Warehouse
-> Show Mira the evidence
-> Observe the outcome
```

NPC bubbles consume the grouped memory schema (`owner_id -> [memories]`) and
must visibly increase Mira's memory count after the claim handoff.

Normal player UI uses a qualitative relationship trend such as "trust is
recovering" or "trust feels strained". Exact numeric relationship values remain
available only in debug views.

### Server-Authored Outcome

The consequence scene consumes a reusable server payload rather than
reconstructing each beat from phase-specific hard-coded client logic:

```json
{
  "presentation_id": "present_...",
  "type": "reconciliation_consequence",
  "path": "reconciled",
  "title": "The Rumor Is Put Right",
  "line": "Mira tells Tomo the torn bag changes what everyone thought happened.",
  "reaction_text": "Tomo looks relieved, though the accusation still stings.",
  "relationship_trend_text": "Tomo and Mira are beginning to rebuild trust.",
  "reflection_text": "Mira resolves to check evidence before repeating a claim.",
  "event_log_id": "log_..."
}
```

The presenter deduplicates by `presentation_id`. Acknowledgement is safe to
retry. A consequence is shown once even if the same payload arrives through a
live diff, cursor recovery, and pending presentation state.

## Connection Recovery Contract

`WorldConnection` distinguishes:

- `Connecting`: initial connection attempt;
- `Reconnecting`: unexpected transport loss with retry scheduled;
- `Online`: socket open and authoritative state active;
- `Offline`: explicit disconnect or retry policy exhausted, if exhaustion is
  configured.

Unexpected disconnects use capped exponential backoff. An explicit disconnect
does not reconnect.

The client retains across a transport reset:

- `last_consumed_event_cursor`;
- processed event or presentation ids;
- pending presentation acknowledgements;
- the last authoritative snapshot for frozen display.

On reconnect:

1. the client includes `after_cursor=<last_consumed_event_cursor>`;
2. while holding the connection dispatch boundary, the server captures one
   authoritative snapshot cursor and sends all intervening events in ordered
   pages of at most 500 entries;
3. every `recovery_events` page declares `from_cursor`, `to_cursor`, and
   `has_more`, with `to_cursor == from_cursor + events.size()`;
4. the client accepts only contiguous pages, accumulates their events, and
   advances only to each page's `to_cursor`;
5. the server sends `world_state` after the final page;
6. the client remains `Reconnecting` unless its consumed cursor exactly equals
   the snapshot's `event_log_cursor`; it never jumps across a recovery gap;
7. after the exact cursor match, the client applies the snapshot while local NPC
   authority remains disabled;
8. the presenter releases exactly one pending consequence;
9. acknowledgement removes it from future pending presentation state.

`pending_presentations` remains the durable consequence fallback, but it does
not authorize skipping ordinary authoritative events. A reconnect gap larger
than 500 events therefore uses multiple contiguous pages rather than truncating
recovery at the first page.

A transient disconnect between evidence discovery and reconciliation must not
lose or duplicate the outcome scene.

## Required Automated Evidence

### Backend

The original 67-test v2 baseline must remain green. Additional tests must cover:

- wrong-location investigation;
- investigation of a non-Warehouse location;
- repeated investigation;
- wrong evidence recipient;
- repeated evidence share;
- stale or replayed evidence choice;
- terminal phase reopen;
- pending episode action after resolution;
- execution-time semantic invalidation;
- debunked rumor spread;
- repeated confrontation from the same causal claim;
- non-accusatory `missing_seeds` social intent;
- false-accusation terminal stability;
- 300+ world-minute `resolved_reconciled` stability.

The long-run fingerprint includes phase, resolution path, both Mira/Tomo
relationship records, Tomo mood/status, rumor verification/confidence/spread and
holders, reflection count, resolution event count, and confrontation count.

### Godot Offline

Headless verification must assert:

- NPC-versus-contextual `E` prompt selection;
- all four backend presentation fields are rendered;
- the complete objective sequence;
- grouped-memory bubble count changes;
- outcome fields render without exposing relationship numbers;
- consequence deduplication by `presentation_id`;
- `Connecting`, `Reconnecting`, and `Offline` states;
- reconnect preserves cursor and does not restore local NPC patrol authority.

### Connected

The real Godot-to-FastAPI test starts a fresh Uvicorn process and completes the
whole evidence reconciliation path. It must also run a transient-disconnect
scenario proving reconnect, cursor recovery, authoritative resync, and
exactly-once outcome delivery.

## Verification Commands

Run these against the final worktree:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v

.\.venv\Scripts\python.exe -m coverage erase
.\.venv\Scripts\python.exe -m coverage run --branch --source=backend.app `
  -m unittest discover -s backend\tests -v
.\.venv\Scripts\python.exe -m coverage report --show-missing

Godot_v4.7-stable_win64_console.exe --headless --path client `
  --script res://tests/verify_client.gd

.\.venv\Scripts\python.exe backend\scripts\verify_connected_godot.py `
  --godot "C:\path\to\Godot_v4.7-stable_win64_console.exe" `
  --runs 3 --godot-timeout 120
```

Recovery is part of `verify_connected_client.gd`: it creates evidence while the
client is paused, drops the transport, reconnects with `after_cursor`, checks
the exact recovered `evidence_found/torn_seed_bag` event, and verifies both
presentation scenes are entered once. `--runs 3` starts and stops an independent
Uvicorn process for each fresh world.

Coverage must be branch-aware. New Missing Seeds rule modules and their failure
branches must appear in the report; a green test suite without executed failure
branches is insufficient evidence.

## Manual Acceptance Without Debug Commands

Use a fresh server process and a normal Godot run. Do not open the dashboard,
press `1-5`, send raw WebSocket payloads, or call a probe script.

1. Confirm the status reaches `Online` and the objective says `Ask Ivo`.
2. Walk to Ivo with `WASD`, press `E`, and select the offered missing-seeds
   choice.
3. Confirm the objective changes to `Tell Mira` and the claim retains Ivo as its
   source.
4. Walk to Mira, press `E`, and select the offered Ivo-claim choice.
5. Confirm Mira's memory bubble visibly increases.
6. Wait for Mira's validator-driven movement and the visible Mira/Tomo social
   consequence; return to the main scene.
7. Confirm the objective changes to `Check the Warehouse`.
8. Walk to the Warehouse. Confirm the prompt names the concrete clue, then press
   `E` once.
9. Confirm the torn seed bag evidence appears with Warehouse provenance and the
   objective changes to `Show Mira the evidence`.
10. Walk to Mira, press `E`, and confirm only Mira offers the evidence choice.
11. Select it once. Confirm the objective changes to `Observe the outcome`.
12. Confirm the reconciliation consequence shows server-authored title, line,
    reaction, relationship trend, and reflection without an exact relationship
    number.
13. Return to the main scene and confirm authoritative actor positions, the
    debunked rumor, Mira's reflection, and the terminal reconciled state remain
    visible and stable.
14. Attempt no second action in the UI; the clue and evidence choice must no
    longer be offered.

Repeat this procedure from a fresh server at least three times and record every
run below. The automated connected test uses the same no-debug input path; it
does not replace the separate visible-operator record.

## Final Verification Record

Automated rows below were produced from the final pre-commit worktree on
2026-07-17. The documentation-only record update does not change runtime code.

| Evidence | Command or procedure | Result | Evidence note |
|---|---|---|---|
| Backend baseline plus v2.1 regressions | `unittest discover` | Pass | 89 tests, 0 failures |
| Branch coverage | `coverage run/report` | Pass | 80% total; `missing_seeds.py` 95%, `protocol.py` 98%, `director.py` 86%, `world.py` 83%, `episode.py` 82% |
| Godot offline headless | `verify_client.gd` | Pass | `Godot playable client verification passed.` |
| Connected full reconciliation | connected harness | Pass | Normal E/Escape/WASD path reached `resolved_reconciled`; final marker present |
| Connected transient recovery | connected harness | Pass | Catch-up contained `evidence_found/torn_seed_bag`; `presentation_evt_missing_seeds_careful_confrontation` and `presentation_evt_missing_seeds_reconciled` each entered once |
| Fresh connected run 1 | fresh harness process | Pass | 2026-07-17, port 54048, final pre-commit `main` worktree |
| Fresh connected run 2 | fresh harness process | Pass | 2026-07-17, port 61041, final pre-commit `main` worktree |
| Fresh connected run 3 | fresh harness process | Pass | 2026-07-17, port 56671, final pre-commit `main` worktree |
| Manual no-debug playthrough | steps above | Not completed | Visible Godot control was stopped by the operator with Escape; no pass is claimed |

## Non-Goals

- No real LLM.
- No database, save system, or multiplayer controller.
- No new NPC, location, or art.
- No general quest engine, dialogue DSL, or cutscene editor.
- No complete playable `resolved_player_manipulated` path.
- No backend pixel coordinates, navigation pathfinding, or per-frame sync.
- No broad protocol rewrite beyond the cursor, contextual action, and pending
  presentation additions required for this slice.
