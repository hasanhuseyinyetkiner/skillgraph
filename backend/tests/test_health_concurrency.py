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
    application = create_app(build_settings(url))
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(application, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        deadline = time.time() + 20
        while time.time() < deadline and not server.started:
            time.sleep(0.05)
        if not server.started:
            raise AssertionError("uvicorn did not start")
        timings: dict[str, float | int] = {}
        errors: list[BaseException] = []

        def heavy() -> None:
            try:
                started = time.perf_counter()
                response = httpx.post(
                    f"http://127.0.0.1:{port}/api/analysis/run",
                    params={"delay_ms": 2000},
                    timeout=10,
                )
                timings["heavy_s"] = time.perf_counter() - started
                timings["heavy_code"] = response.status_code
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        def health() -> None:
            try:
                time.sleep(0.25)
                started = time.perf_counter()
                response = httpx.get(f"http://127.0.0.1:{port}/health", timeout=2)
                timings["health_s"] = time.perf_counter() - started
                timings["health_code"] = response.status_code
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
        assert float(timings["health_s"]) < 1.0
    finally:
        server.should_exit = True
        thread.join(timeout=10)
