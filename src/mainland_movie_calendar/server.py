from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import threading
from argparse import Namespace
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, ClassVar
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from mainland_movie_calendar.cli import run
from mainland_movie_calendar.fetch import DOUBAN_COMING_URL
from mainland_movie_calendar.site import render_index, write_index
from mainland_movie_calendar.state import load_state

LOGGER = logging.getLogger("mainland_movie_calendar.server")
DEFAULT_UPDATE_INTERVAL_SECONDS = 6 * 60 * 60
DEFAULT_RETRY_INTERVAL_SECONDS = 15 * 60


def _positive_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc
    if value <= 0:
        raise ValueError(f"{name} must be greater than zero")
    return value


@dataclass(frozen=True)
class ServerConfig:
    data_dir: Path
    seed_root: Path
    public_base_url: str
    source_url: str
    host: str
    port: int
    timezone: str
    update_interval_seconds: int
    retry_interval_seconds: int

    @classmethod
    def from_env(cls) -> ServerConfig:
        return cls(
            data_dir=Path(os.environ.get("DATA_DIR", "/data")),
            seed_root=Path(os.environ.get("SEED_ROOT", "/app")),
            public_base_url=os.environ.get("PUBLIC_BASE_URL", "http://localhost:8000"),
            source_url=os.environ.get("SOURCE_URL", DOUBAN_COMING_URL),
            host=os.environ.get("HOST", "0.0.0.0"),
            port=_positive_int("PORT", 8000),
            timezone=os.environ.get("TZ", "Asia/Shanghai"),
            update_interval_seconds=_positive_int(
                "UPDATE_INTERVAL_SECONDS", DEFAULT_UPDATE_INTERVAL_SECONDS
            ),
            retry_interval_seconds=_positive_int(
                "RETRY_INTERVAL_SECONDS", DEFAULT_RETRY_INTERVAL_SECONDS
            ),
        )

    @property
    def state_path(self) -> Path:
        return self.data_dir / "movies.json"

    @property
    def public_dir(self) -> Path:
        return self.data_dir / "public"

    @property
    def calendar_path(self) -> Path:
        return self.public_dir / "calendar.ics"

    @property
    def index_path(self) -> Path:
        return self.public_dir / "index.html"


class ServiceStatus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._started_at = datetime.now(UTC).isoformat()
        self._last_attempt_at: str | None = None
        self._last_success_at: str | None = None
        self._last_error: str | None = None
        self._last_change_count = 0

    def mark_attempt(self) -> None:
        with self._lock:
            self._last_attempt_at = datetime.now(UTC).isoformat()

    def mark_success(self, changes: list[dict[str, Any]]) -> None:
        with self._lock:
            self._last_success_at = datetime.now(UTC).isoformat()
            self._last_error = None
            self._last_change_count = len(changes)

    def mark_failure(self, error: Exception) -> None:
        with self._lock:
            self._last_error = f"{type(error).__name__}: {error}"

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            if self._last_error:
                state = "degraded"
            elif self._last_success_at:
                state = "ok"
            else:
                state = "starting"
            return {
                "status": state,
                "started_at": self._started_at,
                "last_attempt_at": self._last_attempt_at,
                "last_success_at": self._last_success_at,
                "last_error": self._last_error,
                "last_change_count": self._last_change_count,
            }


class CalendarRequestHandler(SimpleHTTPRequestHandler):
    extensions_map: ClassVar[dict[str, str]] = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".ics": "text/calendar; charset=utf-8",
        ".json": "application/json; charset=utf-8",
    }

    def __init__(
        self,
        *args: Any,
        directory: str,
        status: ServiceStatus,
        **kwargs: Any,
    ) -> None:
        self.status = status
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/healthz":
            payload = json.dumps(self.status.snapshot(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
            return
        super().do_GET()

    def end_headers(self) -> None:
        if urlsplit(self.path).path.endswith((".ics", ".html", "/")):
            self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("http client=%s message=%s", self.client_address[0], format % args)


def ensure_seed_data(config: ServerConfig) -> None:
    config.public_dir.mkdir(parents=True, exist_ok=True)
    seeds = (
        (config.seed_root / "data" / "movies.json", config.state_path),
        (config.seed_root / "docs" / "calendar.ics", config.calendar_path),
        (config.seed_root / "docs" / "index.html", config.index_path),
    )
    for source, destination in seeds:
        if not destination.exists() and source.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def refresh_index(config: ServerConfig) -> None:
    """Render the landing page with this server's public subscription URL."""
    today = datetime.now(ZoneInfo(config.timezone)).date()
    write_index(
        config.index_path,
        render_index(
            load_state(config.state_path),
            today=today,
            public_base_url=config.public_base_url,
        ),
    )


def update_once(config: ServerConfig) -> list[dict[str, Any]]:
    today = datetime.now(ZoneInfo(config.timezone)).date()
    args = Namespace(
        state=config.state_path,
        ics=config.calendar_path,
        html=config.index_path,
        source_url=config.source_url,
        public_base_url=config.public_base_url,
        fixture=None,
        today=today,
    )
    return run(args)


def update_loop(
    config: ServerConfig,
    status: ServiceStatus,
    stop_event: threading.Event,
    *,
    updater: Callable[[], list[dict[str, Any]]] | None = None,
) -> None:
    execute = updater or partial(update_once, config)
    while not stop_event.is_set():
        status.mark_attempt()
        try:
            changes = execute()
        except Exception as exc:
            status.mark_failure(exc)
            LOGGER.exception(
                "calendar update failed; keeping the last valid files and retrying in %ss",
                config.retry_interval_seconds,
            )
            delay = config.retry_interval_seconds
        else:
            status.mark_success(changes)
            LOGGER.info(
                "calendar update succeeded changes=%s next_update_in=%ss",
                len(changes),
                config.update_interval_seconds,
            )
            delay = config.update_interval_seconds
        stop_event.wait(delay)


def serve(config: ServerConfig) -> None:
    ensure_seed_data(config)
    refresh_index(config)
    status = ServiceStatus()
    stop_event = threading.Event()
    handler = partial(
        CalendarRequestHandler,
        directory=str(config.public_dir),
        status=status,
    )
    server = ThreadingHTTPServer((config.host, config.port), handler)
    worker = threading.Thread(
        target=update_loop,
        args=(config, status, stop_event),
        name="calendar-updater",
        daemon=True,
    )

    def request_shutdown(_signum: int, _frame: Any) -> None:
        stop_event.set()
        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, request_shutdown)
    signal.signal(signal.SIGINT, request_shutdown)
    worker.start()
    LOGGER.info(
        "serving calendar url=%s/calendar.ics listen=%s:%s interval=%ss",
        config.public_base_url.rstrip("/"),
        config.host,
        config.port,
        config.update_interval_seconds,
    )
    try:
        server.serve_forever()
    finally:
        stop_event.set()
        server.server_close()
        worker.join(timeout=5)


def main() -> None:
    logging.basicConfig(
        level=os.environ.get("LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    serve(ServerConfig.from_env())


if __name__ == "__main__":
    main()
