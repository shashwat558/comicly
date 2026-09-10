import pytest

from app.core.db import engine


@pytest.fixture(autouse=True)
async def fresh_engine():
    # each test gets its own event loop, drop pooled connections from the last one
    await engine.dispose()
    yield
    await engine.dispose()
