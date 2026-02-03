from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.deps import (
    ensure_can_respond_conversation,
    get_current_user,
    get_db,
    require_roles,
)
from app.db import crud
from app.db.models import (
    Conversation,
    ConversationEventType,
    ConversationState,
    MessageDirection,
    SenderType,
    User,
    UserRole,
)
from app.realtime import (
    build_conversation_event,
    build_message_event,
    dispatch_event,
    make_recipient_filter_for_conversation_update,
    make_recipient_filter_for_message,
)
from app.whatsapp import send_outbound_text

router = APIRouter()


class ConversationActionResponse(BaseModel):
    ok: bool
    conversation_id: int
    state: str
    assigned_to: int | None = None


class ReassignRequest(BaseModel):
    assignee_user_id: int


class SendMessageRequest(BaseModel):
    text: str


class SendMessageResponse(BaseModel):
    ok: bool
    conversation_id: int
    message_id: int
    whatsapp_message_id: str | None


@router.post("/{conversation_id}/take", response_model=ConversationActionResponse)
def take_conversation(
    conversation_id: int,
    current_user: User = Depends(require_roles(UserRole.AGENT, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ConversationActionResponse:
    now = datetime.now(timezone.utc)
    stmt = (
        update(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.state == ConversationState.EN_ESPERA,
            Conversation.assigned_to.is_(None),
        )
        .values(
            state=ConversationState.ASIGNADO,
            assigned_to=current_user.id,
            last_activity_at=now,
        )
    )
    result = db.execute(stmt)
    if result.rowcount != 1:
        conversation = crud.get_conversation(db, conversation_id=conversation_id)
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation already taken or not in waiting",
        )

    crud.create_conversation_event(
        db,
        conversation_id=conversation_id,
        event_type=ConversationEventType.TAKEN,
        actor_user_id=current_user.id,
    )
    db.commit()

    dispatch_event(
        build_conversation_event(
            conversation_id=conversation_id,
            state=ConversationState.ASIGNADO,
            assigned_to=current_user.id,
            last_activity_at=now,
            previous_state=ConversationState.EN_ESPERA,
            previous_assigned_to=None,
            reason="take",
        ),
        make_recipient_filter_for_conversation_update(
            state=ConversationState.ASIGNADO,
            assigned_to=current_user.id,
            previous_state=ConversationState.EN_ESPERA,
            previous_assigned_to=None,
        ),
    )

    return ConversationActionResponse(
        ok=True,
        conversation_id=conversation_id,
        state=ConversationState.ASIGNADO.value,
        assigned_to=current_user.id,
    )


@router.post("/{conversation_id}/reassign", response_model=ConversationActionResponse)
def reassign_conversation(
    conversation_id: int,
    payload: ReassignRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> ConversationActionResponse:
    assignee = crud.get_user(db, user_id=payload.assignee_user_id)
    if assignee is None or assignee.disabled_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found")
    if assignee.role == UserRole.ADMIN and assignee.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Assignee must be an agent or the current admin",
        )

    conversation_before = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation_before is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    if conversation_before.state != ConversationState.ASIGNADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation not assigned",
        )

    previous_assigned_to = conversation_before.assigned_to
    now = datetime.now(timezone.utc)
    stmt = (
        update(Conversation)
        .where(
            Conversation.id == conversation_id,
            Conversation.state == ConversationState.ASIGNADO,
        )
        .values(
            assigned_to=assignee.id,
            last_activity_at=now,
        )
    )
    result = db.execute(stmt)
    if result.rowcount != 1:
        conversation = crud.get_conversation(db, conversation_id=conversation_id)
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
        if conversation.state != ConversationState.ASIGNADO:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conversation not assigned",
            )
        if conversation.assigned_to == assignee.id:
            return ConversationActionResponse(
                ok=True,
                conversation_id=conversation_id,
                state=ConversationState.ASIGNADO.value,
                assigned_to=assignee.id,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation not assigned",
        )

    crud.create_conversation_event(
        db,
        conversation_id=conversation_id,
        event_type=ConversationEventType.REASSIGNED,
        actor_user_id=current_user.id,
    )
    db.commit()

    dispatch_event(
        build_conversation_event(
            conversation_id=conversation_id,
            state=ConversationState.ASIGNADO,
            assigned_to=assignee.id,
            last_activity_at=now,
            previous_state=ConversationState.ASIGNADO,
            previous_assigned_to=previous_assigned_to,
            reason="reassign",
        ),
        make_recipient_filter_for_conversation_update(
            state=ConversationState.ASIGNADO,
            assigned_to=assignee.id,
            previous_state=ConversationState.ASIGNADO,
            previous_assigned_to=previous_assigned_to,
        ),
    )

    return ConversationActionResponse(
        ok=True,
        conversation_id=conversation_id,
        state=ConversationState.ASIGNADO.value,
        assigned_to=assignee.id,
    )


