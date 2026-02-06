from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.attachment_storage import resolve_attachment_storage_path
from app.config import get_extras_config
from app.db import crud
from app.db.models import (
    AttachmentMetadata,
    Conversation,
    ConversationEvent,
    ConversationReadState,
    Message,
    MessageReceipt,
    UserRole,
)


@dataclass(frozen=True)
class HardDeleteResult:
    conversation_id: int
    deleted_attachment_files: int
    missing_attachment_files: int
    deleted_export_files: int
    cleared_previous_conversation_references: int
    deleted_attachment_rows: int
    deleted_message_receipt_rows: int
    deleted_message_rows: int
    deleted_read_state_rows: int
    deleted_conversation_event_rows: int
    deleted_conversation_rows: int


def _normalize_reason(reason: str | None) -> str | None:
    candidate = (reason or "").strip()
    return candidate or None


def _resolve_conversation_dir(base_dir: str, conversation_id: int) -> Path:
    base_path = Path(base_dir).expanduser().resolve()
    conversation_dir = (base_path / str(conversation_id)).resolve()
    conversation_dir.relative_to(base_path)
    return conversation_dir


def _delete_attachment_files(
    *,
    attachments_dir: str,
    conversation_id: int,
    attachments: list[AttachmentMetadata],
) -> tuple[int, int]:
    deleted = 0
    missing = 0
    for attachment in attachments:
        path = resolve_attachment_storage_path(
            attachments_dir=attachments_dir,
            storage_relpath=attachment.storage_relpath,
        )
        if not path.exists():
            missing += 1
            continue
        if path.is_dir():
            raise OSError(
                f"attachment storage path is a directory, expected file: {attachment.storage_relpath}"
            )
        path.unlink()
        deleted += 1

    attachment_dir = _resolve_conversation_dir(attachments_dir, conversation_id)
    if attachment_dir.exists() and attachment_dir.is_dir() and not any(attachment_dir.iterdir()):
        attachment_dir.rmdir()
    return deleted, missing


def _delete_export_artifacts(*, exports_dir: str, conversation_id: int) -> int:
    conversation_dir = _resolve_conversation_dir(exports_dir, conversation_id)
    if not conversation_dir.exists():
        return 0
    if not conversation_dir.is_dir():
        raise OSError("conversation export path is not a directory")

    deleted_files = 0
    for node in sorted(
        conversation_dir.rglob("*"),
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if node.is_symlink() or node.is_file():
            node.unlink()
            deleted_files += 1
            continue
        if node.is_dir() and not any(node.iterdir()):
            node.rmdir()

    if conversation_dir.exists() and not any(conversation_dir.iterdir()):
        conversation_dir.rmdir()

    return deleted_files


def hard_delete_conversation(
    db: Session,
    *,
    conversation_id: int,
    actor_user_id: int,
    reason: str | None = None,
    now: datetime | None = None,
    attachments_dir: str | None = None,
    exports_dir: str | None = None,
) -> HardDeleteResult:
    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise ValueError("conversation not found")

    actor = crud.get_user(db, actor_user_id)
    if actor is None or actor.disabled_at is not None:
        raise PermissionError("actor not authorized")
    if actor.role != UserRole.ADMIN:
        raise PermissionError("admin role required")

    resolved_now = now or datetime.now(timezone.utc)
    extras = get_extras_config()
    effective_attachments_dir = attachments_dir or extras.attachments_dir
    effective_exports_dir = exports_dir or extras.exports_dir
    normalized_reason = _normalize_reason(reason)

    attachments = crud.list_attachments_by_conversation(db, conversation_id=conversation_id)
    deleted_attachment_files, missing_attachment_files = _delete_attachment_files(
        attachments_dir=effective_attachments_dir,
        conversation_id=conversation_id,
        attachments=attachments,
    )
    deleted_export_files = _delete_export_artifacts(
        exports_dir=effective_exports_dir,
        conversation_id=conversation_id,
    )

    message_ids_subquery = select(Message.id).where(Message.conversation_id == conversation_id)
    deleted_message_receipt_rows = (
        db.execute(
            delete(MessageReceipt).where(MessageReceipt.message_id.in_(message_ids_subquery))
        ).rowcount
        or 0
    )
    deleted_read_state_rows = (
        db.execute(
            delete(ConversationReadState).where(
                ConversationReadState.conversation_id == conversation_id
            )
        ).rowcount
        or 0
    )
    deleted_attachment_rows = (
        db.execute(
            delete(AttachmentMetadata).where(AttachmentMetadata.conversation_id == conversation_id)
        ).rowcount
        or 0
    )
    deleted_conversation_event_rows = (
        db.execute(
            delete(ConversationEvent).where(ConversationEvent.conversation_id == conversation_id)
        ).rowcount
        or 0
    )
    cleared_previous_conversation_references = (
        db.execute(
            update(Conversation)
            .where(Conversation.previous_conversation_id == conversation_id)
            .values(previous_conversation_id=None)
        ).rowcount
        or 0
    )
    deleted_message_rows = (
        db.execute(delete(Message).where(Message.conversation_id == conversation_id)).rowcount or 0
    )
    deleted_conversation_rows = (
        db.execute(delete(Conversation).where(Conversation.id == conversation_id)).rowcount or 0
    )
    if deleted_conversation_rows != 1:
        raise RuntimeError("failed to delete conversation")

    crud.create_conversation_deletion_event(
        db,
        conversation_id=conversation_id,
        actor_user_id=actor_user_id,
        reason=normalized_reason,
        created_at=resolved_now,
    )

    return HardDeleteResult(
        conversation_id=conversation_id,
        deleted_attachment_files=deleted_attachment_files,
        missing_attachment_files=missing_attachment_files,
        deleted_export_files=deleted_export_files,
        cleared_previous_conversation_references=cleared_previous_conversation_references,
        deleted_attachment_rows=deleted_attachment_rows,
        deleted_message_receipt_rows=deleted_message_receipt_rows,
        deleted_message_rows=deleted_message_rows,
        deleted_read_state_rows=deleted_read_state_rows,
        deleted_conversation_event_rows=deleted_conversation_event_rows,
        deleted_conversation_rows=deleted_conversation_rows,
    )
