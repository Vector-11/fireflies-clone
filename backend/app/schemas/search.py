"""Global search responses."""

from pydantic import BaseModel

from app.schemas.common import UtcDateTime


class SearchHitOut(BaseModel):
    sentence_id: int
    idx: int
    start_ms: int
    speaker_name: str | None = None
    # Contains <mark> tags around the matched terms, produced by FTS5's
    # snippet(). The frontend renders it as HTML after sanitising.
    snippet: str


class SearchResultOut(BaseModel):
    """All the hits inside one meeting, plus enough context to render a card."""

    meeting_id: int
    title: str
    date: UtcDateTime
    duration_seconds: int
    meeting_type: str | None = None
    match_count: int
    hits: list[SearchHitOut]


class SearchResponse(BaseModel):
    query: str
    total_meetings: int
    # False when FTS5 was unavailable and the LIKE fallback answered instead.
    ranked: bool
    results: list[SearchResultOut]
