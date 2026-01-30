from __future__ import annotations

from datetime import datetime, timezone, timedelta


def beijing_now_str(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Shanghai")).strftime(fmt)
    except Exception:
        return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8))).strftime(fmt)

