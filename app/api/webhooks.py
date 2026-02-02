from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.bot import menu as bot_menu
from app.db import crud
from app.db.models import ConversationState, MessageDirection, MessageReceiptStatus, SenderType

router = APIRouter()

_RECEIPT_STATUS_MAP = {
    "sent": MessageReceiptStatus.SENT,
    "delivered": MessageReceiptStatus.DELIVERED,
    "read": MessageReceiptStatus.READ,
    "failed": MessageReceiptStatus.FAILED,
}


@dataclass(frozen=True)
class InboundMessage:
    whatsapp_message_id: str | None
    from_number: str
    text: str | None
    profile_name: str | None


@dataclass(frozen=True)
class InboundReceipt:
    whatsapp_message_id: str | None
    status: str | None
    payload: dict


def _get_verify_token() -> str:
    token = os.getenv("WHATSAPP_VERIFY_TOKEN")
    if not token:
        raise RuntimeError("WHATSAPP_VERIFY_TOKEN is not set")
    return token


def _get_app_secret() -> str:
    secret = os.getenv("WHATSAPP_APP_SECRET")
    if not secret:
        raise RuntimeError("WHATSAPP_APP_SECRET is not set")
    return secret


def _env_requires_signature() -> bool:
    env = os.getenv("APP_ENV", "development").lower()
    return env in {"staging", "production"}


def _verify_signature(headers: dict[str, str], body: bytes) -> None:
    signature = headers.get("x-hub-signature-256") or headers.get("X-Hub-Signature-256")
    if not signature:
        if _env_requires_signature():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing signature")
        return

    try:
        secret = _get_app_secret()
    except RuntimeError as exc:
        if _env_requires_signature():
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
        return

    expected = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    expected_signature = f"sha256={expected}"
    if not hmac.compare_digest(signature, expected_signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")


def _iter_webhook_values(payload: dict) -> list[dict]:
    values: list[dict] = []
    for entry in payload.get("entry", []) or []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []) or []:
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if isinstance(value, dict):
                values.append(value)
    return values


def _extract_inbound_messages(payload: dict) -> list[InboundMessage]:
    inbound: list[InboundMessage] = []
    for value in _iter_webhook_values(payload):
        contacts = {}
        for contact in value.get("contacts", []) or []:
            if not isinstance(contact, dict):
                continue
            wa_id = contact.get("wa_id")
            profile = contact.get("profile") or {}
            if wa_id:
                contacts[wa_id] = profile.get("name")

        for message in value.get("messages", []) or []:
            if not isinstance(message, dict):
                continue
            if message.get("type") != "text":
                continue
            text = (message.get("text") or {}).get("body")
            inbound.append(
                InboundMessage(
                    whatsapp_message_id=message.get("id"),
                    from_number=message.get("from"),
                    text=text,
                    profile_name=contacts.get(message.get("from")),
                )
            )
    return inbound


def _extract_receipts(payload: dict) -> list[InboundReceipt]:
    receipts: list[InboundReceipt] = []
    for value in _iter_webhook_values(payload):
        for receipt in value.get("statuses", []) or []:
            if not isinstance(receipt, dict):
                continue
            receipts.append(
                InboundReceipt(
                    whatsapp_message_id=receipt.get("id"),
                    status=receipt.get("status"),
                    payload=receipt,
                )
            )
    return receipts


def _get_or_create_contact(
    db: Session,
    *,
    whatsapp_number: str,
    display_name: str | None,
) -> int:
    contact = crud.get_contact_by_whatsapp_number(db, whatsapp_number=whatsapp_number)
    if contact is not None:
        return contact.id

    contact = crud.create_contact(
        db,
        whatsapp_number=whatsapp_number,
        display_name=display_name,
    )
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        contact = crud.get_contact_by_whatsapp_number(db, whatsapp_number=whatsapp_number)
        if contact is None:
            raise
    return contact.id


def _get_or_create_conversation(db: Session, *, contact_id: int) -> tuple[int, ConversationState]:
    conversation = crud.get_latest_conversation_for_contact(db, contact_id=contact_id)
    if conversation is None:
        conversation = crud.create_conversation(
            db,
            contact_id=contact_id,
            state=ConversationState.CHATBOT,
        )
        db.flush()
        return conversation.id, conversation.state

    if conversation.state == ConversationState.CERRADO:
        conversation = crud.create_conversation(
            db,
            contact_id=contact_id,
            state=ConversationState.CHATBOT,
            previous_conversation_id=conversation.id,
        )
        db.flush()
        return conversation.id, conversation.state

    return conversation.id, conversation.state


def _resolve_current_node_id(config: bot_menu.BotConfig, last_bot_text: str | None) -> str | None:
    if not last_bot_text:
        return None
    for node in config.nodes.values():
        if node.on_enter_text == last_bot_text:
            return node.node_id
        if node.terminal_text and node.terminal_text == last_bot_text:
            return node.node_id
    return None


