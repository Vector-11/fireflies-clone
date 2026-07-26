"""Shared response building blocks."""

from datetime import UTC, datetime
from typing import Annotated, Generic, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict

T = TypeVar("T")


def _ensure_utc(value: datetime) -> datetime:
    """Stamp naive datetimes as UTC.

    SQLite has no native timestamp type, so ``DateTime(timezone=True)`` round
    trips through a string and comes back **naive**. Serialising that straight
    to JSON would hand the browser a time with no zone, which it would then
    interpret as local — every timestamp in the UI silently shifted. Normalising
    in one shared type means no individual schema has to remember.
    """
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


UtcDateTime = Annotated[datetime, AfterValidator(_ensure_utc)]


class ORMModel(BaseModel):
    """Base for anything read directly off a SQLAlchemy object."""

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel, Generic[T]):
    """Uniform envelope for every list endpoint."""

    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorResponse(BaseModel):
    detail: str
    code: str = "error"
