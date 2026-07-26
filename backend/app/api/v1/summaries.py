"""Meeting summary: read it, or regenerate it from the transcript."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_meeting
from app.core.db import get_db
from app.models.meeting import Meeting
from app.schemas.summary import SummaryOut
from app.services import meeting_service

router = APIRouter(prefix="/meetings/{meeting_id}", tags=["summary"])


@router.get("/summary", response_model=SummaryOut)
def read_summary(meeting: Meeting = Depends(get_meeting)) -> SummaryOut:
    if meeting.summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="This meeting has no summary yet. Upload a transcript first.",
        )
    return SummaryOut.model_validate(meeting.summary)


@router.post("/summary/regenerate", response_model=SummaryOut)
def regenerate_summary(
    meeting: Meeting = Depends(get_meeting), db: Session = Depends(get_db)
) -> SummaryOut:
    """Re-run the summariser over the current transcript.

    Replaces the summary, the chapters, and the *extracted* action items.
    Anything the user added by hand is left alone.
    """
    if not meeting.sentences:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="There is no transcript to summarise.",
        )

    summary = meeting_service.generate_summary(db, meeting)
    db.commit()
    db.refresh(summary)
    return SummaryOut.model_validate(summary)
