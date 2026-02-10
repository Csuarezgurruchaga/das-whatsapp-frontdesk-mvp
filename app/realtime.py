from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

import anyio
from fastapi import WebSocket
from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import ConversationState, User, UserRole
from app.security import SESSION_COOKIE_NAME, decode_session_cookie


class WebSocketAuthError(Exception):
    pass


@dataclass(frozen=True)
class ConnectionInfo:
    websocket: WebSocket
    user_id: int
    role: UserRole


RecipientFilter = Callable[[ConnectionInfo], bool]


class RealtimeManager:
    def __init__(self) -> None:
        self._connections: dict[WebSocket, ConnectionInfo] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user: User) -> None:
        await websocket.accept()
        info = ConnectionInfo(websocket=websocket, user_id=user.id, role=user.role)
        async with self._lock:
            self._connections[websocket] = info

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._connections.pop(websocket, None)

    async def broadcast(self, payload: dict, recipient_filter: RecipientFilter | None = None) -> None:
        async with self._lock:
            recipients = list(self._connections.values())

        for info in recipients:
            if recipient_filter is not None and not recipient_filter(info):
                continue
            try:
                await info.websocket.send_json(payload)
            except Exception:
                await self.disconnect(info.websocket)


manager = RealtimeManager()


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def dispatch_event(payload: dict, recipient_filter: RecipientFilter | None = None) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        anyio.from_thread.run(manager.broadcast, payload, recipient_filter)
        return

    loop.create_task(manager.broadcast(payload, recipient_filter))


def build_message_event(
    *,
    conversation_id: int,
    message_id: int,
    direction: str,
    sender_type: str,
    text: str | None,
    whatsapp_message_id: str | None,
    created_at: datetime | None,
    conversation_state: ConversationState,
    assigned_to: int | None,
) -> dict:
    return {
        "type": "message.new",
        "data": {
            "conversation_id": conversation_id,
            "message_id": message_id,
            "direction": direction,
            "sender_type": sender_type,
            "text": text,
            "whatsapp_message_id": whatsapp_message_id,
            "created_at": _serialize_datetime(created_at),
            "conversation_state": conversation_state.value,
            "assigned_to": assigned_to,
        },
    }


def build_conversation_event(
    *,
    conversation_id: int,
    state: ConversationState,
    assigned_to: int | None,
    last_activity_at: datetime | None,
    previous_state: ConversationState | None = None,
    previous_assigned_to: int | None = None,
    reason: str | None = None,
) -> dict:
    return {
        "type": "conversation.updated",
        "data": {
            "conversation_id": conversation_id,
            "state": state.value,
            "assigned_to": assigned_to,
            "last_activity_at": _serialize_datetime(last_activity_at),
            "previous_state": previous_state.value if previous_state else None,
            "previous_assigned_to": previous_assigned_to,
            "reason": reason,
        },
    }


def make_recipient_filter_for_message(
    *,
    state: ConversationState,
    assigned_to: int | None,
) -> RecipientFilter:
    include_all_agents = state in {ConversationState.CHATBOT, ConversationState.EN_ESPERA}
    allowed_agent_ids = {assigned_to} if state == ConversationState.ASIGNADO and assigned_to else set()

    def _filter(info: ConnectionInfo) -> bool:
        if info.role == UserRole.ADMIN:
            return True
        if include_all_agents:
            return True
        return info.user_id in allowed_agent_ids

    return _filter


def make_recipient_filter_for_conversation_update(
    *,
    state: ConversationState,
    assigned_to: int | None,
    previous_state: ConversationState | None = None,
    previous_assigned_to: int | None = None,
) -> RecipientFilter:
    include_all_agents = False
    allowed_agent_ids: set[int] = set()

    def _include_state(state_value: ConversationState | None, assigned_id: int | None) -> None:
        nonlocal include_all_agents
        if state_value in {ConversationState.CHATBOT, ConversationState.EN_ESPERA}:
            include_all_agents = True
            return
        if state_value == ConversationState.ASIGNADO and assigned_id:
            allowed_agent_ids.add(assigned_id)

    _include_state(previous_state, previous_assigned_to)
    _include_state(state, assigned_to)

    def _filter(info: ConnectionInfo) -> bool:
        if info.role == UserRole.ADMIN:
            return True
        if include_all_agents:
            return True
        return info.user_id in allowed_agent_ids

    return _filter


def get_current_user_for_websocket(websocket: WebSocket, db: Session) -> User:
    session_cookie = websocket.cookies.get(SESSION_COOKIE_NAME)
    session_id = decode_session_cookie(session_cookie)
    if not session_id:
        raise WebSocketAuthError("Not authenticated")

    user_session = crud.get_user_session_by_session_id(db, session_id=session_id)
    if user_session is None or user_session.revoked_at is not None:
        raise WebSocketAuthError("Not authenticated")

    now = datetime.now(timezone.utc)
    expires_at = user_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        crud.revoke_user_session(db, user_session, revoked_at=now)
        db.commit()
        raise WebSocketAuthError("Not authenticated")

    user = crud.get_user(db, user_session.user_id)
    if user is None or user.disabled_at is not None:
        raise WebSocketAuthError("Not authenticated")

    return user
