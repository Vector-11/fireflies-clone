"""FastAPI application factory.

Startup does three things in order: create the tables, build the full-text
index, and seed the demo workspace if the database is empty. That sequence
matters — the FTS triggers have to exist before any sentence is inserted, or the
index starts life out of step with the table.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.v1 import api_router
from app.core.config import settings
from app.core.db import SessionLocal, engine
from app.db import fts
from app.db.seed import ensure_owner, seed_if_empty
from app.models import Base
from app.services.transcript_parser import TranscriptParseError

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    fts.init_fts(engine)

    # The workspace user always exists; the demo meetings are optional.
    with SessionLocal() as db:
        ensure_owner(db)

    if settings.seed_on_startup:
        with SessionLocal() as db:
            if seed_if_empty(db):
                # Belt and braces: the triggers already indexed every insert,
                # but a rebuild after a bulk load costs milliseconds and removes
                # any doubt about the two being in step.
                fts.rebuild_index(engine)

    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "Backend for a Fireflies.ai-style meeting notes and transcription "
            "workspace. Transcripts are seeded or uploaded; summaries, chapters "
            "and action items are generated from them deterministically."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.exception_handler(TranscriptParseError)
    async def _handle_parse_error(request: Request, exc: TranscriptParseError) -> JSONResponse:
        """A transcript we cannot read is the user's problem to fix, not a bug.

        Mapping it here means no route has to remember to catch it.
        """
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc), "code": "transcript_parse_error"},
        )

    @app.exception_handler(IntegrityError)
    async def _handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        logger.warning("Integrity error on %s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": "That change conflicts with existing data.",
                "code": "conflict",
            },
        )

    @app.get("/health", tags=["health"])
    def health() -> dict[str, object]:
        """Liveness probe, and a quick way to confirm FTS5 is actually active."""
        return {"status": "ok", "fts5": fts.fts_available()}

    return app


app = create_app()
