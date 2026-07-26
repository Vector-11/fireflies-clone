"""The transcript itself: read it, filter it, correct a line."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_meeting
from app.core.db import get_db
from app.models.meeting import Meeting
from app.models.transcript import Sentence
from app.schemas.transcript import SentenceOut, SentenceUpdate, TranscriptOut

router = APIRouter(tags=["transcript"])

InsightFilter = Literal["task", "question", "metric", "datetime"]

# The filter pills above the transcript map onto the boolean columns that
# insight_tagger populated at ingestion.
_FILTER_COLUMNS = {
    "task": Sentence.is_task,
    "question": Sentence.is_question,
    "metric": Sentence.is_metric,
    "datetime": Sentence.is_date_time,
}


@router.get("/meetings/{meeting_id}/transcript", response_model=TranscriptOut)
def read_transcript(
    q: str | None = Query(None, description="Only return sentences containing this text"),
    insight: InsightFilter | None = Query(None, description="task | question | metric | datetime"),
    speaker_id: int | None = Query(None),
    meeting: Meeting = Depends(get_meeting),
    db: Session = Depends(get_db),
) -> TranscriptOut:
    """Return the transcript, optionally filtered.

    The client also highlights matches locally as you type — that is instant and
    needs no round trip. This endpoint exists for the case where you want the
    transcript *narrowed* rather than highlighted, and for the filter pills.
    """
    stmt = select(Sentence).where(Sentence.meeting_id == meeting.id)

    if q and q.strip():
        stmt = stmt.where(Sentence.text.ilike(f"%{q.strip()}%"))
    if insight:
        stmt = stmt.where(_FILTER_COLUMNS[insight].is_(True))
    if speaker_id is not None:
        stmt = stmt.where(Sentence.speaker_id == speaker_id)

    sentences = list(db.execute(stmt.order_by(Sentence.idx)).scalars().all())
    return TranscriptOut(
        meeting_id=meeting.id,
        total=len(sentences),
        sentences=[SentenceOut.model_validate(sentence) for sentence in sentences],
    )


@router.patch("/meetings/{meeting_id}/sentences/{sentence_id}", response_model=SentenceOut)
def update_sentence(
    sentence_id: int,
    payload: SentenceUpdate,
    meeting: Meeting = Depends(get_meeting),
    db: Session = Depends(get_db),
) -> SentenceOut:
    """Correct a mis-transcribed line.

    Fireflies distinguishes the original ``raw_text`` from user-edited ``text``.
    This keeps one column and lets the edit stand — but the update *does* flow
    through to the search index automatically, because the FTS5 triggers fire on
    UPDATE as well as INSERT.
    """
    sentence = db.get(Sentence, sentence_id)
    if sentence is None or sentence.meeting_id != meeting.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sentence {sentence_id} is not part of meeting {meeting.id}.",
        )

    text = payload.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A transcript line cannot be empty.",
        )

    sentence.text = text
    db.commit()
    db.refresh(sentence)
    return SentenceOut.model_validate(sentence)
