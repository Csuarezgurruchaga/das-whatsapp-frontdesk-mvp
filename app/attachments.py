from __future__ import annotations

from dataclasses import dataclass
import os
import unicodedata


MAX_UPLOAD_BYTES = 100 * 1024 * 1024
IMAGE_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
AUDIO_MAX_UPLOAD_BYTES = 16 * 1024 * 1024
VIDEO_MAX_UPLOAD_BYTES = 16 * 1024 * 1024
DOCUMENT_MAX_UPLOAD_BYTES = MAX_UPLOAD_BYTES
MAX_FILENAME_BASE_CHARS = 120

SUPPORTED_MIME_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "video/mp4",
        "video/3gp",
        "video/3gpp",
        "audio/aac",
        "audio/amr",
        "audio/mp4",
        "audio/ogg",
        "audio/mpeg",
        "text/plain",
        "application/pdf",
        "application/msword",
        "application/vnd.ms-excel",
        "application/vnd.ms-powerpoint",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
)

EXTENSION_TO_MIME = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".mp4": "video/mp4",
    ".3gp": "video/3gp",
    ".3gpp": "video/3gpp",
    ".aac": "audio/aac",
    ".amr": "audio/amr",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".mp3": "audio/mpeg",
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".xls": "application/vnd.ms-excel",
    ".ppt": "application/vnd.ms-powerpoint",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}

MEDIA_KIND_LIMITS = {
    "image": IMAGE_MAX_UPLOAD_BYTES,
    "audio": AUDIO_MAX_UPLOAD_BYTES,
    "video": VIDEO_MAX_UPLOAD_BYTES,
    "document": DOCUMENT_MAX_UPLOAD_BYTES,
}


@dataclass(frozen=True)
class ValidatedAttachment:
    safe_filename: str
    mime: str
    media_kind: str
    size_bytes: int


def _is_safe_char(value: str) -> bool:
    return value.isalnum() or value in {"-", "_", "."}


def sanitize_attachment_filename(filename: str) -> str:
    normalized = unicodedata.normalize("NFC", filename or "").strip()
    if not normalized:
        normalized = "file"

    cleaned_chars: list[str] = []
    for char in normalized:
        if char in {"/", "\\"}:
            cleaned_chars.append("_")
            continue
        cleaned_chars.append(char if _is_safe_char(char) else "_")

    cleaned = "".join(cleaned_chars)
    while ".." in cleaned:
        cleaned = cleaned.replace("..", "_")

    cleaned = cleaned.strip(" .")
    if not cleaned:
        cleaned = "file"

    base, extension = os.path.splitext(cleaned)
    if not base:
        base = "file"
    if len(base) > MAX_FILENAME_BASE_CHARS:
        base = base[:MAX_FILENAME_BASE_CHARS]

    safe_filename = f"{base}{extension}"
    return safe_filename or "file"


def infer_mime_from_filename(filename: str) -> str | None:
    _, extension = os.path.splitext(filename.strip().lower())
    if not extension:
        return None
    inferred = EXTENSION_TO_MIME.get(extension)
    if inferred in SUPPORTED_MIME_TYPES:
        return inferred
    return None


def resolve_attachment_mime(*, filename: str, reported_mime: str | None) -> str:
    mime = (reported_mime or "").strip().lower()
    if mime and mime != "application/octet-stream":
        if mime not in SUPPORTED_MIME_TYPES:
            raise ValueError(f"Unsupported MIME type: {mime}")
        return mime

    inferred = infer_mime_from_filename(filename)
    if inferred is None:
        raise ValueError("Unable to infer a supported MIME type from file extension")
    return inferred


def media_kind_from_mime(mime: str) -> str:
    if mime.startswith("image/"):
        return "image"
    if mime.startswith("audio/"):
        return "audio"
    if mime.startswith("video/"):
        return "video"
    return "document"


def validate_attachment_size(*, size_bytes: int, mime: str) -> str:
    if size_bytes <= 0:
        raise ValueError("Attachment size must be greater than 0 bytes")
    if size_bytes > MAX_UPLOAD_BYTES:
        raise ValueError("Attachment exceeds the global 100MB upload limit")

    media_kind = media_kind_from_mime(mime)
    media_limit = MEDIA_KIND_LIMITS[media_kind]
    if size_bytes > media_limit:
        raise ValueError(
            f"Attachment exceeds the {media_kind} limit of {media_limit} bytes"
        )
    return media_kind


def validate_attachment(
    *,
    filename: str,
    reported_mime: str | None,
    size_bytes: int,
) -> ValidatedAttachment:
    safe_filename = sanitize_attachment_filename(filename)
    mime = resolve_attachment_mime(filename=safe_filename, reported_mime=reported_mime)
    media_kind = validate_attachment_size(size_bytes=size_bytes, mime=mime)
    return ValidatedAttachment(
        safe_filename=safe_filename,
        mime=mime,
        media_kind=media_kind,
        size_bytes=size_bytes,
    )
