"""Meetings: list, create, read, update, delete, and transcript upload."""

from __future__ import annotations

from datetime import UTC, date, datetime, time

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from sqlalchemy import Select, case, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, get_meeting
from app.core.db import get_db
from app.models.action_item import STATUS_OPEN, ActionItem
from app.models.meeting import Meeting, Participant, Tag
from app.models.summary import Summary
from app.models.transcript import Sentence
from app.models.user import User
from app.schemas.common import Page
from app.schemas.meeting import (
    MeetingCreate,
    MeetingDetail,
    MeetingListItem,
    MeetingUpdate,
    SortOption,
)
from app.services import meeting_service
from app.services.transcript_parser import TranscriptParseError, parse_transcript

router = APIRouter(prefix="/meetings", tags=["meetings"])

# Whitelist rather than an ORDER BY built from user input.
_SORTS = {
    "recent": Meeting.date.desc(),
    "oldest": Meeting.date.asc(),
    "longest": Meeting.duration_seconds.desc(),
    "shortest": Meeting.duration_seconds.asc(),
    "title": Meeting.title.asc(),
}

_MAX_UPLOAD_BYTES = 5 * 1024 * 1024


def _apply_filters(
    stmt: Select,
    *,
    q: str | None,
    participant: str | None,
    tag: str | None,
    date_from: date | None,
    date_to: date | None,
) -> Select:
    """Every filter is optional and they compose."""
    if q and q.strip():
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(Meeting.title.ilike(pattern), Meeting.meeting_type.ilike(pattern)))

    if participant and participant.strip():
        pattern = f"%{participant.strip()}%"
        stmt = (
            stmt.join(Participant, Participant.meeting_id == Meeting.id)
            .where(or_(Participant.email.ilike(pattern), Participant.name.ilike(pattern)))
            .distinct()
        )

    if tag and tag.strip():
        stmt = stmt.join(Meeting.tags).where(Tag.name.ilike(tag.strip())).distinct()

    # Timestamps are stored as UTC wall-clock, so the bounds are built naive in
    # UTC to compare like with like.
    if date_from:
        stmt = stmt.where(Meeting.date >= datetime.combine(date_from, time.min))
    if date_to:
        stmt = stmt.where(Meeting.date <= datetime.combine(date_to, time.max))

    return stmt


def _decorate(db: Session, meetings: list[Meeting]) -> list[MeetingListItem]:
    """Attach the aggregate columns the library grid shows.

    Three grouped queries for the whole page rather than three per row — the
    difference between a constant number of round trips and an N+1.
    """
    items = [MeetingListItem.model_validate(meeting) for meeting in meetings]
    ids = [meeting.id for meeting in meetings]
    if not ids:
        return items

    sentence_counts = dict(
        db.execute(
            select(Sentence.meeting_id, func.count())
            .where(Sentence.meeting_id.in_(ids))
            .group_by(Sentence.meeting_id)
        ).all()
    )
    action_rows = db.execute(
        select(
            ActionItem.meeting_id,
            func.count(),
            func.sum(case((ActionItem.status == STATUS_OPEN, 1), else_=0)),
        )
        .where(ActionItem.meeting_id.in_(ids))
        .group_by(ActionItem.meeting_id)
    ).all()
    action_counts = {row[0]: (row[1], row[2] or 0) for row in action_rows}
    gists = dict(
        db.execute(
            select(Summary.meeting_id, Summary.gist).where(Summary.meeting_id.in_(ids))
        ).all()
    )

    for item in items:
        item.sentence_count = sentence_counts.get(item.id, 0)
        total, open_count = action_counts.get(item.id, (0, 0))
        item.action_item_count = total
        item.open_action_item_count = open_count
        item.gist = gists.get(item.id)

    return items


def _detail(db: Session, meeting: Meeting) -> MeetingDetail:
    db.refresh(meeting)
    detail = MeetingDetail.model_validate(meeting)
    detail.sentence_count = (
        db.execute(
            select(func.count()).select_from(Sentence).where(Sentence.meeting_id == meeting.id)
        ).scalar_one()
        or 0
    )
    return detail


