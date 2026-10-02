"""WebSocket router: JWT-authenticated room chat / events."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import UTC, datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError

from app.schemas import WSInMessage, WSOutMessage
from app.security import decode_token

router = APIRouter(tags=["ws"])


@router.websocket("/ws/{room}")
async def websocket_endpoint(websocket: WebSocket, room: str) -> None:
    # Token arrives as ?token=... (browsers cannot set headers on WebSocket).
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="missing token")
        return
    try:
        payload = decode_token(token)
        user_id = int(payload["sub"])
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="invalid token")
        return

    hub = websocket.app.state.hub
    await websocket.accept()
    subscriber = await hub.subscribe(room)

    async def sender() -> None:
        """Pump queued broadcasts to this socket."""
        while True:
            message = await subscriber.queue.get()
            await websocket.send_text(message)

    sender_task = asyncio.create_task(sender())
    try:
        await hub.publish(
            room,
            WSOutMessage(
                room=room, user_id=user_id, text="joined", ts=datetime.now(UTC)
            ).model_dump_json(),
        )
        while True:
            raw = await websocket.receive_text()
            try:
                msg = WSInMessage.model_validate_json(raw)
            except ValidationError:
                await websocket.send_json({"error": "invalid message schema"})
                continue
            if msg.room != room:
                await websocket.send_json({"error": f"room mismatch; you are in {room!r}"})
                continue
            out = WSOutMessage(room=room, user_id=user_id, text=msg.text, ts=datetime.now(UTC))
            await hub.publish(room, out.model_dump_json())
    except WebSocketDisconnect:
        pass
    finally:
        sender_task.cancel()
        with suppress(asyncio.CancelledError):
            await sender_task
        await hub.unsubscribe(room, subscriber)
        await hub.publish(
            room,
            WSOutMessage(
                room=room, user_id=user_id, text="left", ts=datetime.now(UTC)
            ).model_dump_json(),
        )
