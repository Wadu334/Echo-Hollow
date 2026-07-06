from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .agent import AgentContext, DeterministicAgentLoop


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
        }


@dataclass
class PlayerState:
    player_id: str = "player"
    current_location: str = "square"

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_id": self.player_id,
            "current_location": self.current_location,
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


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


class WorldSimulation:
    """Deterministic MVP world simulation.

    The simulation intentionally contains no LLM hooks yet. It proves the
    server-authoritative clock, NPC schedule loop, event log, and client sync.
    """

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
        self.agent_loop = DeterministicAgentLoop()
        self._event_counter = 0
        self._memory_counter = 0
        self._event_log: list[EventLogEntry] = []
        self.last_validator_result: dict[str, Any] | None = None
        self.last_agent_trace: dict[str, Any] | None = None
        self._append_event(
            event_type="world_started",
            actor_id=None,
            target_id=None,
            payload={
                "message": "The village wakes to a missing seed bag notice.",
                "active_events": self.active_events,
            },
        )

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
                tags=["work", "food", "tomo"],
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
                current_location="tavern",
                current_action="serve",
                current_goal="keep_business_running",
                mood="watchful",
                status_flags=["rumor_hub"],
                schedule=[
                    ScheduleSlot(8 * 60, "serve", "tavern", "keep_business_running"),
                    ScheduleSlot(11 * 60, "visit", "square", "hear_village_news"),
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
        for npc in self.npcs.values():
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
                npc.current_location = slot.location_id
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

        return self._diff(
            reason="tick",
            changed_actor_ids=changed_actor_ids,
            latest_events_count=max(1, len(changed_actor_ids)),
        )

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
        claim = self._claim_payload(claim_id)
        validation = self._validate_tool(
            tool_name="share_memory",
            actor_id=self.player.player_id,
            target_id=target_id,
            topic=claim["topic"],
        )
        if not validation["accepted"]:
            return self._tool_rejection(validation)

        event_id = self._append_event(
            event_type="memory_shared",
            actor_id=self.player.player_id,
            target_id=target_id,
            payload={
                "claim_id": claim_id,
                "topic": claim["topic"],
                "claim": claim["summary"],
                "claim_target_id": claim.get("claim_target_id"),
                "truth_state": claim["truth_state"],
            },
        )
        memory = self._write_memory(
            owner_id=target_id,
            memory_type="episodic",
            topic=claim["topic"],
            summary=claim["summary"],
            source_event_log_id=event_id,
            truth_state=claim["truth_state"],
            target_id=claim.get("claim_target_id"),
            importance=claim["importance"],
            emotional_valence=claim["emotional_valence"],
        )
        changed_actor_ids = [target_id]
        changed_actor_ids.extend(self._agent_planner_after_memory(memory))
        return self._diff(reason="memory_shared", changed_actor_ids=changed_actor_ids, latest_events_count=6)

    def gossip(self, actor_id: str, target_id: str, rumor_id: str) -> dict[str, Any]:
        validation = self._validate_tool(
            tool_name="gossip",
            actor_id=actor_id,
            target_id=target_id,
            topic="missing_seeds",
            rumor_id=rumor_id,
        )
        if not validation["accepted"]:
            return self._tool_rejection(validation)

        rumor = self.rumors[rumor_id]
        if target_id not in rumor.current_holder_ids:
            rumor.current_holder_ids.append(target_id)
        if target_id not in rumor.source_chain:
            rumor.source_chain.append(actor_id)
        rumor.spread_count += 1
        rumor.distortion_level = _clamp(rumor.distortion_level + 0.03)
        rumor.confidence = _clamp(rumor.confidence + 0.05)

        event_id = self._append_event(
            event_type="rumor_spread",
            actor_id=actor_id,
            target_id=target_id,
            payload={"rumor": rumor.to_dict()},
        )
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

        event = self.world_events["evt_missing_seeds"]
        for fact in event["facts"]:
            if fact["fact_id"] == "fact_torn_seed_bag":
                fact["verified"] = True
                fact["public"] = True
        event["phase"] = "evidence_found"

        event_id = self._append_event(
            event_type="evidence_found",
            actor_id=self.player.player_id,
            target_id=subject_id,
            payload={
                "fact_id": "fact_torn_seed_bag",
                "content": "The seed bag was torn open near the warehouse.",
                "event_phase": event["phase"],
            },
        )
        self._write_memory(
            owner_id=self.player.player_id,
            memory_type="episodic",
            topic="missing_seeds",
            summary="Player found a torn seed bag near the warehouse.",
            source_event_log_id=event_id,
            truth_state="verified",
            importance=0.9,
        )
        return self._diff(reason="evidence_found", changed_actor_ids=["player"], latest_events_count=3)

    def reject_client_message(self, message_type: str, reason: str) -> dict[str, Any]:
        self._append_event(
            event_type="client_message_rejected",
            actor_id=self.player.player_id,
            target_id=None,
            payload={"message_type": message_type, "reason": reason},
        )
        return self._diff(reason="client_message_rejected", changed_actor_ids=[], latest_events_count=1)

    def snapshot(self) -> dict[str, Any]:
        occupants = self._location_occupants()
        return {
            "world_id": self.world_id,
            "day": self.day,
            "time": format_world_time(self.day, self.minute_of_day),
            "minute_of_day": self.minute_of_day,
            "active_events": self.active_events,
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
            "last_validator_result": self.last_validator_result,
            "last_agent_trace": self.last_agent_trace,
            "latest_events": self.events(limit=8),
        }

    def events(self, limit: int = 50) -> list[dict[str, Any]]:
        bounded_limit = max(1, min(limit, 200))
        return [entry.to_dict() for entry in self._event_log[-bounded_limit:]]

    def _current_slot(self, schedule: list[ScheduleSlot]) -> ScheduleSlot:
        current = schedule[0]
        for slot in schedule:
            if self.minute_of_day >= slot.start_minute:
                current = slot
            else:
                break
        return current

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
    ) -> dict[str, Any]:
        snapshot = self.snapshot()
        return {
            "world_id": self.world_id,
            "reason": reason,
            "time": snapshot["time"],
            "minute_of_day": snapshot["minute_of_day"],
            "event_log_cursor": snapshot["event_log_cursor"],
            "changed_actor_ids": changed_actor_ids,
            "locations": snapshot["locations"],
            "player": snapshot["player"],
            "npcs": snapshot["npcs"],
            "memories": snapshot["memories"],
            "relationships": snapshot["relationships"],
            "rumors": snapshot["rumors"],
            "world_events": snapshot["world_events"],
            "last_validator_result": snapshot["last_validator_result"],
            "last_agent_trace": snapshot["last_agent_trace"],
            "latest_events": self.events(limit=latest_events_count),
        }

    def _rejection(self, code: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._append_event(
            event_type="client_action_rejected",
            actor_id=self.player.player_id,
            target_id=None,
            payload={"code": code, **payload},
        )
        return self._diff(reason=code, changed_actor_ids=[], latest_events_count=1)

    def _tool_rejection(self, validation: dict[str, Any]) -> dict[str, Any]:
        self.last_validator_result = validation
        self._append_event(
            event_type="tool_rejected",
            actor_id=validation.get("actor_id"),
            target_id=validation.get("target_id"),
            payload=validation,
        )
        return self._diff(reason=validation["rejection_code"], changed_actor_ids=[], latest_events_count=1)

    def _validate_tool(
        self,
        tool_name: str,
        actor_id: str,
        target_id: str,
        topic: str,
        rumor_id: str | None = None,
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
        if actor_id not in self._actor_ids():
            result["rejection_code"] = "actor_not_found"
            result["debug_reason"] = f"Unknown actor {actor_id}."
        elif tool_name in {"talk_to", "share_memory", "gossip"} and target_id not in self.npcs:
            result["rejection_code"] = "target_not_found"
            result["debug_reason"] = f"Unknown NPC target {target_id}."
        elif tool_name == "investigate" and target_id not in self.locations:
            result["rejection_code"] = "location_not_found"
            result["debug_reason"] = f"Unknown investigation location {target_id}."
        elif tool_name in {"talk_to", "share_memory", "gossip"} and self._actor_location(actor_id) != self._actor_location(target_id):
            result["rejection_code"] = "target_unavailable"
            result["debug_reason"] = "Actor and target must be in the same location."
        elif tool_name == "gossip" and (rumor_id is None or rumor_id not in self.rumors):
            result["rejection_code"] = "rumor_not_found"
            result["debug_reason"] = "Rumor must exist before it can spread."
        elif tool_name == "gossip" and actor_id not in self.rumors[str(rumor_id)].current_holder_ids:
            result["rejection_code"] = "memory_not_owned"
            result["debug_reason"] = "Actor does not hold this rumor."
        elif tool_name == "gossip" and target_id in self.rumors[str(rumor_id)].current_holder_ids:
            result["rejection_code"] = "duplicate_information"
            result["debug_reason"] = "Target already knows this rumor."
        elif tool_name == "investigate" and self.player.current_location != target_id:
            result["rejection_code"] = "not_reachable"
            result["debug_reason"] = "Player must be at the location to investigate it."
        else:
            result["accepted"] = True
            result["debug_reason"] = "Validator accepted tool proposal."

        self.last_validator_result = result
        return result

    def _agent_planner_after_memory(self, memory: MemoryRecord) -> list[str]:
        changed_actor_ids: list[str] = []
        context = self._agent_context(memory)
        decision = self.agent_loop.decide_after_memory(context)
        if decision.decision != "investigate_missing_seeds" or decision.tool_proposal is None:
            self.last_agent_trace = decision.to_dict()
            return changed_actor_ids

        target_id = decision.tool_proposal.target_id

        deltas = {"trust": -0.08, "affinity": -0.03}
        relationship_event_id = self._change_relationship("mira", target_id, deltas, memory.memory_id)
        npc = self.npcs["mira"]
        npc.current_goal = "investigate_missing_seeds"
        npc.current_action = "consider_rumor"
        npc.mood = "suspicious"
        flag = f"suspicious_of_{target_id}"
        if flag not in npc.status_flags:
            npc.status_flags.append(flag)
        changed_actor_ids.append("mira")

        if memory.target_id == "tomo":
            rumor = self.rumors["rumor_tomo_took_seeds"]
            if "mira" not in rumor.current_holder_ids:
                rumor.current_holder_ids.append("mira")
            rumor.confidence = _clamp(max(rumor.confidence, 0.46))
            rumor.spread_count += 1
            self._write_memory(
                owner_id="mira",
                memory_type="rumor",
                topic="missing_seeds",
                summary=rumor.content,
                source_event_log_id=relationship_event_id,
                truth_state="unverified",
                target_id="tomo",
                importance=0.7,
                emotional_valence=-0.35,
            )

        self.last_agent_trace = decision.to_dict()
        self.last_agent_trace["validator_result"] = self._validate_tool(
            tool_name=decision.tool_proposal.tool_name,
            actor_id=decision.tool_proposal.actor_id,
            target_id=decision.tool_proposal.target_id,
            topic=decision.tool_proposal.topic,
        )
        self._append_event(
            event_type="agent_action_planned",
            actor_id="mira",
            target_id=target_id,
            payload=self.last_agent_trace,
        )
        self.world_events["evt_missing_seeds"]["phase"] = "conflicting_claims"
        return changed_actor_ids

    def _agent_context(self, memory: MemoryRecord) -> AgentContext:
        relationship_state = None
        if memory.target_id and memory.owner_id in self.npcs:
            relationship = self.relationships.get(self._relationship_key(memory.owner_id, memory.target_id))
            relationship_state = relationship.to_dict() if relationship else None

        retrieved_memories = [
            candidate.to_dict()
            for candidate in self.memories.values()
            if candidate.owner_id == memory.owner_id and candidate.topic == memory.topic
        ][-5:]
        facts = self.world_events["evt_missing_seeds"]["facts"] if memory.topic == "missing_seeds" else []
        return AgentContext(
            actor_id=memory.owner_id,
            objective="Protect village order while avoiding unsupported accusations.",
            triggering_memory=memory.to_dict(),
            retrieved_memories=retrieved_memories,
            relationship_state=relationship_state,
            world_facts=facts,
            allowed_tools=["talk_to", "share_memory", "gossip", "investigate"],
            observations=[
                f"{memory.owner_id} received {memory.type} memory {memory.memory_id}.",
                f"Current event phase is {self.world_events['evt_missing_seeds']['phase']}.",
            ],
        )

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
            world_time=format_world_time(self.day, self.minute_of_day),
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

    def _memories_by_owner(self) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for memory in self.memories.values():
            grouped.setdefault(memory.owner_id, []).append(memory.to_dict())
        return grouped

    def _claim_payload(self, claim_id: str) -> dict[str, Any]:
        claims = {
            "tomo_took_seeds": {
                "topic": "missing_seeds",
                "summary": "Player says Tomo may have taken the public seed bag.",
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
        return claims.get(claim_id, claims["tomo_took_seeds"])

    def _dialogue_line(self, target_id: str, topic: str) -> str:
        if topic != "missing_seeds":
            return f"{self.npcs[target_id].name} has nothing new to say."
        return {
            "mira": "If someone took community seeds, I need proof before the village turns on itself.",
            "tomo": "I did not take them. Everyone is already looking at me like I did.",
            "ivo": "People talk when supplies go missing. I only repeat what I hear.",
        }.get(target_id, "No response.")

    def _actor_ids(self) -> set[str]:
        return {self.player.player_id, *self.npcs.keys()}

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
                world_time=format_world_time(self.day, self.minute_of_day),
                type=event_type,
                actor_id=actor_id,
                target_id=target_id,
                payload=payload,
            )
        )
        return event_id
