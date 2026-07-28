from pathlib import Path

import httpx
import pytest

from mainland_movie_calendar.fetch import (
    DOUBAN_COMING_URL,
    DOUBAN_READER_URL,
    fetch_upcoming_html,
)

FIXTURE = Path(__file__).parent / "fixtures" / "douban-coming.html"


def test_falls_back_to_html_reader_when_direct_source_is_blocked() -> None:
    fixture = FIXTURE.read_text(encoding="utf-8")
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if str(request.url) == DOUBAN_COMING_URL:
            return httpx.Response(403, request=request)
        assert str(request.url) == DOUBAN_READER_URL
        assert request.headers["X-Return-Format"] == "html"
        return httpx.Response(200, text=fixture, request=request)

    html = fetch_upcoming_html(
        attempts=1,
        transport=httpx.MockTransport(handler),
    )

    assert "coming_list" in html
    assert [str(request.url) for request in requests] == [
        DOUBAN_COMING_URL,
        DOUBAN_READER_URL,
    ]


def test_raises_when_direct_and_fallback_sources_fail() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request)

    with pytest.raises(RuntimeError, match="any source"):
        fetch_upcoming_html(
            attempts=1,
            transport=httpx.MockTransport(handler),
        )
