from datetime import UTC, date, datetime

from mainland_movie_calendar.models import MovieListing
from mainland_movie_calendar.state import empty_state, merge_listings

NOW = datetime(2026, 7, 28, 12, 0, tzinfo=UTC)


def listing(release_date: str) -> MovieListing:
    return MovieListing(
        source_id="42",
        title="测试电影",
        release_date=release_date,
        genres=("剧情",),
        countries=("中国大陆",),
        source_url="https://movie.douban.com/subject/42/",
        wish_count=100,
    )


def test_schedule_change_updates_existing_movie_without_changing_id() -> None:
    state, first_changes = merge_listings(
        empty_state(), [listing("2026-08-07")], today=date(2026, 7, 28), now=NOW
    )
    state, second_changes = merge_listings(
        state, [listing("2026-08-01")], today=date(2026, 7, 28), now=NOW
    )

    assert first_changes[0]["kind"] == "added"
    assert second_changes[0]["kind"] == "updated"
    assert state["movies"][0]["source_id"] == "42"
    assert state["movies"][0]["release_date"] == "2026-08-01"
    assert state["movies"][0]["history"][-1]["changes"]["release_date"] == {
        "from": "2026-08-07",
        "to": "2026-08-01",
    }


def test_unchanged_listing_is_idempotent() -> None:
    state, _ = merge_listings(
        empty_state(), [listing("2026-08-07")], today=date(2026, 7, 28), now=NOW
    )
    unchanged, changes = merge_listings(
        state,
        [listing("2026-08-07")],
        today=date(2026, 7, 29),
        now=datetime(2026, 7, 29, 12, 0, tzinfo=UTC),
    )

    assert unchanged == state
    assert changes == []


def test_future_movie_is_withdrawn_only_after_three_missing_runs_and_can_return() -> None:
    state, _ = merge_listings(
        empty_state(), [listing("2026-08-07")], today=date(2026, 7, 28), now=NOW
    )

    for expected_missing_runs in range(1, 4):
        state, changes = merge_listings(state, [], today=date(2026, 7, 28), now=NOW)
        assert state["movies"][0]["missing_runs"] == expected_missing_runs
        if expected_missing_runs < 3:
            assert state["movies"][0]["status"] == "active"
            assert changes == []

    assert state["movies"][0]["status"] == "withdrawn"
    assert changes[0]["kind"] == "withdrawn"

    state, changes = merge_listings(
        state, [listing("2026-08-14")], today=date(2026, 7, 28), now=NOW
    )
    assert state["movies"][0]["status"] == "active"
    assert state["movies"][0]["missing_runs"] == 0
    assert changes[0]["kind"] == "updated"
