"""Full-text search over transcript sentences, using SQLite's FTS5 extension.

Why not ``LIKE '%term%'``? Because it cannot use an index, so it degrades
linearly with transcript volume, it cannot rank results by relevance, and it
cannot tell you *where* in a sentence the match was. FTS5 gives all three for
free: an inverted index, ``bm25()`` relevance ranking, and ``snippet()`` which
returns the matching fragment with the hit already wrapped in a marker.

The index is declared as an **external content** table (``content='sentences'``)
so the sentence text is stored exactly once. The FTS table holds only the
inverted index and reads the original rows from ``sentences`` by rowid. That
does mean SQLite will not keep the two in sync by itself, which is what the
three triggers below are for.

FTS5 is compiled into effectively every modern SQLite build, but not
*guaranteed* to be, so availability is probed once at startup and the search
service falls back to LIKE if it is missing. The demo degrades; it never breaks.
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

FTS_TABLE = "sentences_fts"

_CREATE_STATEMENTS: tuple[str, ...] = (
    f"""
    CREATE VIRTUAL TABLE IF NOT EXISTS {FTS_TABLE} USING fts5(
        text,
        content='sentences',
        content_rowid='id',
        tokenize='porter unicode61'
    );
    """,
    # Keep the index in step with the table it shadows.
    f"""
    CREATE TRIGGER IF NOT EXISTS sentences_fts_ai AFTER INSERT ON sentences BEGIN
        INSERT INTO {FTS_TABLE}(rowid, text) VALUES (new.id, new.text);
    END;
    """,
    f"""
    CREATE TRIGGER IF NOT EXISTS sentences_fts_ad AFTER DELETE ON sentences BEGIN
        INSERT INTO {FTS_TABLE}({FTS_TABLE}, rowid, text) VALUES('delete', old.id, old.text);
    END;
    """,
    f"""
    CREATE TRIGGER IF NOT EXISTS sentences_fts_au AFTER UPDATE ON sentences BEGIN
        INSERT INTO {FTS_TABLE}({FTS_TABLE}, rowid, text) VALUES('delete', old.id, old.text);
        INSERT INTO {FTS_TABLE}(rowid, text) VALUES (new.id, new.text);
    END;
    """,
)

# Set once at startup by init_fts().
_fts_available = False


def fts_available() -> bool:
    return _fts_available


def init_fts(engine: Engine) -> bool:
    """Create the virtual table and its triggers. Returns whether FTS5 works."""
    global _fts_available

    if engine.dialect.name != "sqlite":
        _fts_available = False
        return False

    try:
        with engine.begin() as connection:
            for statement in _CREATE_STATEMENTS:
                connection.execute(text(statement))
        _fts_available = True
        logger.info("FTS5 index ready on %s", FTS_TABLE)
    except Exception:
        _fts_available = False
        logger.warning("FTS5 unavailable; search will fall back to LIKE", exc_info=True)

    return _fts_available


_TRIGGERS = ("sentences_fts_ai", "sentences_fts_ad", "sentences_fts_au")


def drop_fts(engine: Engine) -> None:
    """Remove the virtual table and its triggers.

    Necessary before ``Base.metadata.drop_all``: the FTS table is not part of
    SQLAlchemy's metadata, so ``drop_all`` leaves it behind. Recreating
    ``sentences`` afterwards restarts rowids at 1, which then collide with the
    stale index entries and make the very next insert fail.
    """
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        for trigger in _TRIGGERS:
            connection.execute(text(f"DROP TRIGGER IF EXISTS {trigger}"))
        connection.execute(text(f"DROP TABLE IF EXISTS {FTS_TABLE}"))


def rebuild_index(engine: Engine) -> None:
    """Rebuild the index from the content table.

    Only needed after a bulk load that bypassed the triggers, but cheap enough
    to run after seeding as a guarantee rather than an assumption.
    """
    if not _fts_available:
        return
    with engine.begin() as connection:
        connection.execute(text(f"INSERT INTO {FTS_TABLE}({FTS_TABLE}) VALUES('rebuild')"))


_TOKEN_RE = re.compile(r"[\w']+", re.UNICODE)


def to_match_expression(query: str) -> str | None:
    """Turn arbitrary user input into a safe FTS5 MATCH expression.

    User text cannot be passed to MATCH directly: characters like ``"``, ``*``,
    ``(`` and the bare word ``OR`` are FTS5 *syntax*, so a stray quote turns a
    search into a 500. Tokenising and re-quoting removes that whole class of
    error. The final token gets a ``*`` so type-ahead matches prefixes —
    searching "pric" finds "pricing" before the user finishes typing.
    """
    tokens = _TOKEN_RE.findall(query.lower())
    if not tokens:
        return None
    quoted = [f'"{token}"' for token in tokens[:-1]]
    quoted.append(f'"{tokens[-1]}"*')
    return " ".join(quoted)
