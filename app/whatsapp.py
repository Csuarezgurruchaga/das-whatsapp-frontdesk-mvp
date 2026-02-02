from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


def _parse_json_payload(raw: bytes | None) -> dict | None:
    if not raw:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None


def send_text_message(*, to_number: str, text: str) -> WhatsAppSendResponse:
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text},
    }
    body = json.dumps(payload).encode("utf-8")
    request = Request(
        _build_messages_url(),
        data=body,
        headers={
            "Authorization": f"Bearer {_get_access_token()}",
            "Content-Type": "application/json",
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

    response_payload = _parse_json_payload(raw) or {}
    message_id = None
    messages = response_payload.get("messages")
    if isinstance(messages, list) and messages:
        first = messages[0]
        if isinstance(first, dict):
            message_id = first.get("id")

    return WhatsAppSendResponse(message_id=message_id, payload=response_payload)


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
