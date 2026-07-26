"""Cross-meeting search, backed by the FTS5 index with a LIKE fallback.

Results are grouped by meeting rather than returned as a flat list of
sentences, because that is how the answer is actually useful: "three of your
meetings mention pricing, here is the strongest line from each".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.db import fts
from app.models.meeting import Meeting
from app.models.transcript import Sentence

# How many raw sentence hits to pull before grouping. Generous enough that a
# meeting far down the ranking still surfaces, small enough to stay fast.
_HIT_LIMIT = 200
_SNIPPETS_PER_MEETING = 3


@dataclass
class SentenceHit:
    sentence_id: int
    meeting_id: int
    idx: int
    start_ms: int
    speaker_name: str | None
    snippet: str


@dataclass
class MeetingGroup:
    meeting: Meeting
    match_count: int
    hits: list[SentenceHit] = field(default_factory=list)


_FTS_SQL = text(
    """
    SELECT s.id           AS sentence_id,
           s.meeting_id   AS meeting_id,
           s.idx          AS idx,
           s.start_ms     AS start_ms,
           sp.name        AS speaker_name,
           snippet(sentences_fts, 0, '<mark>', '</mark>', '…', 18) AS snippet,
           bm25(sentences_fts) AS rank
    FROM sentences_fts
    JOIN sentences s  ON s.id = sentences_fts.rowid
    LEFT JOIN speakers sp ON sp.id = s.speaker_id
    WHERE sentences_fts MATCH :match
    ORDER BY rank
    LIMIT :limit
    """
)


def _fts_hits(db: Session, query: str) -> list[SentenceHit]:
    match = fts.to_match_expression(query)
    if not match:
        return []
    rows = db.execute(_FTS_SQL, {"match": match, "limit": _HIT_LIMIT}).mappings().all()
    return [
        SentenceHit(
            sentence_id=row["sentence_id"],
            meeting_id=row["meeting_id"],
            idx=row["idx"],
            start_ms=row["start_ms"],
            speaker_name=row["speaker_name"],
            snippet=row["snippet"],
        )
        for row in rows
    ]


def _like_hits(db: Session, query: str) -> list[SentenceHit]:
    """Fallback when FTS5 is unavailable. Same shape, worse ranking."""
    pattern = f"%{query.strip()}%"
    rows = (
        db.execute(
            select(Sentence).where(Sentence.text.ilike(pattern)).limit(_HIT_LIMIT)
        )
        .scalars()
        .all()
    )
    hits = []
    for sentence in rows:
        # Mark the match by hand so the frontend renders both paths identically.
        lowered = sentence.text.lower()
        position = lowered.find(query.strip().lower())
        if position < 0:
            snippet = sentence.text[:160]
        else:
            start = max(0, position - 60)
            end = min(len(sentence.text), position + len(query) + 60)
            body = sentence.text[start:end]
            marked = body.replace(
                sentence.text[position : position + len(query)],
                f"<mark>{sentence.text[position : position + len(query)]}</mark>",
                1,
            )
            snippet = ("…" if start > 0 else "") + marked + ("…" if end < len(sentence.text) else "")
        hits.append(
            SentenceHit(
                sentence_id=sentence.id,
                meeting_id=sentence.meeting_id,
                idx=sentence.idx,
                start_ms=sentence.start_ms,
                speaker_name=sentence.speaker.name if sentence.speaker else None,
                snippet=snippet,
            )
        )
    return hits


def search(db: Session, query: str, limit: int = 20) -> list[MeetingGroup]:
    """Search transcripts and meeting titles, grouped by meeting.

    Ordering preserves the ranking of each meeting's best sentence hit, so the
    most relevant conversation comes first. Meetings matched only by title are
    appended after the transcript matches.
    """
    if not query or not query.strip():
        return []

    hits = _fts_hits(db, query) if fts.fts_available() else _like_hits(db, query)

    grouped: dict[int, MeetingGroup] = {}
    order: list[int] = []
    for hit in hits:
        group = grouped.get(hit.meeting_id)
        if group is None:
            group = MeetingGroup(meeting=None, match_count=0)  # type: ignore[arg-type]
            grouped[hit.meeting_id] = group
            order.append(hit.meeting_id)
        group.match_count += 1
        if len(group.hits) < _SNIPPETS_PER_MEETING:
            group.hits.append(hit)

    # Meetings whose *title* matches but whose transcript does not.
    title_matches = (
        db.execute(
            select(Meeting)
            .where(
                or_(
                    Meeting.title.ilike(f"%{query.strip()}%"),
                    Meeting.meeting_type.ilike(f"%{query.strip()}%"),
                )
            )
            .limit(limit)
        )
        .scalars()
        .all()
    )
    for meeting in title_matches:
        if meeting.id not in grouped:
            grouped[meeting.id] = MeetingGroup(meeting=meeting, match_count=0)
            order.append(meeting.id)

    # One query for every meeting we are about to return, rather than one each.
    ids = order[:limit]
    if not ids:
        return []
    meetings = {
        meeting.id: meeting
        for meeting in db.execute(select(Meeting).where(Meeting.id.in_(ids))).scalars().all()
    }

    results: list[MeetingGroup] = []
    for meeting_id in ids:
        meeting = meetings.get(meeting_id)
        if meeting is None:
            continue
        group = grouped[meeting_id]
        group.meeting = meeting
        results.append(group)
    return results


def count_matching_sentences(db: Session, meeting_id: int, query: str) -> int:
    """Total transcript hits inside one meeting (drives the 'N results' label)."""
    if not query.strip():
        return 0
    return (
        db.execute(
            select(func.count())
            .select_from(Sentence)
            .where(Sentence.meeting_id == meeting_id, Sentence.text.ilike(f"%{query.strip()}%"))
        ).scalar_one()
        or 0
    )
