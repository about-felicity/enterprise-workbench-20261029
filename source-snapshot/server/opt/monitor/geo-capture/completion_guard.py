"""Skip a completed historical Doubao batch when starting the GEO target."""
import json
import os
from pathlib import Path
import re
import sys


def is_complete(path):
    try:
        health = json.loads(Path(path).read_text())
    except FileNotFoundError:
        return False
    planned = health.get('planned', 105)
    return (planned > 0 and health.get('status') == 'complete' and health.get('captured') == planned
            and health.get('geo_processed') == planned and not health.get('tasks', {}).get('needs_attention'))


if __name__ == '__main__':
    batch = os.environ.get('DOUBAO_BATCH')
    if batch:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', batch):
            raise SystemExit(255)
        path = Path('/home/user/redroid-doubao/batches') / batch / 'bridge_health.json'
    else:
        path = Path(sys.argv[1])
    try:
        raise SystemExit(1 if is_complete(path) else 0)
    except (ValueError, TypeError, OSError):
        raise SystemExit(255)
