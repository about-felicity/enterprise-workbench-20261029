"""Prefer off-peak execution; do not interrupt work already in flight."""
from datetime import datetime
from zoneinfo import ZoneInfo


def resume_at(epoch):
    now = datetime.fromtimestamp(epoch, ZoneInfo('Asia/Shanghai'))
    # Unknown public holidays retain weekday restrictions conservatively.
    if now.weekday() < 5:
        for start, end in ((9, 12), (14, 18)):
            if start <= now.hour < end:
                return now.replace(hour=end, minute=0, second=0, microsecond=0).timestamp()
    return None
