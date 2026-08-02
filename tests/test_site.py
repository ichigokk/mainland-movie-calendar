from datetime import date

from mainland_movie_calendar.site import render_index


def test_index_contains_subscription_link_and_escapes_titles() -> None:
    state = {
        "generated_at": "2026-07-28T12:00:00+00:00",
        "movies": [
            {
                "title": "<测试电影>",
                "release_date": "2026-08-01",
                "countries": ["中国大陆"],
                "source_url": "https://example.com/movie",
                "status": "active",
            }
        ],
    }
    content = render_index(
        state,
        today=date(2026, 7, 28),
        public_base_url="https://ichigokk.github.io/mainland-movie-calendar",
    )

    assert "webcal://ichigokk.github.io/mainland-movie-calendar/calendar.ics" in content
    assert "&lt;测试电影&gt;" in content
    assert "<测试电影>" not in content


def test_index_converts_http_subscription_to_webcal() -> None:
    content = render_index(
        {"generated_at": None, "movies": []},
        today=date(2026, 8, 2),
        public_base_url="http://192.168.1.10:8000",
    )

    assert "webcal://192.168.1.10:8000/calendar.ics" in content
