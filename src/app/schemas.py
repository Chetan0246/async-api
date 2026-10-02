"""Pydantic v2 request/response schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


# ---------------------------------------------------------------- schemas ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str = "user"
    is_active: bool
    created_at: datetime


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str



class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    price: float = Field(default=0.0, ge=0)


class ItemRead(ItemCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    created_at: datetime


# ----------------------------------------------------------------- events ---
class WSInMessage(BaseModel):
    """Message sent by a client over the websocket."""

    room: str = Field(min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")
    text: str = Field(min_length=1, max_length=2000)


class WSOutMessage(BaseModel):
    """Message broadcast to room subscribers."""

    room: str
    user_id: int
    text: str
    ts: datetime
