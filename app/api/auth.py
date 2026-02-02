from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_db, get_current_user
from app.db import crud
from app.db.models import ConversationEventType, User
from app.security import (
    SESSION_COOKIE_NAME,
    decode_session_cookie,
    encode_session_cookie,
    verify_password,
)

SESSION_TTL_HOURS = 24

router = APIRouter()


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    user_id: int
    username: str
    role: str


def _cookie_secure() -> bool:
    env = os.getenv("APP_ENV", "development").lower()
    return env in {"staging", "production"}


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> LoginResponse:
    user = crud.get_user_by_username(db, username=payload.username)
    if user is None:
        crud.create_conversation_event(
            db,
            conversation_id=None,
            event_type=ConversationEventType.LOGIN_FAIL,
            actor_user_id=None,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if user.disabled_at is not None or not verify_password(payload.password, user.password_hash):
        crud.create_conversation_event(
            db,
            conversation_id=None,
            event_type=ConversationEventType.LOGIN_FAIL,
            actor_user_id=user.id,
        )
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(hours=SESSION_TTL_HOURS)

    for _ in range(3):
        session_id = secrets.token_urlsafe(32)
        try:
            crud.create_user_session(
                db,
                session_id=session_id,
                user_id=user.id,
                expires_at=expires_at,
            )
            db.flush()
            break
        except IntegrityError:
            db.rollback()
            session_id = None
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Session error")

    crud.create_conversation_event(
        db,
        conversation_id=None,
        event_type=ConversationEventType.LOGIN_SUCCESS,
        actor_user_id=user.id,
    )
    db.commit()

    response.set_cookie(
        SESSION_COOKIE_NAME,
        encode_session_cookie(session_id),
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=int(timedelta(hours=SESSION_TTL_HOURS).total_seconds()),
        path="/",
    )

    return LoginResponse(user_id=user.id, username=user.username, role=user.role.value)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    session_id = decode_session_cookie(session_cookie)

    if session_id:
        user_session = crud.get_user_session_by_session_id(db, session_id=session_id)
        if user_session is not None and user_session.revoked_at is None:
            crud.revoke_user_session(db, user_session)
            db.commit()

    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True, "user_id": current_user.id}
