"""Assemble a complete meeting from a parsed transcript.

This is the one place that knows how the pieces fit together: sentences get
insight flags, unique voices become speakers, the summariser produces the
summary, chapters and tasks, and everything is wired up with the right foreign
keys. Both transcript upload and database seeding go through it, so a seeded
meeting and an uploaded one are built by identical code — if the seed data looks
right, uploads work too.
"""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.action_item import SOURCE_EXTRACTED, ActionItem
from app.models.meeting import Meeting, Participant, Speaker, Tag
from app.models.summary import Summary
from app.models.transcript import Chapter, Sentence
from app.models.user import User
from app.services import insight_tagger
from app.services.summarizer import SentenceInput, get_summarizer
from app.services.transcript_parser import ParsedSentence

# Must match the avatar palette length in the frontend.
SPEAKER_PALETTE_SIZE = 8
TAG_COLORS = ("purple", "teal", "blue", "yellow", "green", "fuchsia", "orange")

_NON_WORD_RE = re.compile(r"[^a-z0-9]+")


def _slug(value: str) -> str:
    return _NON_WORD_RE.sub(".", value.strip().lower()).strip(".")


def _placeholder_email(name: str) -> str:
    """Speakers found only in a transcript still need an identity to show in
    the participants list. Marked as a non-Fireflies user so the UI can be
    honest that this person was inferred, not invited."""
    return f"{_slug(name) or 'speaker'}@example.com"


def get_or_create_tag(db: Session, name: str) -> Tag:
    normalised = name.strip()
    existing = db.execute(select(Tag).where(Tag.name == normalised)).scalar_one_or_none()
    if existing:
        return existing
    # Deterministic colour so a tag looks the same everywhere it appears.
    color = TAG_COLORS[sum(map(ord, normalised.lower())) % len(TAG_COLORS)]
    tag = Tag(name=normalised, color=color)
    db.add(tag)
    db.flush()
    return tag


def build_meeting(
    db: Session,
    *,
    owner: User,
    title: str,
    date: datetime,
    parsed: list[ParsedSentence],
    participants: list[dict] | None = None,
    tags: list[str] | None = None,
    meeting_type: str | None = None,
    meeting_link: str | None = None,
    calendar_type: str | None = "manual",
    audio_url: str | None = None,
    duration_seconds: int | None = None,
) -> Meeting:
    """Create and persist a meeting with its transcript, summary and tasks."""
    last_end_ms = parsed[-1].end_ms if parsed else 0
    meeting = Meeting(
        owner_id=owner.id,
        title=title.strip(),
        date=date,
        duration_seconds=duration_seconds
        if duration_seconds is not None
        else round((last_end_ms or 0) / 1000),
        organizer_email=owner.email,
        meeting_link=meeting_link,
        calendar_type=calendar_type,
        meeting_type=meeting_type,
        audio_url=audio_url,
    )
    db.add(meeting)
    db.flush()  # need meeting.id for every child row below

    speakers = _create_speakers(db, meeting, parsed)
    _create_participants(db, meeting, participants, speakers)
    sentences = _create_sentences(db, meeting, parsed, speakers)

    for name in tags or []:
        if name.strip():
            meeting.tags.append(get_or_create_tag(db, name))

    generate_summary(db, meeting, sentences)

    db.flush()
    return meeting


def _create_speakers(
    db: Session, meeting: Meeting, parsed: list[ParsedSentence]
) -> dict[str, Speaker]:
    """One speaker per distinct name, numbered by first appearance so the
    colour assignment is stable across re-imports of the same transcript."""
    speakers: dict[str, Speaker] = {}
    for sentence in parsed:
        name = (sentence.speaker_name or "").strip()
        if not name or name in speakers:
            continue
        index = len(speakers)
        speaker = Speaker(
            meeting_id=meeting.id,
            speaker_index=index,
            name=name,
            color_key=index % SPEAKER_PALETTE_SIZE,
        )
        db.add(speaker)
        speakers[name] = speaker

    db.flush()
    return speakers


