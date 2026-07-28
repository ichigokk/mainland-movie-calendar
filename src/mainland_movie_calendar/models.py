from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class MovieListing:
    source_id: str
    title: str
    release_date: str
    genres: tuple[str, ...]
    countries: tuple[str, ...]
    source_url: str
    wish_count: int | None = None

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["genres"] = list(self.genres)
        payload["countries"] = list(self.countries)
        payload.pop("wish_count", None)
        return payload
