from __future__ import annotations

from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.datetime_utils import ensure_datetime_utc


def main() -> None:
    # This simulates how MySQL commonly returns datetimes: naive but representing UTC.
    naive_utc = datetime(2026, 2, 5, 4, 41, 0)
    aware_utc = ensure_datetime_utc(naive_utc)

    print("naive:", naive_utc.isoformat())
    print("aware_utc:", aware_utc.isoformat() if aware_utc else None)

    try:
        from zoneinfo import ZoneInfo
    except Exception:
        print("zoneinfo not available; skipping timezone conversion example")
        return

    ba = ZoneInfo("America/Argentina/Buenos_Aires")
    ba_time = aware_utc.astimezone(ba) if aware_utc else None
    print("Buenos_Aires:", ba_time.isoformat() if ba_time else None)


if __name__ == "__main__":
    main()
