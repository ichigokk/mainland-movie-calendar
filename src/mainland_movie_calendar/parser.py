from __future__ import annotations

import re
from datetime import date, timedelta

from bs4 import BeautifulSoup

from mainland_movie_calendar.models import MovieListing

SUBJECT_ID_RE = re.compile(r"/subject/(\d+)/?")
MONTH_DAY_RE = re.compile(r"(\d{1,2})月(\d{1,2})日")
WISH_COUNT_RE = re.compile(r"([\d,]+)")
CJK_RE = re.compile(r"[\u3400-\u9fff]")


def _split_values(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split("/") if part.strip())


def _display_title(link_title: str, visible_title: str) -> str:
    full_title = link_title.strip() or visible_title.strip()
    if CJK_RE.search(full_title):
        return re.split(r"\s+(?=[A-Za-z][A-Za-z0-9])", full_title, maxsplit=1)[0]
    return full_title


def _infer_release_date(raw_date: str, today: date) -> date | None:
    match = MONTH_DAY_RE.search(raw_date)
    if not match:
        return None

    month, day = (int(value) for value in match.groups())
    candidate = date(today.year, month, day)
    if candidate < today - timedelta(days=14):
        candidate = date(today.year + 1, month, day)
    return candidate


def parse_upcoming_movies(html: str, *, today: date) -> list[MovieListing]:
    """Parse every movie in the mainland-China upcoming-release table."""
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.coming_list tbody tr")
    if not rows:
        raise ValueError("upcoming-movie table is empty or its markup changed")

    movies: list[MovieListing] = []
    seen_ids: set[str] = set()

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 4:
            continue

        link = cells[1].find("a", href=SUBJECT_ID_RE)
        if link is None:
            continue

        id_match = SUBJECT_ID_RE.search(link["href"])
        if id_match is None:
            continue

        source_id = id_match.group(1)
        if source_id in seen_ids:
            continue
        seen_ids.add(source_id)

        release_date = _infer_release_date(cells[0].get_text(" ", strip=True), today)
        if release_date is None:
            continue
        wish_match = (
            WISH_COUNT_RE.search(cells[4].get_text(" ", strip=True)) if len(cells) > 4 else None
        )
        wish_count = int(wish_match.group(1).replace(",", "")) if wish_match else None

        movies.append(
            MovieListing(
                source_id=source_id,
                title=_display_title(link.get("title", ""), link.get_text(" ", strip=True)),
                release_date=release_date.isoformat(),
                genres=_split_values(cells[2].get_text(" ", strip=True)),
                countries=_split_values(cells[3].get_text(" ", strip=True)),
                source_url=link["href"],
                wish_count=wish_count,
            )
        )

    if not movies:
        raise ValueError("no movies could be parsed from the upcoming-movie table")
    return movies
