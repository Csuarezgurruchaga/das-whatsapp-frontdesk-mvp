from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from starlette.requests import Request
from starlette.websockets import WebSocket

from app.api.deps import get_current_user
from app.db.base import Base
from app.db.models import User, UserRole, UserSession
from app.realtime import get_current_user_for_websocket
from app.security import encode_session_cookie


def _build_test_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    local_session = sessionmaker(bind=engine, future=True)
    return local_session()


def _build_http_request_with_cookie(cookie_value: str) -> Request:
    scope = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [(b"cookie", f"session_id={cookie_value}".encode("ascii"))],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }
    return Request(scope)


def _build_websocket_with_cookie(cookie_value: str) -> WebSocket:
    scope = {
        "type": "websocket",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "scheme": "ws",
        "path": "/realtime/ws",
        "raw_path": b"/realtime/ws",
        "query_string": b"",
        "headers": [(b"cookie", f"session_id={cookie_value}".encode("ascii"))],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
        "subprotocols": [],
    }

    async def _receive():
        return {"type": "websocket.connect"}

    async def _send(_message):
        return None

    return WebSocket(scope, _receive, _send)


class TestSessionExpiryTimezoneCoercion(unittest.TestCase):
    def setUp(self) -> None:
        # Required for encode/decode of signed session cookies.
        os.environ.setdefault("SESSION_SECRET", "test-secret")
        self.db = _build_test_session()
        self.user = User(id=1, username="agent1", password_hash="hash", role=UserRole.AGENT)
        self.db.add(self.user)
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()

    def test_http_auth_accepts_naive_expires_at_on_sqlite(self) -> None:
        session_id = "sess_http_naive"
        # Naive datetime is common with SQLite even when the column is timezone-aware.
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(tzinfo=None)
        self.db.add(
            UserSession(
                id=100,
                session_id=session_id,
                user_id=self.user.id,
                expires_at=expires_at,
                revoked_at=None,
            )
        )
        self.db.commit()

        cookie_value = encode_session_cookie(session_id)
        request = _build_http_request_with_cookie(cookie_value)
        user = get_current_user(request, db=self.db)
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(user.role, UserRole.AGENT)

    def test_websocket_auth_accepts_naive_expires_at_on_sqlite(self) -> None:
        session_id = "sess_ws_naive"
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).replace(tzinfo=None)
        self.db.add(
            UserSession(
                id=101,
                session_id=session_id,
                user_id=self.user.id,
                expires_at=expires_at,
                revoked_at=None,
            )
        )
        self.db.commit()

        cookie_value = encode_session_cookie(session_id)
        ws = _build_websocket_with_cookie(cookie_value)
        user = get_current_user_for_websocket(ws, db=self.db)
        self.assertEqual(user.id, self.user.id)
        self.assertEqual(user.role, UserRole.AGENT)
