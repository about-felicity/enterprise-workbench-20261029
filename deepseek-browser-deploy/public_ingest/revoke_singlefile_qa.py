from pathlib import Path
import json
p=Path('/opt/monitor/geo-capture/public_ingest/clients.json')
v=json.loads(p.read_text())
ids=['desktop-d4808df18ea346dbae1c24b143036c92', 'desktop-60e9e1d3842444799d190503d35cf8d7', 'desktop-0f5fb506c4c441c390090843200d60d0']
for c in v['clients']:
 if c['id'] in ids:c['enabled']=False
t=p.with_suffix('.tmp');t.write_text(json.dumps(v));t.chmod(0o600);t.replace(p)
print('All package QA devices revoked')