def _handle_chatbot_message(
    db: Session,
    *,
    conversation_id: int,
    inbound_text: str,
    now: datetime,
) -> ConversationState:
    config = bot_menu.get_bot_config()
    last_bot_text = crud.get_last_bot_message_text(db, conversation_id=conversation_id)
    current_node_id = _resolve_current_node_id(config, last_bot_text)

    if current_node_id is None and not inbound_text.strip().isdigit():
        root_node = config.nodes[config.root]
        crud.append_message(
            db,
            conversation_id=conversation_id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.BOT,
            text=root_node.on_enter_text,
        )
        crud.touch_conversation(db, conversation_id=conversation_id, now=now)
        return ConversationState.CHATBOT

    route = bot_menu.route_chatbot_input(
        config,
        current_node_id=current_node_id or config.root,
        inbound_text=inbound_text,
        now=now,
    )
    for message in route.messages:
        crud.append_message(
            db,
            conversation_id=conversation_id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.BOT,
            text=message,
        )

    if route.handoff_requested and route.handoff_available:
        crud.update_conversation_state(
            db,
            conversation_id=conversation_id,
            state=ConversationState.EN_ESPERA,
            assigned_to=None,
            now=now,
        )
        return ConversationState.EN_ESPERA

    crud.touch_conversation(db, conversation_id=conversation_id, now=now)
    return ConversationState.CHATBOT


def _handle_waiting_message(
    db: Session,
    *,
    conversation_id: int,
    now: datetime,
) -> None:
    bot_texts = crud.list_bot_message_texts(db, conversation_id=conversation_id)
    if bot_menu.should_send_waiting_followup(bot_texts):
        crud.append_message(
            db,
            conversation_id=conversation_id,
            direction=MessageDirection.OUTBOUND,
            sender_type=SenderType.BOT,
            text=bot_menu.WAITING_FOLLOWUP_TEXT,
        )
    crud.touch_conversation(db, conversation_id=conversation_id, now=now)


def _process_inbound_message(
    db: Session,
    inbound: InboundMessage,
    *,
    seen_message_ids: set[str],
) -> None:
    if inbound.whatsapp_message_id:
        if inbound.whatsapp_message_id in seen_message_ids:
            return
        existing = crud.get_message_by_whatsapp_message_id(
            db, whatsapp_message_id=inbound.whatsapp_message_id
        )
        if existing is not None:
            return
        seen_message_ids.add(inbound.whatsapp_message_id)

    if not inbound.from_number:
        return

    contact_id = _get_or_create_contact(
        db,
        whatsapp_number=inbound.from_number,
        display_name=inbound.profile_name,
    )
    conversation_id, state = _get_or_create_conversation(db, contact_id=contact_id)

    crud.append_message(
        db,
        conversation_id=conversation_id,
        direction=MessageDirection.INBOUND,
        sender_type=SenderType.USER,
        text=inbound.text,
        whatsapp_message_id=inbound.whatsapp_message_id,
    )

    now = datetime.now(timezone.utc)
    crud.touch_conversation(db, conversation_id=conversation_id, now=now)

    if inbound.text is None:
        return

    if state == ConversationState.CHATBOT:
        _handle_chatbot_message(db, conversation_id=conversation_id, inbound_text=inbound.text, now=now)
    elif state == ConversationState.EN_ESPERA:
        _handle_waiting_message(db, conversation_id=conversation_id, now=now)


def _process_receipt(db: Session, receipt: InboundReceipt) -> None:
    status_value = _RECEIPT_STATUS_MAP.get(receipt.status or "")
    if status_value is None or receipt.whatsapp_message_id is None:
        return
    crud.create_message_receipt(
        db,
        status=status_value,
        whatsapp_message_id=receipt.whatsapp_message_id,
        payload_raw=json.dumps(receipt.payload, ensure_ascii=True),
    )


@router.get("/whatsapp")
def verify_whatsapp_webhook(request: Request) -> Response:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    try:
        expected_token = _get_verify_token()
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

    if mode == "subscribe" and token == expected_token:
        return Response(content=challenge or "", media_type="text/plain")
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid verify token")


@router.post("/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> dict:
    body = await request.body()
    headers = {key.lower(): value for key, value in request.headers.items()}
    _verify_signature(headers, body)

    try:
        payload = json.loads(body or b"{}")
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON") from exc

    seen_message_ids: set[str] = set()
    for inbound in _extract_inbound_messages(payload):
        _process_inbound_message(db, inbound, seen_message_ids=seen_message_ids)

    for receipt in _extract_receipts(payload):
        _process_receipt(db, receipt)

    db.commit()
    return {"ok": True}
