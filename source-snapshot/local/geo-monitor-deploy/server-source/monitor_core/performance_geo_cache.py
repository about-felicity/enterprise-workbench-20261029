"""Reuse unchanged daily GEO evidence without sharing a cross-month build lock."""
from collections import defaultdict
from datetime import date, timedelta
import threading

from . import database
from .analytics import daily_owned_product_recommendations

_guard = threading.Lock()
_locks = [threading.Lock() for _ in range(16)]
_cache = {}


def load_rows(start, end, excluded=()):
    key = (start, tuple(sorted(excluded)))
    with _guard:
        lock = _locks[hash(key) % len(_locks)]
    with lock:
        versions = database.owned_product_day_versions(start, end)
        cached = _cache.get(key, {})
        days = []
        current = date.fromisoformat(start)
        while current <= date.fromisoformat(end):
            days.append(current.isoformat())
            current += timedelta(days=1)
        changed = [day for day in days if day not in cached or cached[day][0] != versions.get(day)]
        result = dict(cached)
        if changed:
            for day in changed:
                grouped = database.load_owned_product_runs(
                    day=day, exclude_questions=excluded, compact=True,
                )
                rows = daily_owned_product_recommendations(
                    grouped, ['deepseek', 'doubao', 'wenxin', 'yuanbao'], day_limit=3660,
                )
                result[day] = (versions.get(day), rows)
            # A concurrent ingestion/review must invalidate the next request.
            after = database.owned_product_day_versions(start, end)
            retained = {day: value for day, value in result.items() if after.get(day) == value[0]}
            with _guard:
                _cache.pop(key, None)
                _cache[key] = retained
                while len(_cache) > 6:
                    _cache.pop(next(iter(_cache)))
        return [row for day in reversed(days) for row in result[day][1]]
