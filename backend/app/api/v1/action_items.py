"""Action items: list and create under a meeting, update and delete by id."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_meeting
from app.core.db import get_db
from app.models.action_item import (
    SOURCE_MANUAL,
    STATUS_COMPLETED,
    ActionItem,
)
from app.models.meeting import Meeting, Participant
from app.schemas.action_item import ActionItemCreate, ActionItemOut, ActionItemUpdate

router = APIRouter(tags=["action-items"])


def _validate_assignee(db: Session, meeting_id: int, participant_id: int | None) -> None:
    """An assignee has to actually be in the meeting."""
    if participant_id is None:
        return
    participant = db.get(Participant, participant_id)
    if participant is None or participant.meeting_id != meeting_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Participant {participant_id} is not part of this meeting.",
        )


@router.get("/meetings/{meeting_id}/action-items", response_model=list[ActionItemOut])
def list_action_items(meeting: Meeting = Depends(get_meeting)) -> list[ActionItemOut]:
    return [ActionItemOut.model_validate(item) for item in meeting.action_items]


@router.post(
    "/meetings/{meeting_id}/action-items",
    response_model=ActionItemOut,
    status_code=status.HTTP_201_CREATED,
)
def create_action_item(
    payload: ActionItemCreate,
    meeting: Meeting = Depends(get_meeting),
    db: Session = Depends(get_db),
) -> ActionItemOut:
    _validate_assignee(db, meeting.id, payload.assignee_participant_id)

    next_order = (
        db.execute(
            select(func.coalesce(func.max(ActionItem.order_index), -1)).where(
                ActionItem.meeting_id == meeting.id
            )
        ).scalar_one()
        + 1
    )

    item = ActionItem(
        meeting_id=meeting.id,
        text=payload.text.strip(),
        assignee_participant_id=payload.assignee_participant_id,
        due_date=payload.due_date,
        # Hand-authored, so regenerating the summary will not delete it.
        source=SOURCE_MANUAL,
        order_index=next_order,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return ActionItemOut.model_validate(item)


@router.patch("/action-items/{action_item_id}", response_model=ActionItemOut)
def update_action_item(
    action_item_id: int, payload: ActionItemUpdate, db: Session = Depends(get_db)
) -> ActionItemOut:
    item = db.get(ActionItem, action_item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item {action_item_id} not found.",
        )

    data = payload.model_dump(exclude_unset=True)

    if "assignee_participant_id" in data:
        _validate_assignee(db, item.meeting_id, data["assignee_participant_id"])
        item.assignee_participant_id = data["assignee_participant_id"]

    if "status" in data and data["status"] is not None:
        item.status = data["status"]
        # completed_at is derived from status, never set by the client — that
        # way the two can't contradict each other.
        item.completed_at = datetime.now(UTC) if data["status"] == STATUS_COMPLETED else None

    for field in ("text", "due_date", "order_index"):
        if field in data and data[field] is not None:
            setattr(item, field, data[field].strip() if field == "text" else data[field])

    db.commit()
    db.refresh(item)
    return ActionItemOut.model_validate(item)


@router.delete("/action-items/{action_item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_action_item(action_item_id: int, db: Session = Depends(get_db)) -> None:
    item = db.get(ActionItem, action_item_id)
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item {action_item_id} not found.",
        )
    db.delete(item)
    db.commit()
