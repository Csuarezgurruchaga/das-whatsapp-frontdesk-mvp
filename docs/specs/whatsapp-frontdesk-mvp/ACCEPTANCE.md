# ACCEPTANCE — WhatsApp FrontDesk Core MVP

## A0 — Browser smoke (web)
- The app loads in Chromium without critical console errors.
- The primary happy-path flow works end-to-end in the browser.

## A1 — Bot YAML-driven menu (with submenus)
- The bot behavior is driven by a YAML file (`BOT_MENU_YAML_PATH`) using the decided `root` + `nodes` schema.
- User can navigate the menu using numeric replies; invalid input triggers the global invalid-input response and re-shows the current menu.
- Handoff is offered as an explicit option (`action: "handoff"`) where configured in YAML.

## A2 — Handoff to queue (`EN_ESPERA`)
- Selecting the handoff option transitions the conversation from `CHATBOT` to `EN_ESPERA` only when handoff is available per configured business hours/holidays (`handoff_schedule`, timezone `America/Argentina/Buenos_Aires`).
- When handoff is not available (outside schedule / holiday), the conversation stays in `CHATBOT` and the bot replies with:
  - “Nuestros/as operadores/as se encuentran disponibles los días hábiles de 9 a 18hs. Si se encuentra fuera de este rango horario puede comunicarse vía mail a través de contacto@das.gob.ar.
Por emergencias comunicarse al 0810-999-767-3876
 
Saludos”
- After sending the blocked-handoff reply, the bot re-shows the current menu; selecting handoff again while blocked repeats the reply (no rate limit).
- On entering `EN_ESPERA`, the bot sends exactly one auto-reply: “Te estoy derivando con un agente 🙌 En breve te responderá”.
- While in `EN_ESPERA`, inbound user messages are persisted.
- While in `EN_ESPERA`, on the first inbound message received while waiting, the bot sends exactly one additional follow-up message (single-shot): “Seguimos con tu caso. En breve un agente te responde. Gracias por tu paciencia 🙌”.
- Further inbound messages while in `EN_ESPERA` are persisted and do not trigger additional bot replies.

## A3 — Exclusive “take conversation” (atomic)
- In the `EN ESPERA` tab, if two agents attempt to take the same conversation concurrently, exactly one succeeds.
- After a successful take, the conversation disappears from `EN ESPERA` for other agents and appears only in the taker’s `ASIGNADOS`.

## A4 — Assigned chat send/receive (text)
- An agent can send a text message from `ASIGNADOS` and the user receives it via WhatsApp.
- User replies are ingested via webhook and appear in the assigned agent’s UI.

## A5 — Admin reassign + admin reply safety
- Admin can force-reassign an assigned conversation to a different agent or to themselves (not to other admins); it moves between `ASIGNADOS` accordingly.
- Admin can only reply after assigning the conversation to themselves (no double-operator replies).

## A6 — Close conversation + post-close new conversation linking
- Closing a conversation sets state `CERRADO`, records who/when, and removes it from all 3 tabs while preserving history.
- Admin can close an `ASIGNADO` conversation without assigning it to themselves.
- If the user messages after `CERRADO`, a new conversation is created in `CHATBOT` and links to the previous one via `previous_conversation_id`.

## A7 — Security + audit baseline
- Webhook rejects invalid signatures; signature verification is enabled in all non-dev environments.
- Idempotency: duplicate webhook deliveries do not create duplicate inbound messages (dedupe by `whatsapp_message_id`).
- Audit baseline:
  - Critical events are persisted (`TAKEN`, `REASSIGNED`, `CLOSED`, `MESSAGE_SENT_FAILED`, `LOGIN_SUCCESS`, `LOGIN_FAIL`).
  - `LOGIN_SUCCESS` / `LOGIN_FAIL` may be stored without a `conversation_id`.
  - WhatsApp receipts are persisted for audit-only (`sent`, `delivered`, `read`, `failed`) without UI requirements.

## Scope note
- Attachments and tipification are explicitly out-of-scope for this Core MVP and belong to `docs/specs/whatsapp-frontdesk-extensions/`.
