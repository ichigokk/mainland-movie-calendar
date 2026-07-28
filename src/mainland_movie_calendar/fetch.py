from __future__ import annotations

import time

import httpx

DOUBAN_COMING_URL = "https://movie.douban.com/coming"
DOUBAN_READER_URL = "https://r.jina.ai/http://movie.douban.com/coming"

HEADERS = {
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.6",
    "Cache-Control": "no-cache",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0 Safari/537.36 mainland-movie-calendar/0.1"
    ),
}


def fetch_upcoming_html(
    url: str = DOUBAN_COMING_URL,
    *,
    attempts: int = 2,
    timeout_seconds: float = 20,
    transport: httpx.BaseTransport | None = None,
) -> str:
    """Fetch upcoming releases, falling back to an HTML-preserving reader."""
    last_error: Exception | None = None
    sources = [(url, {})]
    if url == DOUBAN_COMING_URL:
        sources.append((DOUBAN_READER_URL, {"X-Return-Format": "html"}))

    with httpx.Client(
        headers=HEADERS,
        follow_redirects=True,
        timeout=timeout_seconds,
        transport=transport,
    ) as client:
        for source_url, extra_headers in sources:
            for attempt in range(attempts):
                try:
                    response = client.get(source_url, headers=extra_headers)
                    response.raise_for_status()
                    if "coming_list" not in response.text:
                        raise ValueError("response does not contain the upcoming-movie table")
                    return response.text
                except (httpx.HTTPError, ValueError) as exc:
                    last_error = exc
                    if attempt + 1 < attempts:
                        time.sleep(2**attempt)

    raise RuntimeError("could not fetch upcoming movies from any source") from last_error
