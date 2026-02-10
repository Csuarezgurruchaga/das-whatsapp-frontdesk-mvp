from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import argparse
import logging
from pathlib import Path
import re
from typing import Sequence

from app.config import get_extras_config

_EXPORT_FILENAME_RE = re.compile(r"^conversation-(?P<conversation_id>\d+)-[A-Za-z0-9_-]+\.zip$")
_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExportCleanupResult:
    exports_dir: str
    ttl_days: int
    cutoff_utc: datetime
    scanned_export_files: int
    expired_export_files: int
    kept_export_files: int
    deleted_export_files: int
    deleted_relpaths: tuple[str, ...]
    skipped_non_export_files: int
    removed_directories: int
    dry_run: bool


def _to_utc(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_export_zip(path: Path) -> bool:
    match = _EXPORT_FILENAME_RE.fullmatch(path.name)
    if match is None:
        return False
    return path.parent.name == match.group("conversation_id")


def cleanup_expired_exports(
    *,
    now: datetime | None = None,
    dry_run: bool = False,
    exports_dir: str | None = None,
    exports_ttl_days: int | None = None,
) -> ExportCleanupResult:
    extras = get_extras_config()
    resolved_exports_dir = (exports_dir or extras.exports_dir).strip()
    resolved_ttl_days = exports_ttl_days or extras.exports_ttl_days
    now_utc = _to_utc(now)
    cutoff = now_utc - timedelta(days=resolved_ttl_days)
    base_path = Path(resolved_exports_dir).expanduser().resolve()

    if not base_path.exists():
        return ExportCleanupResult(
            exports_dir=str(base_path),
            ttl_days=resolved_ttl_days,
            cutoff_utc=cutoff,
            scanned_export_files=0,
            expired_export_files=0,
            kept_export_files=0,
            deleted_export_files=0,
            deleted_relpaths=(),
            skipped_non_export_files=0,
            removed_directories=0,
            dry_run=dry_run,
        )

    scanned_export_files = 0
    expired_export_files = 0
    kept_export_files = 0
    deleted_export_files = 0
    deleted_relpaths: list[str] = []
    skipped_non_export_files = 0

    for candidate in sorted(base_path.rglob("*.zip")):
        if not _is_export_zip(candidate):
            skipped_non_export_files += 1
            continue

        scanned_export_files += 1
        mtime_utc = datetime.fromtimestamp(candidate.stat().st_mtime, tz=timezone.utc)
        if mtime_utc >= cutoff:
            kept_export_files += 1
            continue

        expired_export_files += 1
        relpath = candidate.relative_to(base_path).as_posix()
        if dry_run:
            _LOG.info("dry-run: would delete expired export zip: %s", relpath)
            continue

        candidate.unlink()
        deleted_export_files += 1
        deleted_relpaths.append(relpath)
        _LOG.info("deleted expired export zip: %s", relpath)

    removed_directories = 0
    for directory in sorted(
        [path for path in base_path.rglob("*") if path.is_dir()],
        key=lambda path: len(path.parts),
        reverse=True,
    ):
        if directory.parent != base_path:
            continue
        if not directory.name.isdigit():
            continue
        if any(directory.iterdir()):
            continue
        if dry_run:
            _LOG.info(
                "dry-run: would remove empty export conversation directory: %s",
                directory.relative_to(base_path).as_posix(),
            )
            continue
        directory.rmdir()
        removed_directories += 1
        _LOG.info(
            "removed empty export conversation directory: %s",
            directory.relative_to(base_path).as_posix(),
        )

    return ExportCleanupResult(
        exports_dir=str(base_path),
        ttl_days=resolved_ttl_days,
        cutoff_utc=cutoff,
        scanned_export_files=scanned_export_files,
        expired_export_files=expired_export_files,
        kept_export_files=kept_export_files,
        deleted_export_files=deleted_export_files,
        deleted_relpaths=tuple(deleted_relpaths),
        skipped_non_export_files=skipped_non_export_files,
        removed_directories=removed_directories,
        dry_run=dry_run,
    )


def _parse_now(value: str | None) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cleanup expired conversation export ZIP files.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only report what would be deleted without modifying files.",
    )
    parser.add_argument(
        "--now",
        type=str,
        default=None,
        help="UTC timestamp override in ISO-8601 format.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    result = cleanup_expired_exports(now=_parse_now(args.now), dry_run=args.dry_run)
    _LOG.info(
        "export cleanup summary: scanned=%d expired=%d kept=%d deleted=%d "
        "skipped_non_export=%d removed_dirs=%d dry_run=%s cutoff=%s",
        result.scanned_export_files,
        result.expired_export_files,
        result.kept_export_files,
        result.deleted_export_files,
        result.skipped_non_export_files,
        result.removed_directories,
        result.dry_run,
        result.cutoff_utc.isoformat(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
