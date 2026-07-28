from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any


def _escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace(";", "\\;").replace(",", "\\,")


def _fold_line(line: str) -> list[str]:
    """Fold one RFC 5545 content line without splitting UTF-8 code points."""
    lines: list[str] = []
    remaining = line
    first = True

    while remaining:
        limit = 75 if first else 74
        size = 0
        cut = 0
        for index, char in enumerate(remaining):
            char_size = len(char.encode("utf-8"))
            if size + char_size > limit:
                break
            size += char_size
            cut = index + 1
        if cut == 0:
            cut = 1
        chunk, remaining = remaining[:cut], remaining[cut:]
        lines.append(chunk if first else f" {chunk}")
        first = False
    return lines or [""]


def _event_lines(movie: dict[str, Any], *, generated_at: datetime) -> list[str]:
    release = date.fromisoformat(movie["release_date"])
    withdrawn = movie.get("status") == "withdrawn"
    title = f"🎬《{movie['title']}》上映"
    if withdrawn:
        title += "（已撤档，待定）"

    details = [
        f"中国大陆院线上映日期：{movie['release_date']}",
        f"制片国家/地区：{' / '.join(movie.get('countries', [])) or '未知'}",
        f"类型：{' / '.join(movie.get('genres', [])) or '未知'}",
        "数据来源：豆瓣电影“即将上映”页面",
        "档期易变，请以片方或购票平台最新公告为准。",
    ]

    return [
        "BEGIN:VEVENT",
        f"UID:douban-{movie['source_id']}@mainland-movie-calendar",
        f"DTSTAMP:{generated_at.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        f"LAST-MODIFIED:{generated_at.astimezone(UTC).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;VALUE=DATE:{release.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{(release + timedelta(days=1)).strftime('%Y%m%d')}",
        f"SUMMARY:{_escape_text(title)}",
        "LOCATION:中国大陆院线",
        f"DESCRIPTION:{_escape_text(chr(10).join(details))}",
        f"URL:{movie['source_url']}",
        "CATEGORIES:电影,中国大陆院线",
        f"STATUS:{'TENTATIVE' if withdrawn else 'CONFIRMED'}",
        "TRANSP:TRANSPARENT",
        "END:VEVENT",
    ]


def render_calendar(
    state: dict[str, Any],
    *,
    today: date,
    generated_at: datetime | None = None,
    past_days: int = 30,
    future_days: int = 370,
) -> str:
    generated = generated_at or datetime.now(UTC)
    minimum = today - timedelta(days=past_days)
    maximum = today + timedelta(days=future_days)
    movies = [
        movie
        for movie in state.get("movies", [])
        if minimum <= date.fromisoformat(movie["release_date"]) <= maximum
    ]

    content = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//mainland-movie-calendar//Mainland China Theatrical Releases//ZH-CN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:中国大陆院线上映",
        "X-WR-CALDESC:中国大陆院线定档日历（国产片与进口片）",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:P1D",
    ]
    for movie in sorted(movies, key=lambda item: (item["release_date"], item["title"])):
        content.extend(_event_lines(movie, generated_at=generated))
    content.append("END:VCALENDAR")

    folded = [folded_line for line in content for folded_line in _fold_line(line)]
    return "\r\n".join(folded) + "\r\n"


def write_calendar(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")
