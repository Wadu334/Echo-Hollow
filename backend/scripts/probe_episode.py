from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.world import WorldSimulation  # noqa: E402


def main() -> int:
    world = WorldSimulation()

    world.move_player("workshop")
    claim = world.share_claim(target_id="mira", claim_id="tomo_took_seeds")

    for _ in range(3):
        world.tick()

    if world.player.current_location != world.npcs["mira"].current_location:
        world.move_player("square")
        if world.npcs["mira"].current_location == "farm":
            world.move_player("farm")
        elif world.npcs["mira"].current_location == "workshop":
            world.move_player("workshop")

    world.move_player("warehouse")
    evidence = world.investigate("warehouse")
    world.move_player("square")
    world.move_player(world.npcs["mira"].current_location)
    resolved = world.player_share_evidence(target_id="mira", evidence_id="torn_seed_bag")

    snapshot = world.snapshot()
    summary = {
        "claim_reason": claim["reason"],
        "evidence_reason": evidence["reason"],
        "resolved_reason": resolved["reason"],
        "episode_phase": snapshot["episode_phase"],
        "resolution_path": snapshot["world_events"]["evt_missing_seeds"]["resolution_path"],
        "action_queue": [
            {
                "action_id": action["action_id"],
                "tool_name": action["tool_name"],
                "status": action["status"],
                "validator": (action["validator_result"] or {}).get("rejection_code")
                if action["validator_result"]
                else None,
            }
            for action in snapshot["action_queue"]
        ],
        "mira_memories": [
            {
                "type": memory["type"],
                "summary": memory["summary"],
            }
            for memory in snapshot["memories"].get("mira", [])
        ],
        "relationships": {
            key: value
            for key, value in snapshot["relationships"].items()
            if key in {"mira->tomo", "tomo->mira"}
        },
        "latest_events": [
            {
                "time": event["world_time"],
                "type": event["type"],
                "actor": event["actor_id"],
                "target": event["target_id"],
            }
            for event in snapshot["latest_events"]
        ],
    }
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
