# async-api

[![CI](https://img.shields.io/badge/CI-GitHub_Actions-blue)](.github/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12%2B-3776AB)](pyproject.toml)

Advanced async REST + WebSocket API built with **FastAPI**, **SQLAlchemy 2.0 (async)**,
**Pydantic v2**, **JWT auth**, **Argon2 password hashing**, a sliding-window **rate limiter**,
and a websocket **room hub**.

## Features

- **JWT Auth with Dual-Token Rotation:** Access tokens + rotatable refresh tokens (`/auth/login`, `/auth/refresh`, `/auth/logout`) with revocation blacklist
- **Role-Based Access Control (RBAC):** Configurable user roles (`user`, `admin`) and `require_role()` dependency guards
- **Health & Telemetry:** `/health` endpoint reporting system status, uptime, and active WebSocket rooms
- Owner-scoped CRUD for items with pagination
- JWT-authenticated WebSocket rooms at `/ws/{room}?token=...`
- In-process sliding-window rate limiting (429 + `Retry-After`)
- Async SQLAlchemy sessions, auto teardown via lifespan
- Typed end-to-end: full annotations, `py312`, ruff (`E,F,I,UP,B,ASYNC,S`)

## Layout

```
async-api/
├── pyproject.toml
├── .env.example
├── src/app/
│   ├── main.py          # app factory + lifespan
│   ├── config.py        # pydantic-settings
│   ├── db.py            # async engine/session
│   ├── models.py        # ORM models
│   ├── schemas.py       # pydantic schemas
│   ├── security.py      # argon2 + JWT
│   ├── dependencies.py  # auth DI
│   ├── ratelimit.py     # sliding window limiter
│   ├── ws.py            # pub/sub hub
│   └── routers/         # auth, items, ws
└── tests/               # pytest + httpx ASGI tests
```

## Run

```bash
cd async-api
python -m venv .venv && source .venv/Scripts/activate  # Windows bash
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload    # or: python -m app
```

Interactive docs: http://127.0.0.1:8000/docs

## Tests

```bash
pytest
```
