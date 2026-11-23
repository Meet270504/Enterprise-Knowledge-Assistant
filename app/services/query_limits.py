"""In-memory query rate and daily budget guards for public demos."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone

from fastapi import HTTPException, Request

from app.config import Settings, get_settings

# Per-process state (fine for a single Render web instance).
_lock = threading.Lock()
_ip_hits: dict[str, deque[float]] = defaultdict(deque)
_day_key: str | None = None
_day_count: int = 0


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _utc_day() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def check_query_budget(request: Request, settings: Settings | None = None) -> None:
    """Raise HTTP 429 when per-IP hourly or global daily limits are exceeded.

    Limits of 0 disable that check (useful for local development).
    """
    cfg = settings or get_settings()
    per_ip = max(0, int(cfg.query_rate_limit_per_ip))
    daily = max(0, int(cfg.query_daily_global_limit))
    if per_ip == 0 and daily == 0:
        return

    ip = _client_ip(request)
    now = time.time()
    window = 3600.0

    with _lock:
        global _day_key, _day_count

        today = _utc_day()
        if _day_key != today:
            _day_key = today
            _day_count = 0

        if daily and _day_count >= daily:
            raise HTTPException(
                status_code=429,
                detail=(
                    f"Public demo daily budget reached ({daily} questions / UTC day). "
                    "Try again tomorrow, or raise QUERY_DAILY_GLOBAL_LIMIT for interview day."
                ),
            )

        if per_ip:
            hits = _ip_hits[ip]
            while hits and now - hits[0] >= window:
                hits.popleft()
            if len(hits) >= per_ip:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Too many questions from this network "
                        f"({per_ip} / hour). Please wait and try again."
                    ),
                )
            hits.append(now)

        if daily:
            _day_count += 1
