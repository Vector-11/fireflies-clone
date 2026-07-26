"""The meeting aggregate: the meeting itself plus the entities it owns
directly — participants, speakers and tags.

Grouped in one module because they share a lifecycle: nothing here is
meaningful without its parent meeting, and all of it is cascade-deleted with it.

Participants and speakers are deliberately *separate* tables. A participant is
someone invited to the meeting (identified by email); a speaker is a voice
identified in the transcript. They usually overlap but not always — a guest can
attend and never speak, and a transcript can contain an unmatched "Speaker 3".
Fireflies' own API models them as two distinct collections for the same reason.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.action_item import ActionItem
    from app.models.summary import Summary
    from app.models.transcript import Chapter, Sentence
    from app.models.user import User


meeting_tags = Table(
    "meeting_tags",
    Base.metadata,
    Column("meeting_id", ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Meeting(TimestampMixin, Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    title: Mapped[str] = mapped_column(String(300), nullable=False)
    # Indexed because the library's default sort is "most recent first".
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    organizer_email: Mapped[str | None] = mapped_column(String(255))
    meeting_link: Mapped[str | None] = mapped_column(String(500))
    calendar_type: Mapped[str | None] = mapped_column(String(40))  # google | outlook | manual
    meeting_type: Mapped[str | None] = mapped_column(String(60))  # e.g. "Sales Call"

    # Optional real media. When both are null the player falls back to a
    # virtual clock driven off the last sentence's end time.
    audio_url: Mapped[str | None] = mapped_column(String(500))
    video_url: Mapped[str | None] = mapped_column(String(500))

    is_live: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    owner: Mapped["User"] = relationship(back_populates="meetings")

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Participant.id",
    )
    speakers: Mapped[list["Speaker"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Speaker.speaker_index",
    )
    sentences: Mapped[list["Sentence"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Sentence.idx",
    )
    chapters: Mapped[list["Chapter"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Chapter.idx",
    )
    action_items: Mapped[list["ActionItem"]] = relationship(
        back_populates="meeting",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ActionItem.order_index",
    )
    # One summary per meeting: a 1-to-1, enforced by the unique FK on summaries.
    summary: Mapped["Summary | None"] = relationship(
        back_populates="meeting", cascade="all, delete-orphan", passive_deletes=True
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary=meeting_tags, back_populates="meetings", order_by="Tag.name"
    )


class Participant(Base):
    """Someone invited to the meeting, keyed by email."""

    __tablename__ = "participants"
    __table_args__ = (UniqueConstraint("meeting_id", "email", name="uq_participant_meeting_email"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str | None] = mapped_column(String(120))
    # Mirrors Fireflies' distinction between guests and workspace members.
    is_fireflies_user: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    meeting: Mapped["Meeting"] = relationship(back_populates="participants")


class Speaker(Base):
    """A voice identified in the transcript."""

    __tablename__ = "speakers"
    __table_args__ = (UniqueConstraint("meeting_id", "speaker_index", name="uq_speaker_meeting_idx"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Position within this meeting (0, 1, 2 …), stable across renames.
    speaker_index: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    # Index into the frontend's avatar palette, stored so a speaker's colour
    # never changes between renders or page loads.
    color_key: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    meeting: Mapped["Meeting"] = relationship(back_populates="speakers")
    sentences: Mapped[list["Sentence"]] = relationship(back_populates="speaker")


class Tag(Base):
    """Free-form topic label, shared across meetings (many-to-many)."""

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True, index=True, nullable=False)
    color: Mapped[str] = mapped_column(String(20), default="purple", nullable=False)

    meetings: Mapped[list["Meeting"]] = relationship(secondary=meeting_tags, back_populates="tags")
