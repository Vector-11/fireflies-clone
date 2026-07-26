"""Global search across every transcript."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.db import fts
from app.schemas.search import SearchHitOut, SearchResponse, SearchResultOut
from app.services import search_service

router = APIRouter(tags=["search"])


@router.get("/search", response_model=SearchResponse)
def global_search(
    q: str = Query(..., min_length=1, description="Free text; matched against transcripts and titles"),
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
) -> SearchResponse:
    """Search transcripts and meeting titles, grouped by meeting.

    ``ranked`` tells the client whether it is looking at bm25-ordered results
    from the FTS5 index or the unranked LIKE fallback, so the UI can be honest
    about result quality instead of pretending they are the same thing.
    """
    groups = search_service.search(db, q, limit=limit)

    return SearchResponse(
        query=q,
        total_meetings=len(groups),
        ranked=fts.fts_available(),
        results=[
            SearchResultOut(
                meeting_id=group.meeting.id,
                title=group.meeting.title,
                date=group.meeting.date,
                duration_seconds=group.meeting.duration_seconds,
                meeting_type=group.meeting.meeting_type,
                match_count=group.match_count,
                hits=[
                    SearchHitOut(
                        sentence_id=hit.sentence_id,
                        idx=hit.idx,
                        start_ms=hit.start_ms,
                        speaker_name=hit.speaker_name,
                        snippet=hit.snippet,
                    )
                    for hit in group.hits
                ],
            )
            for group in groups
        ],
    )
