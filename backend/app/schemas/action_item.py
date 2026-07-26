"""Action item requests and responses."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, UtcDateTime
from app.schemas.meeting import ParticipantOut

Status = Literal["open", "completed"]


class ActionItemOut(ORMModel):
    id: int
    meeting_id: int
    text: str
    status: Status
    source: str
    due_date: date | None = None
    order_index: int
    completed_at: UtcDateTime | None = None
    sentence_id: int | None = None
    assignee: ParticipantOut | None = None


class ActionItemCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)
    assignee_participant_id: int | None = None
    due_date: date | None = None


class ActionItemUpdate(BaseModel):
    """Every field optional — this is a PATCH, not a replace."""

    text: str | None = Field(default=None, min_length=1, max_length=2000)
    status: Status | None = None
    assignee_participant_id: int | None = None
    due_date: date | None = None
    order_index: int | None = None
