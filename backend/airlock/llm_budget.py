"""Bound API spend and live inference concurrency within one FastAPI process.

NOT a persistent/global account hard cap. Configure provider-side project spend
limits; use shared persistent counters for multi-worker/multi-instance deployments.
"""
from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import HTTPException

_lock = asyncio.Lock()
_semaphore = asyncio.Semaphore(2)
_hour = None
_day = None
_hour_count = 0
_day_count = 0


def _limit(name: str, default: int) -> int:
    try:
        return max(1, min(10000, int(os.environ.get(name, str(default)))))
    except ValueError:
        return default


async def consume() -> None:
    global _hour, _day, _hour_count, _day_count
    now = datetime.now(timezone.utc)
    hour, day = now.strftime('%Y%m%d%H'), now.strftime('%Y%m%d')
    async with _lock:
        if hour != _hour:
            _hour, _hour_count = hour, 0
        if day != _day:
            _day, _day_count = day, 0
        if _hour_count >= _limit('AIRLOCK_LLM_HOURLY_LIMIT', 12) or _day_count >= _limit('AIRLOCK_LLM_DAILY_LIMIT', 36):
            raise HTTPException(status_code=429, detail='Public LLM demo budget reached. Recorded Attack Studio evidence remains available.')
        _hour_count += 1
        _day_count += 1


@asynccontextmanager
async def inference_slot():
    try:
        await asyncio.wait_for(_semaphore.acquire(), timeout=1.0)
    except asyncio.TimeoutError as exc:
        raise HTTPException(status_code=429, detail='Too many simultaneous LLM demonstrations. Try again later.') from exc
    try:
        yield
    finally:
        _semaphore.release()


def status() -> dict:
    return {"hourly_limit_per_process": _limit('AIRLOCK_LLM_HOURLY_LIMIT', 12),
            "daily_limit_per_process": _limit('AIRLOCK_LLM_DAILY_LIMIT', 36),
            "max_concurrent_per_process": 2, "scope": "in-memory per worker; resets on restart"}
