from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent_runtime import AgentRuntimeV1
from .director import VillageDirector
from .episode import MissingSeedsEpisodeManager


def format_world_time(day: int, minute_of_day: int) -> str:
    hour = minute_of_day // 60
    minute = minute_of_day % 60
    return f"day {day} {hour:02d}:{minute:02d}"


@dataclass(frozen=True)
class ScheduleSlot:
    start_minute: int
    action: str
    location_id: str
    goal: str


@dataclass
class Location:
    location_id: str
    name: str
    position: tuple[int, int]
    capacity: int
    tags: list[str]
    connected_locations: list[str]

    def to_dict(self, occupants: list[str]) -> dict[str, Any]:
        return {
            "location_id": self.location_id,
            "name": self.name,
            "position": {"x": self.position[0], "y": self.position[1]},
            "visual_anchor": {"x": self.position[0], "y": self.position[1]},
            "interaction_radius": 96,
            "capacity": self.capacity,
            "tags": self.tags,
            "connected_locations": self.connected_locations,
            "current_occupants": occupants,
        }


@dataclass
class NPCState:
    npc_id: str
    name: str
    role: str
    current_location: str
    current_action: str
    current_goal: str
    mood: str
    schedule: list[ScheduleSlot]
    status_flags: list[str] = field(default_factory=list)
    behavior_modifiers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "npc_id": self.npc_id,
            "name": self.name,
            "role": self.role,
            "current_location": self.current_location,
            "current_action": self.current_action,
            "current_goal": self.current_goal,
            "mood": self.mood,
            "status_flags": self.status_flags,
            "behavior_modifiers": self.behavior_modifiers,
        }


@dataclass
class PlayerState:
    player_id: str = "player"
    current_location: str = "square"
    notes: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "current_location": self.current_location,
            "notes": self.notes,
        }


@dataclass
class MemoryRecord:
    memory_id: str
    type: str
    owner_id: str
    topic: str
    summary: str
    world_time: str
    source_event_log_id: str
    truth_state: str = "unverified"
    target_id: str | None = None
    importance: float = 0.5
    emotional_valence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_id": self.memory_id,
            "type": self.type,
            "owner_id": self.owner_id,
            "topic": self.topic,
            "summary": self.summary,
            "world_time": self.world_time,
            "source_event_log_id": self.source_event_log_id,
            "truth_state": self.truth_state,
            "target_id": self.target_id,
            "importance": self.importance,
            "emotional_valence": self.emotional_valence,
        }


@dataclass
class RelationshipState:
    owner_id: str
    target_id: str
    trust: float = 0.5
    affinity: float = 0.5
    fear: float = 0.0
    debt: float = 0.0
    last_updated_by: str | None = None

    def apply(self, deltas: dict[str, float], source_event_log_id: str) -> None:
        self.trust = _clamp(self.trust + deltas.get("trust", 0.0))
        self.affinity = _clamp(self.affinity + deltas.get("affinity", 0.0))
        self.fear = _clamp(self.fear + deltas.get("fear", 0.0))
        self.debt = max(0.0, self.debt + deltas.get("debt", 0.0))
        self.last_updated_by = source_event_log_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "target_id": self.target_id,
            "trust": round(self.trust, 3),
            "affinity": round(self.affinity, 3),
            "fear": round(self.fear, 3),
            "debt": round(self.debt, 3),
            "last_updated_by": self.last_updated_by,
        }


@dataclass
class RumorState:
    rumor_id: str
    topic: str
    content: str
    source_chain: list[str]
    current_holder_ids: list[str]
    confidence: float
    distortion_level: float
    verified_state: str = "unknown"
    spread_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rumor_id": self.rumor_id,
            "topic": self.topic,
            "content": self.content,
            "source_chain": self.source_chain,
            "current_holder_ids": self.current_holder_ids,
            "confidence": round(self.confidence, 3),
            "distortion_level": round(self.distortion_level, 3),
            "verified_state": self.verified_state,
            "spread_count": self.spread_count,
        }


@dataclass
class EventLogEntry:
    event_log_id: str
    world_id: str
    world_time: str
    type: str
    actor_id: str | None
    target_id: str | None
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_log_id": self.event_log_id,
            "world_id": self.world_id,
            "world_time": self.world_time,
            "type": self.type,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "payload": self.payload,
        }


@dataclass
class QueuedAction:
    action_id: str
    actor_id: str
    tool_name: str
    args: dict[str, Any]
    status: str
    priority: int
    created_at: str
    execute_after_minute: int
    expires_at_minute: int
    source_memory_ids: list[str]
    reason: str
    validator_result: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "actor_id": self.actor_id,
            "tool_name": self.tool_name,
            "args": self.args,
            "status": self.status,
            "priority": self.priority,
            "created_at": self.created_at,
            "execute_after_minute": self.execute_after_minute,
            "expires_at_minute": self.expires_at_minute,
            "source_memory_ids": self.source_memory_ids,
            "reason": self.reason,
            "validator_result": self.validator_result,
        }


@dataclass
class ConversationSession:
    conversation_id: str
    client_session_id: str
    npc_id: str
    status: str
    offer_version: int
    offered_choice_ids: list[str]
    close_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "conversation_id": self.conversation_id,
            "client_session_id": self.client_session_id,
            "npc_id": self.npc_id,
            "status": self.status,
            "offer_version": self.offer_version,
            "offered_choice_ids": list(self.offered_choice_ids),
            "close_reason": self.close_reason,
        }


ACTION_EXECUTABLE_STATUSES = {"proposed", "queued", "fallback_planned"}
MAX_CLOSED_CONVERSATIONS = 64


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