def _create_participants(
    db: Session,
    meeting: Meeting,
    supplied: list[dict] | None,
    speakers: dict[str, Speaker],
) -> None:
    # Seeded from whoever is already on the meeting so re-importing a
    # transcript tops the list up instead of colliding with the unique
    # (meeting_id, email) constraint.
    seen_emails: set[str] = {
        participant.email.strip().lower() for participant in meeting.participants
    }
    # Names are tracked separately because the two sources identify people
    # differently: an invite carries an email, a transcript carries only a
    # display name. Matching on email alone would add "Sofia Reyes" a second
    # time under a synthesised address and show her twice in the UI.
    seen_names: set[str] = {
        (participant.name or "").strip().lower()
        for participant in meeting.participants
        if participant.name
    }

    for entry in supplied or []:
        email = (entry.get("email") or "").strip().lower()
        if not email or email in seen_emails:
            continue
        name = entry.get("name") or email.split("@")[0].replace(".", " ").title()
        seen_emails.add(email)
        seen_names.add(name.strip().lower())
        db.add(
            Participant(
                meeting_id=meeting.id,
                email=email,
                name=name,
                is_fireflies_user=bool(entry.get("is_fireflies_user", False)),
            )
        )

    # Anyone who spoke but was not on the invite list still belongs in the room.
    for name in speakers:
        if name.strip().lower() in seen_names:
            continue
        email = _placeholder_email(name)
        if email in seen_emails:
            continue
        seen_emails.add(email)
        seen_names.add(name.strip().lower())
        db.add(
            Participant(meeting_id=meeting.id, email=email, name=name, is_fireflies_user=False)
        )

    db.flush()


def _create_sentences(
    db: Session,
    meeting: Meeting,
    parsed: list[ParsedSentence],
    speakers: dict[str, Speaker],
) -> list[Sentence]:
    sentences: list[Sentence] = []
    for idx, item in enumerate(parsed):
        speaker = speakers.get((item.speaker_name or "").strip())
        sentence = Sentence(
            meeting_id=meeting.id,
            speaker_id=speaker.id if speaker else None,
            idx=idx,
            text=item.text.strip(),
            start_ms=item.start_ms or 0,
            end_ms=item.end_ms or (item.start_ms or 0),
            # One call populates all four filter flags plus sentiment.
            **insight_tagger.tag(item.text),
        )
        db.add(sentence)
        sentences.append(sentence)

    db.flush()
    return sentences


def sync_participants(db: Session, meeting: Meeting, payloads: list[dict]) -> None:
    """Reconcile the participant list against what the client sent.

    Matched on email rather than rebuilt from scratch, so a participant who is
    still on the list keeps their row — and therefore keeps any action items
    assigned to them. Deleting and re-adding would silently orphan every
    assignment, because the FK is ON DELETE SET NULL.
    """
    desired: dict[str, dict] = {}
    for payload in payloads:
        email = (payload.get("email") or "").strip().lower()
        if email:
            desired[email] = payload

    for existing in list(meeting.participants):
        key = existing.email.strip().lower()
        entry = desired.pop(key, None)
        if entry is None:
            db.delete(existing)
            continue
        if entry.get("name"):
            existing.name = entry["name"]
        if "is_fireflies_user" in entry:
            existing.is_fireflies_user = bool(entry["is_fireflies_user"])

    for email, entry in desired.items():
        db.add(
            Participant(
                meeting_id=meeting.id,
                email=email,
                name=entry.get("name") or email.split("@")[0].replace(".", " ").title(),
                is_fireflies_user=bool(entry.get("is_fireflies_user", False)),
            )
        )

    db.flush()


def sync_tags(db: Session, meeting: Meeting, names: list[str]) -> None:
    """Replace the tag set. Order-preserving and de-duplicated."""
    unique = list(dict.fromkeys(name.strip() for name in names if name and name.strip()))
    meeting.tags = [get_or_create_tag(db, name) for name in unique]
    db.flush()


