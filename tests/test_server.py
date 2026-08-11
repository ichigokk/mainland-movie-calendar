from __future__ import annotations

import threading
from pathlib import Path

from mainland_movie_calendar.server import (
    ServerConfig,
    ServiceStatus,
    ensure_seed_data,
    refresh_index,
    update_loop,
)


def make_config(tmp_path: Path, *, seed_root: Path | None = None) -> ServerConfig:
    return ServerConfig(
        data_dir=tmp_path / "data",
        seed_root=seed_root or tmp_path / "seed",
        public_base_url="http://calendar.test:8000",
        source_url="https://example.test/coming",
        host="127.0.0.1",
        port=8000,
        timezone="Asia/Shanghai",
        update_interval_seconds=3600,
        retry_interval_seconds=60,
    )


def test_ensure_seed_data_copies_missing_files_without_overwriting(tmp_path: Path) -> None:
    seed_root = tmp_path / "seed"
    (seed_root / "data").mkdir(parents=True)
    (seed_root / "docs").mkdir(parents=True)
    (seed_root / "data" / "movies.json").write_text('{"movies": []}\n', encoding="utf-8")
    (seed_root / "docs" / "calendar.ics").write_text("BEGIN:VCALENDAR\n", encoding="utf-8")
    (seed_root / "docs" / "index.html").write_text("seed page", encoding="utf-8")

    config = make_config(tmp_path, seed_root=seed_root)
    config.public_dir.mkdir(parents=True)
    config.index_path.write_text("keep me", encoding="utf-8")

    ensure_seed_data(config)

    assert config.state_path.read_text(encoding="utf-8") == '{"movies": []}\n'
    assert config.calendar_path.read_text(encoding="utf-8") == "BEGIN:VCALENDAR\n"
    assert config.index_path.read_text(encoding="utf-8") == "keep me"


def test_refresh_index_uses_self_hosted_public_url(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    config.data_dir.mkdir(parents=True)
    config.state_path.write_text(
        '{"schema_version": 1, "generated_at": null, "movies": []}\n',
        encoding="utf-8",
    )

    refresh_index(config)

    content = config.index_path.read_text(encoding="utf-8")
    assert 'href="webcal://calendar.test:8000/calendar.ics"' in content
    assert 'href="http://calendar.test:8000/calendar.ics"' in content


def test_service_status_reports_success_and_failure() -> None:
    status = ServiceStatus()

    assert status.snapshot()["status"] == "starting"

    status.mark_attempt()
    status.mark_success([{"kind": "added"}])
    snapshot = status.snapshot()
    assert snapshot["status"] == "ok"
    assert snapshot["last_error"] is None
    assert snapshot["last_change_count"] == 1

    status.mark_failure(RuntimeError("source unavailable"))
    snapshot = status.snapshot()
    assert snapshot["status"] == "degraded"
    assert snapshot["last_error"] == "RuntimeError: source unavailable"


def test_update_loop_keeps_running_status_on_failure(tmp_path: Path) -> None:
    config = make_config(tmp_path)
    status = ServiceStatus()
    stop_event = threading.Event()

    def fail_once() -> list[dict]:
        stop_event.set()
        raise RuntimeError("source unavailable")

    update_loop(config, status, stop_event, updater=fail_once)

    snapshot = status.snapshot()
    assert snapshot["status"] == "degraded"
    assert snapshot["last_success_at"] is None
    assert snapshot["last_error"] == "RuntimeError: source unavailable"
