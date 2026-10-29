import json
from pathlib import Path
base=Path('/opt/monitor/geo-content/runtime')
bad=[];total=0
for p in base.glob('runs/*/approved/*/*/*/draft.md'):
 text=p.read_text();lines=text.strip().splitlines();first=lines[0] if lines else '';total+=1
 if not first.startswith('# ') or len(first)>100:
  receipt=json.loads((p.parent/'receipt.json').read_text());bad.append({'path':str(p),'first':first,'headings':[l for l in lines if l.startswith('#')][:4],'receipt':receipt,'excerpt':text[:1100]})
print(json.dumps({'total':total,'bad_count':len(bad),'samples':bad[:4]},ensure_ascii=False))
Path('/tmp/article-title-audit.json').write_text(json.dumps(bad,ensure_ascii=False,indent=2))
