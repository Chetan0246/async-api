"""Shared pytest fixtures."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db import Base, build_engine, get_session
from app.main import create_app
from app.models import User
from app.security import hash_password


@pytest.fixture(scope="session")
def event_loop() -> AsyncIterator[asyncio.AbstractEventLoop]:
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def client(tmp_path: Path) -> AsyncIterator[AsyncClient]:
    """App client backed by an isolated per-test SQLite database."""
    db_path = tmp_path / "test.db"
    test_engine = build_engine(f"sqlite+aiosqlite:///{db_path}")
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    test_sessionmaker = async_sessionmaker(test_engine, expire_on_commit=False)

    app = create_app()

    async def override_session():
        async with test_sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_session] = override_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await test_engine.dispose()


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    """Register a user and return Authorization headers for them."""
    await client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )
    resp = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "supersecret123"},
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


_ = (hash_password, User)  # re-exported for convenience in tests
