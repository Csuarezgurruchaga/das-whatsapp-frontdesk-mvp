from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
import os
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import yaml

DEFAULT_BOT_MENU_PATH = "./config/bot.yaml"
DEFAULT_TIMEZONE = "America/Argentina/Buenos_Aires"

HANDOFF_BLOCKED_TEXT = (
    "Nuestros/as operadores/as se encuentran disponibles los días hábiles de 9 a 18hs. "
    "Si se encuentra fuera de este rango horario puede comunicarse vía mail a través de "
    "contacto@das.gob.ar.\n"
    "Por emergencias comunicarse al 0810-999-767-3876\n\n"
    "Saludos"
)
WAITING_ENTRY_TEXT = "Te estoy derivando con un agente 🙌 En breve te responderá"
WAITING_FOLLOWUP_TEXT = (
    "Seguimos con tu caso. En breve un agente te responde. Gracias por tu paciencia 🙌"
)

_ALLOWED_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
_DAY_TO_INDEX = {
    "mon": 0,
    "tue": 1,
    "wed": 2,
    "thu": 3,
    "fri": 4,
    "sat": 5,
    "sun": 6,
}
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class BotConfigError(Exception):
    def __init__(self, errors: list[str]):
        super().__init__("Bot config validation failed")
        self.errors = errors


@dataclass(frozen=True)
class BotOption:
    key: str
    label: str
    next_node_id: str | None = None
    action: str | None = None


@dataclass(frozen=True)
class BotNode:
    node_id: str
    on_enter_text: str
    terminal_text: str | None
    options: list[BotOption]


@dataclass(frozen=True)
class BotWindow:
    days: set[int]
    start: time
    end: time

    def includes(self, dt: datetime) -> bool:
        if dt.weekday() not in self.days:
            return False
        current = dt.time()
        return self.start <= current < self.end


@dataclass(frozen=True)
class BotHandoffSchedule:
    windows: list[BotWindow]
    closed_dates: set[date]
    closed_ranges: list[tuple[date, date]]

    def is_open(self, dt: datetime) -> bool:
        if dt.date() in self.closed_dates:
            return False
        for start, end in self.closed_ranges:
            if start <= dt.date() <= end:
                return False
        if not self.windows:
            return False
        return any(window.includes(dt) for window in self.windows)


