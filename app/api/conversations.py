from __future__ import annotations

from datetime import datetime, timezone
import logging
from pathlib import Path, PurePosixPath
import re
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.attachment_storage import resolve_attachment_storage_path
from app.api.deps import (
    ensure_can_respond_conversation,
    ensure_can_view_conversation,
    get_current_user,
    get_db,
    require_roles,
)
from app.config import get_extras_config
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
from app.datetime_utils import ensure_datetime_utc
from app.attachment_pipeline import send_outbound_attachment
from app.hard_delete import hard_delete_conversation as execute_hard_delete_conversation
from app.whatsapp import send_outbound_text

router = APIRouter()
_LOG = logging.getLogger(__name__)
_VIEWABLE_ATTACHMENT_MIME_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "text/plain",
}
_EXPORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_ATTACHMENTS_ACCEL_PREFIX = "/_internal/attachments"
_EXPORTS_ACCEL_PREFIX = "/_internal/exports"
_MAX_TAXONOMY_TAG_NAME_LENGTH = 64


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


class TaxonomyTagOut(BaseModel):
    tag_id: int
    name: str
    is_archived: bool


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
    tags: list[TaxonomyTagOut]
    available_tags: list[TaxonomyTagOut]


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


class SetConversationTagsRequest(BaseModel):
    tag_ids: list[int]


class TaxonomyTagCreateRequest(BaseModel):
    name: str


class TaxonomyTagUpdateRequest(BaseModel):
    name: str | None = None
    is_archived: bool | None = None


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


def _normalize_relpath_for_proxy(storage_relpath: str) -> str:
    candidate = (storage_relpath or "").strip().replace("\\", "/")
    if not candidate:
        raise ValueError("storage_relpath is empty")

    relpath = PurePosixPath(candidate)
    if relpath.is_absolute() or ".." in relpath.parts:
        raise ValueError("storage_relpath is invalid")

    normalized = relpath.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        raise ValueError("storage_relpath is invalid")
    return normalized


def _build_content_disposition(filename: str, *, inline: bool) -> str:
    disposition = "inline" if inline else "attachment"
    safe = (filename or "").strip().replace('"', "_").replace("\r", "_").replace("\n", "_")
    if not safe:
        safe = "file"
    ascii_fallback = safe.encode("ascii", "ignore").decode("ascii") or "file"
    encoded = quote(safe, safe="")
    return f"{disposition}; filename=\"{ascii_fallback}\"; filename*=UTF-8''{encoded}"


def _build_proxy_response(
    *,
    accel_prefix: str,
    relpath: str,
    content_type: str,
    filename: str,
    inline: bool,
) -> Response:
    return Response(
        status_code=status.HTTP_200_OK,
        headers={
            "X-Accel-Redirect": f"{accel_prefix}/{relpath}",
            "Content-Type": content_type,
            "Content-Disposition": _build_content_disposition(filename, inline=inline),
            "X-Content-Type-Options": "nosniff",
        },
    )


def _get_authorized_attachment(
    *,
    conversation_id: int,
    attachment_id: str,
    current_user: User,
    db: Session,
):
    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    try:
        ensure_can_view_conversation(current_user, conversation)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            _LOG.warning(
                "proxy_attachment_auth_denied conversation_id=%s attachment_id=%s user_id=%s role=%s",
                conversation_id,
                attachment_id,
                current_user.id,
                current_user.role.value,
            )
        raise

    attachment = crud.get_attachment_by_attachment_id(db, attachment_id=attachment_id)
    if attachment is None or attachment.conversation_id != conversation_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")

    extras = get_extras_config()
    try:
        absolute_path = resolve_attachment_storage_path(
            attachments_dir=extras.attachments_dir,
            storage_relpath=attachment.storage_relpath,
        )
        relpath = _normalize_relpath_for_proxy(attachment.storage_relpath)
    except ValueError as exc:
        _LOG.error(
            "proxy_attachment_path_invalid conversation_id=%s attachment_id=%s relpath=%s",
            conversation_id,
            attachment_id,
            attachment.storage_relpath,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Attachment path is invalid",
        ) from exc
    if not absolute_path.is_file():
        _LOG.warning(
            "proxy_attachment_file_missing conversation_id=%s attachment_id=%s relpath=%s",
            conversation_id,
            attachment_id,
            attachment.storage_relpath,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file not found")
    return attachment, relpath


def _require_taxonomy_feature_enabled() -> None:
    if not get_extras_config().features.taxonomy_admin_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxonomy feature is disabled",
        )


