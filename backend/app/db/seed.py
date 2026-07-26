"""Load the demo workspace.

The seed data is stored as plain transcripts plus a small JSON manifest, not as
pre-baked database rows. Loading them runs the *same* pipeline an uploaded file
goes through — parse, tag, derive speakers, summarise, extract tasks. So the
seed is also a continuous test of the ingestion path: if the demo meetings look
right, upload works.

Dates are relative to now, so the library always looks like a live workspace
rather than a snapshot from whenever the repository was cloned.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.meeting import Meeting
from app.models.user import User
from app.services import meeting_service
from app.services.transcript_parser import parse_transcript

logger = logging.getLogger(__name__)

SEEDS_DIR = Path(__file__).parent / "seeds"
MANIFEST_PATH = SEEDS_DIR / "manifest.json"


def _load_manifest() -> dict:
    with MANIFEST_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def get_or_create_owner(db: Session, profile: dict) -> User:
    """The single logged-in user. Real auth is out of scope for this assignment."""
    user = db.execute(select(User).where(User.email == profile["email"])).scalar_one_or_none()
    if user:
        return user
    user = User(
        name=profile["name"],
        email=profile["email"],
        job_title=profile.get("job_title"),
        timezone=profile.get("timezone", "Asia/Kolkata"),
        avatar_url=profile.get("avatar_url"),
    )
    db.add(user)
    db.flush()
    return user


def ensure_owner(db: Session) -> User:
    """Guarantee the workspace has its user, independently of the demo data.

    These are two different concerns and conflating them is a real bug: with
    seeding switched off, a fresh container would come up with no user at all
    and every write endpoint would 503. A workspace always has an owner; the
    demo meetings are optional content on top of it.
    """
    user = get_or_create_owner(db, _load_manifest()["owner"])
    db.commit()
    return user


def _workspace_zone(name: str) -> ZoneInfo | timezone:
    """Resolve the workspace timezone, falling back to UTC if unavailable.

    Windows ships no system tz database, so `tzdata` is a dependency. Guarding
    the lookup means a missing database degrades the seed times rather than
    stopping the app from starting.
    """
    try:
        return ZoneInfo(name)
    except Exception:
        logger.warning("Timezone %s unavailable, seeding in UTC", name)
        return UTC


def _meeting_date(entry: dict, reference: datetime, zone: ZoneInfo | timezone) -> datetime:
    """Build the meeting time as wall-clock in the workspace timezone, then
    convert to UTC for storage.

    The manifest says "10:00" meaning ten in the morning where this workspace
    is, not ten UTC. Storing the manifest hour directly as UTC is what puts a
    seeded investor update at 23:00 for anyone east of Greenwich.
    """
    local_day = reference.astimezone(zone) - timedelta(days=int(entry.get("days_ago", 0)))
    local = local_day.replace(
        hour=int(entry.get("start_hour", 10)),
        minute=int(entry.get("start_minute", 0)),
        second=0,
        microsecond=0,
    )
    return local.astimezone(UTC)


def seed(db: Session) -> int:
    """Create every meeting in the manifest. Returns how many were created."""
    manifest = _load_manifest()
    owner = get_or_create_owner(db, manifest["owner"])
    reference = datetime.now(UTC)
    zone = _workspace_zone(owner.timezone)

    created = 0
    for entry in manifest["meetings"]:
        transcript_path = SEEDS_DIR / entry["file"]
        if not transcript_path.exists():
            logger.warning("Seed transcript missing, skipping: %s", transcript_path.name)
            continue

        content = transcript_path.read_text(encoding="utf-8")
        parsed = parse_transcript(
            content,
            filename=entry["file"],
            words_per_minute=int(entry.get("words_per_minute", 150)),
        )

        meeting_service.build_meeting(
            db,
            owner=owner,
            title=entry["title"],
            date=_meeting_date(entry, reference, zone),
            parsed=parsed,
            participants=entry.get("participants"),
            tags=entry.get("tags"),
            meeting_type=entry.get("meeting_type"),
            meeting_link=entry.get("meeting_link"),
            calendar_type=entry.get("calendar_type", "manual"),
        )
        created += 1

    db.commit()
    logger.info("Seeded %s meetings", created)
    return created


def seed_if_empty(db: Session) -> int:
    """Idempotent entry point used at startup.

    Render's free tier has no persistent disk, so the container starts with an
    empty database after every deploy or cold start. Seeding on an empty
    database means the demo is always populated without ever duplicating data
    on a warm restart.
    """
    existing = db.execute(select(func.count()).select_from(Meeting)).scalar_one()
    if existing:
        logger.info("Database already has %s meetings, skipping seed", existing)
        return 0
    return seed(db)
