"""Read-only balance query using the existing server credential; never print the key."""
import json
from datetime import datetime,timedelta,timezone
from geo_source_cards.deepseek_api import DeepSeekClient,APIError
try:
    result=DeepSeekClient('/home/user/geo-editorial/secrets/deepseek.key').balance()
    print(json.dumps({'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),**result},ensure_ascii=False))
except APIError as e:
    print(json.dumps({'ok':False,'error':e.code}));raise SystemExit(1)
