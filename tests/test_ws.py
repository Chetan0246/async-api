"""WebSocket endpoint tests (regression: unhashable Subscriber).

Starlette's TestClient is synchronous and manages its own event portal, so
these tests must NOT be async (mixing the two deadlocks the portal).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from app.db import Base, build_engine, get_session
from app.main import create_app


def _make_client(tmp_path: Path) -> TestClient:
    """App with an isolated per-test SQLite DB (sync context)."""
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker

    engine = build_engine(f"sqlite+aiosqlite:///{tmp_path / 'ws-test.db'}")
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False)

    async def _create_tables() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_create_tables())

    async def override_session():
        async with sessionmaker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app = create_app()
    app.dependency_overrides[get_session] = override_session
    return TestClient(app)


@pytest.fixture()
def ws_client(tmp_path: Path) -> TestClient:
    client = _make_client(tmp_path)
    with client as tc:
        yield tc


def _register_and_login(tc: TestClient) -> str:
    tc.post("/auth/register", json={"email": "ws@example.com", "password": "supersecret123"})
    resp = tc.post("/auth/login", json={"email": "ws@example.com", "password": "supersecret123"})
    return resp.json()["access_token"]


def test_ws_room_broadcast(ws_client: TestClient) -> None:
    token = _register_and_login(ws_client)
    with ws_client.websocket_connect(f"/ws/testroom?token={token}") as ws:
        hello = ws.receive_json()
        assert hello["text"] == "joined"
        assert hello["room"] == "testroom"

        ws.send_json({"room": "testroom", "text": "hi there"})
        msg = ws.receive_json()
        assert msg["text"] == "hi there"
        assert msg["room"] == "testroom"

        # leaving produces a broadcast too
        ws.close()
        # after client disconnect the server broadcast 'left' into a room
        # with no subscribers, which is a no-op; nothing to assert here.


def test_ws_rejects_missing_token(ws_client: TestClient) -> None:
    with pytest.raises(Exception):
        with ws_client.websocket_connect("/ws/testroom"):
            pass


def test_ws_rejects_invalid_token(ws_client: TestClient) -> None:
    with pytest.raises(Exception):
        with ws_client.websocket_connect("/ws/testroom?token=not-a-jwt"):
            pass
