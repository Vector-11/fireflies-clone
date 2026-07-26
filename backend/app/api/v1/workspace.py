"""Workspace-level endpoints: the current user, and the dashboard stat tiles."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.models.action_item import STATUS_OPEN, ActionItem
from app.models.meeting import Meeting, Participant, Tag
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter(tags=["workspace"])


class TagCount(BaseModel):
    name: str
    color: str
    count: int


class AnalyticsOverview(BaseModel):
    total_meetings: int
    meetings_this_week: int
    total_duration_seconds: int
    open_action_items: int
    completed_action_items: int
    unique_participants: int
    top_tags: list[TagCount]


@router.get("/me", response_model=UserOut)
def read_current_user(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(user)


@router.get("/analytics/overview", response_model=AnalyticsOverview)
def analytics_overview(db: Session = Depends(get_db)) -> AnalyticsOverview:
    """Aggregate counts for the home dashboard.

    Every figure is a single aggregate query — nothing here loads rows into
    Python to count them.
    """
    week_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)

    total_meetings = db.execute(select(func.count()).select_from(Meeting)).scalar_one() or 0
    meetings_this_week = (
        db.execute(
            select(func.count()).select_from(Meeting).where(Meeting.date >= week_ago)
        ).scalar_one()
        or 0
    )
    total_duration = (
        db.execute(select(func.coalesce(func.sum(Meeting.duration_seconds), 0))).scalar_one() or 0
    )
    open_items = (
        db.execute(
            select(func.count())
            .select_from(ActionItem)
            .where(ActionItem.status == STATUS_OPEN)
        ).scalar_one()
        or 0
    )
    total_items = db.execute(select(func.count()).select_from(ActionItem)).scalar_one() or 0
    unique_participants = (
        db.execute(select(func.count(func.distinct(Participant.email)))).scalar_one() or 0
    )

    tag_rows = db.execute(
        select(Tag.name, Tag.color, func.count(Meeting.id))
        .join(Tag.meetings)
        .group_by(Tag.id)
        .order_by(func.count(Meeting.id).desc())
        .limit(6)
    ).all()

    return AnalyticsOverview(
        total_meetings=total_meetings,
        meetings_this_week=meetings_this_week,
        total_duration_seconds=total_duration,
        open_action_items=open_items,
        completed_action_items=total_items - open_items,
        unique_participants=unique_participants,
        top_tags=[TagCount(name=row[0], color=row[1], count=row[2]) for row in tag_rows],
    )