def replace_transcript(db: Session, meeting: Meeting, parsed: list[ParsedSentence]) -> Meeting:
    """Swap in a new transcript and rebuild everything derived from it.

    Sentences and speakers go, then are rebuilt; the summary, chapters and
    extracted tasks are regenerated. Manual action items survive, though any
    that pointed at a deleted sentence lose that link rather than disappearing.
    """
    for sentence in list(meeting.sentences):
        db.delete(sentence)
    for speaker in list(meeting.speakers):
        db.delete(speaker)
    db.flush()
    db.refresh(meeting)

    speakers = _create_speakers(db, meeting, parsed)
    _create_participants(db, meeting, None, speakers)
    sentences = _create_sentences(db, meeting, parsed, speakers)

    meeting.duration_seconds = round((parsed[-1].end_ms or 0) / 1000) if parsed else 0
    db.flush()
    db.refresh(meeting)

    generate_summary(db, meeting, sentences)
    return meeting


def generate_summary(
    db: Session, meeting: Meeting, sentences: list[Sentence] | None = None
) -> Summary:
    """Run the summariser and persist the summary, chapters and extracted tasks.

    Safe to call repeatedly: it replaces the previous summary, all chapters, and
    only the *extracted* action items. Anything the user typed by hand survives,
    which is the whole reason ``ActionItem.source`` exists.
    """
    if sentences is None:
        sentences = list(
            db.execute(
                select(Sentence).where(Sentence.meeting_id == meeting.id).order_by(Sentence.idx)
            )
            .scalars()
            .all()
        )

    speaker_names = {
        speaker.id: speaker.name
        for speaker in db.execute(
            select(Speaker).where(Speaker.meeting_id == meeting.id)
        ).scalars()
    }

    draft = get_summarizer().summarize(
        [
            SentenceInput(
                idx=sentence.idx,
                text=sentence.text,
                start_ms=sentence.start_ms,
                end_ms=sentence.end_ms,
                speaker_name=speaker_names.get(sentence.speaker_id),
            )
            for sentence in sentences
        ]
    )

    # Replace the generated artefacts, leave manual ones untouched.
    for existing in list(meeting.chapters):
        db.delete(existing)
    for existing in list(meeting.action_items):
        if existing.source == SOURCE_EXTRACTED:
            db.delete(existing)
    if meeting.summary is not None:
        db.delete(meeting.summary)
    db.flush()

    summary = Summary(
        meeting_id=meeting.id,
        gist=draft.gist,
        short_summary=draft.short_summary,
        overview=draft.overview,
        bullet_gist=draft.bullet_gist,
        shorthand_bullet=draft.shorthand_bullet,
        notes=draft.notes,
        keywords=draft.keywords,
        topics_discussed=draft.topics_discussed,
        generated_by=draft.generated_by,
        model=draft.model,
    )
    db.add(summary)

    for chapter in draft.chapters:
        db.add(
            Chapter(
                meeting_id=meeting.id,
                idx=chapter.idx,
                title=chapter.title,
                gist=chapter.gist,
                start_ms=chapter.start_ms,
                end_ms=chapter.end_ms,
            )
        )

    sentence_by_idx = {sentence.idx: sentence for sentence in sentences}
    participants_by_name = {
        (participant.name or "").strip().lower(): participant
        for participant in meeting.participants
    }
    # Manual tasks keep their positions; extracted ones are appended after.
    next_order = max(
        (item.order_index for item in meeting.action_items if item.source != SOURCE_EXTRACTED),
        default=-1,
    )

    for offset, item in enumerate(draft.action_items, start=1):
        sentence = sentence_by_idx.get(item.sentence_idx) if item.sentence_idx is not None else None
        assignee = participants_by_name.get((item.speaker_name or "").strip().lower())
        db.add(
            ActionItem(
                meeting_id=meeting.id,
                sentence_id=sentence.id if sentence else None,
                assignee_participant_id=assignee.id if assignee else None,
                text=item.text,
                source=SOURCE_EXTRACTED,
                order_index=next_order + offset,
            )
        )

    db.flush()
    db.refresh(meeting)
    return summary
