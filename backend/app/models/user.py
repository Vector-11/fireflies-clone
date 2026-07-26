"""The workspace user.

Real authentication is out of scope for this assignment, so the app runs as a
single seeded user. The table exists anyway because every meeting belongs to
someone, and modelling that now is what makes adding auth later a non-event.
"""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.meeting import Meeting


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    job_title: Mapped[str | None] = mapped_column(String(120))
    timezone: Mapped[str] = mapped_column(String(64), default="Asia/Kolkata", nullable=False)

    meetings: Mapped[list["Meeting"]] = relationship(
        back_populates="owner", cascade="all, delete-orphan", passive_deletes=True
    )
