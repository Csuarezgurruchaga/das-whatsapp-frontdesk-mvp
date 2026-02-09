from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import Conversation, ConversationState, User, UserRole
from app.db.session import SessionLocal, get_engine
from app.security import SESSION_COOKIE_NAME, decode_session_cookie


def _coerce_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        # SQLite commonly returns naive datetimes even for timezone=True columns.
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def get_db() -> Session:
    engine = get_engine()
    db = SessionLocal(bind=engine)
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    session_cookie = request.cookies.get(SESSION_COOKIE_NAME)
    session_id = decode_session_cookie(session_cookie)
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user_session = crud.get_user_session_by_session_id(db, session_id=session_id)
    if user_session is None or user_session.revoked_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    now = datetime.now(timezone.utc)
    if _coerce_utc(user_session.expires_at) <= now:
        crud.revoke_user_session(db, user_session, revoked_at=now)
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    user = crud.get_user(db, user_session.user_id)
    if user is None or user.disabled_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    return user


def require_roles(*roles: UserRole):
    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return _dependency


def ensure_can_view_conversation(user: User, conversation: Conversation) -> None:
    if user.role == UserRole.ADMIN:
        return
    if conversation.state in {ConversationState.CHATBOT, ConversationState.EN_ESPERA}:
        return
    if conversation.assigned_to == user.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


def ensure_can_respond_conversation(user: User, conversation: Conversation) -> None:
    if user.role == UserRole.SUPERVISOR:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if conversation.state != ConversationState.ASIGNADO:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if conversation.assigned_to != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
