import pytest

from ledgerly.database import get_engine, init_db, make_session_factory


@pytest.fixture
def session():
    """Fresh in-memory database for every test."""
    engine = get_engine(":memory:")
    init_db(engine)
    s = make_session_factory(engine)()
    yield s
    s.close()
    engine.dispose()
