from datetime import date
from pathlib import Path

import pytest

from mainland_movie_calendar.parser import parse_upcoming_movies

FIXTURE = Path(__file__).parent / "fixtures" / "douban-coming.html"


def test_parses_mainland_release_table_and_full_titles() -> None:
    movies = parse_upcoming_movies(FIXTURE.read_text(encoding="utf-8"), today=date(2026, 7, 28))

    assert [movie.source_id for movie in movies] == ["36246195", "36791178", "99999999"]
    assert movies[0].title == "蜘蛛侠：崭新之日"
    assert movies[0].release_date == "2026-07-29"
    assert movies[0].wish_count == 59892
    assert movies[1].title == "汪汪队立大功大电影3：勇闯恐龙岛"
    assert movies[1].countries == ("加拿大", "美国")
    assert movies[2].release_date == "2027-01-01"
    assert all(movie.source_id != "88888888" for movie in movies)


def test_rejects_markup_without_upcoming_table() -> None:
    with pytest.raises(ValueError, match="table"):
        parse_upcoming_movies("<html></html>", today=date(2026, 7, 28))
