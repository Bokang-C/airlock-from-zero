"""Best-effort, per-worker browser-use budget. Use persistent counters for production."""
import asyncio
import os
from datetime import datetime, timezone
from fastapi import HTTPException

_lock = asyncio.Lock()
_hour_key = ""
_day_key = ""
_hour_count = 0
_day_count = 0


def _limit(name: str, default: int) -> int:
    try:
        return max(1, min(100000, int(os.environ.get(name, str(default)))))
    except ValueError:
        return default


async def consume() -> None:
    global _hour_key, _day_key, _hour_count, _day_count
    now = datetime.now(timezone.utc)
    hour, day = now.strftime("%Y-%m-%d-%H"), now.strftime("%Y-%m-%d")
    hourly = _limit("AIRLOCK_BROWSER_HOURLY_LIMIT", 36)
    daily = _limit("AIRLOCK_BROWSER_DAILY_LIMIT", 150)
    async with _lock:
        if hour != _hour_key:
            _hour_key, _hour_count = hour, 0
        if day != _day_key:
            _day_key, _day_count = day, 0
        if _hour_count >= hourly or _day_count >= daily:
            raise HTTPException(status_code=429, detail="Public browser-use budget reached. Try again later.")
        _hour_count += 1
        _day_count += 1


def status() -> dict:
    return {"hourly_limit": _limit("AIRLOCK_BROWSER_HOURLY_LIMIT", 36),
            "daily_limit": _limit("AIRLOCK_BROWSER_DAILY_LIMIT", 150),
            "scope": "in-memory per process; reset on restart"}
