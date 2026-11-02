import hashlib,json,subprocess
from pathlib import Path
base=Path('/opt/monitor/geo-content');studio=base/'studio'
def read(p):
 try:return json.loads(p.read_text())
 except FileNotFoundError:return {}
for name in ['materials.py','studio.py','supplement.py','client.py','source_cache.py']:
 p=base/'creation'/name;print('CODE',name,hashlib.sha256(p.read_bytes()).hexdigest())
print('POLICY',json.dumps(read(base/'runtime/supplement_policy.json'),ensure_ascii=False))
spray='plan-4c988f3863344f52aff3aa2b1f96beb2'
for p in sorted((studio/'capture'/spray).rglob('results.jsonl')):
 raw=p.read_bytes();lines=raw.decode('utf-8-sig').splitlines();bad=[]
 for n,line in enumerate(lines,1):
  if not line.strip():continue
  try:json.loads(line)
  except (ValueError,UnicodeError) as e:bad.append({'line':n,'bytes':len(line),'error':str(e)})
 if bad:
  physical=raw.decode('utf-8-sig').split('\n');physical_bad=[]
  for n,line in enumerate(physical,1):
   if line.strip():
    try:json.loads(line)
    except ValueError as e:physical_bad.append({'line':n,'error':str(e)})
  print('BAD_JSONL',json.dumps({'path':str(p),'bytes':len(raw),'lines':len(lines),'bad':bad[:4],'physical_bad':physical_bad[:4],'physical_lines':len(physical),'mtime':p.stat().st_mtime},ensure_ascii=False))
for p in (studio/'days').glob('*/*.supplement-state'):
 s=read(p)
 if s.get('status') in ['capturing','checking_materials','waiting','waiting_verification']:print('SUPPLEMENT',json.dumps({'path':str(p),**s},ensure_ascii=False))
for jid,rid in [('creation-1793397144-33d4e53e','c06ff7ed0ce26c6097e4fb97'),('creation-1793400211-f3855aab','e6154840a210bc391de15473')]:
 run=base/'runtime/runs'/jid/'api/runs'/rid
 for p in run.rglob('*'):
  if p.is_file() and p.name in ['api_state.json','answer.json']:
   text=p.read_text();print('RESPONSE',str(p),text[:2500] if p.name=='api_state.json' else json.dumps({'bytes':len(text),'head':text[:250],'tail':text[-250:]},ensure_ascii=False))
 print('FILES',jid,[str(p.relative_to(run)) for p in run.rglob('*') if p.is_file()][:35])
