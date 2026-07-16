# Playable World v2: Rumor Handoff And Visible Agent Consequence

## Goal

Playable World v2 proves the MVP's core product claim through one small,
deterministic vertical slice:

```text
Ivo offers a rumor
-> player carries a sourced claim
-> Mira receives it through a stateful dialogue choice
-> memory triggers AgentRuntime
-> VillageDirector schedules a legal follow-up
-> Validator rejects remote talk and plans movement + retry
-> Mira reaches Tomo
-> the accepted talk creates a visible consequence scene
```

This slice extends the existing world, Director, validator, and Godot client. It
does not replace them with a new dialogue framework, quest system, or cutscene
engine.

## Authority Boundary

While connected, the backend is the only authority for the player's and NPCs'
logical `current_location`.

- Godot owns input, pixel coordinates, collision, animation, tweening, camera,
  and scene presentation.
- Crossing a local area sends a location intent. It does not commit logical
  state locally.
- NPC schedule changes and accepted movement tools change logical location on
  the backend and emit `actor_movements`.
- `world_state` and `world_diff` always win during reconciliation.
- A rejected player move snaps the player back to the location in the
  authoritative diff.
- A movement event whose `to_location` disagrees with the current NPC snapshot
  is stale and must not be animated; Godot snaps to the snapshot instead.

Offline mode remains available for visual and headless client checks. After a
connection has been established, a disconnect freezes NPCs instead of silently
switching back to local patrol authority.

## Connection And Protocol Contract

Each WebSocket connection receives a unique session id in its initial message:

```json
{
  "type": "world_state",
  "client_session_id": "session_...",
  "data": {
    "world_id": "demo_world_001"
  }
}
```

Incoming WebSocket text is parsed as strict JSON. The top level must be an
object, and command fields must have the documented type. One malformed command
returns `client_error` without closing the connection or mutating the world.
Stable protocol error codes are:

- `malformed_json`
- `payload_not_object`
- `missing_field`
- `invalid_field_type`
- `unsupported_message_type`

Dialogue validation failures use `dialogue_rejected` so the client can
distinguish protocol recovery from world mutation.

Dialogue, interaction-denial, and protocol responses are sent only to the
requesting connection. Any embedded world diff is also broadcast as shared
state, with connection-local dialogue toasts removed. World mutation and
outbound delivery are serialized so a later tick cannot be followed by an
older authoritative snapshot.

### Open Conversation

The client starts an interaction with the existing command:

```json
{
  "type": "player_interact_npc",
  "npc_id": "ivo",
  "interaction": "talk"
}
```

The server returns choices derived from current authoritative state:

```json
{
  "type": "dialogue_opened",
  "conversation_id": "conv_...",
  "offer_version": 1,
  "npc_id": "ivo",
  "speaker": "Ivo",
  "line": "Welcome in. If you need a warm meal or a local story, you came to the right place.",
  "choices": [
    {
      "choice_id": "ask_about_missing_seeds",
      "text": "Ask About the Missing Seeds"
    }
  ]
}
```

The ordinary choices `greet`, `ask_about_work`, `ask_about_village`, and
`goodbye` remain available. State-specific additions are:

- Ivo offers `ask_about_missing_seeds` until the player has his claim.
- Mira offers `share_ivo_claim` only while the player has Ivo's claim and Mira
  has not received it.

### Submit A Choice

Every choice submission must echo the current conversation and offer:

```json
{
  "type": "dialogue_choice",
  "conversation_id": "conv_...",
  "offer_version": 1,
  "choice_id": "ask_about_missing_seeds"
}
```

Successful non-terminal choices increment `offer_version` and return the next
stateful choice set. `goodbye` and `share_ivo_claim` close the conversation.
The result includes:

- `accepted_offer_version`
- current `offer_version`
- `choices`
- `conversation_closed`
- `world_diff`

The server validates in this order:

1. Conversation exists.
2. Conversation belongs to this WebSocket session.
3. Conversation is open.
4. `offer_version` is current.
5. `choice_id` was offered in that version.
6. Player and NPC still satisfy the interaction location rule.

Stable rejection reasons are:

- `conversation_not_found`
- `session_mismatch`
- `conversation_closed`
- `stale_offer`
- `choice_not_offered`
- `interaction_invalidated`
- `missing_conversation_id` for the retired v1 request shape

