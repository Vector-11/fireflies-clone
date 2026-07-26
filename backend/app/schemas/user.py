"""The current user."""

from app.schemas.common import ORMModel


class UserOut(ORMModel):
    id: int
    name: str
    email: str
    job_title: str | None = None
    avatar_url: str | None = None
    timezone: str