def _normalize_tag_name(name: str) -> str:
    normalized = (name or "").strip()
    if not normalized:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Tag name is required")
    if len(normalized) > _MAX_TAXONOMY_TAG_NAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tag name must be <= {_MAX_TAXONOMY_TAG_NAME_LENGTH} characters",
        )
    return normalized


def _serialize_taxonomy_tag(tag) -> TaxonomyTagOut:
    return TaxonomyTagOut(
        tag_id=tag.id,
        name=tag.name,
        is_archived=bool(tag.is_archived),
    )


def _serialize_taxonomy_tags(tags: list) -> list[TaxonomyTagOut]:
    return [_serialize_taxonomy_tag(tag) for tag in tags]


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
                last_activity_at=ensure_datetime_utc(conversation.last_activity_at),
                last_message_text=last_message.text if last_message else None,
                unread_count=unread_count,
            )
        )
    return summaries


@router.get("/taxonomy/tags", response_model=list[TaxonomyTagOut])
def list_taxonomy_tags(
    include_archived: bool = True,
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SUPERVISOR)),
    db: Session = Depends(get_db),
) -> list[TaxonomyTagOut]:
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPERVISOR}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    _require_taxonomy_feature_enabled()
    tags = crud.list_taxonomy_tags(db, include_archived=include_archived)
    return _serialize_taxonomy_tags(tags)


