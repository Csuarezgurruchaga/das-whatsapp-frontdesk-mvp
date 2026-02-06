from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from threading import Lock
from uuid import uuid4

from sqlalchemy.orm import Session

from app.attachment_storage import read_attachment_binary, store_attachment_binary
from app.attachments import media_kind_from_mime, sanitize_attachment_filename, validate_attachment
from app.config import get_extras_config
from app.db import crud
from app.db.models import (
    AttachmentMetadata,
    AttachmentStatus,
    ConversationEventType,
    Message,
    MessageDirection,
    MessageReceiptStatus,
    SenderType,
)
from app.whatsapp import WhatsAppSendError, send_media_message, upload_media

_LOG = logging.getLogger(__name__)
_ATTACHMENT_SEND_COUNTERS: Counter[str] = Counter()
_ATTACHMENT_SEND_COUNTERS_LOCK = Lock()


@dataclass(frozen=True)
class OutboundAttachmentResult:
    ok: bool
    attachment_id: str
    message_id: int
    whatsapp_message_id: str | None
    status: AttachmentStatus
    error: str | None = None


def _attachment_message_text(filename: str) -> str:
    return f"[attachment] {filename}"


def _increment_attachment_send_counter(outcome: str) -> None:
    with _ATTACHMENT_SEND_COUNTERS_LOCK:
        _ATTACHMENT_SEND_COUNTERS[outcome] += 1


def get_attachment_send_counters() -> dict[str, int]:
    with _ATTACHMENT_SEND_COUNTERS_LOCK:
        return {
            "success": int(_ATTACHMENT_SEND_COUNTERS.get("success", 0)),
            "failure": int(_ATTACHMENT_SEND_COUNTERS.get("failure", 0)),
        }


def reset_attachment_send_counters() -> None:
    with _ATTACHMENT_SEND_COUNTERS_LOCK:
        _ATTACHMENT_SEND_COUNTERS.clear()


def _get_message_for_attachment(db: Session, attachment: AttachmentMetadata) -> Message | None:
    if attachment.message_id is None:
        return None
    return db.get(Message, attachment.message_id)