class WorldSimulation:
    """Deterministic world simulation with a bounded autonomous episode loop."""

    def __init__(self, world_id: str = "demo_world_001") -> None:
        self.world_id = world_id
        self.day = 1
        self.minute_of_day = 8 * 60
        self.player = PlayerState()
        self.locations = self._build_locations()
        self.npcs = self._build_npcs()
        self.active_events = ["evt_missing_seeds"]
        self.world_events = self._build_world_events()
        self.memories: dict[str, MemoryRecord] = {}
        self.relationships = self._build_relationships()
        self.rumors = self._build_rumors()
        self._npc_schedule_locks: dict[str, int] = {}
        self.action_queue: dict[str, QueuedAction] = {}
        self.agent_runtime = AgentRuntimeV1()
        self.director = VillageDirector()
        self.episode_manager = MissingSeedsEpisodeManager()
        self._event_counter = 0
        self._memory_counter = 0
        self._action_counter = 0
        self._conversation_counter = 0
        self._event_log: list[EventLogEntry] = []
        self._pending_actor_movements: list[dict[str, Any]] = []
        self.conversations: dict[str, ConversationSession] = {}
        self._open_conversation_by_client: dict[str, str] = {}
        self._closed_conversation_ids: list[str] = []
        self.last_validator_result: dict[str, Any] | None = None
        self.last_agent_trace: dict[str, Any] | None = None
        self.last_director_trace: dict[str, Any] | None = None
        self.last_relationship_change: dict[str, Any] | None = None
        self._append_event(
            event_type="world_started",
            actor_id=None,
            target_id=None,
            payload={
                "message": "The village wakes to a missing seed bag notice.",
                "active_events": self.active_events,
            },
        )

    @property
    def world_minute(self) -> int:
        return (self.day - 1) * 24 * 60 + self.minute_of_day

    def _build_locations(self) -> dict[str, Location]:
        return {
            "square": Location(
                location_id="square",
                name="Square",
                position=(420, 240),
                capacity=8,
                tags=["public", "notice", "gossip"],
                connected_locations=["tavern", "farm", "workshop", "warehouse"],
            ),
            "tavern": Location(
                location_id="tavern",
                name="Tavern",
                position=(170, 150),
                capacity=6,
                tags=["social", "gossip", "food"],
                connected_locations=["square", "warehouse"],
            ),
            "farm": Location(
                location_id="farm",
                name="Farm",
                position=(690, 160),
                capacity=5,
                tags=["work", "tomo"],
                connected_locations=["square", "warehouse"],
            ),
            "workshop": Location(
                location_id="workshop",
                name="Workshop",
                position=(190, 440),
                capacity=4,
                tags=["work", "mira"],
                connected_locations=["square"],
            ),
            "warehouse": Location(
                location_id="warehouse",
                name="Warehouse",
                position=(670, 430),
                capacity=4,
                tags=["evidence", "storage"],
                connected_locations=["square", "tavern", "farm"],
            ),
        }

    def _build_npcs(self) -> dict[str, NPCState]:
        return {
            "mira": NPCState(
                npc_id="mira",
                name="Mira",
                role="carpenter",
                current_location="workshop",
                current_action="work",
                current_goal="finish_repairs",
                mood="tense",
                status_flags=["concerned_about_seeds"],
                schedule=[
                    ScheduleSlot(8 * 60, "work", "workshop", "finish_repairs"),
                    ScheduleSlot(12 * 60, "eat", "tavern", "hear_village_news"),
                    ScheduleSlot(14 * 60, "work", "workshop", "maintain_order"),
                    ScheduleSlot(17 * 60, "inspect", "square", "maintain_order"),
                    ScheduleSlot(18 * 60, "rest", "workshop", "recover"),
                ],
            ),
            "tomo": NPCState(
                npc_id="tomo",
                name="Tomo",
                role="farmer",
                current_location="farm",
                current_action="work",
                current_goal="protect_farm",
                mood="worried",
                status_flags=["needs_seeds"],
                schedule=[
                    ScheduleSlot(8 * 60, "work", "farm", "protect_farm"),
                    ScheduleSlot(12 * 60, "eat", "tavern", "avoid_public_shame"),
                    ScheduleSlot(13 * 60, "work", "farm", "protect_farm"),
                    ScheduleSlot(17 * 60, "visit", "square", "check_notice"),
                    ScheduleSlot(18 * 60, "rest", "farm", "recover"),
                ],
            ),
            "ivo": NPCState(
                npc_id="ivo",
                name="Ivo",
                role="tavern keeper",
                current_location="square",
                current_action="chat",
                current_goal="welcome_villagers",
                mood="watchful",
                status_flags=["rumor_hub"],
                schedule=[
                    ScheduleSlot(8 * 60, "chat", "square", "welcome_villagers"),
                    ScheduleSlot(11 * 60, "serve", "tavern", "keep_business_running"),
                    ScheduleSlot(12 * 60, "serve", "tavern", "host_lunch"),
                    ScheduleSlot(16 * 60, "check", "warehouse", "protect_reputation"),
                    ScheduleSlot(17 * 60, "serve", "tavern", "keep_business_running"),
                ],
            ),
        }

    def _build_world_events(self) -> dict[str, dict[str, Any]]:
        return {
            "evt_missing_seeds": {
                "event_id": "evt_missing_seeds",
                "state": "active",
                "phase": "public_problem",
                "phase_started_minute": self.world_minute,
                "rumor_started_minute": None,
                "confrontation_minute": None,
                "facts": [
                    {
                        "fact_id": "fact_seed_bag_missing",
                        "content": "The shared seed bag is missing.",
                        "verified": True,
                        "public": True,
                    },
                    {
                        "fact_id": "fact_ivo_near_warehouse",
                        "content": "Ivo was near the warehouse late last night.",
                        "verified": False,
                        "public": False,
                    },
                    {
                        "fact_id": "fact_torn_seed_bag",
                        "content": "The seed bag was torn open near the warehouse.",
                        "verified": False,
                        "public": False,
                    },
                ],
                "resolution_path": None,
            }
        }

    def _build_relationships(self) -> dict[str, RelationshipState]:
        relationships: dict[str, RelationshipState] = {}
        for owner_id in ["mira", "tomo", "ivo"]:
            for target_id in ["mira", "tomo", "ivo", "player"]:
                if owner_id != target_id:
                    relationships[self._relationship_key(owner_id, target_id)] = RelationshipState(
                        owner_id=owner_id,
                        target_id=target_id,
                    )
        return relationships

    def _build_rumors(self) -> dict[str, RumorState]:
        return {
            "rumor_tomo_took_seeds": RumorState(
                rumor_id="rumor_tomo_took_seeds",
                topic="missing_seeds",
                content="Tomo may have taken the public seed bag.",
                source_chain=["ivo"],
                current_holder_ids=["ivo"],
                confidence=0.32,
                distortion_level=0.18,
                spread_count=1,
            )
        }

    def tick(self) -> dict[str, Any]:
        self.minute_of_day += 1
        if self.minute_of_day >= 24 * 60:
            self.minute_of_day = 0
            self.day += 1
            self._append_event(
                event_type="day_started",
                actor_id=None,
                target_id=None,
                payload={"day": self.day},
            )

        changed_actor_ids: list[str] = []
        for npc_id, npc in self.npcs.items():
            if self._npc_schedule_locks.get(npc_id, 0) > self.world_minute:
                continue
            slot = self._current_slot(npc.schedule)
            if (
                npc.current_location != slot.location_id
                or npc.current_action != slot.action
                or npc.current_goal != slot.goal
            ):
                previous = {
                    "location_id": npc.current_location,
                    "action": npc.current_action,
                    "goal": npc.current_goal,
                }
                self._change_npc_location(
                    actor_id=npc_id,
                    location_id=slot.location_id,
                    movement_reason="schedule",
                )
                npc.current_action = slot.action
                npc.current_goal = slot.goal
                changed_actor_ids.append(npc.npc_id)
                self._append_event(
                    event_type="npc_schedule_changed",
                    actor_id=npc.npc_id,
                    target_id=slot.location_id,
                    payload={
                        "previous": previous,
                        "current": {
                            "location_id": npc.current_location,
                            "action": npc.current_action,
                            "goal": npc.current_goal,
                        },
                    },
                )

        self.director.on_tick(self)
        changed_actor_ids.extend(self._execute_due_actions())
        self.episode_manager.on_tick(self)

        return self._diff(
            reason="tick",
            changed_actor_ids=sorted(set(changed_actor_ids)),
            latest_events_count=max(1, len(changed_actor_ids) + 8),
        )

    def wait_minutes(self, minutes: int) -> dict[str, Any]:
        bounded_minutes = max(1, min(minutes, 12 * 60))
        actor_movements: list[dict[str, Any]] = []
        changed_actor_ids: set[str] = set()
        for _ in range(bounded_minutes):
            tick_diff = self.tick()
            actor_movements.extend(tick_diff.get("actor_movements", []))
            changed_actor_ids.update(tick_diff.get("changed_actor_ids", []))
        diff = self._diff(
            reason="wait_completed",
            changed_actor_ids=sorted(changed_actor_ids),
            latest_events_count=16,
        )
        diff["actor_movements"] = actor_movements + diff["actor_movements"]
        return diff

    def move_player(self, location_id: str) -> dict[str, Any]:
        if location_id not in self.locations:
            return self._rejection("location_not_found", {"location_id": location_id})

        current_location = self.locations[self.player.current_location]
        if location_id != self.player.current_location and location_id not in current_location.connected_locations:
            return self._rejection(
                "not_reachable",
                {
                    "from": self.player.current_location,
                    "to": location_id,
                },
            )

        previous_location = self.player.current_location
        self.player.current_location = location_id
        if previous_location != location_id:
            self._close_conversations_for_actor(self.player.player_id, "player_moved")
        self._append_event(
            event_type="player_moved",
            actor_id=self.player.player_id,
            target_id=location_id,
            payload={
                "from": previous_location,
                "to": location_id,
            },
        )
        return self._diff(reason="player_moved", changed_actor_ids=["player"], latest_events_count=1)

    def player_entered_location(self, location_id: str) -> dict[str, Any]:
        return self.move_player(location_id)

    def player_interact_npc(
        self,
        npc_id: str,
        interaction: str = "talk",
        client_session_id: str = "local",
    ) -> dict[str, Any]:
        validation = self._validate_player_interaction(npc_id=npc_id, interaction=interaction)
        if not validation["accepted"]:
            return {
                "type": "interaction_denied",
                "reason": validation["rejection_code"],
                "display_text": validation["display_text"],
            }

        self._append_event(
            event_type="player_interacted_npc",
            actor_id=self.player.player_id,
            target_id=npc_id,
            payload={
                "interaction": interaction,
                "client_session_id": client_session_id,
            },
        )
        conversation = self._open_conversation(
            client_session_id=client_session_id,
            npc_id=npc_id,
        )
        return self._dialogue_payload(conversation)

    def dialogue_choice(
        self,
        conversation_id: str,
        offer_version: int,
        choice_id: str,
        client_session_id: str = "local",
    ) -> dict[str, Any]:
        conversation = self.conversations.get(conversation_id)
        if conversation is None:
            return self._dialogue_rejection(
                "conversation_not_found",
                "That conversation no longer exists.",
                conversation_id=conversation_id,
            )
        if conversation.client_session_id != client_session_id:
            return self._dialogue_rejection(
                "session_mismatch",
                "That conversation belongs to another connection.",
                conversation_id=conversation_id,
            )
        if conversation.status != "open":
            return self._dialogue_rejection(
                "conversation_closed",
                "That conversation is already closed.",
                conversation_id=conversation_id,
            )
        if offer_version != conversation.offer_version:
            return self._dialogue_rejection(
                "stale_offer",
                "Those dialogue choices are no longer current.",
                conversation_id=conversation_id,
                offer_version=conversation.offer_version,
            )
        if choice_id not in conversation.offered_choice_ids:
            return self._dialogue_rejection(
                "choice_not_offered",
                "That choice was not offered in this conversation.",
                conversation_id=conversation_id,
                offer_version=conversation.offer_version,
            )

        npc_id = conversation.npc_id
        current_choice_ids = {
            choice["choice_id"]
            for choice in self._dialogue_choices(npc_id)
        }
        if choice_id not in current_choice_ids:
            self._close_conversation(conversation, "offer_invalidated")
            return self._dialogue_rejection(
                "choice_not_offered",
                "That choice is no longer available in the current world state.",
                conversation_id=conversation_id,
                offer_version=conversation.offer_version,
            )

        validation = self._validate_player_interaction(npc_id=npc_id, interaction="talk")
        if not validation["accepted"]:
            self._close_conversation(conversation, "interaction_invalidated")
            return self._dialogue_rejection(
                "interaction_invalidated",
                validation["display_text"],
                conversation_id=conversation_id,
            )

        event_id = self._append_event(
            event_type="dialogue_choice_selected",
            actor_id=self.player.player_id,
            target_id=npc_id,
            payload={
                "conversation_id": conversation_id,
                "offer_version": offer_version,
                "choice_id": choice_id,
            },
        )
        toast = self._dialogue_choice_response(npc_id, choice_id)
        changed_actor_ids = [self.player.player_id, npc_id]
        conversation_closed = choice_id in {"goodbye", "share_ivo_claim"}

        if npc_id == "ivo" and choice_id == "ask_about_missing_seeds":
            self._add_player_note(
                note_id="ivo_tomo_seed_claim",
                title="Ivo's Seed Claim",
                text="Ivo says Tomo may have taken the public seed bag.",
                source_event_log_id=event_id,
                claim_id="tomo_took_seeds",
                source_actor_id="ivo",
            )
            self._close_conversations_offering(
                "ask_about_missing_seeds",
                "offer_invalidated",
                exclude_conversation_id=conversation_id,
            )
            toast = "Ivo quietly shares a claim about Tomo and the missing seeds."
        elif npc_id == "mira" and choice_id == "share_ivo_claim":
            changed_actor_ids.extend(
                self._apply_player_claim_effect(
                    target_id="mira",
                    claim_id="tomo_took_seeds",
                    source_actor_id="ivo",
                    source_note_id="ivo_tomo_seed_claim",
                )
            )
            self._close_conversations_offering(
                "share_ivo_claim",
                "offer_invalidated",
                exclude_conversation_id=conversation_id,
            )
            toast = "Mira remembers Ivo's claim and decides to ask Tomo herself."

        next_choices: list[dict[str, str]] = []
        if conversation_closed:
            self._close_conversation(conversation, f"choice:{choice_id}")
        else:
            conversation.offer_version += 1
            next_choices = self._dialogue_choices(npc_id)
            conversation.offered_choice_ids = [choice["choice_id"] for choice in next_choices]

        diff = self._diff(
            reason="dialogue_choice",
            changed_actor_ids=sorted(set(changed_actor_ids)),
            latest_events_count=12,
            toasts=[toast],
        )
        result = {
            "type": "dialogue_result",
            "conversation_id": conversation_id,
            "npc_id": npc_id,
            "choice_id": choice_id,
            "accepted_offer_version": offer_version,
            "offer_version": conversation.offer_version,
            "choices": next_choices,
            "conversation_closed": conversation_closed,
            "toast": toast,
            "display_text": toast,
            "world_diff": diff,
        }
        return result

    def investigate_location(self, location_id: str) -> dict[str, Any]:
        return self.investigate(location_id)

    def observe(self) -> dict[str, Any]:
        event_id = self._append_event(
            event_type="player_observed",
            actor_id=self.player.player_id,
            target_id=self.player.current_location,
            payload={"location_id": self.player.current_location},
        )
        for npc_id in self._actors_at_location(self.player.current_location, include_player=False):
            self._write_memory(
                owner_id=npc_id,
                memory_type="episodic",
                topic="player_presence",
                summary=f"Player was seen at {self.locations[self.player.current_location].name}.",
                source_event_log_id=event_id,
                truth_state="verified",
                importance=0.2,
            )
        return self._diff(reason="player_observed", changed_actor_ids=["player"], latest_events_count=1)

    def talk_to(self, target_id: str, topic: str = "missing_seeds") -> dict[str, Any]:
        validation = self._validate_tool(
            tool_name="talk_to",
            actor_id=self.player.player_id,
            target_id=target_id,
            topic=topic,
        )
        if not validation["accepted"]:
            return self._tool_rejection(validation)

        event_id = self._append_event(
            event_type="dialogue_started",
            actor_id=self.player.player_id,
            target_id=target_id,
            payload={
                "topic": topic,
                "line": self._dialogue_line(target_id, topic),
            },
        )
        self._write_memory(
            owner_id=target_id,
            memory_type="episodic",
            topic=topic,
            summary=f"Player asked about {topic}.",
            source_event_log_id=event_id,
            truth_state="verified",
            importance=0.35,
        )
        return self._diff(reason="dialogue_started", changed_actor_ids=[target_id], latest_events_count=2)

    def share_claim(self, target_id: str, claim_id: str) -> dict[str, Any]:
        if claim_id not in self._claim_definitions():
            return self._rejection("claim_not_found", {"claim_id": claim_id})

        claim = self._claim_payload(claim_id)
        validation = self._validate_tool(
            tool_name="share_memory",
            actor_id=self.player.player_id,
            target_id=target_id,
            topic=claim["topic"],
        )
        if not validation["accepted"]:
            return self._tool_rejection(validation)

        changed_actor_ids = self._apply_player_claim_effect(
            target_id=target_id,
            claim_id=claim_id,
        )
        return self._diff(reason="memory_shared", changed_actor_ids=changed_actor_ids, latest_events_count=8)

    def gossip(self, actor_id: str, target_id: str, rumor_id: str) -> dict[str, Any]:
        validation = self._validate_tool(
            tool_name="npc_gossip",
            actor_id=actor_id,
            target_id=target_id,
            topic="missing_seeds",
            rumor_id=rumor_id,
        )
        if not validation["accepted"]:
            return self._tool_rejection(validation)

        self._execute_validated_tool(
            QueuedAction(
                action_id="direct_gossip",
                actor_id=actor_id,
                tool_name="npc_gossip",
                args={"actor_id": actor_id, "target_id": target_id, "rumor_id": rumor_id},
                status="validating",
                priority=0,
                created_at=self.current_time,
                execute_after_minute=self.world_minute,
                expires_at_minute=self.world_minute + 1,
                source_memory_ids=[],
                reason="Manual dashboard NPC gossip.",
                validator_result=validation,
            )
        )
        return self._diff(reason="rumor_spread", changed_actor_ids=[actor_id, target_id], latest_events_count=4)

    def investigate(self, subject_id: str) -> dict[str, Any]:
        validation = self._validate_tool(
            tool_name="investigate",
            actor_id=self.player.player_id,
            target_id=subject_id,
            topic="missing_seeds",
        )
        if not validation["accepted"]:
            return self._tool_rejection(validation)

        self._mark_torn_seed_evidence_public()
        self.episode_manager.set_phase(self, "evidence_found")
        event_id = self._append_event(
            event_type="evidence_found",
            actor_id=self.player.player_id,
            target_id=subject_id,
            payload={
                "evidence_id": "torn_seed_bag",
                "fact_id": "fact_torn_seed_bag",
                "content": "The seed bag was torn open near the warehouse.",
                "event_phase": self.world_events["evt_missing_seeds"]["phase"],
            },
        )
        self._write_memory(
            owner_id=self.player.player_id,
            memory_type="evidence",
            topic="missing_seeds",
            summary="Player found a torn seed bag near the warehouse.",
            source_event_log_id=event_id,
            truth_state="verified",
            importance=0.9,
        )
        return self._diff(reason="evidence_found", changed_actor_ids=["player"], latest_events_count=4)

    def player_share_evidence(self, target_id: str, evidence_id: str = "torn_seed_bag") -> dict[str, Any]:
        validation = self._validate_tool(
            tool_name="player_share_evidence",
            actor_id=self.player.player_id,
            target_id=target_id,
            evidence_id=evidence_id,
            topic="missing_seeds",
        )
        if not validation["accepted"]:
            return self._tool_rejection(validation)

        self.episode_manager.set_phase(self, "resolution_pending")
        event_id = self._append_event(
            event_type="evidence_shared",
            actor_id=self.player.player_id,
            target_id=target_id,
            payload={
                "evidence_id": evidence_id,
                "summary": "Player showed Mira the torn seed bag evidence.",
            },
        )
        self._write_memory(
            owner_id=target_id,
            memory_type="evidence",
            topic="missing_seeds",
            summary="Player showed evidence that the seed bag was torn near the warehouse.",
            source_event_log_id=event_id,
            truth_state="verified",
            target_id=None,
            importance=0.95,
            emotional_valence=0.15,
        )
        self.episode_manager.resolve_event(self, "reconciled")
        return self._diff(reason="evidence_shared", changed_actor_ids=[target_id, "player"], latest_events_count=12)

    def resolve_event(self, event_id: str, path: str) -> dict[str, Any]:
        validation = self._validate_tool(
            tool_name="resolve_event",
            actor_id="player",
            target_id=event_id,
            topic="missing_seeds",
            path=path,
            internal_call=False,
        )
        return self._tool_rejection(validation)

    def run_autonomous_episode_step(self, actor_id: str = "mira") -> dict[str, Any]:
        if actor_id not in self.npcs:
            return self._rejection("actor_not_found", {"actor_id": actor_id})

        triggering_memory = self._latest_relevant_memory(actor_id)
        decision = self.agent_runtime.propose_step(self, actor_id, triggering_memory)
        self.last_agent_trace = decision.to_dict()
        director_decision = self.director.review_agent_decision(self, decision)
        self._append_event(
            event_type="agent_runtime_step",
            actor_id=actor_id,
            target_id=director_decision.queued_action_ids[0] if director_decision.queued_action_ids else None,
            payload=self.last_agent_trace,
        )
        return self._diff(reason="autonomous_step", changed_actor_ids=[actor_id], latest_events_count=4)

    def reject_client_message(self, message_type: str, reason: str) -> dict[str, Any]:
        self._append_event(
            event_type="client_message_rejected",
            actor_id=self.player.player_id,
            target_id=None,
            payload={"message_type": message_type, "reason": reason},
        )
        return self._diff(reason="client_message_rejected", changed_actor_ids=[], latest_events_count=1)

    def close_conversations_for_session(self, client_session_id: str) -> None:
        conversation_id = self._open_conversation_by_client.get(client_session_id)
        if conversation_id is None:
            return
        conversation = self.conversations.get(conversation_id)
        if conversation is not None:
            self._close_conversation(conversation, "client_disconnected")

    def snapshot(self) -> dict[str, Any]:
        occupants = self._location_occupants()
        event = self.world_events["evt_missing_seeds"]
        return {
            "world_id": self.world_id,
            "day": self.day,
            "time": self.current_time,
            "minute_of_day": self.minute_of_day,
            "world_minute": self.world_minute,
            "active_events": self.active_events,
            "episode_phase": event["phase"],
            "world_events": self.world_events,
            "event_log_cursor": self._event_counter,
            "locations": {
                location_id: location.to_dict(occupants.get(location_id, []))
                for location_id, location in self.locations.items()
            },
            "player": self.player.to_dict(),
            "npcs": {npc_id: npc.to_dict() for npc_id, npc in self.npcs.items()},
            "memories": self._memories_by_owner(),
            "relationships": {
                key: relationship.to_dict()
                for key, relationship in sorted(self.relationships.items())
            },
            "rumors": {
                rumor_id: rumor.to_dict()
                for rumor_id, rumor in sorted(self.rumors.items())
            },
            "action_queue": [action.to_dict() for action in self._sorted_actions()],
            "last_validator_result": self.last_validator_result,
            "last_agent_trace": self.last_agent_trace,
            "last_director_trace": self.last_director_trace,
            "director_state": self.director.to_dict(),
            "last_relationship_change": self.last_relationship_change,
            "presentation": self._presentation(),
            "latest_events": self.events(limit=8),
        }

    @property
    def current_time(self) -> str:
        return format_world_time(self.day, self.minute_of_day)

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 200))
        return [entry.to_dict() for entry in self._event_log[-bounded_limit:]]

    def enqueue_action(
        self,
        actor_id: str,
        tool_name: str,
        args: dict[str, Any],
        priority: int,
        execute_after_minute: int | None = None,
        expires_at_minute: int | None = None,
        source_memory_ids: list[str] | None = None,
        reason: str = "",
        status: str = "queued",
    ) -> str:
        self._action_counter += 1
        action_id = f"act_{self._action_counter:06d}"
        action = QueuedAction(
            action_id=action_id,
            actor_id=actor_id,
            tool_name=tool_name,
            args=args,
            status=status,
            priority=priority,
            created_at=self.current_time,
            execute_after_minute=execute_after_minute if execute_after_minute is not None else self.world_minute,
            expires_at_minute=expires_at_minute if expires_at_minute is not None else self.world_minute + 60,
            source_memory_ids=source_memory_ids or [],
            reason=reason,
            validator_result=None,
        )
        self.action_queue[action_id] = action
        self._append_event(
            event_type="action_queued",
            actor_id=actor_id,
            target_id=action_id,
            payload=action.to_dict(),
        )
        return action_id

    def has_pending_action(self, actor_id: str, tool_name: str, args: dict[str, Any]) -> bool:
        comparable_args = {key: value for key, value in args.items() if key != "actor_id"}
        for action in self.action_queue.values():
            if action.status not in ACTION_EXECUTABLE_STATUSES:
                continue
            if action.actor_id != actor_id or action.tool_name != tool_name:
                continue
            action_args = {key: value for key, value in action.args.items() if key != "actor_id"}
            if action_args == comparable_args:
                return True
        return False

    def _execute_due_actions(self) -> list[str]:
        changed_actor_ids: list[str] = []
        due_actions = [
            action
            for action in self._sorted_actions()
            if action.status in ACTION_EXECUTABLE_STATUSES and action.execute_after_minute <= self.world_minute
        ]
        for action in due_actions:
            if action.expires_at_minute < self.world_minute:
                action.status = "expired"
                self._append_event(
                    event_type="action_expired",
                    actor_id=action.actor_id,
                    target_id=action.action_id,
                    payload=action.to_dict(),
                )
                continue

            action.status = "validating"
            validation = self._validate_action(action)
            action.validator_result = validation
            self._append_event(
                event_type="action_validated",
                actor_id=action.actor_id,
                target_id=action.action_id,
                payload={"action_id": action.action_id, "validator_result": validation},
            )
            if not validation["accepted"]:
                action.status = "rejected"
                self._append_event(
                    event_type="action_rejected",
                    actor_id=action.actor_id,
                    target_id=action.action_id,
                    payload=action.to_dict(),
                )
                self._plan_fallback_for_rejection(action, validation)
                continue

            changed_actor_ids.extend(self._execute_validated_tool(action))
            action.status = "executed"
            self._append_event(
                event_type="action_executed",
                actor_id=action.actor_id,
                target_id=action.action_id,
                payload=action.to_dict(),
            )
            self.episode_manager.on_action_executed(self, action)
        return changed_actor_ids

    def _execute_validated_tool(self, action: QueuedAction) -> list[str]:
        args = action.args
        if action.tool_name == "npc_move_to":
            return self._execute_npc_move_to(str(args["actor_id"]), str(args["location_id"]))
        if action.tool_name == "npc_talk_to":
            return self._execute_npc_talk_to(str(args["actor_id"]), str(args["target_id"]), str(args["topic"]))
        if action.tool_name == "npc_share_memory":
            return self._execute_npc_share_memory(str(args["actor_id"]), str(args["target_id"]), str(args["memory_id"]))
        if action.tool_name == "npc_gossip":
            return self._execute_npc_gossip(str(args["actor_id"]), str(args["target_id"]), str(args["rumor_id"]))
        if action.tool_name == "npc_investigate":
            return self._execute_npc_investigate(str(args["actor_id"]), str(args["subject_id"]))
        if action.tool_name == "player_share_evidence":
            self.player_share_evidence(str(args["target_id"]), str(args.get("evidence_id", "torn_seed_bag")))
            return ["player", str(args["target_id"])]
        return []

    def _execute_npc_move_to(self, actor_id: str, location_id: str) -> list[str]:
        npc = self.npcs[actor_id]
        previous = self._change_npc_location(
            actor_id=actor_id,
            location_id=location_id,
            movement_reason="validated_action",
        )
        npc.current_action = "move"
        npc.current_goal = f"move_to_{location_id}"
        self._npc_schedule_locks[actor_id] = self.world_minute + 30
        self._append_event(
            event_type="npc_moved",
            actor_id=actor_id,
            target_id=location_id,
            payload={"from": previous, "to": location_id},
        )
        return [actor_id]

    def _execute_npc_talk_to(self, actor_id: str, target_id: str, topic: str) -> list[str]:
        line = self.agent_runtime.provider.generate_dialogue(
            {"speaker_id": actor_id, "target_id": target_id, "topic": topic}
        ).line
        event_id = self._append_event(
            event_type="npc_dialogue_started",
            actor_id=actor_id,
            target_id=target_id,
            payload={"topic": topic, "line": line},
        )
        self._npc_schedule_locks[actor_id] = self.world_minute + 20
        self._npc_schedule_locks[target_id] = self.world_minute + 20
        self._write_memory(
            owner_id=actor_id,
            memory_type="episodic",
            topic=topic,
            summary=f"{self.npcs[actor_id].name} questioned {self.npcs[target_id].name} about {topic}.",
            source_event_log_id=event_id,
            truth_state="verified",
            target_id=target_id,
            importance=0.58,
            emotional_valence=-0.12,
        )
        self._write_memory(
            owner_id=target_id,
            memory_type="episodic",
            topic=topic,
            summary=f"{self.npcs[actor_id].name} questioned {self.npcs[target_id].name} about {topic}.",
            source_event_log_id=event_id,
            truth_state="verified",
            target_id=actor_id,
            importance=0.62,
            emotional_valence=-0.28,
        )
        if actor_id == "mira" and target_id == "tomo" and topic == "missing_seeds":
            if "suspicious_of_tomo" not in self.npcs["mira"].status_flags:
                self.npcs["mira"].status_flags.append("suspicious_of_tomo")
            self.npcs["mira"].mood = "stern"
            self.npcs["tomo"].mood = "hurt"
            self._change_relationship("tomo", "mira", {"trust": -0.08, "affinity": -0.04}, event_id)
            self._spread_rumor_state("mira", "tomo", "rumor_tomo_took_seeds")
        return [actor_id, target_id]

    def _execute_npc_share_memory(self, actor_id: str, target_id: str, memory_id: str) -> list[str]:
        source_memory = self.memories[memory_id]
        event_id = self._append_event(
            event_type="npc_memory_shared",
            actor_id=actor_id,
            target_id=target_id,
            payload={"memory_id": memory_id, "summary": source_memory.summary},
        )
        self._write_memory(
            owner_id=target_id,
            memory_type=source_memory.type,
            topic=source_memory.topic,
            summary=source_memory.summary,
            source_event_log_id=event_id,
            truth_state=source_memory.truth_state,
            target_id=source_memory.target_id,
            importance=source_memory.importance,
            emotional_valence=source_memory.emotional_valence,
        )
        return [actor_id, target_id]

    def _execute_npc_gossip(self, actor_id: str, target_id: str, rumor_id: str) -> list[str]:
        event_id = self._append_event(
            event_type="rumor_spread",
            actor_id=actor_id,
            target_id=target_id,
            payload={"rumor": self._spread_rumor_state(actor_id, target_id, rumor_id).to_dict()},
        )
        rumor = self.rumors[rumor_id]
        self._write_memory(
            owner_id=target_id,
            memory_type="rumor",
            topic=rumor.topic,
            summary=rumor.content,
            source_event_log_id=event_id,
            truth_state="unverified",
            target_id="tomo",
            importance=0.62,
            emotional_valence=-0.3,
        )
        return [actor_id, target_id]

    def _execute_npc_investigate(self, actor_id: str, subject_id: str) -> list[str]:
        event_id = self._append_event(
            event_type="npc_investigated",
            actor_id=actor_id,
            target_id=subject_id,
            payload={"topic": "missing_seeds", "subject_id": subject_id},
        )
        summary = f"{self.npcs[actor_id].name} investigated {self.locations[subject_id].name}."
        if subject_id == "warehouse":
            self._mark_torn_seed_evidence_public()
            summary = f"{self.npcs[actor_id].name} found torn seed bag evidence near the warehouse."
        self._write_memory(
            owner_id=actor_id,
            memory_type="evidence" if subject_id == "warehouse" else "episodic",
            topic="missing_seeds",
            summary=summary,
            source_event_log_id=event_id,
            truth_state="verified",
            importance=0.82,
        )
        return [actor_id]

    def _validate_action(self, action: QueuedAction) -> dict[str, Any]:
        return self._validate_tool(
            tool_name=action.tool_name,
            actor_id=str(action.args.get("actor_id", action.actor_id)),
            target_id=action.args.get("target_id"),
            topic=str(action.args.get("topic", "missing_seeds")),
            location_id=action.args.get("location_id"),
            rumor_id=action.args.get("rumor_id"),
            memory_id=action.args.get("memory_id"),
            evidence_id=action.args.get("evidence_id"),
            subject_id=action.args.get("subject_id"),
            path=action.args.get("path"),
            internal_call=bool(action.args.get("internal_call", False)),
        )

    def _validate_tool(
        self,
        tool_name: str,
        actor_id: str,
        target_id: str | None = None,
        topic: str = "missing_seeds",
        location_id: str | None = None,
        rumor_id: str | None = None,
        memory_id: str | None = None,
        evidence_id: str | None = None,
        subject_id: str | None = None,
        path: str | None = None,
        internal_call: bool = False,
    ) -> dict[str, Any]:
        result = {
            "tool_name": tool_name,
            "actor_id": actor_id,
            "target_id": target_id,
            "topic": topic,
            "accepted": False,
            "rejection_code": None,
            "debug_reason": "",
        }
        actor_ids = self._actor_ids()
        if tool_name == "resolve_event":
            if internal_call and target_id in self.world_events and path:
                result["accepted"] = True
                result["debug_reason"] = "Scenario engine may resolve the event."
            else:
                result["rejection_code"] = "internal_only"
                result["debug_reason"] = "resolve_event is callable only from the scenario engine."
        elif actor_id not in actor_ids:
            result["rejection_code"] = "actor_not_found"
            result["debug_reason"] = f"Unknown actor {actor_id}."
        elif tool_name in {"talk_to", "share_memory"}:
            if target_id not in self.npcs:
                result["rejection_code"] = "target_not_found"
                result["debug_reason"] = f"Unknown NPC target {target_id}."
            elif self._actor_location(actor_id) != self._actor_location(str(target_id)):
                result["rejection_code"] = "target_unavailable"
                result["debug_reason"] = "Actor and target must be in the same location."
            else:
                result["accepted"] = True
                result["debug_reason"] = "Validator accepted player social tool."
        elif tool_name == "investigate":
            if target_id not in self.locations:
                result["rejection_code"] = "location_not_found"
                result["debug_reason"] = f"Unknown investigation location {target_id}."
            elif self.player.current_location != target_id:
                result["rejection_code"] = "not_reachable"
                result["debug_reason"] = "Player must be at the location to investigate it."
            else:
                result["accepted"] = True
                result["debug_reason"] = "Validator accepted player investigation."
        elif tool_name == "npc_move_to":
            if actor_id not in self.npcs:
                result["rejection_code"] = "actor_not_found"
                result["debug_reason"] = "Only NPCs may use npc_move_to."
            elif location_id not in self.locations:
                result["rejection_code"] = "location_not_found"
                result["debug_reason"] = f"Unknown location {location_id}."
            else:
                result["accepted"] = True
                result["debug_reason"] = "Validator accepted NPC movement."
        elif tool_name == "npc_talk_to":
            if actor_id not in self.npcs:
                result["rejection_code"] = "actor_not_found"
                result["debug_reason"] = "Only NPCs may initiate npc_talk_to."
            elif target_id not in self.npcs:
                result["rejection_code"] = "target_not_found"
                result["debug_reason"] = f"Unknown NPC target {target_id}."
            elif self._actor_location(actor_id) != self._actor_location(str(target_id)):
                result["rejection_code"] = "target_unavailable"
                result["debug_reason"] = "NPCs must share a location before talking."
            else:
                result["accepted"] = True
                result["debug_reason"] = "Validator accepted NPC talk."
        elif tool_name == "npc_share_memory":
            if actor_id not in self.npcs or target_id not in self.npcs:
                result["rejection_code"] = "target_not_found"
                result["debug_reason"] = "Both actor and target must be NPCs."
            elif self._actor_location(actor_id) != self._actor_location(str(target_id)):
                result["rejection_code"] = "target_unavailable"
                result["debug_reason"] = "NPCs must share a location before sharing memory."
            elif memory_id not in self.memories:
                result["rejection_code"] = "memory_not_found"
                result["debug_reason"] = f"Unknown memory {memory_id}."
            elif self.memories[str(memory_id)].owner_id != actor_id:
                result["rejection_code"] = "memory_not_owned"
                result["debug_reason"] = "Actor does not own the memory."
            else:
                result["accepted"] = True
                result["debug_reason"] = "Validator accepted NPC memory share."
        elif tool_name == "npc_gossip":
            if actor_id not in self.npcs or target_id not in self.npcs:
                result["rejection_code"] = "target_not_found"
                result["debug_reason"] = "Both actor and target must be NPCs."
            elif self._actor_location(actor_id) != self._actor_location(str(target_id)):
                result["rejection_code"] = "target_unavailable"
                result["debug_reason"] = "NPCs must share a location before gossip."
            elif rumor_id is None or rumor_id not in self.rumors:
                result["rejection_code"] = "rumor_not_found"
                result["debug_reason"] = "Rumor must exist before it can spread."
            elif actor_id not in self.rumors[str(rumor_id)].current_holder_ids:
                result["rejection_code"] = "memory_not_owned"
                result["debug_reason"] = "Actor does not hold this rumor."
            elif target_id in self.rumors[str(rumor_id)].current_holder_ids:
                result["rejection_code"] = "duplicate_information"
                result["debug_reason"] = "Target already knows this rumor."
            else:
                result["accepted"] = True
                result["debug_reason"] = "Validator accepted NPC gossip."
        elif tool_name == "npc_investigate":
            if actor_id not in self.npcs:
                result["rejection_code"] = "actor_not_found"
                result["debug_reason"] = "Only NPCs may use npc_investigate."
            elif subject_id not in self.locations:
                result["rejection_code"] = "location_not_found"
                result["debug_reason"] = f"Unknown investigation subject {subject_id}."
            elif self._actor_location(actor_id) != subject_id:
                result["rejection_code"] = "target_unavailable"
                result["debug_reason"] = "NPC must be at the location before investigating."
            else:
                result["accepted"] = True
                result["debug_reason"] = "Validator accepted NPC investigation."
        elif tool_name == "player_share_evidence":
            if target_id not in self.npcs:
                result["rejection_code"] = "target_not_found"
                result["debug_reason"] = f"Unknown NPC target {target_id}."
            elif self.player.current_location != self._actor_location(str(target_id)):
                result["rejection_code"] = "target_unavailable"
                result["debug_reason"] = "Player must be near the NPC to share evidence."
            elif not self._player_has_evidence(str(evidence_id or "torn_seed_bag")):
                result["rejection_code"] = "evidence_not_found"
                result["debug_reason"] = "Player has not found this evidence yet."
            else:
                result["accepted"] = True
                result["debug_reason"] = "Validator accepted evidence share."
        else:
            result["rejection_code"] = "tool_not_found"
            result["debug_reason"] = f"Unknown tool {tool_name}."

        self.last_validator_result = result
        return result

    def _tool_rejection(self, validation: dict[str, Any]) -> dict[str, Any]:
        self.last_validator_result = validation
        self._append_event(
            event_type="tool_rejected",
            actor_id=validation.get("actor_id"),
            target_id=validation.get("target_id"),
            payload=validation,
        )
        return self._diff(reason=validation["rejection_code"], changed_actor_ids=[], latest_events_count=1)

    def _plan_fallback_for_rejection(self, action: QueuedAction, validation: dict[str, Any]) -> None:
        self.director.on_action_rejected(self, action, validation)

    def _agent_planner_after_memory(self, memory: MemoryRecord) -> list[str]:
        if memory.owner_id not in self.npcs:
            return []

        changed_actor_ids: list[str] = [memory.owner_id]
        self.episode_manager.on_claim_memory(self, memory)

        if memory.owner_id == "mira" and memory.topic == "missing_seeds" and memory.target_id == "tomo":
            cautious = self._mira_has_reflection_modifier()
            deltas = {"trust": -0.015, "affinity": -0.005} if cautious else {"trust": -0.08, "affinity": -0.03}
            relationship_event_id = self._change_relationship("mira", "tomo", deltas, memory.memory_id)
            npc = self.npcs["mira"]
            npc.current_goal = "investigate_missing_seeds"
            npc.current_action = "consider_rumor"
            npc.mood = "skeptical" if cautious else "suspicious"
            flag = "checking_before_accusing" if cautious else "suspicious_of_tomo"
            if flag not in npc.status_flags:
                npc.status_flags.append(flag)
            rumor = self.rumors["rumor_tomo_took_seeds"]
            if "mira" not in rumor.current_holder_ids:
                rumor.current_holder_ids.append("mira")
                rumor.source_chain.append("player")
                rumor.spread_count += 1
            rumor.confidence = _clamp(max(rumor.confidence, 0.38 if cautious else 0.46))
            self._write_memory(
                owner_id="mira",
                memory_type="rumor",
                topic="missing_seeds",
                summary=rumor.content,
                source_event_log_id=relationship_event_id,
                truth_state="unverified",
                target_id="tomo",
                importance=0.7,
                emotional_valence=-0.2 if cautious else -0.35,
            )

        self.director.on_memory_written(self, memory)
        return changed_actor_ids

    def _change_relationship(
        self,
        owner_id: str,
        target_id: str,
        deltas: dict[str, float],
        source_memory_id: str,
    ) -> str:
        relationship = self.relationships[self._relationship_key(owner_id, target_id)]
        event_id = self._append_event(
            event_type="relationship_changed",
            actor_id=owner_id,
            target_id=target_id,
            payload={
                "deltas": deltas,
                "source_memory_id": source_memory_id,
            },
        )
        relationship.apply(deltas, source_event_log_id=event_id)
        self.last_relationship_change = relationship.to_dict() | {"deltas": deltas}
        return event_id

    def _write_memory(
        self,
        owner_id: str,
        memory_type: str,
        topic: str,
        summary: str,
        source_event_log_id: str,
        truth_state: str = "unverified",
        target_id: str | None = None,
        importance: float = 0.5,
        emotional_valence: float = 0.0,
    ) -> MemoryRecord:
        self._memory_counter += 1
        memory = MemoryRecord(
            memory_id=f"mem_{self._memory_counter:06d}",
            type=memory_type,
            owner_id=owner_id,
            topic=topic,
            summary=summary,
            world_time=self.current_time,
            source_event_log_id=source_event_log_id,
            truth_state=truth_state,
            target_id=target_id,
            importance=importance,
            emotional_valence=emotional_valence,
        )
        self.memories[memory.memory_id] = memory
        self._append_event(
            event_type="memory_written",
            actor_id=owner_id,
            target_id=target_id,
            payload=memory.to_dict(),
        )
        return memory

    def _write_reflection_memory(
        self,
        owner_id: str,
        summary: str,
        source_event_log_id: str,
        modifier: str,
    ) -> MemoryRecord:
        npc = self.npcs[owner_id]
        for behavior_modifier in {modifier, "rumor_skepticism", "investigate_before_accuse"}:
            if behavior_modifier not in npc.behavior_modifiers:
                npc.behavior_modifiers.append(behavior_modifier)
        return self._write_memory(
            owner_id=owner_id,
            memory_type="reflection",
            topic="missing_seeds",
            summary=summary,
            source_event_log_id=source_event_log_id,
            truth_state="verified",
            target_id="tomo",
            importance=0.88,
            emotional_valence=0.1,
        )

    def _memories_by_owner(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for memory in self.memories.values():
            grouped.setdefault(memory.owner_id, []).append(memory.to_dict())
        return grouped

    def _claim_definitions(self) -> dict[str, dict[str, Any]]:
        return {
            "tomo_took_seeds": {
                "topic": "missing_seeds",
                "summary": "Player says Tomo may have taken the public seed bag.",
                "relayed_summary": "Player relayed Ivo's claim that Tomo may have taken the public seed bag.",
                "claim_target_id": "tomo",
                "truth_state": "unverified",
                "importance": 0.75,
                "emotional_valence": -0.45,
            },
            "ivo_near_warehouse": {
                "topic": "missing_seeds",
                "summary": "Player says Ivo was near the warehouse late last night.",
                "claim_target_id": "ivo",
                "truth_state": "unverified",
                "importance": 0.68,
                "emotional_valence": -0.28,
            },
            "torn_seed_bag": {
                "topic": "missing_seeds",
                "summary": "Player says the seed bag was torn open near the warehouse.",
                "claim_target_id": None,
                "truth_state": "verified",
                "importance": 0.9,
                "emotional_valence": -0.1,
            },
        }

    def _claim_payload(self, claim_id: str) -> dict[str, Any]:
        return self._claim_definitions()[claim_id]

    def _apply_player_claim_effect(
        self,
        target_id: str,
        claim_id: str,
        source_actor_id: str | None = None,
        source_note_id: str | None = None,
    ) -> list[str]:
        claim = self._claim_payload(claim_id)
        summary = claim["summary"]
        if source_actor_id == "ivo":
            summary = claim.get("relayed_summary", summary)
        event_payload = {
            "claim_id": claim_id,
            "topic": claim["topic"],
            "claim": summary,
            "claim_target_id": claim.get("claim_target_id"),
            "truth_state": claim["truth_state"],
        }
        if source_actor_id is not None:
            event_payload["source_actor_id"] = source_actor_id
        if source_note_id is not None:
            event_payload["source_note_id"] = source_note_id
        event_id = self._append_event(
            event_type="memory_shared",
            actor_id=self.player.player_id,
            target_id=target_id,
            payload=event_payload,
        )
        memory = self._write_memory(
            owner_id=target_id,
            memory_type="episodic",
            topic=claim["topic"],
            summary=summary,
            source_event_log_id=event_id,
            truth_state=claim["truth_state"],
            target_id=claim.get("claim_target_id"),
            importance=claim["importance"],
            emotional_valence=claim["emotional_valence"],
        )
        changed_actor_ids = [target_id]
        changed_actor_ids.extend(self._agent_planner_after_memory(memory))
        return sorted(set(changed_actor_ids))

    def _dialogue_line(self, target_id: str, topic: str) -> str:
        if topic != "missing_seeds":
            return f"{self.npcs[target_id].name} has nothing new to say."
        return {
            "mira": "If someone took community seeds, I need proof before the village turns on itself.",
            "tomo": "I did not take them. Everyone is already looking at me like I did.",
            "ivo": "People talk when supplies go missing. I only repeat what I hear.",
        }.get(target_id, "No response.")

    def _spread_rumor_state(self, actor_id: str, target_id: str, rumor_id: str) -> RumorState:
        rumor = self.rumors[rumor_id]
        if actor_id not in rumor.current_holder_ids:
            rumor.current_holder_ids.append(actor_id)
        if target_id not in rumor.current_holder_ids:
            rumor.current_holder_ids.append(target_id)
            rumor.spread_count += 1
        if actor_id not in rumor.source_chain:
            rumor.source_chain.append(actor_id)
        rumor.distortion_level = _clamp(rumor.distortion_level + 0.03)
        rumor.confidence = _clamp(rumor.confidence + 0.05)
        return rumor

    def _mark_torn_seed_evidence_public(self) -> None:
        event = self.world_events["evt_missing_seeds"]
        for fact in event["facts"]:
            if fact["fact_id"] == "fact_torn_seed_bag":
                fact["verified"] = True
                fact["public"] = True

    def _validate_player_interaction(self, npc_id: str, interaction: str) -> dict[str, Any]:
        if npc_id not in self.npcs:
            return {
                "accepted": False,
                "rejection_code": "npc_not_found",
                "display_text": "No one is close enough to talk right now.",
            }
        if interaction != "talk":
            return {
                "accepted": False,
                "rejection_code": "unsupported_interaction",
                "display_text": "That interaction is not available yet.",
            }
        if self.player.current_location != self.npcs[npc_id].current_location:
            return {
                "accepted": False,
                "rejection_code": "not_nearby",
                "display_text": f"{self.npcs[npc_id].name} is not close enough right now.",
            }
        if "uninteractable" in self.npcs[npc_id].status_flags:
            return {
                "accepted": False,
                "rejection_code": "not_interactable",
                "display_text": f"{self.npcs[npc_id].name} is busy right now.",
            }
        return {"accepted": True, "rejection_code": None, "display_text": ""}

    def _dialogue_payload(self, conversation: ConversationSession) -> dict[str, Any]:
        npc_id = conversation.npc_id
        dialogues = {
            "mira": {
                "line": "Good to see you. I am checking the workshop list before the afternoon.",
            },
            "tomo": {
                "line": "Morning. I am keeping an eye on the fields while the weather holds.",
            },
            "ivo": {
                "line": "Welcome in. If you need a warm meal or a local story, you came to the right place.",
            },
        }
        dialogue = dialogues[npc_id]
        choices = self._dialogue_choices(npc_id)
        conversation.offered_choice_ids = [choice["choice_id"] for choice in choices]
        return {
            "type": "dialogue_opened",
            "conversation_id": conversation.conversation_id,
            "offer_version": conversation.offer_version,
            "npc_id": npc_id,
            "speaker": self.npcs[npc_id].name,
            "line": dialogue["line"],
            "choices": choices,
        }

    def _dialogue_choices(self, npc_id: str) -> list[dict[str, str]]:
        choices = [
            {"choice_id": "greet", "text": "Greet"},
            {"choice_id": "ask_about_work", "text": "Ask About Work"},
            {"choice_id": "ask_about_village", "text": "Ask About Village"},
        ]
        if (
            npc_id == "ivo"
            and self._missing_seeds_accepts_claims()
            and not self._player_has_claim_note("tomo_took_seeds")
        ):
            choices.append(
                {
                    "choice_id": "ask_about_missing_seeds",
                    "text": "Ask About the Missing Seeds",
                }
            )
        if (
            npc_id == "mira"
            and self._missing_seeds_accepts_claims()
            and self._player_has_claim_note("tomo_took_seeds")
            and not self._npc_has_received_claim("mira", "tomo_took_seeds")
        ):
            choices.append(
                {
                    "choice_id": "share_ivo_claim",
                    "text": "Share Ivo's Claim About Tomo",
                }
            )
        choices.append({"choice_id": "goodbye", "text": "Goodbye"})
        return choices

    def _open_conversation(
        self,
        client_session_id: str,
        npc_id: str,
    ) -> ConversationSession:
        existing_id = self._open_conversation_by_client.get(client_session_id)
        if existing_id is not None:
            existing = self.conversations.get(existing_id)
            if existing is not None:
                self._close_conversation(existing, "superseded")

        self._conversation_counter += 1
        conversation = ConversationSession(
            conversation_id=f"conv_{self._conversation_counter:06d}",
            client_session_id=client_session_id,
            npc_id=npc_id,
            status="open",
            offer_version=1,
            offered_choice_ids=[],
        )
        self.conversations[conversation.conversation_id] = conversation
        self._open_conversation_by_client[client_session_id] = conversation.conversation_id
        return conversation

    def _close_conversation(
        self,
        conversation: ConversationSession,
        reason: str,
    ) -> None:
        if conversation.status != "open":
            return
        conversation.status = "closed"
        conversation.close_reason = reason
        if self._open_conversation_by_client.get(conversation.client_session_id) == conversation.conversation_id:
            del self._open_conversation_by_client[conversation.client_session_id]
        self._closed_conversation_ids.append(conversation.conversation_id)
        self._prune_closed_conversations()

    def _close_conversations_for_actor(self, actor_id: str, reason: str) -> None:
        for conversation in list(self.conversations.values()):
            if conversation.status != "open":
                continue
            if actor_id == self.player.player_id or conversation.npc_id == actor_id:
                self._close_conversation(conversation, reason)

    def _close_conversations_offering(
        self,
        choice_id: str,
        reason: str,
        *,
        exclude_conversation_id: str | None = None,
    ) -> None:
        for conversation in list(self.conversations.values()):
            if conversation.status != "open":
                continue
            if conversation.conversation_id == exclude_conversation_id:
                continue
            if choice_id in conversation.offered_choice_ids:
                self._close_conversation(conversation, reason)

    def _prune_closed_conversations(self) -> None:
        while len(self._closed_conversation_ids) > MAX_CLOSED_CONVERSATIONS:
            conversation_id = self._closed_conversation_ids.pop(0)
            self.conversations.pop(conversation_id, None)

    def _dialogue_rejection(
        self,
        code: str,
        display_text: str,
        *,
        conversation_id: str,
        offer_version: int | None = None,
    ) -> dict[str, Any]:
        response: dict[str, Any] = {
            "type": "dialogue_rejected",
            "reason": code,
            "code": code,
            "conversation_id": conversation_id,
            "display_text": display_text,
        }
        if offer_version is not None:
            response["offer_version"] = offer_version
        return response

    def _dialogue_choice_response(self, npc_id: str, choice_id: str) -> str:
        responses = {
            "mira": {
                "greet": "Mira gives a small nod and relaxes her shoulders.",
                "ask_about_work": "Mira says the workshop is quiet, which is exactly how she likes it.",
                "ask_about_village": "Mira says the village works best when everyone keeps their promises.",
                "share_ivo_claim": "Mira listens carefully and decides to ask Tomo herself.",
                "goodbye": "You step back from Mira's workbench.",
            },
            "tomo": {
                "greet": "Tomo smiles briefly, then glances back toward the fields.",
                "ask_about_work": "Tomo says the farm always has one more task waiting.",
                "ask_about_village": "Tomo says people here notice everything, even when they pretend not to.",
                "goodbye": "You let Tomo get back to his field work.",
            },
            "ivo": {
                "greet": "Ivo welcomes you like an old regular.",
                "ask_about_work": "Ivo says the tavern runs on warm food and careful listening.",
                "ask_about_village": "Ivo says every village story changes a little by sunset.",
                "ask_about_missing_seeds": "Ivo lowers his voice and shares what he heard about Tomo.",
                "goodbye": "You leave Ivo to tend the tavern.",
            },
        }
        npc_responses = responses.get(npc_id, {})
        return npc_responses.get(choice_id, "They nod and return to their day.")

    def _add_player_note(
        self,
        note_id: str,
        title: str,
        text: str,
        source_event_log_id: str,
        claim_id: str | None = None,
        source_actor_id: str | None = None,
    ) -> None:
        note: dict[str, Any] = {
            "note_id": note_id,
            "title": title,
            "text": text,
        }
        if claim_id is not None:
            note["claim_id"] = claim_id
        if source_actor_id is not None:
            note["source_actor_id"] = source_actor_id
        if not any(existing["note_id"] == note_id for existing in self.player.notes):
            self.player.notes.append(note)
        self._append_event(
            event_type="player_note_added",
            actor_id=self.player.player_id,
            target_id=None,
            payload={
                **note,
                "source_event_log_id": source_event_log_id,
            },
        )

    def _player_has_claim_note(self, claim_id: str) -> bool:
        return any(note.get("claim_id") == claim_id for note in self.player.notes)

    def _npc_has_received_claim(self, npc_id: str, claim_id: str) -> bool:
        return any(
            event.type == "memory_shared"
            and event.target_id == npc_id
            and event.payload.get("claim_id") == claim_id
            for event in self._event_log
        )

    def _missing_seeds_accepts_claims(self) -> bool:
        phase = str(self.world_events["evt_missing_seeds"]["phase"])
        return not phase.startswith("resolved_")

    def _player_has_evidence(self, evidence_id: str) -> bool:
        normalized = evidence_id.replace("fact_", "")
        if normalized not in {"torn_seed_bag", "seed_bag"}:
            return False
        return any(
            memory.owner_id == "player"
            and memory.type == "evidence"
            and "torn seed bag" in memory.summary.lower()
            for memory in self.memories.values()
        )

    def _mira_has_reflection_modifier(self) -> bool:
        modifiers = set(self.npcs["mira"].behavior_modifiers)
        return bool({"rumor_skepticism", "investigate_before_accuse"} & modifiers)

    def _latest_relevant_memory(self, actor_id: str) -> MemoryRecord | None:
        for memory in reversed(list(self.memories.values())):
            if memory.owner_id == actor_id and memory.topic == "missing_seeds":
                return memory
        return None

    def _current_slot(self, schedule: list[ScheduleSlot]) -> ScheduleSlot:
        current = schedule[0]
        for slot in schedule:
            if self.minute_of_day >= slot.start_minute:
                current = slot
            else:
                break
        return current

    def _change_npc_location(
        self,
        actor_id: str,
        location_id: str,
        movement_reason: str,
    ) -> str:
        npc = self.npcs[actor_id]
        previous = npc.current_location
        if previous == location_id:
            return previous
        npc.current_location = location_id
        self._pending_actor_movements.append(
            {
                "actor_id": actor_id,
                "from_location": previous,
                "to_location": location_id,
                "duration_seconds": 4.0,
                "display_text": f"{npc.name} is heading to the {self.locations[location_id].name}.",
                "reason": movement_reason,
            }
        )
        self._close_conversations_for_actor(actor_id, "npc_moved")
        return previous

    def _location_occupants(self) -> dict[str, list[str]]:
        occupants: dict[str, list[str]] = {location_id: [] for location_id in self.locations}
        occupants[self.player.current_location].append(self.player.player_id)
        for npc in self.npcs.values():
            occupants[npc.current_location].append(npc.npc_id)
        return occupants

    def _diff(
        self,
        reason: str,
        changed_actor_ids: list[str],
        latest_events_count: int,
        toasts: list[str] | None = None,
    ) -> dict[str, Any]:
        snapshot = self.snapshot()
        actor_movements = list(self._pending_actor_movements)
        self._pending_actor_movements.clear()
        return {
            "world_id": self.world_id,
            "reason": reason,
            "time": snapshot["time"],
            "minute_of_day": snapshot["minute_of_day"],
            "world_minute": snapshot["world_minute"],
            "episode_phase": snapshot["episode_phase"],
            "event_log_cursor": snapshot["event_log_cursor"],
            "changed_actor_ids": changed_actor_ids,
            "locations": snapshot["locations"],
            "player": snapshot["player"],
            "npcs": snapshot["npcs"],
            "memories": snapshot["memories"],
            "relationships": snapshot["relationships"],
            "rumors": snapshot["rumors"],
            "world_events": snapshot["world_events"],
            "action_queue": snapshot["action_queue"],
            "last_validator_result": snapshot["last_validator_result"],
            "last_agent_trace": snapshot["last_agent_trace"],
            "last_director_trace": snapshot["last_director_trace"],
            "director_state": snapshot["director_state"],
            "last_relationship_change": snapshot["last_relationship_change"],
            "actor_movements": actor_movements,
            "presentation": self._presentation(toasts=toasts),
            "latest_events": self.events(limit=latest_events_count),
        }

    def _presentation(self, toasts: list[str] | None = None) -> dict[str, Any]:
        phase = self.world_events["evt_missing_seeds"]["phase"]
        phase_text = {
            "public_problem": "A Little Problem",
            "conflicting_claims": "Gathering Clues",
            "suspicion_spread": "Checking In",
            "confrontation_pending": "Someone Wants to Ask",
            "confrontation_happened": "A Helpful Talk",
            "evidence_found": "A Clue Found",
            "resolution_pending": "Ready to Clear Things Up",
            "resolved_reconciled": "Seeds Found Together",
            "resolved_false_accusation": "A Misunderstanding",
            "resolved_player_manipulated": "Trust Needs Repair",
        }.get(phase, "Village Day")
        flow_text = {
            "public_problem": "The village is looking for a missing seed pouch.",
            "conflicting_claims": "Neighbors are comparing small clues and trying to be fair.",
            "suspicion_spread": "Mira is checking in with the village before anyone jumps ahead.",
            "confrontation_pending": "Someone wants to ask a careful question.",
            "confrontation_happened": "A helpful talk has moved things forward.",
            "evidence_found": "A useful clue is ready to share.",
            "resolution_pending": "The village is ready to clear things up.",
            "resolved_reconciled": "The village worked together and trust feels warmer.",
            "resolved_false_accusation": "A misunderstanding left feelings bruised.",
            "resolved_player_manipulated": "The village needs time to rebuild trust.",
        }.get(phase, "The village day continues.")
        return {
            "event_title": "The Missing Seed Pouch",
            "event_phase_text": phase_text,
            "village_flow_text": flow_text,
            "toasts": toasts or [],
        }

    def _rejection(self, code: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._append_event(
            event_type="client_action_rejected",
            actor_id=self.player.player_id,
            target_id=None,
            payload={"code": code, **payload},
        )
        return self._diff(reason=code, changed_actor_ids=[], latest_events_count=1)

    def _actor_ids(self) -> set[str]:
        return {self.player.player_id, "scenario_engine", *self.npcs.keys()}

    def _actor_location(self, actor_id: str) -> str:
        if actor_id == self.player.player_id:
            return self.player.current_location
        return self.npcs[actor_id].current_location

    def _actors_at_location(self, location_id: str, include_player: bool = True) -> list[str]:
        actors = []
        if include_player and self.player.current_location == location_id:
            actors.append(self.player.player_id)
        actors.extend(npc_id for npc_id, npc in self.npcs.items() if npc.current_location == location_id)
        return actors

    def _relationship_key(self, owner_id: str, target_id: str) -> str:
        return f"{owner_id}->{target_id}"

    def _sorted_actions(self) -> list[QueuedAction]:
        return sorted(
            self.action_queue.values(),
            key=lambda action: (-action.priority, action.execute_after_minute, action.action_id),
        )

    def _append_event(
        self,
        event_type: str,
        actor_id: str | None,
        target_id: str | None,
        payload: dict[str, Any],
    ) -> str:
        self._event_counter += 1
        event_id = f"elog_{self._event_counter:06d}"
        self._event_log.append(
            EventLogEntry(
                event_log_id=event_id,
                world_id=self.world_id,
                world_time=self.current_time,
                type=event_type,
                actor_id=actor_id,
                target_id=target_id,
                payload=payload,
            )
        )
        return event_id
