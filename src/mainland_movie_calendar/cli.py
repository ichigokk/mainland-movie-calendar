from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path

from mainland_movie_calendar.fetch import DOUBAN_COMING_URL, fetch_upcoming_html
from mainland_movie_calendar.ics import render_calendar, write_calendar
from mainland_movie_calendar.parser import parse_upcoming_movies
from mainland_movie_calendar.site import render_index, write_index
from mainland_movie_calendar.state import load_state, merge_listings, write_state

DEFAULT_PUBLIC_URL = "https://ichigokk.github.io/mainland-movie-calendar"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Update the mainland-China theatrical release calendar."
    )
    parser.add_argument("--state", type=Path, default=Path("data/movies.json"))
    parser.add_argument("--ics", type=Path, default=Path("docs/calendar.ics"))
    parser.add_argument("--html", type=Path, default=Path("docs/index.html"))
    parser.add_argument("--source-url", default=DOUBAN_COMING_URL)
    parser.add_argument(
        "--public-base-url",
        default=os.environ.get("PUBLIC_BASE_URL", DEFAULT_PUBLIC_URL),
    )
    parser.add_argument("--fixture", type=Path, help="Read HTML from a local fixture.")
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    return parser


def run(args: argparse.Namespace) -> list[dict]:
    html = (
        args.fixture.read_text(encoding="utf-8")
        if args.fixture
        else fetch_upcoming_html(args.source_url)
    )
    listings = parse_upcoming_movies(html, today=args.today)
    current = load_state(args.state)
    now = datetime.now(UTC)
    merged, changes = merge_listings(current, listings, today=args.today, now=now)
    rendered_at = datetime.fromisoformat(merged["generated_at"])

    write_state(args.state, merged)
    write_calendar(args.ics, render_calendar(merged, today=args.today, generated_at=rendered_at))
    write_index(
        args.html,
        render_index(merged, today=args.today, public_base_url=args.public_base_url),
    )
    return changes


def main() -> None:
    args = build_parser().parse_args()
    changes = run(args)
    print(json.dumps({"changes": changes, "count": len(changes)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
