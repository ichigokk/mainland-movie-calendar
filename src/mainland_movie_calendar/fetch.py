from __future__ import annotations

import time

import httpx

DOUBAN_COMING_URL = "https://movie.douban.com/coming"

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
    attempts: int = 3,
    timeout_seconds: float = 20,
) -> str:
    """Fetch the mainland-China upcoming-release page with bounded retries."""
    last_error: Exception | None = None

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=timeout_seconds) as client:
        for attempt in range(attempts):
            try:
                response = client.get(url)
                response.raise_for_status()
                if "coming_list" not in response.text:
                    raise ValueError("response does not contain the upcoming-movie table")
                return response.text
            except (httpx.HTTPError, ValueError) as exc:
                last_error = exc
                if attempt + 1 < attempts:
                    time.sleep(2**attempt)

    raise RuntimeError(f"could not fetch upcoming movies after {attempts} attempts") from last_error
