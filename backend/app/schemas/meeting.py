"""Meeting requests and responses.

Two read shapes on purpose. ``MeetingListItem`` is what the library grid needs
and nothing more; ``MeetingDetail`` carries the summary, chapters and speakers.
Sending the detail shape for a list of twenty meetings would move a great deal
of text nobody is going to read.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel, UtcDateTime
from app.schemas.summary import ChapterOut, SummaryOut
from app.schemas.user import UserOut


class TagOut(ORMModel):
    id: int
    name: str
    color: str


class ParticipantOut(ORMModel):
    id: int
    email: str
    name: str | None = None
    is_fireflies_user: bool


class ParticipantIn(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    name: str | None = Field(default=None, max_length=120)
    is_fireflies_user: bool = False


class SpeakerOut(ORMModel):
    id: int
    speaker_index: int
    name: str
    color_key: int


class MeetingListItem(ORMModel):
    id: int
    title: str
    date: UtcDateTime
    duration_seconds: int
    meeting_type: str | None = None
    calendar_type: str | None = None
    is_live: bool
    participants: list[ParticipantOut] = []
    tags: list[TagOut] = []

    # Populated by the router from aggregate queries rather than by walking
    # relationships, so listing N meetings stays a fixed number of queries.
    gist: str | None = None
    sentence_count: int = 0
    action_item_count: int = 0
    open_action_item_count: int = 0


class MeetingDetail(ORMModel):
    id: int
    title: str
    date: UtcDateTime
    duration_seconds: int
    organizer_email: str | None = None
    meeting_link: str | None = None
    calendar_type: str | None = None
    meeting_type: str | None = None
    audio_url: str | None = None
    video_url: str | None = None
    is_live: bool
    created_at: UtcDateTime
    updated_at: UtcDateTime

    owner: UserOut
    participants: list[ParticipantOut] = []
    speakers: list[SpeakerOut] = []
    chapters: list[ChapterOut] = []
    tags: list[TagOut] = []
    summary: SummaryOut | None = None

    sentence_count: int = 0


class MeetingCreate(BaseModel):
    """Create a meeting, optionally with a transcript pasted straight in.

    Leaving ``transcript`` out produces an empty meeting the user can upload a
    file to afterwards — that is the "create via a form" path from the brief.
    """

    title: str = Field(min_length=1, max_length=300)
    date: datetime | None = None
    transcript: str | None = None
    transcript_filename: str | None = None
    participants: list[ParticipantIn] = []
    tags: list[str] = []
    meeting_type: str | None = Field(default=None, max_length=60)
    meeting_link: str | None = Field(default=None, max_length=500)
    audio_url: str | None = Field(default=None, max_length=500)


class MeetingUpdate(BaseModel):
    """PATCH. Omitted fields are left alone; an empty list *does* clear."""

    title: str | None = Field(default=None, min_length=1, max_length=300)
    date: datetime | None = None
    meeting_type: str | None = Field(default=None, max_length=60)
    meeting_link: str | None = Field(default=None, max_length=500)
    participants: list[ParticipantIn] | None = None
    tags: list[str] | None = None


SortOption = Literal["recent", "oldest", "longest", "shortest", "title"]
