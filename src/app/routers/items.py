"""Items CRUD router, scoped to the authenticated user."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.dependencies import CurrentUser
from app.models import Item
from app.schemas import ItemCreate, ItemRead

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemRead])
async def list_items(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> list[Item]:
    total = await session.scalar(
        select(func.count()).select_from(Item).where(Item.owner_id == user.id)
    )
    offset = (page - 1) * page_size
    result = await session.scalars(
        select(Item)
        .where(Item.owner_id == user.id)
        .order_by(Item.id)
        .offset(offset)
        .limit(page_size)
    )
    items = list(result)
    _ = total  # available for response headers (X-Total-Count) in future
    return items


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Item:
    item = Item(**payload.model_dump(), owner_id=user.id)
    session.add(item)
    await session.flush()
    await session.refresh(item)
    return item


@router.get("/{item_id}", response_model=ItemRead)
async def get_item(
    item_id: int,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Item:
    item = await session.get(Item, item_id)
    if item is None or item.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item


@router.put("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: int,
    payload: ItemCreate,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> Item:
    item = await session.get(Item, item_id)
    if item is None or item.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    for key, value in payload.model_dump().items():
        setattr(item, key, value)
    await session.flush()
    await session.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: int,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> None:
    item = await session.get(Item, item_id)
    if item is None or item.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    await session.delete(item)
