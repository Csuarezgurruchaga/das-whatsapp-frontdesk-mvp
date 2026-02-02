#!/usr/bin/env python3
import argparse
import re
import sys
from pathlib import Path

import yaml

ALLOWED_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _err(msg, errors):
    errors.append(msg)


def _is_str(value):
    return isinstance(value, str)


def _validate_handoff_schedule(schedule, errors):
    if schedule is None:
        return
    if not isinstance(schedule, dict):
        _err("handoff_schedule must be an object", errors)
        return

    windows = schedule.get("windows")
    if windows is not None:
        if not isinstance(windows, list):
            _err("handoff_schedule.windows must be a list", errors)
        else:
            for idx, window in enumerate(windows):
                if not isinstance(window, dict):
                    _err(f"handoff_schedule.windows[{idx}] must be an object", errors)
                    continue
                days = window.get("days")
                if not isinstance(days, list) or not days:
                    _err(f"handoff_schedule.windows[{idx}].days must be a non-empty list", errors)
                else:
                    for day in days:
                        if day not in ALLOWED_DAYS:
                            _err(
                                f"handoff_schedule.windows[{idx}].days has invalid day '{day}'",
                                errors,
                            )
                start = window.get("start")
                end = window.get("end")
                if not _is_str(start) or not TIME_RE.match(start):
                    _err(f"handoff_schedule.windows[{idx}].start must be HH:MM", errors)
                if not _is_str(end) or not TIME_RE.match(end):
                    _err(f"handoff_schedule.windows[{idx}].end must be HH:MM", errors)

    closed_dates = schedule.get("closed_dates")
    if closed_dates is not None:
        if not isinstance(closed_dates, list):
            _err("handoff_schedule.closed_dates must be a list", errors)
        else:
            for date in closed_dates:
                if not _is_str(date) or not DATE_RE.match(date):
                    _err(f"handoff_schedule.closed_dates has invalid date '{date}'", errors)

    closed_ranges = schedule.get("closed_ranges")
    if closed_ranges is not None:
        if not isinstance(closed_ranges, list):
            _err("handoff_schedule.closed_ranges must be a list", errors)
        else:
            for idx, item in enumerate(closed_ranges):
                if not isinstance(item, dict):
                    _err(f"handoff_schedule.closed_ranges[{idx}] must be an object", errors)
                    continue
                start = item.get("start")
                end = item.get("end")
                if not _is_str(start) or not DATE_RE.match(start):
                    _err(f"handoff_schedule.closed_ranges[{idx}].start must be YYYY-MM-DD", errors)
                if not _is_str(end) or not DATE_RE.match(end):
                    _err(f"handoff_schedule.closed_ranges[{idx}].end must be YYYY-MM-DD", errors)


def validate_bot_yaml(data):
    errors = []
    if not isinstance(data, dict):
        _err("Root must be a mapping", errors)
        return errors

    root = data.get("root")
    if not _is_str(root) or not root:
        _err("root must be a non-empty string", errors)

    invalid_input_text = data.get("invalid_input_text")
    if not _is_str(invalid_input_text) or not invalid_input_text:
        _err("invalid_input_text must be a non-empty string", errors)

    timezone = data.get("timezone")
    if not _is_str(timezone) or not timezone:
        _err("timezone must be a non-empty string", errors)

    _validate_handoff_schedule(data.get("handoff_schedule"), errors)

    nodes = data.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        _err("nodes must be a non-empty mapping", errors)
        return errors

    node_ids = set(nodes.keys())
    if _is_str(root) and root not in node_ids:
        _err(f"root '{root}' not found in nodes", errors)

    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            _err(f"node '{node_id}' must be an object", errors)
            continue
        on_enter_text = node.get("on_enter_text")
        if not _is_str(on_enter_text) or not on_enter_text:
            _err(f"node '{node_id}' must have non-empty on_enter_text", errors)
        terminal_text = node.get("terminal_text")
        if terminal_text is not None and not _is_str(terminal_text):
            _err(f"node '{node_id}' terminal_text must be a string", errors)

        options = node.get("options")
        if not isinstance(options, list):
            _err(f"node '{node_id}' options must be a list", errors)
            continue
        for idx, option in enumerate(options):
            if not isinstance(option, dict):
                _err(f"node '{node_id}' options[{idx}] must be an object", errors)
                continue
            key = option.get("key")
            label = option.get("label")
            if not _is_str(key) or not re.match(r"^\d+$", key):
                _err(f"node '{node_id}' options[{idx}].key must be numeric string", errors)
            if not _is_str(label) or not label:
                _err(f"node '{node_id}' options[{idx}].label must be non-empty string", errors)

            has_next = "next" in option
            has_action = "action" in option
            if has_next == has_action:
                _err(
                    f"node '{node_id}' options[{idx}] must have exactly one of next/action",
                    errors,
                )
                continue
            if has_next:
                next_node = option.get("next")
                if not _is_str(next_node) or next_node not in node_ids:
                    _err(
                        f"node '{node_id}' options[{idx}].next must reference an existing node",
                        errors,
                    )
            if has_action:
                action = option.get("action")
                if action != "handoff":
                    _err(
                        f"node '{node_id}' options[{idx}].action must be 'handoff'",
                        errors,
                    )

    return errors


def main():
    parser = argparse.ArgumentParser(description="Validate bot YAML against MVP schema")
    parser.add_argument(
        "--path",
        default="config/bot.yaml",
        help="Path to bot YAML (default: config/bot.yaml)",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"error: file not found: {path}", file=sys.stderr)
        return 2

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"error: failed to parse YAML: {exc}", file=sys.stderr)
        return 2

    errors = validate_bot_yaml(data)
    if errors:
        print("YAML validation failed:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    print(f"YAML validation OK: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