Only one conversation may be open for a client session. Moving the player or
the conversation NPC closes the affected conversation. The backend retains the
64 most recent closed conversations so replay attempts receive a stable
`conversation_closed` response instead of becoming ambiguous.

## Golden Path And Provenance

Selecting Ivo's rumor choice writes a player note with explicit provenance:

```json
{
  "note_id": "ivo_tomo_seed_claim",
  "claim_id": "tomo_took_seeds",
  "source_actor_id": "ivo"
}
```

Sharing it with Mira uses the existing player-claim effect rather than a second
quest implementation. The resulting memory and `memory_shared` event preserve
Ivo as the source and the player as the messenger.

The remainder of the path uses existing deterministic boundaries:

1. `AgentRuntimeV1` proposes that Mira talk to Tomo about `missing_seeds`.
2. `VillageDirector` approves and queues the proposal.
3. Validator rejects the first `npc_talk_to` with `target_unavailable` because
   Mira and Tomo are in different locations.
4. Director schedules an `npc_move_to` fallback and a retry.
5. The accepted move emits an `actor_movements` entry for Mira.
6. The accepted retry writes `npc_dialogue_started`.
7. Authoritative mood, relationship, event log, and trace fields expose the
   consequence.

Unknown player claim ids return `claim_not_found`; they are never coerced into
the Tomo claim.

## Godot Connection And Consequence Scene

`WorldConnection` is a project Autoload that owns the single WebSocket across
scene changes. It caches:

- connection state and `client_session_id`
- latest authoritative `world_data`
- active dialogue id, version, and choices
- processed event-log ids
- the pending rumor-consequence payload

The URL defaults to:

```text
ws://127.0.0.1:8000/ws/world/demo_world_001
```

Set `ECHO_HOLLOW_SERVER_URL` to override it.

The main scene consumes `world_state`, `world_diff`, and `actor_movements`.
Valid NPC movement is tweened between local location anchors; missing or
contradictory movement metadata falls back to an authoritative snap.

The connection emits the consequence signal once for an event matching:

```text
type = npc_dialogue_started
actor_id = mira
target_id = tomo
topic = missing_seeds
```

The main scene then performs a real `SceneTree` change to
`res://scenes/rumor_consequence.tscn`. The scene presents the server-authored
line, Tomo's current mood, and the current Tomo-to-Mira relationship summary.
It creates no second socket. It returns to the main scene after 3.5 seconds or
when skipped, and the rebuilt main scene immediately applies the Autoload's
latest authoritative snapshot.

`ECHO_HOLLOW_CUTSCENE_DURATION` may shorten the scene for integration tests.

## Verification

Run deterministic backend and offline Godot checks first:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
Godot_v4.7-stable_win64_console.exe --headless --path client --script res://tests/verify_client.gd
```

Then run the repeatable connected check:

```powershell
.\.venv\Scripts\python.exe backend\scripts\verify_connected_godot.py `
  --godot "C:\path\to\Godot_v4.7-stable_win64_console.exe"
```

The harness:

1. Selects a free loopback port.
2. Starts a fresh Uvicorn process and waits for `/health`.
3. Sets `ECHO_HOLLOW_SERVER_URL` and a short consequence duration.
4. Runs `res://tests/verify_connected_client.gd`.
5. Requires the Godot success marker and exit code zero.
6. Terminates Uvicorn on success, failure, or timeout.

The connected test verifies the Ivo-to-Mira choice flow, a rejected movement
and authoritative player resync, Mira's fallback movement and accepted retry,
the real consequence scene transition, continued socket ownership, and
authoritative restoration after returning to the main scene.

## Compatibility And Non-Goals

- HTTP routes and non-dialogue WebSocket commands remain compatible.
- `world_state.data`, `world_diff`, and `actor_movements` remain additive
  contracts.
- `dialogue_choice` intentionally rejects the v1 `npc_id + choice_id` shape.
- The backend does not gain pixel coordinates, pathfinding, or per-frame sync.
- This slice does not add multiplayer ownership, persistence, LLM calls, NPCs,
  locations, endings, or art.
- It does not introduce a general dialogue DSL or cutscene system.
- It does not move state mutation into AgentRuntime or VillageDirector.