def send_outbound_attachment(
    db: Session,
    *,
    conversation_id: int,
    to_number: str,
    actor_user_id: int,
    original_filename: str,
    reported_mime: str | None,
    content: bytes,
    attachment_id: str | None = None,
    now: datetime | None = None,
) -> OutboundAttachmentResult:
    now = now or datetime.now(timezone.utc)
    extras = get_extras_config()
    resolved_attachment_id = (attachment_id or uuid4().hex).strip()
    if not resolved_attachment_id:
        raise ValueError("attachment_id must not be empty")

    existing = crud.get_attachment_by_attachment_id(
        db, attachment_id=resolved_attachment_id
    )
    attachment: AttachmentMetadata
    message: Message
    safe_filename: str
    mime: str
    media_bytes: bytes

    if existing is not None:
        if existing.conversation_id != conversation_id:
            raise ValueError("attachment_id already belongs to another conversation")
        message = _get_message_for_attachment(db, existing) or crud.append_message(
            db,
            conversation_id=conversation_id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.AGENT,
            text=_attachment_message_text(existing.original_filename),
        )
        db.flush()
        if existing.message_id is None:
            existing.message_id = message.id
        if existing.status == AttachmentStatus.SENT:
            return OutboundAttachmentResult(
                ok=True,
                attachment_id=existing.attachment_id,
                message_id=message.id,
                whatsapp_message_id=message.whatsapp_message_id,
                status=existing.status,
            )

        safe_filename = sanitize_attachment_filename(existing.original_filename)
        mime = existing.mime
        media_bytes = read_attachment_binary(
            attachments_dir=extras.attachments_dir,
            storage_relpath=existing.storage_relpath,
        )
        existing.status = AttachmentStatus.UPLOADING
        attachment = existing
    else:
        validated = validate_attachment(
            filename=original_filename,
            reported_mime=reported_mime,
            size_bytes=len(content),
        )
        safe_filename = validated.safe_filename
        mime = validated.mime
        media_bytes = bytes(content)
        storage_relpath = store_attachment_binary(
            attachments_dir=extras.attachments_dir,
            conversation_id=conversation_id,
            attachment_id=resolved_attachment_id,
            original_filename=original_filename,
            content=media_bytes,
        )
        message = crud.append_message(
            db,
            conversation_id=conversation_id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.AGENT,
            text=_attachment_message_text(safe_filename),
        )
        db.flush()
        attachment = crud.get_or_create_attachment_metadata(
            db,
            conversation_id=conversation_id,
            message_id=message.id,
            attachment_id=resolved_attachment_id,
            original_filename=original_filename,
            mime=mime,
            size_bytes=len(media_bytes),
            storage_relpath=storage_relpath,
            status=AttachmentStatus.UPLOADING,
            created_by=actor_user_id,
        )
        if attachment.message_id is None:
            attachment.message_id = message.id

    media_kind = media_kind_from_mime(mime)
    try:
        media_id = upload_media(filename=safe_filename, mime=mime, content=media_bytes)
        send_response = send_media_message(
            to_number=to_number,
            media_kind=media_kind,
            media_id=media_id,
            filename=safe_filename,
        )
    except (WhatsAppSendError, RuntimeError, OSError) as exc:
        error_payload = None
        status_code = None
        if isinstance(exc, WhatsAppSendError):
            error_payload = exc.payload
            status_code = exc.status_code
        payload_raw = json.dumps(
            {
                "error": str(exc),
                "status_code": status_code,
                "payload": error_payload,
                "attachment_id": attachment.attachment_id,
            },
            ensure_ascii=True,
        )
        _increment_attachment_send_counter("failure")
        _LOG.warning(
            "attachment_send_failed conversation_id=%s attachment_id=%s actor_user_id=%s "
            "status_code=%s error=%s",
            conversation_id,
            attachment.attachment_id,
            actor_user_id,
            status_code,
            str(exc),
        )
        attachment.status = AttachmentStatus.FAILED
        crud.create_message_receipt(
            db,
            status=MessageReceiptStatus.FAILED,
            message_id=message.id,
            payload_raw=payload_raw,
        )
        crud.create_conversation_event(
            db,
            conversation_id=conversation_id,
            event_type=ConversationEventType.MESSAGE_SENT_FAILED,
            actor_user_id=actor_user_id,
            meta_json=payload_raw,
        )
        crud.touch_conversation(db, conversation_id=conversation_id, now=now)
        return OutboundAttachmentResult(
            ok=False,
            attachment_id=attachment.attachment_id,
            message_id=message.id,
            whatsapp_message_id=message.whatsapp_message_id,
            status=attachment.status,
            error=str(exc),
        )

    if send_response.message_id:
        message.whatsapp_message_id = send_response.message_id
    _increment_attachment_send_counter("success")
    _LOG.info(
        "attachment_send_succeeded conversation_id=%s attachment_id=%s actor_user_id=%s "
        "media_kind=%s whatsapp_message_id=%s",
        conversation_id,
        attachment.attachment_id,
        actor_user_id,
        media_kind,
        send_response.message_id,
    )
    attachment.status = AttachmentStatus.SENT
    crud.create_message_receipt(
        db,
        status=MessageReceiptStatus.SENT,
        message_id=message.id,
        payload_raw=json.dumps(
            {
                "upload_media_id": media_id,
                "send_payload": send_response.payload,
                "attachment_id": attachment.attachment_id,
            },
            ensure_ascii=True,
        ),
    )
    crud.touch_conversation(db, conversation_id=conversation_id, now=now)
    return OutboundAttachmentResult(
        ok=True,
        attachment_id=attachment.attachment_id,
        message_id=message.id,
        whatsapp_message_id=send_response.message_id,
        status=attachment.status,
    )
