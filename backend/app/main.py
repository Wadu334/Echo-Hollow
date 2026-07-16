from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from .protocol import ProtocolError, parse_client_message, validate_client_payload
from .world import WorldSimulation


TICK_INTERVAL_SECONDS = float(os.getenv("ECHO_HOLLOW_TICK_INTERVAL", "1.0"))
WORLD_ID = os.getenv("ECHO_HOLLOW_WORLD_ID", "demo_world_001")

INDEX_HTML = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Echo Hollow World Server</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #111513;
      color: #eef5ef;
    }
    body {
      margin: 0;
      min-height: 100vh;
      background: #111513;
    }
    main {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 340px;
      gap: 24px;
      padding: 24px;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 18px 24px;
      border-bottom: 1px solid #26322d;
      background: #171d1a;
    }
    h1 {
      margin: 0;
      font-size: 22px;
      letter-spacing: 0;
    }
    h2 {
      margin: 0 0 12px;
      font-size: 16px;
    }
    a {
      color: #90d7ff;
    }
    .status {
      color: #b8c7bd;
      font-size: 14px;
    }
    .map {
      position: relative;
      min-height: 560px;
      border: 1px solid #26322d;
      background:
        linear-gradient(90deg, rgba(255,255,255,0.04) 1px, transparent 1px),
        linear-gradient(rgba(255,255,255,0.04) 1px, transparent 1px),
        #151b18;
      background-size: 40px 40px;
      overflow: hidden;
    }
    .location {
      position: absolute;
      width: 150px;
      min-height: 76px;
      transform: translate(-50%, -50%);
      border: 1px solid #435347;
      background: #202923;
      padding: 10px;
      box-sizing: border-box;
    }
    .location strong {
      display: block;
      margin-bottom: 8px;
      font-size: 14px;
    }
    .occupants {
      color: #c8d7cc;
      font-size: 12px;
      line-height: 1.35;
    }
    .actor {
      display: inline-block;
      margin: 2px 4px 2px 0;
      padding: 2px 6px;
      border-radius: 999px;
      background: #334438;
    }
    .player {
      background: #216aa3;
    }
    .mira {
      background: #9d4c3f;
    }
    .tomo {
      background: #3f8545;
    }
    .ivo {
      background: #8f7430;
      color: #fff7cc;
    }
    aside {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    section {
      border: 1px solid #26322d;
      background: #171d1a;
      padding: 16px;
    }
    .buttons {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }
    button {
      min-height: 36px;
      border: 1px solid #405044;
      background: #243027;
      color: #eef5ef;
      cursor: pointer;
    }
    button:hover {
      background: #2f3f34;
    }
    pre {
      margin: 0;
      white-space: pre-wrap;
      color: #cad8cf;
      font-size: 12px;
      line-height: 1.4;
    }
    .events {
      max-height: 260px;
      overflow: auto;
    }
    @media (max-width: 900px) {
      main {
        grid-template-columns: 1fr;
      }
      .map {
        min-height: 520px;
      }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>Echo Hollow World Server</h1>
      <div class="status" id="status">Connecting...</div>
    </div>
    <div class="status">
      <a href="/health">health</a> |
      <a href="/api/world/__WORLD_ID__">world json</a> |
      <a href="/api/world/__WORLD_ID__/events">events</a>
      <span data-ws-path="/ws/world/__WORLD_ID__"></span>
    </div>
  </header>
  <main>
    <div class="map" id="map"></div>
    <aside>
      <section>
        <h2>World</h2>
        <pre id="world"></pre>
      </section>
      <section>
        <h2>Move Player</h2>
        <div class="buttons" id="buttons"></div>
      </section>
      <section>
        <h2>Agent Tools</h2>
        <div class="buttons">
          <button onclick="sendTool({ type: 'move_player', location_id: 'workshop' })">Move to Workshop</button>
          <button onclick="sendTool({ type: 'share_claim', target_id: 'mira', claim_id: 'tomo_took_seeds' })">Tell Mira Tomo rumor</button>
          <button onclick="sendTool({ type: 'wait_minutes', minutes: 30 })">Wait 30 minutes</button>
          <button onclick="sendTool({ type: 'investigate', subject_id: 'warehouse' })">Investigate Warehouse</button>
          <button onclick="sendTool({ type: 'player_share_evidence', target_id: 'mira', evidence_id: 'torn_seed_bag' })">Show evidence to Mira</button>
          <button onclick="sendTool({ type: 'autonomous_step', actor_id: 'mira' })">Run autonomous episode step</button>
          <button onclick="sendTool({ type: 'observe' })">Observe</button>
          <button onclick="sendTool({ type: 'talk_to', target_id: 'mira', topic: 'missing_seeds' })">Talk to Mira</button>
          <button onclick="sendTool({ type: 'share_claim', target_id: 'mira', claim_id: 'ivo_near_warehouse' })">Tell Mira: Ivo clue</button>
          <button onclick="sendTool({ type: 'gossip', actor_id: 'mira', target_id: 'ivo', rumor_id: 'rumor_tomo_took_seeds' })">Mira gossips to Ivo</button>
        </div>
      </section>
      <section>
        <h2>Episode</h2>
        <pre id="episode"></pre>
      </section>
      <section>
        <h2>Action Queue</h2>
        <pre class="events" id="queue"></pre>
      </section>
      <section>
        <h2>Agent Trace</h2>
        <pre id="agent"></pre>
      </section>
      <section>
        <h2>Relationships</h2>
        <pre class="events" id="relationships"></pre>
      </section>
      <section>
        <h2>Memory</h2>
        <pre class="events" id="memory"></pre>
      </section>
      <section>
        <h2>Recent Events</h2>
        <pre class="events" id="events"></pre>
      </section>
    </aside>
  </main>
  <script>
    const worldId = "__WORLD_ID__";
    const statusEl = document.getElementById("status");
    const mapEl = document.getElementById("map");
    const worldEl = document.getElementById("world");
    const eventsEl = document.getElementById("events");
    const buttonsEl = document.getElementById("buttons");
    const agentEl = document.getElementById("agent");
    const memoryEl = document.getElementById("memory");
    const episodeEl = document.getElementById("episode");
    const queueEl = document.getElementById("queue");
    const relationshipsEl = document.getElementById("relationships");
    let socket;
    let latest = {};

    function actorClass(actorId) {
      if (actorId === "player") return "actor player";
      if (actorId === "mira") return "actor mira";
      if (actorId === "tomo") return "actor tomo";
      if (actorId === "ivo") return "actor ivo";
      return "actor";
    }

    function connect() {
      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${scheme}://${window.location.host}/ws/world/${worldId}`);
      socket.onopen = () => statusEl.textContent = "WebSocket connected";
      socket.onclose = () => statusEl.textContent = "WebSocket disconnected";
      socket.onerror = () => statusEl.textContent = "WebSocket error";
      socket.onmessage = (event) => {
        const message = JSON.parse(event.data);
        if (message.type === "world_state") {
          latest = message.data;
        } else if (message.type === "world_diff") {
          latest = { ...latest, ...message.data };
        }
        render();
      };
    }

    function movePlayer(locationId) {
      sendTool({ type: "move_player", location_id: locationId });
    }

    function sendTool(payload) {
      if (!socket || socket.readyState !== WebSocket.OPEN) return;
      socket.send(JSON.stringify(payload));
    }

    function render() {
      const locations = latest.locations || {};
      const events = latest.latest_events || [];
      mapEl.innerHTML = "";
      buttonsEl.innerHTML = "";
      Object.values(locations).forEach(location => {
        const card = document.createElement("div");
        card.className = "location";
        card.style.left = `${location.position.x}px`;
        card.style.top = `${location.position.y}px`;
        const occupants = (location.current_occupants || []).map(id =>
          `<span class="${actorClass(id)}">${id}</span>`
        ).join("");
        card.innerHTML = `<strong>${location.name}</strong><div class="occupants">${occupants || "empty"}</div>`;
        mapEl.appendChild(card);

        const button = document.createElement("button");
        button.textContent = location.name;
        button.onclick = () => movePlayer(location.location_id);
        buttonsEl.appendChild(button);
      });

      worldEl.textContent = [
        `world: ${latest.world_id || worldId}`,
        `time: ${latest.time || "unknown"}`,
        `phase: ${latest.episode_phase || "-"}`,
        `event log: ${latest.event_log_cursor ?? "-"}`,
        `player: ${(latest.player || {}).current_location || "-"}`,
        `queued actions: ${(latest.action_queue || []).filter(action => ["queued", "proposed", "fallback_planned"].includes(action.status)).length}`
      ].join("\\n");

      const missingSeeds = ((latest.world_events || {}).evt_missing_seeds || {});
      episodeEl.textContent = JSON.stringify({
        phase: latest.episode_phase || missingSeeds.phase || null,
        resolution_path: missingSeeds.resolution_path || null,
        facts: missingSeeds.facts || []
      }, null, 2);

      queueEl.textContent = (latest.action_queue || []).map(action =>
        `${action.action_id} ${action.status} ${action.tool_name} ${action.actor_id} p${action.priority}`
      ).join("\\n") || "empty";

      agentEl.textContent = JSON.stringify({
        validator: latest.last_validator_result || null,
        agent: latest.last_agent_trace || null,
        director: latest.last_director_trace || null
      }, null, 2);

      relationshipsEl.textContent = Object.values(latest.relationships || {}).map(rel =>
        `${rel.owner_id} -> ${rel.target_id}  trust ${rel.trust}  affinity ${rel.affinity}`
      ).join("\\n");

      memoryEl.textContent = JSON.stringify({
        memories: latest.memories || {},
        rumors: latest.rumors || {}
      }, null, 2);

      eventsEl.textContent = events.map(event =>
        `${event.world_time}  ${event.type}  ${event.actor_id || ""}`
      ).join("\\n");
    }

    connect();
  </script>
</body>
</html>
"""


class WorldHub:
    def __init__(self, world: WorldSimulation) -> None:
        self.world = world
        self._clients: set[WebSocket] = set()
        self._client_sessions: dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()
        self._dispatch_lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> str:
        await websocket.accept()
        client_session_id = f"session_{uuid4().hex}"
        async with self._dispatch_lock:
            async with self._lock:
                self._clients.add(websocket)
                self._client_sessions[websocket] = client_session_id
                snapshot = self.world.snapshot()
            await self.send_to(
                websocket,
                {
                    "type": "world_state",
                    "client_session_id": client_session_id,
                    "data": snapshot,
                },
            )
        return client_session_id

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(websocket)
            client_session_id = self._client_sessions.pop(websocket, None)
            if client_session_id is not None:
                self.world.close_conversations_for_session(client_session_id)

    async def tick(self) -> dict[str, Any]:
        async with self._dispatch_lock:
            async with self._lock:
                diff = self.world.tick()
            await self.broadcast({"type": "world_diff", "data": diff})
        return diff

    async def handle_text(
        self,
        text: str,
        websocket: WebSocket | None = None,
        client_session_id: str = "local",
    ) -> dict[str, Any]:
        try:
            payload = parse_client_message(text)
        except ProtocolError as error:
            result = error.to_message()
            async with self._dispatch_lock:
                await self.send_to(websocket, result)
            return result
        return await self.handle_message(
            payload,
            websocket=websocket,
            client_session_id=client_session_id,
        )

    async def handle_message(
        self,
        payload: Any,
        websocket: WebSocket | None = None,
        client_session_id: str = "local",
    ) -> dict[str, Any]:
        try:
            validated = validate_client_payload(payload)
        except ProtocolError as error:
            result = error.to_message()
            async with self._dispatch_lock:
                await self.send_to(websocket, result)
            return result

        async with self._dispatch_lock:
            return await self._handle_validated_message(
                validated,
                websocket=websocket,
                client_session_id=client_session_id,
            )

    async def _handle_validated_message(
        self,
        validated: dict[str, Any],
        *,
        websocket: WebSocket | None,
        client_session_id: str,
    ) -> dict[str, Any]:
        message_type = validated["type"]
        async with self._lock:
            if message_type == "move_player":
                result = self.world.move_player(validated["location_id"])
            elif message_type == "player_entered_location":
                result = self.world.player_entered_location(validated["location_id"])
            elif message_type == "player_interact_npc":
                result = self.world.player_interact_npc(
                    npc_id=validated["npc_id"],
                    interaction=validated["interaction"],
                    client_session_id=client_session_id,
                )
            elif message_type == "dialogue_choice":
                result = self.world.dialogue_choice(
                    conversation_id=validated["conversation_id"],
                    offer_version=validated["offer_version"],
                    choice_id=validated["choice_id"],
                    client_session_id=client_session_id,
                )
            elif message_type == "observe":
                result = self.world.observe()
            elif message_type == "talk_to":
                result = self.world.talk_to(
                    target_id=validated["target_id"],
                    topic=validated["topic"],
                )
            elif message_type == "share_claim":
                result = self.world.share_claim(
                    target_id=validated["target_id"],
                    claim_id=validated["claim_id"],
                )
            elif message_type == "gossip":
                result = self.world.gossip(
                    actor_id=validated["actor_id"],
                    target_id=validated["target_id"],
                    rumor_id=validated["rumor_id"],
                )
            elif message_type == "investigate":
                result = self.world.investigate(subject_id=validated["subject_id"])
            elif message_type == "investigate_location":
                result = self.world.investigate_location(location_id=validated["location_id"])
            elif message_type == "player_share_evidence":
                result = self.world.player_share_evidence(
                    target_id=validated["target_id"],
                    evidence_id=validated["evidence_id"],
                )
            elif message_type == "wait_minutes":
                result = self.world.wait_minutes(validated["minutes"])
            elif message_type == "autonomous_step":
                result = self.world.run_autonomous_episode_step(
                    actor_id=validated["actor_id"],
                )
            elif message_type == "run_village_step":
                result = self.world.run_autonomous_episode_step(
                    actor_id=validated["actor_id"],
                )
            else:
                raise AssertionError(f"Unrouted validated message type: {message_type}")
        if result.get("type") in {
            "dialogue_opened",
            "dialogue_result",
            "dialogue_rejected",
            "interaction_denied",
            "client_error",
        }:
            await self.send_to(websocket, result)
            if "world_diff" in result:
                await self.broadcast(
                    {
                        "type": "world_diff",
                        "data": self._shared_world_diff(result["world_diff"]),
                    }
                )
        else:
            await self.broadcast({"type": "world_diff", "data": result})
        return result

    @staticmethod
    def _shared_world_diff(diff: dict[str, Any]) -> dict[str, Any]:
        shared = dict(diff)
        presentation = dict(shared.get("presentation", {}))
        presentation["toasts"] = []
        shared["presentation"] = presentation
        return shared

    async def send_to(
        self,
        websocket: WebSocket | None,
        message: dict[str, Any],
    ) -> None:
        if websocket is None:
            await self.broadcast(message)
            return
        try:
            await websocket.send_json(message)
        except RuntimeError:
            await self.disconnect(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        stale_clients: list[WebSocket] = []
        for websocket in list(self._clients):
            try:
                await websocket.send_json(message)
            except RuntimeError:
                stale_clients.append(websocket)
        if stale_clients:
            async with self._lock:
                for websocket in stale_clients:
                    self._clients.discard(websocket)
                    client_session_id = self._client_sessions.pop(websocket, None)
                    if client_session_id is not None:
                        self.world.close_conversations_for_session(client_session_id)


world = WorldSimulation(world_id=WORLD_ID)
hub = WorldHub(world)


async def simulation_loop() -> None:
    while True:
        await asyncio.sleep(TICK_INTERVAL_SECONDS)
        await hub.tick()


@asynccontextmanager
async def lifespan(_: FastAPI):
    task = asyncio.create_task(simulation_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="Echo Hollow World Server", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "world_id": world.world_id}


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(INDEX_HTML.replace("__WORLD_ID__", world.world_id))


@app.get("/api/world/{world_id}")
async def get_world(world_id: str) -> dict[str, Any]:
    if world_id != world.world_id:
        return {"error": "world_not_found", "world_id": world_id}
    return {"type": "world_state", "data": world.snapshot()}


@app.get("/api/world/{world_id}/events")
async def get_events(world_id: str, limit: int = 50) -> dict[str, Any]:
    if world_id != world.world_id:
        return {"error": "world_not_found", "world_id": world_id}
    return {"world_id": world.world_id, "events": world.events(limit=limit)}


@app.get("/api/world/{world_id}/agent")
async def get_agent_state(world_id: str) -> dict[str, Any]:
    if world_id != world.world_id:
        return {"error": "world_not_found", "world_id": world_id}
    snapshot = world.snapshot()
    return {
        "world_id": world.world_id,
        "memories": snapshot["memories"],
        "relationships": snapshot["relationships"],
        "rumors": snapshot["rumors"],
        "episode_phase": snapshot["episode_phase"],
        "action_queue": snapshot["action_queue"],
        "last_validator_result": snapshot["last_validator_result"],
        "last_agent_trace": snapshot["last_agent_trace"],
        "last_director_trace": snapshot["last_director_trace"],
        "director_state": snapshot["director_state"],
        "last_relationship_change": snapshot["last_relationship_change"],
    }


@app.websocket("/ws/world/{world_id}")
async def world_socket(websocket: WebSocket, world_id: str) -> None:
    if world_id != world.world_id:
        await websocket.close(code=1008)
        return

    client_session_id = await hub.connect(websocket)
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break
            text = message.get("text")
            if not isinstance(text, str):
                await hub.send_to(
                    websocket,
                    ProtocolError(
                        "invalid_field_type",
                        "WebSocket messages must use text JSON frames.",
                        field="payload",
                    ).to_message(),
                )
                continue
            await hub.handle_text(
                text,
                websocket=websocket,
                client_session_id=client_session_id,
            )
    except WebSocketDisconnect:
        pass
    finally:
        await hub.disconnect(websocket)
