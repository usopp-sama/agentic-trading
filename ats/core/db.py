"""Database engine and session management."""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from ats.core.config import get_settings
from ats.core.models import Base

_engine: Engine | None = None
_SessionFactory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        settings = get_settings()
        connect_args = {}
        if settings.db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
        _engine = create_engine(
            settings.db_url, connect_args=connect_args, future=True
        )
        if settings.db_url.startswith("sqlite"):
            # QA-10.3: WAL + NORMAL sync — fewer write stalls with our many
            # small writers (bars, signals, snapshots, journal) on the host
            # laptop. No-op/harmless on :memory: test engines.
            @event.listens_for(_engine, "connect")
            def _sqlite_pragmas(dbapi_conn, _rec):  # noqa: ANN001
                cur = dbapi_conn.cursor()
                try:
                    cur.execute("PRAGMA journal_mode=WAL")
                    cur.execute("PRAGMA synchronous=NORMAL")
                except Exception:  # noqa: BLE001 — pragmas are best-effort
                    pass
                finally:
                    cur.close()
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionFactory
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(
            bind=get_engine(), expire_on_commit=False, future=True
        )
    return _SessionFactory


def init_db() -> None:
    """Create all tables. Idempotent."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    # create_all does not add indexes to tables that already exist, so add the
    # ones introduced later explicitly (idempotent). P0.4: news_id was N+1'd.
    from sqlalchemy import text

    with engine.begin() as conn:
        for stmt in (
            "CREATE INDEX IF NOT EXISTS ix_sentiment_scores_news_id "
            "ON sentiment_scores (news_id)",
            # P3: add the news category column to pre-existing DBs (ALTER is a
            # no-op error when it already exists, swallowed below).
            "ALTER TABLE news_items ADD COLUMN category VARCHAR(32) DEFAULT ''",
            "CREATE INDEX IF NOT EXISTS ix_news_items_category "
            "ON news_items (category)",
        ):
            try:
                conn.execute(text(stmt))
            except Exception:  # noqa: BLE001 — index creation is best-effort
                pass


@contextmanager
def session_scope() -> Iterator[Session]:
    """Transactional session context manager."""
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
