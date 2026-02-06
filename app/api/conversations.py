from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.deps import (
    ensure_can_respond_conversation,
    ensure_can_view_conversation,
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
from app.attachment_pipeline import send_outbound_attachment
from app.hard_delete import hard_delete_conversation as execute_hard_delete_conversation
from app.whatsapp import send_outbound_text

router = APIRouter()


class ConversationActionResponse(BaseModel):
    ok: bool
    conversation_id: int
    state: str
    assigned_to: int | None = None


class ConversationSummary(BaseModel):
    conversation_id: int
    state: str
    assigned_to: int | None
    contact_number: str
    contact_name: str | None
    last_activity_at: datetime | None
    last_message_text: str | None
    unread_count: int


class ConversationDetail(BaseModel):
    conversation_id: int
    state: str
    assigned_to: int | None
    assigned_to_username: str | None
    contact_number: str
    contact_name: str | None
    last_activity_at: datetime | None
    closed_at: datetime | None
    closed_by: int | None
    previous_conversation_id: int | None


class MessageAttachmentOut(BaseModel):
    attachment_id: str
    filename: str
    mime: str
    size_bytes: int
    status: str


class MessageOut(BaseModel):
    message_id: int
    direction: str
    sender_type: str
    text: str | None
    attachment: MessageAttachmentOut | None = None
    created_at: datetime | None


class ReassignRequest(BaseModel):
    assignee_user_id: int


class SendMessageRequest(BaseModel):
    text: str


class SendMessageResponse(BaseModel):
    ok: bool
    conversation_id: int
    message_id: int
    whatsapp_message_id: str | None


class SendAttachmentResponse(BaseModel):
    ok: bool
    conversation_id: int
    message_id: int
    attachment_id: str
    status: str
    whatsapp_message_id: str | None


class HardDeleteRequest(BaseModel):
    reason: str | None = None


class HardDeleteResponse(BaseModel):
    ok: bool
    conversation_id: int
    deleted_attachment_files: int
    missing_attachment_files: int
    deleted_export_files: int


@router.get("", response_model=list[ConversationSummary])
def list_conversations(
    state: str = Query(..., min_length=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConversationSummary]:
    try:
        state_enum = ConversationState(state)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid state") from exc

    if state_enum == ConversationState.CERRADO and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if state_enum == ConversationState.ASIGNADO and current_user.role == UserRole.AGENT:
        conversations = crud.list_conversations_by_state_and_assignee(
            db,
            state=state_enum,
            assignee_id=current_user.id,
        )
    else:
        conversations = crud.list_conversations_by_state(db, state=state_enum)

    summaries: list[ConversationSummary] = []
    for conversation in conversations:
        contact = conversation.contact
        last_message = crud.get_last_message(db, conversation_id=conversation.id)
        read_state = crud.get_read_state(
            db,
            conversation_id=conversation.id,
            user_id=current_user.id,
        )
        unread_count = crud.count_unread_messages(
            db,
            conversation_id=conversation.id,
            last_read_message_id=read_state.last_read_message_id if read_state else None,
        )
        summaries.append(
            ConversationSummary(
                conversation_id=conversation.id,
                state=conversation.state.value,
                assigned_to=conversation.assigned_to,
                contact_number=contact.whatsapp_number if contact else "",
                contact_name=contact.display_name if contact else None,
                last_activity_at=conversation.last_activity_at,
                last_message_text=last_message.text if last_message else None,
                unread_count=unread_count,
            )
        )
    return summaries


@router.get("/{conversation_id}", response_model=ConversationDetail)
def get_conversation_detail(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ConversationDetail:
    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    ensure_can_view_conversation(current_user, conversation)

    contact = conversation.contact
    assigned_user = conversation.assigned_user
    return ConversationDetail(
        conversation_id=conversation.id,
        state=conversation.state.value,
        assigned_to=conversation.assigned_to,
        assigned_to_username=assigned_user.username if assigned_user else None,
        contact_number=contact.whatsapp_number if contact else "",
        contact_name=contact.display_name if contact else None,
        last_activity_at=conversation.last_activity_at,
        closed_at=conversation.closed_at,
        closed_by=conversation.closed_by,
        previous_conversation_id=conversation.previous_conversation_id,
    )


@router.get("/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: int,
    mark_read: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[MessageOut]:
    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    ensure_can_view_conversation(current_user, conversation)

    messages = crud.list_messages(db, conversation_id=conversation_id)
    if mark_read:
        last_message_id = messages[-1].id if messages else None
        crud.upsert_read_state(
            db,
            conversation_id=conversation_id,
            user_id=current_user.id,
            last_read_message_id=last_message_id,
        )
        db.commit()

    attachments = crud.list_attachments_by_conversation(db, conversation_id=conversation_id)
    attachments_by_message_id = {
        attachment.message_id: attachment
        for attachment in attachments
        if attachment.message_id is not None
    }

    return [
        MessageOut(
            message_id=message.id,
            direction=message.direction.value,
            sender_type=message.sender_type.value,
            text=message.text,
            attachment=(
                MessageAttachmentOut(
                    attachment_id=attachment.attachment_id,
                    filename=attachment.original_filename,
                    mime=attachment.mime,
                    size_bytes=attachment.size_bytes,
                    status=attachment.status.value,
                )
                if (attachment := attachments_by_message_id.get(message.id)) is not None
                else None
            ),
            created_at=message.created_at,
        )
        for message in messages
    ]


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


@router.post("/{conversation_id}/hard-delete", response_model=HardDeleteResponse)
def hard_delete_conversation(
    conversation_id: int,
    payload: HardDeleteRequest | None = None,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> HardDeleteResponse:
    reason = payload.reason if payload is not None else None
    try:
        result = execute_hard_delete_conversation(
            db,
            conversation_id=conversation_id,
            actor_user_id=current_user.id,
            reason=reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found") from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden") from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hard delete failed while removing files",
        ) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hard delete failed",
        ) from exc

    db.commit()
    return HardDeleteResponse(
        ok=True,
        conversation_id=result.conversation_id,
        deleted_attachment_files=result.deleted_attachment_files,
        missing_attachment_files=result.missing_attachment_files,
        deleted_export_files=result.deleted_export_files,
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


@router.post("/{conversation_id}/attachments", response_model=SendAttachmentResponse)
async def send_attachment(
    conversation_id: int,
    file: UploadFile = File(...),
    attachment_id: str | None = Form(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SendAttachmentResponse:
    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    ensure_can_respond_conversation(current_user, conversation)

    if conversation.contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    content = await file.read()
    original_filename = (file.filename or "").strip() or "file"
    now = datetime.now(timezone.utc)

    try:
        result = send_outbound_attachment(
            db,
            conversation_id=conversation_id,
            to_number=conversation.contact.whatsapp_number,
            actor_user_id=current_user.id,
            original_filename=original_filename,
            reported_mime=file.content_type,
            content=content,
            attachment_id=attachment_id,
            now=now,
        )
    except ValueError as exc:
        detail = str(exc) or "Invalid attachment"
        status_code = (
            status.HTTP_409_CONFLICT
            if "another conversation" in detail
            else status.HTTP_400_BAD_REQUEST
        )
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Attachment pipeline configuration error",
        ) from exc
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Attachment storage failed",
        ) from exc

    db.commit()

    attachment = crud.get_attachment_by_attachment_id(db, attachment_id=result.attachment_id)
    attachment_payload = None
    if attachment is not None:
        attachment_payload = {
            "attachment_id": attachment.attachment_id,
            "filename": attachment.original_filename,
            "mime": attachment.mime,
            "size_bytes": attachment.size_bytes,
            "status": attachment.status.value,
        }

    dispatch_event(
        build_message_event(
            conversation_id=conversation_id,
            message_id=result.message_id,
            direction=MessageDirection.OUTBOUND.value,
            sender_type=SenderType.AGENT.value,
            text=f"[attachment] {original_filename}",
            whatsapp_message_id=result.whatsapp_message_id,
            created_at=now,
            conversation_state=conversation.state,
            assigned_to=conversation.assigned_to,
            attachment=attachment_payload,
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

    return SendAttachmentResponse(
        ok=True,
        conversation_id=conversation_id,
        message_id=result.message_id,
        attachment_id=result.attachment_id,
        status=result.status.value,
        whatsapp_message_id=result.whatsapp_message_id,
    )
