from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORLD_ID = "demo_world_001"
DEFAULT_GODOT_SCRIPT = "res://tests/verify_connected_client.gd"
GODOT_COMMAND_CANDIDATES = (
    "Godot_v4.7-stable_win64_console.exe",
    "godot_console",
    "godot",
)


class VerificationError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Start a fresh Echo Hollow FastAPI server and run the real "
            "Godot/WebSocket integration verification against it."
        )
    )
    parser.add_argument(
        "--godot",
        help=(
            "Godot console executable path or command. Defaults to GODOT_BIN, "
            "then common Godot console command names on PATH."
        ),
    )
    parser.add_argument("--python", default=sys.executable, help="Python executable used to launch Uvicorn.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="Server port. Zero selects a free local port.")
    parser.add_argument("--world-id", default=DEFAULT_WORLD_ID)
    parser.add_argument("--startup-timeout", type=float, default=15.0)
    parser.add_argument("--godot-timeout", type=float, default=60.0)
    parser.add_argument(
        "--cutscene-duration",
        type=float,
        default=1.5,
        help="Seconds used by the integration-only consequence scene.",
    )
    parser.add_argument("--godot-script", default=DEFAULT_GODOT_SCRIPT)
    return parser.parse_args()


def resolve_command(candidate: str | None) -> str:
    candidates = [
        candidate,
        os.environ.get("GODOT_BIN"),
        *GODOT_COMMAND_CANDIDATES,
    ]
    for value in candidates:
        if not value:
            continue
        path = Path(value).expanduser()
        if path.is_file():
            return str(path.resolve())
        resolved = shutil.which(value)
        if resolved:
            return resolved
    raise VerificationError(
        "Godot console executable was not found. Pass --godot <path> or set GODOT_BIN."
    )


def select_port(host: str, requested_port: int) -> int:
    if requested_port:
        return requested_port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


def wait_for_health(url: str, process: subprocess.Popen[bytes], timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = "server did not answer"
    while time.monotonic() < deadline:
        return_code = process.poll()
        if return_code is not None:
            raise VerificationError(f"Uvicorn exited before becoming healthy (exit {return_code}).")
        try:
            with urlopen(url, timeout=0.5) as response:
                body = json.loads(response.read().decode("utf-8"))
                if response.status == 200 and body.get("status") == "ok":
                    return
                last_error = f"unexpected health response: HTTP {response.status}, {body!r}"
        except (OSError, URLError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        time.sleep(0.1)
    raise VerificationError(f"Timed out waiting {timeout:.1f}s for {url}: {last_error}")


def stop_process(process: subprocess.Popen[bytes]) -> str:
    if process.poll() is None:
        process.terminate()
    try:
        output, _ = process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        output, _ = process.communicate(timeout=5)
    return (output or b"").decode("utf-8", errors="replace").strip()


def run_verification(args: argparse.Namespace) -> None:
    godot = resolve_command(args.godot)
    port = select_port(args.host, args.port)
    health_url = f"http://{args.host}:{port}/health"
    websocket_url = f"ws://{args.host}:{port}/ws/world/{args.world_id}"
    local_script = REPO_ROOT / "client" / args.godot_script.removeprefix("res://")
    if not local_script.is_file():
        raise VerificationError(f"Godot integration script does not exist: {local_script}")

    server_command = [
        args.python,
        "-m",
        "uvicorn",
        "backend.app.main:app",
        "--host",
        args.host,
        "--port",
        str(port),
        "--log-level",
        "warning",
    ]
    godot_command = [
        godot,
        "--headless",
        "--path",
        str(REPO_ROOT / "client"),
        "--script",
        args.godot_script,
    ]
    env = os.environ.copy()
    env["ECHO_HOLLOW_SERVER_URL"] = websocket_url
    env["ECHO_HOLLOW_WORLD_ID"] = args.world_id
    env["ECHO_HOLLOW_CUTSCENE_DURATION"] = str(args.cutscene_duration)
    env["PYTHONUNBUFFERED"] = "1"

    server = subprocess.Popen(
        server_command,
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    failure: BaseException | None = None
    server_output = ""
    try:
        wait_for_health(health_url, server, args.startup_timeout)
        print(f"Echo Hollow test server is healthy at {health_url}")
        result = subprocess.run(
            godot_command,
            cwd=REPO_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=args.godot_timeout,
            check=False,
        )
        output = result.stdout.strip()
        if output:
            print(output)
        if result.returncode != 0:
            raise VerificationError(
                f"Godot connected verification failed with exit code {result.returncode}."
            )
        if "Godot connected client verification passed." not in output:
            raise VerificationError(
                "Godot exited successfully without the expected verification marker."
            )
    except BaseException as exc:
        failure = exc
    finally:
        server_output = stop_process(server)

    if failure is not None:
        if server_output:
            print("\nUvicorn output:", file=sys.stderr)
            print(server_output, file=sys.stderr)
        raise failure

    print(f"Connected Godot/FastAPI verification passed for {websocket_url}")


def main() -> int:
    args = parse_args()
    try:
        run_verification(args)
    except (VerificationError, OSError, subprocess.TimeoutExpired) as exc:
        print(f"Connected verification failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
