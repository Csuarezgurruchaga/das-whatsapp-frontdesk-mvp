from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from .attachments import sanitize_attachment_filename


def _validate_segment(value: str, *, field_name: str) -> str:
    segment = (value or "").strip()
    if not segment:
        raise ValueError(f"{field_name} must not be empty")
    if "/" in segment or "\\" in segment or ".." in segment:
        raise ValueError(f"{field_name} contains invalid path characters")
    return segment


def build_attachment_storage_relpath(
    *,
    conversation_id: int | str,
    attachment_id: str,
    original_filename: str,
) -> str:
    conversation_segment = _validate_segment(
        str(conversation_id), field_name="conversation_id"
    )
    attachment_segment = _validate_segment(attachment_id, field_name="attachment_id")
    safe_filename = sanitize_attachment_filename(original_filename)
    return f"{conversation_segment}/{attachment_segment}_{safe_filename}"


def resolve_attachment_storage_path(*, attachments_dir: str, storage_relpath: str) -> Path:
    base_dir = (attachments_dir or "").strip()
    if not base_dir:
        raise ValueError("attachments_dir must not be empty")
    relpath = (storage_relpath or "").strip()
    if not relpath:
        raise ValueError("storage_relpath must not be empty")

    base_path = Path(base_dir).expanduser()
    target_path = (base_path / relpath).resolve()
    resolved_base = base_path.resolve()
    if os.path.commonpath([str(resolved_base), str(target_path)]) != str(resolved_base):
        raise ValueError("storage_relpath resolves outside attachments_dir")
    return target_path


def store_attachment_binary(
    *,
    attachments_dir: str,
    conversation_id: int | str,
    attachment_id: str,
    original_filename: str,
    content: bytes,
) -> str:
    if not isinstance(content, (bytes, bytearray, memoryview)):
        raise TypeError("content must be bytes-like")

    storage_relpath = build_attachment_storage_relpath(
        conversation_id=conversation_id,
        attachment_id=attachment_id,
        original_filename=original_filename,
    )
    final_path = resolve_attachment_storage_path(
        attachments_dir=attachments_dir, storage_relpath=storage_relpath
    )
    final_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = final_path.with_name(f"{final_path.name}.tmp-{uuid4().hex}")
    try:
        with temp_path.open("wb") as temp_file:
            temp_file.write(bytes(content))
            temp_file.flush()
            os.fsync(temp_file.fileno())
        os.replace(temp_path, final_path)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise

    return storage_relpath


def read_attachment_binary(*, attachments_dir: str, storage_relpath: str) -> bytes:
    file_path = resolve_attachment_storage_path(
        attachments_dir=attachments_dir, storage_relpath=storage_relpath
    )
    return file_path.read_bytes()
