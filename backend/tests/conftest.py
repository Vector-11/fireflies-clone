"""Test fixtures.

The environment is configured *before* any application module is imported,
because ``app.core.config`` builds its Settings at import time and
``app.core.db`` builds the engine from it. Setting these afterwards would have
no effect and the tests would quietly run against the development database.
"""

import os
import tempfile

_TEST_DB_DIR = tempfile.mkdtemp(prefix="fireflies-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_DIR}/test.db".replace("\\", "/")
os.environ["SEED_ON_STARTUP"] = "false"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402
from app.db import fts  # noqa: E402
from app.db.seed import seed  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402


@pytest.fixture
def client():
    """A client against a database that is empty at the start of every test."""
    # The FTS table has to go first — it is not in SQLAlchemy's metadata, and
    # leaving it behind means recycled rowids collide with stale index rows.
    fts.drop_fts(engine)
    Base.metadata.drop_all(engine)
    with TestClient(app) as test_client:  # lifespan creates tables and the FTS index
        yield test_client


@pytest.fixture
def seeded_client(client):
    """A client with the demo workspace loaded."""
    with SessionLocal() as db:
        seed(db)
    return client


@pytest.fixture
def db_session():
    with SessionLocal() as session:
        yield session
