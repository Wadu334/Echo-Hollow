from __future__ import annotations

import asyncio
import json
import sys

import websockets


async def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8000/ws/world/demo_world_001"
    async with websockets.connect(url) as websocket:
        first_message = json.loads(await websocket.recv())
        print(json.dumps(first_message, indent=2))

        await websocket.send(json.dumps({"type": "move_player", "location_id": "tavern"}))
        while True:
            move_response = json.loads(await asyncio.wait_for(websocket.recv(), timeout=5))
            if move_response.get("type") == "world_diff" and move_response.get("data", {}).get("reason") == "player_moved":
                break
        print(json.dumps(move_response, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
