from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import pytest
import redis


ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.realtime.yml"


def _docker_compose(
    *args: str,
    project_name: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(COMPOSE_FILE),
            "-p",
            project_name,
            *args,
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


def _wait_for_port(host: str, port: int, timeout_seconds: float = 30.0) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for {host}:{port}")


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


@pytest.fixture(autouse=True)
def _test_env_defaults(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("PRISM_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("PRISM_RATE_LIMIT_STORAGE_URI", "memory://")
    monkeypatch.setenv("PRISM_NOTIFICATIONS_BACKEND", "memory")
    monkeypatch.setenv("PRISM_NOTIFICATIONS_REDIS_CHANNEL", "prism:test-notifications")


@pytest.fixture(scope="session")
def realtime_stack():
    project_name = f"prismrealtime{uuid4().hex[:8]}"
    redis_port = _find_free_port()
    mqtt_port = _find_free_port()
    compose_env = {
        "PRISM_REDIS_BIND_ADDRESS": "127.0.0.1",
        "PRISM_REDIS_BIND_PORT": str(redis_port),
        "PRISM_MQTT_BIND_ADDRESS": "127.0.0.1",
        "PRISM_MQTT_BIND_PORT": str(mqtt_port),
    }

    _docker_compose("up", "-d", project_name=project_name, env=compose_env)
    try:
        _wait_for_port("127.0.0.1", redis_port)
        _wait_for_port("127.0.0.1", mqtt_port)
        yield {
            "compose_file": str(COMPOSE_FILE),
            "project_name": project_name,
            "redis_url": f"redis://127.0.0.1:{redis_port}/0",
            "mqtt_host": "127.0.0.1",
            "mqtt_port": mqtt_port,
        }
    finally:
        _docker_compose("down", "-v", "--remove-orphans", project_name=project_name, env=compose_env)


@pytest.fixture()
def redis_client(realtime_stack):
    client = redis.Redis.from_url(realtime_stack["redis_url"], decode_responses=True)
    client.flushdb()
    yield client
    client.flushdb()
