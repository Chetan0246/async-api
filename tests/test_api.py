"""End-to-end API tests against the ASGI transport."""

from __future__ import annotations

from httpx import AsyncClient


async def test_health(client: AsyncClient) -> None:
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_register_login_and_me_flow(client: AsyncClient) -> None:
    r1 = await client.post(
        "/auth/register", json={"email": "bob@example.com", "password": "supersecret123"}
    )
    assert r1.status_code == 201

    # duplicate registration is rejected
    r2 = await client.post(
        "/auth/register", json={"email": "bob@example.com", "password": "supersecret123"}
    )
    assert r2.status_code == 409

    r3 = await client.post(
        "/auth/login", json={"email": "bob@example.com", "password": "supersecret123"}
    )
    assert r3.status_code == 200
    token = r3.json()["access_token"]
    assert token

    # wrong password rejected
    r4 = await client.post(
        "/auth/login", json={"email": "bob@example.com", "password": "wrong-password"}
    )
    assert r4.status_code == 401

    # token grants access to protected route
    r5 = await client.get("/items", headers={"Authorization": f"Bearer {token}"})
    assert r5.status_code == 200
    assert r5.json() == []


async def test_items_crud(auth_headers: dict[str, str], client: AsyncClient) -> None:
    headers = auth_headers

    created = await client.post("/items", json={"title": "Laptop", "price": 999.9}, headers=headers)
    assert created.status_code == 201
    item_id = created.json()["id"]

    got = await client.get(f"/items/{item_id}", headers=headers)
    assert got.status_code == 200
    assert got.json()["title"] == "Laptop"

    updated = await client.put(
        f"/items/{item_id}", json={"title": "Laptop Pro", "price": 1299.0}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["title"] == "Laptop Pro"

    deleted = await client.delete(f"/items/{item_id}", headers=headers)
    assert deleted.status_code == 204

    missing = await client.get(f"/items/{item_id}", headers=headers)
    assert missing.status_code == 404


async def test_protected_route_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/items")
    assert resp.status_code == 401


async def test_token_refresh_and_logout_flow(client: AsyncClient) -> None:
    # 1. Register & login
    await client.post(
        "/auth/register", json={"email": "refresh_user@example.com", "password": "supersecret123"}
    )
    login_resp = await client.post(
        "/auth/login", json={"email": "refresh_user@example.com", "password": "supersecret123"}
    )
    assert login_resp.status_code == 200
    data = login_resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    refresh_token = data["refresh_token"]

    # 2. Refresh access token
    ref_resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_resp.status_code == 200
    new_data = ref_resp.json()
    assert "access_token" in new_data
    assert "refresh_token" in new_data
    new_refresh = new_data["refresh_token"]

    # 3. Old refresh token was rotated / revoked
    old_reuse = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert old_reuse.status_code == 401

    # 4. Logout revokes active refresh token
    logout_resp = await client.post("/auth/logout", json={"refresh_token": new_refresh})
    assert logout_resp.status_code == 204

    # 5. Revoked token rejected on subsequent refresh
    revoked_reuse = await client.post("/auth/refresh", json={"refresh_token": new_refresh})
    assert revoked_reuse.status_code == 401

