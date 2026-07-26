"""Transcript content: the sentences themselves and the chapter outline."""

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.meeting import Meeting, Speaker


class Sentence(Base):
    """One line of the transcript.

    Times are stored as integer milliseconds rather than formatted strings so
    the player can seek and the active line can be found by comparison, with no
    parsing on the hot path.

    The four boolean flags are this app's version of Fireflies' ``ai_filters``.
    They are computed once at ingestion by ``services.insight_tagger`` and drive
    the transcript filter pills; storing them beats recomputing per request.
    """

    __tablename__ = "sentences"
    __table_args__ = (
        UniqueConstraint("meeting_id", "idx", name="uq_sentence_meeting_idx"),
        # Supports "which line is playing right now" lookups.
        Index("ix_sentence_meeting_start", "meeting_id", "start_ms"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Nullable: an unmatched speaker label should not lose us the line.
    speaker_id: Mapped[int | None] = mapped_column(
        ForeignKey("speakers.id", ondelete="SET NULL"), index=True
    )

    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    sentiment: Mapped[str] = mapped_column(String(10), default="neutral", nullable=False)

    is_task: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_question: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_metric: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_date_time: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    meeting: Mapped["Meeting"] = relationship(back_populates="sentences")
    speaker: Mapped["Speaker | None"] = relationship(back_populates="sentences")


class Chapter(Base):
    """A section of the meeting — Fireflies renders these as the outline."""

    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("meeting_id", "idx", name="uq_chapter_meeting_idx"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    idx: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    gist: Mapped[str | None] = mapped_column(Text)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)

    meeting: Mapped["Meeting"] = relationship(back_populates="chapters")