@dataclass(frozen=True)
class BotConfig:
    root: str
    invalid_input_text: str
    timezone: str
    handoff_schedule: BotHandoffSchedule | None
    nodes: dict[str, BotNode]

    def timezone_info(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def is_handoff_available(self, now: datetime | None = None) -> bool:
        if self.handoff_schedule is None:
            return True
        tz = self.timezone_info()
        if now is None:
            now = datetime.now(tz)
        elif now.tzinfo is None:
            now = now.replace(tzinfo=tz)
        else:
            now = now.astimezone(tz)
        return self.handoff_schedule.is_open(now)


@dataclass(frozen=True)
class BotRouteResult:
    messages: list[str]
    next_node_id: str | None
    handoff_requested: bool
    handoff_available: bool


_BOT_CONFIG: BotConfig | None = None


def get_bot_menu_yaml_path() -> str:
    return os.getenv("BOT_MENU_YAML_PATH", DEFAULT_BOT_MENU_PATH)


def get_bot_config() -> BotConfig:
    global _BOT_CONFIG
    if _BOT_CONFIG is None:
        _BOT_CONFIG = load_bot_config(get_bot_menu_yaml_path())
    return _BOT_CONFIG


def reload_bot_config(path: str | None = None) -> BotConfig:
    global _BOT_CONFIG
    config = load_bot_config(path or get_bot_menu_yaml_path())
    _BOT_CONFIG = config
    return config


def route_chatbot_input(
    config: BotConfig,
    *,
    current_node_id: str,
    inbound_text: str,
    now: datetime | None = None,
) -> BotRouteResult:
    node = config.nodes.get(current_node_id)
    if node is None:
        raise ValueError(f"Unknown node '{current_node_id}'")

    normalized = inbound_text.strip()
    option = next((opt for opt in node.options if opt.key == normalized), None)
    if option is None:
        return BotRouteResult(
            messages=[config.invalid_input_text, _render_node_text(node)],
            next_node_id=current_node_id,
            handoff_requested=False,
            handoff_available=False,
        )

    if option.action == "handoff":
        available = config.is_handoff_available(now)
        if available:
            return BotRouteResult(
                messages=[WAITING_ENTRY_TEXT],
                next_node_id=None,
                handoff_requested=True,
                handoff_available=True,
            )
        return BotRouteResult(
            messages=[HANDOFF_BLOCKED_TEXT, _render_node_text(node)],
            next_node_id=current_node_id,
            handoff_requested=True,
            handoff_available=False,
        )

    next_node = config.nodes[option.next_node_id] if option.next_node_id else node
    return BotRouteResult(
        messages=[_render_node_text(next_node)],
        next_node_id=next_node.node_id,
        handoff_requested=False,
        handoff_available=False,
    )


def should_send_waiting_entry(sent_bot_texts: list[str]) -> bool:
    return WAITING_ENTRY_TEXT not in sent_bot_texts


def should_send_waiting_followup(sent_bot_texts: list[str]) -> bool:
    return WAITING_FOLLOWUP_TEXT not in sent_bot_texts


def load_bot_config(path: str) -> BotConfig:
    errors: list[str] = []
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        raise BotConfigError([f"bot yaml not found: {path}"])

    try:
        data = yaml.safe_load(raw)
    except Exception as exc:  # pragma: no cover - defensive for PyYAML errors
        raise BotConfigError([f"failed to parse yaml: {exc}"])

    config = _parse_bot_config(data, errors)
    if errors:
        raise BotConfigError(errors)
    return config


def _parse_bot_config(data: object, errors: list[str]) -> BotConfig:
    if not isinstance(data, dict):
        errors.append("root must be a mapping")
        return _empty_config()

    root = data.get("root")
    if not _is_non_empty_str(root):
        errors.append("root must be a non-empty string")

    invalid_input_text = data.get("invalid_input_text")
    if not _is_non_empty_str(invalid_input_text):
        errors.append("invalid_input_text must be a non-empty string")

    timezone = data.get("timezone", DEFAULT_TIMEZONE)
    if not _is_non_empty_str(timezone):
        errors.append("timezone must be a non-empty string")
        timezone = DEFAULT_TIMEZONE
    else:
        try:
            ZoneInfo(timezone)
        except Exception:
            errors.append(f"timezone '{timezone}' is not a valid IANA timezone")

    handoff_schedule = _parse_handoff_schedule(data.get("handoff_schedule"), errors)

    nodes_data = data.get("nodes")
    if not isinstance(nodes_data, dict) or not nodes_data:
        errors.append("nodes must be a non-empty mapping")
        return _empty_config(
            root=root or "",
            invalid_input_text=invalid_input_text or "",
            timezone=timezone,
            handoff_schedule=handoff_schedule,
        )

    node_ids = set(nodes_data.keys())
    if _is_non_empty_str(root) and root not in node_ids:
        errors.append(f"root '{root}' not found in nodes")

    nodes: dict[str, BotNode] = {}
    for node_id, node in nodes_data.items():
        if not isinstance(node_id, str):
            errors.append(f"node id '{node_id}' must be a string")
            continue
        if not isinstance(node, dict):
            errors.append(f"node '{node_id}' must be an object")
            continue
        on_enter_text = node.get("on_enter_text")
        if not _is_non_empty_str(on_enter_text):
            errors.append(f"node '{node_id}' must have non-empty on_enter_text")
        terminal_text = node.get("terminal_text")
        if terminal_text is not None and not isinstance(terminal_text, str):
            errors.append(f"node '{node_id}' terminal_text must be a string")

        options_data = node.get("options")
        if not isinstance(options_data, list):
            errors.append(f"node '{node_id}' options must be a list")
            continue

        seen_keys: set[str] = set()
        options: list[BotOption] = []
        for idx, option in enumerate(options_data):
            if not isinstance(option, dict):
                errors.append(f"node '{node_id}' options[{idx}] must be an object")
                continue
            key = option.get("key")
            label = option.get("label")
            if not _is_numeric_str(key):
                errors.append(f"node '{node_id}' options[{idx}].key must be numeric string")
            if not _is_non_empty_str(label):
                errors.append(f"node '{node_id}' options[{idx}].label must be non-empty string")

            if isinstance(key, str):
                if key in seen_keys:
                    errors.append(
                        f"node '{node_id}' options[{idx}].key duplicates '{key}'"
                    )
                seen_keys.add(key)

            has_next = "next" in option
            has_action = "action" in option
            if has_next == has_action:
                errors.append(
                    f"node '{node_id}' options[{idx}] must have exactly one of next/action"
                )
                continue

            next_node_id = None
            action = None
            if has_next:
                next_node_id = option.get("next")
                if not _is_non_empty_str(next_node_id) or next_node_id not in node_ids:
                    errors.append(
                        f"node '{node_id}' options[{idx}].next must reference an existing node"
                    )
            if has_action:
                action = option.get("action")
                if action != "handoff":
                    errors.append(
                        f"node '{node_id}' options[{idx}].action must be 'handoff'"
                    )

            if _is_numeric_str(key) and _is_non_empty_str(label):
                options.append(
                    BotOption(
                        key=key,
                        label=label,
                        next_node_id=next_node_id,
                        action=action,
                    )
                )

        nodes[node_id] = BotNode(
            node_id=node_id,
            on_enter_text=on_enter_text or "",
            terminal_text=terminal_text,
            options=options,
        )

    return BotConfig(
        root=root or "",
        invalid_input_text=invalid_input_text or "",
        timezone=timezone,
        handoff_schedule=handoff_schedule,
        nodes=nodes,
    )


def _parse_handoff_schedule(
    raw_schedule: object, errors: list[str]
) -> BotHandoffSchedule | None:
    if raw_schedule is None:
        return None
    if not isinstance(raw_schedule, dict):
        errors.append("handoff_schedule must be an object")
        return None

    windows_raw = raw_schedule.get("windows")
    windows: list[BotWindow] = []
    if windows_raw is not None:
        if not isinstance(windows_raw, list):
            errors.append("handoff_schedule.windows must be a list")
        else:
            for idx, window in enumerate(windows_raw):
                if not isinstance(window, dict):
                    errors.append(f"handoff_schedule.windows[{idx}] must be an object")
                    continue
                days_raw = window.get("days")
                if not isinstance(days_raw, list) or not days_raw:
                    errors.append(
                        f"handoff_schedule.windows[{idx}].days must be a non-empty list"
                    )
                    continue
                invalid_days = [day for day in days_raw if day not in _ALLOWED_DAYS]
                if invalid_days:
                    for day in invalid_days:
                        errors.append(
                            f"handoff_schedule.windows[{idx}].days has invalid day '{day}'"
                        )
                    continue

                start_raw = window.get("start")
                end_raw = window.get("end")
                start = _parse_time(start_raw, errors, f"handoff_schedule.windows[{idx}].start")
                end = _parse_time(end_raw, errors, f"handoff_schedule.windows[{idx}].end")
                if start is None or end is None:
                    continue
                if end <= start:
                    errors.append(
                        f"handoff_schedule.windows[{idx}] end must be after start"
                    )
                    continue

                windows.append(
                    BotWindow(
                        days={_DAY_TO_INDEX[day] for day in days_raw},
                        start=start,
                        end=end,
                    )
                )

    closed_dates_raw = raw_schedule.get("closed_dates")
    closed_dates: set[date] = set()
    if closed_dates_raw is not None:
        if not isinstance(closed_dates_raw, list):
            errors.append("handoff_schedule.closed_dates must be a list")
        else:
            for item in closed_dates_raw:
                closed_date = _parse_date(item, errors, "handoff_schedule.closed_dates")
                if closed_date is not None:
                    closed_dates.add(closed_date)

    closed_ranges_raw = raw_schedule.get("closed_ranges")
    closed_ranges: list[tuple[date, date]] = []
    if closed_ranges_raw is not None:
        if not isinstance(closed_ranges_raw, list):
            errors.append("handoff_schedule.closed_ranges must be a list")
        else:
            for idx, item in enumerate(closed_ranges_raw):
                if not isinstance(item, dict):
                    errors.append(
                        f"handoff_schedule.closed_ranges[{idx}] must be an object"
                    )
                    continue
                start_date = _parse_date(
                    item.get("start"),
                    errors,
                    f"handoff_schedule.closed_ranges[{idx}].start",
                )
                end_date = _parse_date(
                    item.get("end"),
                    errors,
                    f"handoff_schedule.closed_ranges[{idx}].end",
                )
                if start_date is None or end_date is None:
                    continue
                if end_date < start_date:
                    errors.append(
                        f"handoff_schedule.closed_ranges[{idx}].end must be on or after start"
                    )
                    continue
                closed_ranges.append((start_date, end_date))

    return BotHandoffSchedule(
        windows=windows,
        closed_dates=closed_dates,
        closed_ranges=closed_ranges,
    )


def _render_node_text(node: BotNode) -> str:
    if node.terminal_text and not node.options:
        return node.terminal_text
    return node.on_enter_text


def _parse_time(value: object, errors: list[str], field: str) -> time | None:
    if not isinstance(value, str) or not _TIME_RE.match(value):
        errors.append(f"{field} must be HH:MM")
        return None
    try:
        return time.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} must be HH:MM")
        return None


def _parse_date(value: object, errors: list[str], field: str) -> date | None:
    if not isinstance(value, str) or not _DATE_RE.match(value):
        errors.append(f"{field} must be YYYY-MM-DD")
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field} must be YYYY-MM-DD")
        return None


def _is_non_empty_str(value: object) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _is_numeric_str(value: object) -> bool:
    return isinstance(value, str) and value.isdigit()


def _empty_config(
    *,
    root: str = "",
    invalid_input_text: str = "",
    timezone: str = DEFAULT_TIMEZONE,
    handoff_schedule: BotHandoffSchedule | None = None,
) -> BotConfig:
    return BotConfig(
        root=root,
        invalid_input_text=invalid_input_text,
        timezone=timezone,
        handoff_schedule=handoff_schedule,
        nodes={},
    )
