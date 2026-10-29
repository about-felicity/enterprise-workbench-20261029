"""Read current account balances without exposing credentials or making model calls."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import json
from pathlib import Path
import subprocess
from urllib.parse import urlsplit
import requests

info=json.loads(subprocess.run(['docker','inspect','monitor-product-worker'],capture_output=True,text=True,check=True,timeout=20).stdout)[0]
env=dict(row.split('=',1) for row in info['Config']['Env'] if '=' in row)
for path in (Path('/opt/monitor/doubao_mumu_controller/doubao_api_keys.env'),Path('/opt/monitor/doubao_api_keys.env')):
    if not path.exists(): continue
    for raw in path.read_text('utf-8-sig').splitlines():
        raw=raw.strip()
        if not raw or raw.startswith('#') or '=' not in raw: continue
        name,value=raw.split('=',1)
        value=value.strip().strip('"').strip("'")
        if name.strip() not in env and value: env[name.strip()]=value
host=urlsplit(env.get('ANTHROPIC_BASE_URL','https://api.deepseek.com/anthropic')).hostname
geo_key=env.get('ANTHROPIC_API_KEY','').strip() if host=='api.deepseek.com' else ''
editorial_path=Path('/home/user/geo-editorial/secrets/deepseek.key')
editorial_key=editorial_path.read_text('utf-8-sig').strip() if editorial_path.exists() else ''
keys=[]
if geo_key: keys.append(('geo_analysis',geo_key))
if editorial_key and editorial_key!=geo_key: keys.append(('content_workbench',editorial_key))
result={'checked_at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),
        'geo_api_host':host, 'geo_and_content_same_key':bool(geo_key and geo_key==editorial_key),'accounts':[]}
session=requests.Session()
session.trust_env=False
for label,key in keys:
    row={'service':label}
    try:
        r=session.get('https://api.deepseek.com/user/balance',headers={'Authorization':'Bearer '+key},timeout=(10,30),allow_redirects=False)
        row['http_status']=r.status_code
        if r.status_code==200:
            data=r.json()
            assert type(data.get('is_available')) is bool
            row['is_available']=data['is_available']
            row['balance_infos']=[]
            for item in data.get('balance_infos',[]):
                assert item['currency'] in ('CNY','USD')
                clean={'currency':item['currency']}
                for name in ('total_balance','granted_balance','topped_up_balance'):
                    if name in item: clean[name]=str(Decimal(str(item[name])))
                row['balance_infos'].append(clean)
    except Exception as exc:
        row['error_type']=type(exc).__name__
    result['accounts'].append(row)
print(json.dumps(result,ensure_ascii=False,indent=2))
