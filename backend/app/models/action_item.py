"""Tasks extracted from a meeting, or added by hand afterwards."""

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.meeting import Meeting, Participant
    from app.models.transcript import Sentence

STATUS_OPEN = "open"
STATUS_COMPLETED = "completed"

# Where the task came from. Regenerating a summary rewrites the extracted tasks
# and must leave anything the user typed by hand completely alone — this column
# is what makes that distinction possible.
SOURCE_EXTRACTED = "extracted"
SOURCE_MANUAL = "manual"


class ActionItem(TimestampMixin, Base):
    __tablename__ = "action_items"
    __table_args__ = (
        # Cheap integrity guarantee: the DB rejects a bad status even if a bug
        # gets past the Pydantic layer.
        CheckConstraint(
            f"status IN ('{STATUS_OPEN}', '{STATUS_COMPLETED}')", name="ck_action_item_status"
        ),
        CheckConstraint(
            f"source IN ('{SOURCE_EXTRACTED}', '{SOURCE_MANUAL}')", name="ck_action_item_source"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Where in the transcript this came from. SET NULL, not CASCADE: editing a
    # transcript should never silently delete someone's task.
    sentence_id: Mapped[int | None] = mapped_column(
        ForeignKey("sentences.id", ondelete="SET NULL")
    )
    assignee_participant_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL")
    )

    text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=STATUS_OPEN, nullable=False)
    source: Mapped[str] = mapped_column(String(20), default=SOURCE_MANUAL, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    # Explicit ordering so drag-to-reorder is a data change, not a re-sort.
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    meeting: Mapped["Meeting"] = relationship(back_populates="action_items")
    sentence: Mapped["Sentence | None"] = relationship()
    assignee: Mapped["Participant | None"] = relationship()
