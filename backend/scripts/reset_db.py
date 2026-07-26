"""Drop, recreate and reseed the database.

    python -m scripts.reset_db

Useful during development and after changing a model, since this project has no
migration tool — the schema is small and recreating it is faster than
maintaining migrations for an assignment. Adding Alembic later is a drop-in.
"""

from __future__ import annotations

import logging
import sys

from app.core.db import SessionLocal, engine
from app.db import fts
from app.db.seed import seed
from app.models import Base

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("reset_db")


def main() -> int:
    log.info("Dropping all tables")
    # The FTS virtual table is not part of SQLAlchemy's metadata, so it has to
    # be dropped explicitly and before the table it shadows.
    fts.drop_fts(engine)
    Base.metadata.drop_all(engine)

    log.info("Creating tables")
    Base.metadata.create_all(engine)
    fts.init_fts(engine)

    with SessionLocal() as db:
        count = seed(db)
    fts.rebuild_index(engine)

    log.info("Done — seeded %s meetings", count)
    return 0


if __name__ == "__main__":
    sys.exit(main())
