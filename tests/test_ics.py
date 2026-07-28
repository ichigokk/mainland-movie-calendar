from datetime import UTC, date, datetime

from mainland_movie_calendar.ics import render_calendar

MOVIE = {
    "source_id": "36246195",
    "title": "蜘蛛侠：崭新之日",
    "release_date": "2026-07-29",
    "genres": ["动作", "科幻", "奇幻"],
    "countries": ["美国"],
    "source_url": "https://movie.douban.com/subject/36246195/",
    "status": "active",
}


def test_calendar_has_stable_uid_all_day_dates_and_valid_line_folding() -> None:
    content = render_calendar(
        {"movies": [MOVIE]},
        today=date(2026, 7, 28),
        generated_at=datetime(2026, 7, 28, 12, 0, tzinfo=UTC),
    )
    unfolded = content.replace("\r\n ", "")

    assert "UID:douban-36246195@mainland-movie-calendar.ichigokk.github.io" in unfolded
    assert "X-WR-RELCALID:mainland-movie-calendar.ichigokk.github.io" in unfolded
    assert "DTSTART;VALUE=DATE:20260729" in unfolded
    assert "DTEND;VALUE=DATE:20260730" in unfolded
    assert "SUMMARY:🎬《蜘蛛侠：崭新之日》上映" in unfolded
    assert all(len(line.encode("utf-8")) <= 75 for line in content.split("\r\n"))


def test_withdrawn_movie_is_kept_and_marked_tentative() -> None:
    withdrawn = {**MOVIE, "status": "withdrawn"}
    content = render_calendar({"movies": [withdrawn]}, today=date(2026, 7, 28))
    unfolded = content.replace("\r\n ", "")

    assert "已撤档，待定" in unfolded
    assert "STATUS:TENTATIVE" in unfolded
