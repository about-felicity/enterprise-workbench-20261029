"""Read-only metadata audit. Never print cookies, tokens, account IDs or storage values."""
import base64,json,re,sqlite3
from datetime import datetime,timezone
from pathlib import Path
root=Path('/opt/monitor/geo-capture/profiles/deepseek').resolve()
result={'jwt_metadata':[],'cookies':[]}
seen=set()
for path in (root/'Default/Local Storage/leveldb').glob('*'):
 if path.suffix not in {'.log','.ldb'} or path.stat().st_size>20_000_000:continue
 body=path.read_bytes()
 for match in re.finditer(rb'eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}',body):
  token=match.group()
  if token in seen:continue
  seen.add(token)
  try:
   raw=token.split(b'.')[1];value=json.loads(base64.urlsafe_b64decode(raw+b'='*((-len(raw))%4)))
   meta={k:value[k] for k in ['iat','exp','nbf'] if isinstance(value.get(k),(int,float))}
   if 'iat' in meta and 'exp' in meta:meta['lifetime_seconds']=meta['exp']-meta['iat']
   if meta:result['jwt_metadata'].append(meta)
  except Exception:pass
cookie=root/'Default/Network/Cookies'
if not cookie.exists():cookie=root/'Default/Cookies'
if cookie.exists():
 with sqlite3.connect(cookie.as_uri()+'?mode=ro',uri=True) as db:
  for name,expires,persistent in db.execute("select name,expires_utc,is_persistent from cookies where host_key like '%deepseek.com'"):
   result['cookies'].append({'name':name,'persistent':bool(persistent),'expires':datetime.fromtimestamp(expires/1_000_000-11644473600,timezone.utc).isoformat() if expires else None})
print(json.dumps(result,ensure_ascii=False))
