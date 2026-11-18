"""Database layer: engine creation, schema setup and session handling."""
import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .models import Base

DEFAULT_DB = Path.home() / ".ledgerly" / "ledgerly.db"


def get_db_url(path=None):
    """Resolve the DB URL: explicit path > LEDGERLY_DB env var > default file."""
    path = path or os.environ.get("LEDGERLY_DB") or str(DEFAULT_DB)
    if path.startswith("sqlite"):
        return path
    if path == ":memory:":
        return "sqlite://"
    p = Path(path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{p}"


def get_engine(path=None):
    return create_engine(get_db_url(path))


def init_db(engine):
    """Create all tables if they do not exist."""
    Base.metadata.create_all(engine)


def make_session_factory(engine):
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def session_scope(path=None):
    """Transactional scope: commit on success, rollback on error."""
    engine = get_engine(path)
    init_db(engine)
    session = make_session_factory(engine)()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
        engine.dispose()
