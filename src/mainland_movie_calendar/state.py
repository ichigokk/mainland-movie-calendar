from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from mainland_movie_calendar.models import MovieListing

SCHEMA_VERSION = 1
WITHDRAWN_AFTER_MISSING_RUNS = 3


def empty_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": None,
        "source": "https://movie.douban.com/coming",
        "movies": [],
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_state()
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported state schema: {state.get('schema_version')!r}")
    return state


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def merge_listings(
    current_state: dict[str, Any],
    listings: list[MovieListing],
    *,
    today: date,
    now: datetime | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Merge a scrape into durable state, preserving IDs across schedule changes."""
    timestamp = (now or datetime.now(UTC)).astimezone(UTC).isoformat()
    day = today.isoformat()
    merged = deepcopy(current_state)
    existing = {movie["source_id"]: movie for movie in merged.get("movies", [])}
    incoming = {listing.source_id: listing for listing in listings}
    changes: list[dict[str, Any]] = []

    for source_id, listing in incoming.items():
        payload = listing.to_dict()
        movie = existing.get(source_id)

        if movie is None:
            movie = {
                **payload,
                "status": "active",
                "missing_runs": 0,
                "first_seen_at": day,
                "last_seen_at": day,
                "updated_at": timestamp,
                "history": [],
            }
            existing[source_id] = movie
            changes.append({"kind": "added", "source_id": source_id, "title": listing.title})
            continue

        movie.pop("wish_count", None)
        changed_fields: dict[str, dict[str, Any]] = {}
        for field, value in payload.items():
            if movie.get(field) != value:
                changed_fields[field] = {"from": movie.get(field), "to": value}
                movie[field] = value

        if movie.get("status") != "active":
            changed_fields["status"] = {"from": movie.get("status"), "to": "active"}
        movie["status"] = "active"
        movie["missing_runs"] = 0

        if changed_fields:
            movie["last_seen_at"] = day
            movie.setdefault("history", []).append({"at": timestamp, "changes": changed_fields})
            movie["updated_at"] = timestamp
            changes.append(
                {
                    "kind": "updated",
                    "source_id": source_id,
                    "title": listing.title,
                    "changes": changed_fields,
                }
            )

    for source_id, movie in existing.items():
        if source_id in incoming:
            continue

        release_date = date.fromisoformat(movie["release_date"])
        if release_date < today:
            if movie.get("status") == "active":
                previous = movie.get("status")
                movie["status"] = "released"
                movie["updated_at"] = timestamp
                movie.setdefault("history", []).append(
                    {
                        "at": timestamp,
                        "changes": {"status": {"from": previous, "to": "released"}},
                    }
                )
                changes.append(
                    {
                        "kind": "released",
                        "source_id": source_id,
                        "title": movie["title"],
                    }
                )
            continue

        missing_runs = int(movie.get("missing_runs", 0)) + 1
        movie["missing_runs"] = missing_runs
        if missing_runs >= WITHDRAWN_AFTER_MISSING_RUNS and movie.get("status") != "withdrawn":
            previous = movie.get("status")
            movie["status"] = "withdrawn"
            movie["updated_at"] = timestamp
            movie.setdefault("history", []).append(
                {
                    "at": timestamp,
                    "changes": {"status": {"from": previous, "to": "withdrawn"}},
                }
            )
            changes.append(
                {
                    "kind": "withdrawn",
                    "source_id": source_id,
                    "title": movie["title"],
                }
            )

    merged["schema_version"] = SCHEMA_VERSION
    merged["movies"] = sorted(
        existing.values(),
        key=lambda movie: (movie["release_date"], movie["title"], movie["source_id"]),
    )
    if merged["movies"] != current_state.get("movies", []) or not current_state.get("generated_at"):
        merged["generated_at"] = timestamp
    return merged, changes