@router.post("/taxonomy/tags", response_model=TaxonomyTagOut, status_code=status.HTTP_201_CREATED)
def create_taxonomy_tag(
    payload: TaxonomyTagCreateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> TaxonomyTagOut:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    _require_taxonomy_feature_enabled()
    name = _normalize_tag_name(payload.name)
    existing = crud.get_taxonomy_tag_by_name(db, name=name)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists")

    tag = crud.create_taxonomy_tag(
        db,
        name=name,
        created_by=current_user.id,
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists") from exc

    db.refresh(tag)
    return _serialize_taxonomy_tag(tag)


@router.patch("/taxonomy/tags/{tag_id}", response_model=TaxonomyTagOut)
def update_taxonomy_tag(
    tag_id: int,
    payload: TaxonomyTagUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> TaxonomyTagOut:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    _require_taxonomy_feature_enabled()
    tag = crud.get_taxonomy_tag(db, tag_id=tag_id)
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    has_name = payload.name is not None
    has_archive_toggle = payload.is_archived is not None
    if not has_name and not has_archive_toggle:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No changes requested")

    normalized_name: str | None = None
    if has_name:
        normalized_name = _normalize_tag_name(payload.name or "")
        existing = crud.get_taxonomy_tag_by_name(db, name=normalized_name)
        if existing is not None and existing.id != tag.id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Tag already exists")

    updated = crud.update_taxonomy_tag(
        tag,
        name=normalized_name,
        is_archived=payload.is_archived,
    )
    db.commit()
    db.refresh(updated)
    return _serialize_taxonomy_tag(updated)


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
    current_tags = crud.list_conversation_tags(db, conversation_id=conversation_id)
    available_tags = crud.list_taxonomy_tags(db, include_archived=False)
    return ConversationDetail(
        conversation_id=conversation.id,
        state=conversation.state.value,
        assigned_to=conversation.assigned_to,
        assigned_to_username=assigned_user.username if assigned_user else None,
        contact_number=contact.whatsapp_number if contact else "",
        contact_name=contact.display_name if contact else None,
        last_activity_at=ensure_datetime_utc(conversation.last_activity_at),
        closed_at=ensure_datetime_utc(conversation.closed_at),
        closed_by=conversation.closed_by,
        previous_conversation_id=conversation.previous_conversation_id,
        tags=_serialize_taxonomy_tags(current_tags),
        available_tags=_serialize_taxonomy_tags(available_tags),
    )


@router.put("/{conversation_id}/tags", response_model=list[TaxonomyTagOut])
def set_conversation_tags(
    conversation_id: int,
    payload: SetConversationTagsRequest,
    current_user: User = Depends(require_roles(UserRole.AGENT, UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> list[TaxonomyTagOut]:
    if current_user.role not in {UserRole.AGENT, UserRole.ADMIN}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    _require_taxonomy_feature_enabled()
    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    ensure_can_view_conversation(current_user, conversation)

    deduped_tag_ids = list(dict.fromkeys(payload.tag_ids or []))
    if any(tag_id <= 0 for tag_id in deduped_tag_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tag id")

    tags = crud.list_taxonomy_tags_by_ids(db, tag_ids=deduped_tag_ids)
    tags_by_id = {tag.id: tag for tag in tags}
    missing_ids = [tag_id for tag_id in deduped_tag_ids if tag_id not in tags_by_id]
    if missing_ids:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")

    archived_ids = [tag_id for tag_id in deduped_tag_ids if tags_by_id[tag_id].is_archived]
    if archived_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Archived tags cannot be assigned",
        )

    assigned_tags = crud.set_conversation_tags(
        db,
        conversation_id=conversation_id,
        tag_ids=deduped_tag_ids,
        assigned_by=current_user.id,
    )
    db.commit()
    return _serialize_taxonomy_tags(assigned_tags)


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
            created_at=ensure_datetime_utc(message.created_at),
        )
        for message in messages
    ]


@router.get("/{conversation_id}/attachments/{attachment_id}/download")
def authorize_attachment_download(
    conversation_id: int,
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    attachment, relpath = _get_authorized_attachment(
        conversation_id=conversation_id,
        attachment_id=attachment_id,
        current_user=current_user,
        db=db,
    )

    return _build_proxy_response(
        accel_prefix=_ATTACHMENTS_ACCEL_PREFIX,
        relpath=relpath,
        content_type=attachment.mime,
        filename=attachment.original_filename,
        inline=False,
    )


@router.get("/{conversation_id}/attachments/{attachment_id}/view")
def authorize_attachment_view(
    conversation_id: int,
    attachment_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    attachment, relpath = _get_authorized_attachment(
        conversation_id=conversation_id,
        attachment_id=attachment_id,
        current_user=current_user,
        db=db,
    )
    if attachment.mime not in _VIEWABLE_ATTACHMENT_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attachment MIME is not viewable",
        )
    return _build_proxy_response(
        accel_prefix=_ATTACHMENTS_ACCEL_PREFIX,
        relpath=relpath,
        content_type=attachment.mime,
        filename=attachment.original_filename,
        inline=True,
    )


@router.get("/{conversation_id}/exports/{export_id}/download")
def authorize_export_download(
    conversation_id: int,
    export_id: str,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
) -> Response:
    if current_user.role != UserRole.ADMIN:
        _LOG.warning(
            "proxy_export_auth_denied conversation_id=%s export_id=%s user_id=%s role=%s",
            conversation_id,
            export_id,
            current_user.id,
            current_user.role.value,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    try:
        ensure_can_view_conversation(current_user, conversation)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_403_FORBIDDEN:
            _LOG.warning(
                "proxy_export_auth_denied conversation_id=%s export_id=%s user_id=%s role=%s",
                conversation_id,
                export_id,
                current_user.id,
                current_user.role.value,
            )
        raise

    resolved_export_id = export_id.strip()
    if _EXPORT_ID_RE.fullmatch(resolved_export_id) is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid export id")

    filename = f"conversation-{conversation_id}-{resolved_export_id}.zip"
    relpath = _normalize_relpath_for_proxy(f"{conversation_id}/{filename}")
    extras = get_extras_config()
    exports_root = Path(extras.exports_dir).expanduser().resolve()
    export_path = (exports_root / relpath).resolve()
    try:
        export_path.relative_to(exports_root)
    except ValueError as exc:
        _LOG.error(
            "proxy_export_path_invalid conversation_id=%s export_id=%s relpath=%s",
            conversation_id,
            resolved_export_id,
            relpath,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export path is invalid",
        ) from exc
    if not export_path.is_file():
        _LOG.warning(
            "proxy_export_file_missing conversation_id=%s export_id=%s relpath=%s",
            conversation_id,
            resolved_export_id,
            relpath,
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Export not found")

    return _build_proxy_response(
        accel_prefix=_EXPORTS_ACCEL_PREFIX,
        relpath=relpath,
        content_type="application/zip",
        filename=filename,
        inline=False,
    )


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
    if assignee.role != UserRole.AGENT and assignee.id != current_user.id:
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo enviar el mensaje por WhatsApp.",
        )

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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="No se pudo enviar el adjunto por WhatsApp.",
        )

    return SendAttachmentResponse(
        ok=True,
        conversation_id=conversation_id,
        message_id=result.message_id,
        attachment_id=result.attachment_id,
        status=result.status.value,
        whatsapp_message_id=result.whatsapp_message_id,
    )
