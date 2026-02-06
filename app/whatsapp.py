from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from sqlalchemy.orm import Session

from app.db import crud
from app.db.models import ConversationEventType, MessageDirection, MessageReceiptStatus, SenderType

_GRAPH_API_VERSION = "v19.0"
_SEND_TIMEOUT_SECONDS = 10


@dataclass(frozen=True)
class WhatsAppSendResponse:
    message_id: str | None
    payload: dict


@dataclass(frozen=True)
class OutboundSendResult:
    ok: bool
    message_id: int
    whatsapp_message_id: str | None
    error: str | None = None


class WhatsAppSendError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = payload


def _get_access_token() -> str:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN")
    if not token:
        raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not set")
    return token


def _get_phone_number_id() -> str:
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
    if not phone_number_id:
        raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID is not set")
    return phone_number_id


def _build_messages_url() -> str:
    phone_number_id = _get_phone_number_id()
    return f"https://graph.facebook.com/{_GRAPH_API_VERSION}/{phone_number_id}/messages"


def _build_media_url() -> str:
    phone_number_id = _get_phone_number_id()
    return f"https://graph.facebook.com/{_GRAPH_API_VERSION}/{phone_number_id}/media"


def _parse_json_payload(raw: bytes | None) -> dict | None:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def _post_whatsapp_request(*, url: str, body: bytes, content_type: str) -> dict:
    request = Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {_get_access_token()}",
            "Content-Type": content_type,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=_SEND_TIMEOUT_SECONDS) as response:
            raw = response.read()
    except HTTPError as exc:
        error_payload = _parse_json_payload(exc.read())
        message = "WhatsApp send failed"
        if isinstance(error_payload, dict):
            error = error_payload.get("error")
            if isinstance(error, dict) and error.get("message"):
                message = error.get("message")
        raise WhatsAppSendError(message, status_code=exc.code, payload=error_payload) from exc
    except URLError as exc:
        raise WhatsAppSendError(
            f"WhatsApp send failed: {exc.reason}", status_code=None, payload=None
        ) from exc

    return _parse_json_payload(raw) or {}


def _extract_message_id(response_payload: dict) -> str | None:
    message_id = None
    messages = response_payload.get("messages")
    if isinstance(messages, list) and messages:
        first = messages[0]
        if isinstance(first, dict):
            message_id = first.get("id")
    return message_id


def send_text_message(*, to_number: str, text: str) -> WhatsAppSendResponse:
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }
    response_payload = _post_whatsapp_request(
        url=_build_messages_url(),
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
    )
    return WhatsAppSendResponse(
        message_id=_extract_message_id(response_payload),
        payload=response_payload,
    )


def upload_media(*, filename: str, mime: str, content: bytes) -> str:
    boundary = f"----CodexBoundary{uuid4().hex}"
    safe_filename = filename.replace('"', "_")
    chunks = [
        (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="messaging_product"\r\n\r\n'
            "whatsapp\r\n"
        ).encode("utf-8"),
        (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="{safe_filename}"\r\n'
            f"Content-Type: {mime}\r\n\r\n"
        ).encode("utf-8"),
        content,
        b"\r\n",
        f"--{boundary}--\r\n".encode("utf-8"),
    ]
    body = b"".join(chunks)
    response_payload = _post_whatsapp_request(
        url=_build_media_url(),
        body=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    media_id = response_payload.get("id")
    if not isinstance(media_id, str) or not media_id.strip():
        raise WhatsAppSendError(
            "WhatsApp media upload failed: missing media id",
            status_code=None,
            payload=response_payload,
        )
    return media_id.strip()


def send_media_message(
    *,
    to_number: str,
    media_kind: str,
    media_id: str,
    filename: str | None = None,
) -> WhatsAppSendResponse:
    if media_kind not in {"image", "audio", "video", "document"}:
        raise ValueError(f"Unsupported media kind: {media_kind}")
    media_object: dict[str, str] = {"id": media_id}
    if media_kind == "document" and filename:
        media_object["filename"] = filename
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": media_kind,
        media_kind: media_object,
    }
    response_payload = _post_whatsapp_request(
        url=_build_messages_url(),
        body=json.dumps(payload).encode("utf-8"),
        content_type="application/json",
    )
    return WhatsAppSendResponse(
        message_id=_extract_message_id(response_payload),
        payload=response_payload,
    )


def send_outbound_text(
    db: Session,
    *,
    conversation_id: int,
    to_number: str,
    text: str,
    sender_type: SenderType,
    actor_user_id: int | None,
    now: datetime | None = None,
) -> OutboundSendResult:
    now = now or datetime.now(timezone.utc)

    message = crud.append_message(
        db,
        conversation_id=conversation_id,
        direction=MessageDirection.OUTBOUND,
        sender_type=sender_type,
        text=text,
    )
    db.flush()

    try:
        response = send_text_message(to_number=to_number, text=text)
    except (WhatsAppSendError, RuntimeError) as exc:
        error_payload = None
        status_code = None
        if isinstance(exc, WhatsAppSendError):
            error_payload = exc.payload
            status_code = exc.status_code

        payload_raw = json.dumps(
            {"error": str(exc), "status_code": status_code, "payload": error_payload},
            ensure_ascii=True,
        )
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
        return OutboundSendResult(
            ok=False,
            message_id=message.id,
            whatsapp_message_id=None,
            error=str(exc),
        )

    if response.message_id:
        message.whatsapp_message_id = response.message_id

    crud.create_message_receipt(
        db,
        status=MessageReceiptStatus.SENT,
        message_id=message.id,
        payload_raw=json.dumps(response.payload, ensure_ascii=True),
    )
    crud.touch_conversation(db, conversation_id=conversation_id, now=now)

    return OutboundSendResult(
        ok=True,
        message_id=message.id,
        whatsapp_message_id=response.message_id,
    )
