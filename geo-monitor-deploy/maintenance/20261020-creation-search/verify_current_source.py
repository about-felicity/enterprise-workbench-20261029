import hashlib,json
from pathlib import Path
manifest=json.loads(Path('/opt/monitor/geo-capture/maintenance/20261015-unified/current-manifest.json').read_text())
rows=[]
for item in manifest['files']:
    p=Path(item['server'])
    rows.append({'source':item['source'],'server':str(p),'matches':p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']})
out={'files':len(rows),'matched':sum(r['matches'] for r in rows),'mismatches':[r for r in rows if not r['matches']]}
Path('/tmp/brow-current-source-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