@router.post("/{conversation_id}/close", response_model=ConversationActionResponse)
def close_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationActionResponse:
    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if current_user.role != UserRole.ADMIN:
        ensure_can_respond_conversation(current_user, conversation)
    elif conversation.state != ConversationState.ASIGNADO:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation not assigned",
        )

    previous_assigned_to = conversation.assigned_to
    previous_state = conversation.state
    now = datetime.now(timezone.utc)
    conditions = [
        Conversation.id == conversation_id,
        Conversation.state == ConversationState.ASIGNADO,
    ]
    if current_user.role != UserRole.ADMIN:
        conditions.append(Conversation.assigned_to == current_user.id)

    stmt = (
        update(Conversation)
        .where(*conditions)
        .values(
            state=ConversationState.CERRADO,
            assigned_to=None,
            closed_by=current_user.id,
            closed_at=now,
            last_activity_at=now,
        )
    )
    result = db.execute(stmt)
    if result.rowcount != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conversation not assigned to current user",
        )

    crud.create_conversation_event(
        db,
        conversation_id=conversation_id,
        event_type=ConversationEventType.CLOSED,
        actor_user_id=current_user.id,
    )
    db.commit()

    dispatch_event(
        build_conversation_event(
            conversation_id=conversation_id,
            state=ConversationState.CERRADO,
            assigned_to=None,
            last_activity_at=now,
            previous_state=previous_state,
            previous_assigned_to=previous_assigned_to,
            reason="close",
        ),
        make_recipient_filter_for_conversation_update(
            state=ConversationState.CERRADO,
            assigned_to=None,
            previous_state=previous_state,
            previous_assigned_to=previous_assigned_to,
        ),
    )

    return ConversationActionResponse(
        ok=True,
        conversation_id=conversation_id,
        state=ConversationState.CERRADO.value,
        assigned_to=None,
    )


@router.post("/{conversation_id}/messages", response_model=SendMessageResponse)
def send_message(
    conversation_id: int,
    payload: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SendMessageResponse:
    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    ensure_can_respond_conversation(current_user, conversation)

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message text is required")

    if conversation.contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    now = datetime.now(timezone.utc)
    result = send_outbound_text(
        db,
        conversation_id=conversation_id,
        to_number=conversation.contact.whatsapp_number,
        text=text,
        sender_type=SenderType.AGENT,
        actor_user_id=current_user.id,
        now=now,
    )
    db.commit()

    dispatch_event(
        build_message_event(
            conversation_id=conversation_id,
            message_id=result.message_id,
            direction=MessageDirection.OUTBOUND.value,
            sender_type=SenderType.AGENT.value,
            text=text,
            whatsapp_message_id=result.whatsapp_message_id,
            created_at=now,
            conversation_state=conversation.state,
            assigned_to=conversation.assigned_to,
        ),
        make_recipient_filter_for_message(
            state=conversation.state,
            assigned_to=conversation.assigned_to,
        ),
    )
    dispatch_event(
        build_conversation_event(
            conversation_id=conversation_id,
            state=conversation.state,
            assigned_to=conversation.assigned_to,
            last_activity_at=now,
            reason="message",
        ),
        make_recipient_filter_for_conversation_update(
            state=conversation.state,
            assigned_to=conversation.assigned_to,
        ),
    )

    if not result.ok:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="WhatsApp send failed")

    return SendMessageResponse(
        ok=True,
        conversation_id=conversation_id,
        message_id=result.message_id,
        whatsapp_message_id=result.whatsapp_message_id,
    )
