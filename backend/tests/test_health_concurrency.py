"""Prove /health stays responsive while a heavy request sleeps off the event loop."""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path

import httpx
import uvicorn
from app.main import create_app
from tests.conftest import build_settings, reset_database


def test_health_stays_responsive_during_heavy_request(tmp_path: Path) -> None:
    url = "sqlite:///" + (tmp_path / "health.db").as_posix()
    reset_database(url)
    # Skip seed for this concurrency probe — we only need the ASGI app + threadpool offload.
    application = create_app(build_settings(url, auto_seed=False))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(application, host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 20
        while time.time() < deadline and not server.started:
            time.sleep(0.05)
        if not server.started:
            raise AssertionError("uvicorn did not start")

        base = f"http://127.0.0.1:{port}"
        # Warm the accept path so cold-start Windows localhost noise does not skew timings.
        warm = httpx.get(f"{base}/health", timeout=5)
        assert warm.status_code == 200

        timings: dict[str, float | int] = {}
        errors: list[BaseException] = []
        heavy_entered = threading.Event()

        def heavy() -> None:
            try:
                heavy_entered.set()
                started = time.perf_counter()
                response = httpx.post(
                    f"{base}/api/analysis/run",
                    params={"delay_ms": 2000},
                    timeout=15,
                )
                timings["heavy_s"] = time.perf_counter() - started
                timings["heavy_code"] = response.status_code
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        def health() -> None:
            try:
                assert heavy_entered.wait(timeout=5)
                # Sample several times while the heavy sleep holds a worker thread.
                samples: list[float] = []
                codes: list[int] = []
                deadline_inner = time.time() + 1.5
                while time.time() < deadline_inner:
                    started = time.perf_counter()
                    response = httpx.get(f"{base}/health", timeout=2)
                    samples.append(time.perf_counter() - started)
                    codes.append(response.status_code)
                    time.sleep(0.05)
                timings["health_s"] = min(samples) if samples else 999.0
                timings["health_code"] = codes[0] if codes else 0
                timings["health_samples"] = len(samples)
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        workers = [threading.Thread(target=heavy), threading.Thread(target=health)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        assert errors == []
        assert timings["heavy_code"] == 200
        assert timings["health_code"] == 200
        assert float(timings["heavy_s"]) >= 1.5
        # At least one /health sample must complete quickly while heavy still sleeps off-loop.
        assert float(timings["health_s"]) < 0.75
        assert int(timings["health_samples"]) >= 3
    finally:
        server.should_exit = True
        thread.join(timeout=10)