@router.get("", response_model=Page[MeetingListItem])
def list_meetings(
    q: str | None = Query(None, description="Match against meeting title or type"),
    participant: str | None = Query(None, description="Match a participant name or email"),
    tag: str | None = Query(None),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    sort: SortOption = Query("recent"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[MeetingListItem]:
    filters = {
        "q": q,
        "participant": participant,
        "tag": tag,
        "date_from": date_from,
        "date_to": date_to,
    }

    total = (
        db.execute(
            _apply_filters(select(func.count(func.distinct(Meeting.id))), **filters)
        ).scalar_one()
        or 0
    )

    stmt = _apply_filters(select(Meeting), **filters)
    stmt = (
        stmt.options(selectinload(Meeting.participants), selectinload(Meeting.tags))
        .order_by(_SORTS[sort], Meeting.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    meetings = list(db.execute(stmt).scalars().unique().all())

    return Page(items=_decorate(db, meetings), total=total, page=page, page_size=page_size)


@router.post("", response_model=MeetingDetail, status_code=status.HTTP_201_CREATED)
def create_meeting(
    payload: MeetingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MeetingDetail:
    """Create a meeting, with or without a transcript.

    With one, the full pipeline runs and the meeting arrives complete with a
    summary, chapters and tasks. Without, you get an empty meeting to upload a
    transcript to later.
    """
    parsed = []
    if payload.transcript and payload.transcript.strip():
        try:
            parsed = parse_transcript(payload.transcript, payload.transcript_filename)
        except TranscriptParseError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
            ) from exc

    meeting = meeting_service.build_meeting(
        db,
        owner=user,
        title=payload.title,
        date=payload.date or datetime.now(UTC),
        parsed=parsed,
        participants=[participant.model_dump() for participant in payload.participants],
        tags=payload.tags,
        meeting_type=payload.meeting_type,
        meeting_link=payload.meeting_link,
        audio_url=payload.audio_url,
    )
    db.commit()
    return _detail(db, meeting)


@router.get("/{meeting_id}", response_model=MeetingDetail)
def read_meeting(
    meeting: Meeting = Depends(get_meeting), db: Session = Depends(get_db)
) -> MeetingDetail:
    return _detail(db, meeting)


@router.patch("/{meeting_id}", response_model=MeetingDetail)
def update_meeting(
    payload: MeetingUpdate,
    meeting: Meeting = Depends(get_meeting),
    db: Session = Depends(get_db),
) -> MeetingDetail:
    """Partial update. Only the fields present in the body are touched."""
    data = payload.model_dump(exclude_unset=True)

    for field in ("title", "date", "meeting_type", "meeting_link"):
        if field in data and data[field] is not None:
            setattr(meeting, field, data[field])

    if data.get("participants") is not None:
        meeting_service.sync_participants(db, meeting, data["participants"])
    if data.get("tags") is not None:
        meeting_service.sync_tags(db, meeting, data["tags"])

    db.commit()
    return _detail(db, meeting)


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting: Meeting = Depends(get_meeting), db: Session = Depends(get_db)
) -> Response:
    """Delete a meeting and everything belonging to it.

    The cascade is declared on the foreign keys and enforced by SQLite because
    ``PRAGMA foreign_keys=ON`` is set on every connection — see ``core/db.py``.
    """
    db.delete(meeting)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{meeting_id}/upload-transcript", response_model=MeetingDetail)
async def upload_transcript(
    file: UploadFile = File(...),
    meeting: Meeting = Depends(get_meeting),
    db: Session = Depends(get_db),
) -> MeetingDetail:
    """Replace this meeting's transcript from an uploaded .txt/.vtt/.srt/.json."""
    raw = await file.read()
    if len(raw) > _MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Transcript files are limited to 5 MB.",
        )

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError:
        # Windows-authored exports are frequently cp1252 rather than UTF-8.
        content = raw.decode("latin-1", errors="replace")

    try:
        parsed = parse_transcript(content, file.filename)
    except TranscriptParseError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc

    meeting_service.replace_transcript(db, meeting, parsed)
    db.commit()
    return _detail(db, meeting)
