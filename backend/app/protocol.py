from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FieldSpec:
    expected_type: type
    required: bool = True
    default: Any = None


class ProtocolError(ValueError):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        field: str | None = None,
        response_type: str = "client_error",
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.field = field
        self.response_type = response_type

    def to_message(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "type": self.response_type,
            "code": self.code,
            "reason": self.code,
            "message": self.message,
            "display_text": self.message,
        }
        if self.field is not None:
            payload["field"] = self.field
        return payload


STRING = FieldSpec(str)
OPTIONAL_TALK = FieldSpec(str, required=False, default="talk")
OPTIONAL_TOPIC = FieldSpec(str, required=False, default="missing_seeds")
OPTIONAL_EVIDENCE = FieldSpec(str, required=False, default="torn_seed_bag")
OPTIONAL_ACTOR = FieldSpec(str, required=False, default="mira")
OPTIONAL_CLAIM = FieldSpec(str, required=False, default="tomo_took_seeds")
OPTIONAL_RUMOR = FieldSpec(str, required=False, default="rumor_tomo_took_seeds")
OPTIONAL_MINUTES = FieldSpec(int, required=False, default=30)


MESSAGE_SCHEMAS: dict[str, dict[str, FieldSpec]] = {
    "move_player": {"location_id": STRING},
    "player_entered_location": {"location_id": STRING},
    "player_interact_npc": {
        "npc_id": STRING,
        "interaction": OPTIONAL_TALK,
    },
    "dialogue_choice": {
        "conversation_id": STRING,
        "offer_version": FieldSpec(int),
        "choice_id": STRING,
    },
    "observe": {},
    "talk_to": {
        "target_id": STRING,
        "topic": OPTIONAL_TOPIC,
    },
    "share_claim": {
        "target_id": STRING,
        "claim_id": OPTIONAL_CLAIM,
    },
    "gossip": {
        "actor_id": STRING,
        "target_id": STRING,
        "rumor_id": OPTIONAL_RUMOR,
    },
    "investigate": {"subject_id": STRING},
    "investigate_location": {"location_id": STRING},
    "player_share_evidence": {
        "target_id": STRING,
        "evidence_id": OPTIONAL_EVIDENCE,
    },
    "wait_minutes": {"minutes": OPTIONAL_MINUTES},
    "autonomous_step": {"actor_id": OPTIONAL_ACTOR},
    "run_village_step": {"actor_id": OPTIONAL_ACTOR},
}


def parse_client_message(text: str) -> dict[str, Any]:
    try:
        payload = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ProtocolError(
            "malformed_json",
            "Message must be valid JSON text.",
        ) from exc
    return validate_client_payload(payload)


def validate_client_payload(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ProtocolError(
            "payload_not_object",
            "Message payload must be a JSON object.",
        )

    if "type" not in payload:
        raise ProtocolError(
            "missing_field",
            "Required field 'type' is missing.",
            field="type",
        )
    if not _matches_type(payload["type"], str):
        raise ProtocolError(
            "invalid_field_type",
            "Field 'type' must be a string.",
            field="type",
        )

    message_type = payload["type"]
    schema = MESSAGE_SCHEMAS.get(message_type)
    if schema is None:
        raise ProtocolError(
            "unsupported_message_type",
            f"Unsupported client message type '{message_type}'.",
            field="type",
        )

    validated: dict[str, Any] = {"type": message_type}
    for field_name, spec in schema.items():
        if field_name not in payload:
            if field_name == "conversation_id" and message_type == "dialogue_choice":
                raise ProtocolError(
                    "missing_conversation_id",
                    "Dialogue choices require the conversation_id offered by the server.",
                    field=field_name,
                    response_type="dialogue_rejected",
                )
            if spec.required:
                raise ProtocolError(
                    "missing_field",
                    f"Required field '{field_name}' is missing.",
                    field=field_name,
                )
            validated[field_name] = spec.default
            continue

        value = payload[field_name]
        if not _matches_type(value, spec.expected_type):
            raise ProtocolError(
                "invalid_field_type",
                f"Field '{field_name}' must be {_type_label(spec.expected_type)}.",
                field=field_name,
            )
        validated[field_name] = value

    return validated


def _matches_type(value: Any, expected_type: type) -> bool:
    if expected_type is int:
        return isinstance(value, int) and not isinstance(value, bool)
    return isinstance(value, expected_type)


def _type_label(expected_type: type) -> str:
    return {
        str: "a string",
        int: "an integer",
    }.get(expected_type, expected_type.__name__)
