#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path


def _default_store_path() -> Path:
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        return Path(codex_home).expanduser() / "secrets" / "gcp_sa_aliases.json"
    return Path.home() / ".codex" / "secrets" / "gcp_sa_aliases.json"


ALIAS_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,62}$")


def _load_store(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - CLI tool
        raise SystemExit(f"[sa-aliases] ERROR: failed to read {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"[sa-aliases] ERROR: store is not a JSON object: {path}")
    out: dict[str, str] = {}
    for k, v in data.items():
        if isinstance(k, str) and isinstance(v, str):
            out[k] = v
    return out


def _save_store(path: Path, store: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(store, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _validate_alias(alias: str) -> None:
    if not ALIAS_RE.match(alias):
        raise SystemExit(
            "[sa-aliases] ERROR: invalid alias. Use 1-63 chars: letters/numbers plus . _ -"
        )


def cmd_list(args: argparse.Namespace) -> int:
    store = _load_store(args.store)
    for alias in sorted(store.keys()):
        print(f"{alias}\t{store[alias]}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    store = _load_store(args.store)
    email = store.get(args.alias)
    if not email:
        return 1
    print(email)
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    _validate_alias(args.alias)
    store = _load_store(args.store)
    store[args.alias] = args.email
    _save_store(args.store, store)
    return 0


def cmd_rm(args: argparse.Namespace) -> int:
    store = _load_store(args.store)
    if args.alias in store:
        del store[args.alias]
        _save_store(args.store, store)
        return 0
    return 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="sa-aliases",
        description="Manage GCP Service Account aliases for $gcp-agent multi-client workflows.",
    )
    p.add_argument(
        "--store",
        type=Path,
        default=_default_store_path(),
        help="Path to JSON alias store (default: ~/.codex/secrets/gcp_sa_aliases.json).",
    )

    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("list", help="List aliases (tab-separated: alias<TAB>email).")
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("get", help="Print the email for an alias (exit 1 if missing).")
    sp.add_argument("alias")
    sp.set_defaults(func=cmd_get)

    sp = sub.add_parser("set", help="Set/update alias -> email mapping.")
    sp.add_argument("alias")
    sp.add_argument("email")
    sp.set_defaults(func=cmd_set)

    sp = sub.add_parser("rm", help="Remove an alias (exit 1 if missing).")
    sp.add_argument("alias")
    sp.set_defaults(func=cmd_rm)

    return p


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

