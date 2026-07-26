"""The generated meeting summary.

Field names mirror Fireflies' public ``Summary`` schema (gist, short_summary,
overview, bullet_gist, shorthand_bullet, notes, keywords, topics_discussed) so
the UI can render the same set of panels they do.

Kept as its own 1-to-1 table rather than columns on ``meetings`` for two
reasons: the text is large and rarely needed by the library list view, and
regenerating a summary should not touch the meeting row.
"""

from typing import TYPE_CHECKING

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.meeting import Meeting


class Summary(TimestampMixin, Base):
    __tablename__ = "summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique=True is what makes this a 1-to-1 rather than a 1-to-many.
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), unique=True, nullable=False
    )

    gist: Mapped[str | None] = mapped_column(Text)  # one sentence
    short_summary: Mapped[str | None] = mapped_column(Text)  # one paragraph
    overview: Mapped[str | None] = mapped_column(Text)  # the long form
    bullet_gist: Mapped[str | None] = mapped_column(Text)  # newline-separated bullets
    shorthand_bullet: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)

    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    topics_discussed: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    # Provenance, so the UI can be honest about where the text came from.
    generated_by: Mapped[str] = mapped_column(String(20), default="heuristic", nullable=False)
    model: Mapped[str | None] = mapped_column(String(80))

    meeting: Mapped["Meeting"] = relationship(back_populates="summary")
