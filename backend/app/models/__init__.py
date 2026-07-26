"""Every model is imported here so that ``Base.metadata`` is complete.

SQLAlchemy only knows about a table once its class has been imported. Without
this module, ``create_all`` would quietly create whichever subset happened to be
imported first — so all models are collected in one place and imported once at
startup.
"""

from app.models.action_item import ActionItem
from app.models.base import Base
from app.models.meeting import Meeting, Participant, Speaker, Tag, meeting_tags
from app.models.summary import Summary
from app.models.transcript import Chapter, Sentence
from app.models.user import User

__all__ = [
    "ActionItem",
    "Base",
    "Chapter",
    "Meeting",
    "Participant",
    "Sentence",
    "Speaker",
    "Summary",
    "Tag",
    "User",
    "meeting_tags",
]
