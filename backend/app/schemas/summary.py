"""Summary and chapter responses."""

from app.schemas.common import ORMModel


class ChapterOut(ORMModel):
    id: int
    idx: int
    title: str
    gist: str | None = None
    start_ms: int
    end_ms: int


class SummaryOut(ORMModel):
    id: int
    gist: str | None = None
    short_summary: str | None = None
    overview: str | None = None
    bullet_gist: str | None = None
    shorthand_bullet: str | None = None
    notes: str | None = None
    keywords: list[str] = []
    topics_discussed: list[str] = []
    # Provenance, surfaced in the UI so the summary is never passed off as
    # something it isn't.
    generated_by: str
    model: str | None = None
