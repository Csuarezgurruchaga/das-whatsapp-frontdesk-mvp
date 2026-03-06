from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import tempfile
from uuid import uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy.orm import Session

from app.attachment_storage import read_attachment_binary
from app.attachments import sanitize_attachment_filename
from app.config import get_extras_config
from app.db import crud
from app.db.models import AttachmentMetadata, Message

_PAGE_SIZE = 500
_EXPORT_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_ATTACHMENT_ID_SANITIZE_RE = re.compile(r"[^A-Za-z0-9_-]")


@dataclass(frozen=True)
class ConversationExportResult:
    export_id: str
    conversation_id: int
    storage_relpath: str
    absolute_path: str
    attachment_count: int
    missing_attachments: int


def _serialize_datetime(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()


def _resolve_export_id(export_id: str | None) -> str:
    candidate = (export_id or uuid4().hex).strip()
    if not candidate:
        raise ValueError("export_id must not be empty")
    if _EXPORT_ID_RE.fullmatch(candidate) is None:
        raise ValueError("export_id contains invalid characters")
    return candidate


def _list_all_messages(db: Session, *, conversation_id: int) -> list[Message]:
    messages: list[Message] = []
    offset = 0
    while True:
        batch = crud.list_messages(
            db,
            conversation_id=conversation_id,
            limit=_PAGE_SIZE,
            offset=offset,
        )
        if not batch:
            break
        messages.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        offset += len(batch)
    return messages


def _list_all_attachments(db: Session, *, conversation_id: int) -> list[AttachmentMetadata]:
    attachments: list[AttachmentMetadata] = []
    offset = 0
    while True:
        batch = crud.list_attachments_by_conversation(
            db,
            conversation_id=conversation_id,
            limit=_PAGE_SIZE,
            offset=offset,
        )
        if not batch:
            break
        attachments.extend(batch)
        if len(batch) < _PAGE_SIZE:
            break
        offset += len(batch)
    return attachments


def _build_export_output_paths(
    *,
    exports_dir: str,
    conversation_id: int,
    export_id: str,
) -> tuple[Path, Path, str]:
    base_dir = (exports_dir or "").strip()
    if not base_dir:
        raise ValueError("exports_dir must not be empty")

    base_path = Path(base_dir).expanduser().resolve()
    conversation_dir = (base_path / str(conversation_id)).resolve()
    conversation_dir.relative_to(base_path)

    filename = f"conversation-{conversation_id}-{export_id}.zip"
    final_path = (conversation_dir / filename).resolve()
    final_path.relative_to(base_path)
    storage_relpath = f"{conversation_id}/{filename}"
    return conversation_dir, final_path, storage_relpath


def _build_attachment_archive_name(attachment: AttachmentMetadata) -> str:
    safe_attachment_id = _ATTACHMENT_ID_SANITIZE_RE.sub(
        "_", (attachment.attachment_id or "").strip()
    )
    if not safe_attachment_id:
        safe_attachment_id = "attachment"
    safe_filename = sanitize_attachment_filename(attachment.original_filename)
    return f"attachments/{safe_attachment_id}_{safe_filename}"


def generate_conversation_export_zip(
    db: Session,
    *,
    conversation_id: int,
    export_id: str | None = None,
    now: datetime | None = None,
) -> ConversationExportResult:
    now = now or datetime.now(timezone.utc)
    resolved_export_id = _resolve_export_id(export_id)

    conversation = crud.get_conversation(db, conversation_id=conversation_id)
    if conversation is None:
        raise ValueError("conversation not found")

    extras = get_extras_config()
    conversation_dir, final_path, storage_relpath = _build_export_output_paths(
        exports_dir=extras.exports_dir,
        conversation_id=conversation_id,
        export_id=resolved_export_id,
    )
    conversation_dir.mkdir(parents=True, exist_ok=True)

    messages = _list_all_messages(db, conversation_id=conversation_id)
    attachments = _list_all_attachments(db, conversation_id=conversation_id)

    attachment_entries: list[dict] = []
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+b",
            prefix=".tmp-export-",
            suffix=".zip",
            dir=str(conversation_dir),
            delete=False,
        ) as tmp_file:
            temp_path = Path(tmp_file.name)

        with ZipFile(temp_path, "w", compression=ZIP_DEFLATED) as archive:
            for attachment in attachments:
                archive_path = _build_attachment_archive_name(attachment)
                entry = {
                    "attachment_id": attachment.attachment_id,
                    "message_id": attachment.message_id,
                    "filename": attachment.original_filename,
                    "mime": attachment.mime,
                    "size_bytes": int(attachment.size_bytes),
                    "status": attachment.status.value,
                    "storage_relpath": attachment.storage_relpath,
                    "created_at": _serialize_datetime(attachment.created_at),
                    "archive_path": archive_path,
                    "included_in_zip": False,
                    "warning": None,
                }
                try:
                    payload = read_attachment_binary(
                        attachments_dir=extras.attachments_dir,
                        storage_relpath=attachment.storage_relpath,
                    )
                except FileNotFoundError:
                    entry["warning"] = "attachment binary is missing from storage"
                except OSError as exc:
                    entry["warning"] = f"failed to read attachment binary: {exc}"
                else:
                    archive.writestr(archive_path, payload)
                    entry["included_in_zip"] = True
                attachment_entries.append(entry)

            attachment_ids_by_message_id: dict[int, list[str]] = {}
            for entry in attachment_entries:
                message_id = entry["message_id"]
                if message_id is None:
                    continue
                attachment_ids_by_message_id.setdefault(int(message_id), []).append(
                    entry["attachment_id"]
                )

            transcript_payload = {
                "conversation_id": conversation_id,
                "export_id": resolved_export_id,
                "generated_at": _serialize_datetime(now),
                "message_count": len(messages),
                "attachment_count": len(attachments),
                "messages": [
                    {
                        "message_id": message.id,
                        "direction": message.direction.value,
                        "sender_type": message.sender_type.value,
                        "text": message.text,
                        "whatsapp_message_id": message.whatsapp_message_id,
                        "created_at": _serialize_datetime(message.created_at),
                        "attachment_ids": attachment_ids_by_message_id.get(message.id, []),
                    }
                    for message in messages
                ],
                "attachments": attachment_entries,
            }
            archive.writestr(
                "transcript.json",
                json.dumps(
                    transcript_payload,
                    ensure_ascii=True,
                    sort_keys=True,
                    indent=2,
                ),
            )

        os.replace(temp_path, final_path)
        # X-Accel-Redirect serves exports from a separate nginx container, so
        # the final ZIP must be world-readable on the shared volume.
        os.chmod(final_path, 0o644)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)

    missing_attachments = sum(1 for entry in attachment_entries if not entry["included_in_zip"])
    return ConversationExportResult(
        export_id=resolved_export_id,
        conversation_id=conversation_id,
        storage_relpath=storage_relpath,
        absolute_path=str(final_path),
        attachment_count=len(attachments),
        missing_attachments=missing_attachments,
    )
