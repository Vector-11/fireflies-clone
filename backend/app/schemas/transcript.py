"""Transcript responses."""

from pydantic import BaseModel

from app.schemas.common import ORMModel


class SentenceOut(ORMModel):
    id: int
    idx: int
    text: str
    start_ms: int
    end_ms: int
    speaker_id: int | None = None
    sentiment: str
    is_task: bool
    is_question: bool
    is_metric: bool
    is_date_time: bool


class TranscriptOut(BaseModel):
    """The whole transcript in one response.

    Not paginated on purpose. The player needs every timestamp up front to
    highlight the active line and to render the seek bar, and a meeting-length
    transcript is a few hundred rows — small enough that one request is both
    simpler and faster than paging.
    """

    meeting_id: int
    total: int
    sentences: list[SentenceOut]


class SentenceUpdate(BaseModel):
    text: str
