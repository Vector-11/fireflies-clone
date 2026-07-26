"""Shared route dependencies."""

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.meeting import Meeting
from app.models.user import User


def get_current_user(db: Session = Depends(get_db)) -> User:
    """The logged-in user.

    Real authentication is explicitly out of scope for this assignment, so the
    app runs as the single seeded user. Every route that needs an identity takes
    it through this dependency rather than reaching for the database directly —
    swapping in a real session or JWT later means editing this function and
    nothing else.
    """
    user = db.execute(select(User).order_by(User.id).limit(1)).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No user has been seeded yet. Run `python -m scripts.reset_db`.",
        )
    return user


def get_meeting(
    meeting_id: int = Path(..., ge=1), db: Session = Depends(get_db)
) -> Meeting:
    """Load a meeting or 404. Saves repeating the same four lines everywhere."""
    meeting = db.get(Meeting, meeting_id)
    if meeting is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Meeting {meeting_id} not found."
        )
    return meeting
