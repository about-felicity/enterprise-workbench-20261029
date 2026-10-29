"""Update only the two deployed files in current source/recovery snapshots."""
import hashlib,json,shutil,zipfile
from pathlib import Path
W=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
release=W/'geo-monitor-deploy/releases/20261015/unified-current'
deployment=json.loads((D/'deployed.json').read_text('utf8'));mapping={}
for row in deployment['files']:
 target=row['server'];assert target.startswith('/home/user/redroid-doubao/geo-batch-code/')
 source='redroid-deploy/'+target.split('/home/user/redroid-doubao/geo-batch-code/')[1]
 assert hashlib.sha256((W/source).read_bytes()).hexdigest()==row['sha256']
 mapping[source]=target
paths=[release/'manifest.json',release/'source.zip',W/'source-snapshot/local-manifest.json',W/'source-snapshot/production-manifest.json']
back=D/'snapshot-before';back.mkdir(exist_ok=True)
for p in paths:
 dest=back/(p.parent.name+'-'+p.name)
 if not dest.exists():shutil.copy2(p,dest)
manifest=json.loads(paths[0].read_text('utf8'));local=json.loads(paths[2].read_text('utf8'));prod=json.loads(paths[3].read_text('utf8'))
for source,target in mapping.items():
 raw=(W/source).read_bytes();digest=hashlib.sha256(raw).hexdigest();row={'source':source,'server':target,'sha256':digest,'bytes':len(raw)}
 for obj in (manifest,local):
  found=[r for r in obj['files'] if r.get('source')==source and r['server']==target]
  if found:found[0].update(row)
  else:obj['files'].append(row.copy())
 snapshot='server/'+target.lstrip('/');row={'snapshot':snapshot,'server':target,'sha256':digest,'bytes':len(raw)}
 found=[r for r in prod['files'] if r['server']==target]
 if found:found[0].update(row)
 else:prod['files'].append(row)
 for p in [W/'source-snapshot/local'/source,W/'source-snapshot'/snapshot]:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
temp=release/'source.doubao24.tmp'
with zipfile.ZipFile(paths[1]) as old,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as out:
 for info in old.infolist():
  if info.filename not in mapping:out.writestr(info,old.read(info.filename))
 for source in mapping:out.writestr(source,(W/source).read_bytes())
temp.replace(paths[1]);manifest['zip_sha256']=hashlib.sha256(paths[1].read_bytes()).hexdigest();local['zip_sha256']=manifest['zip_sha256']
for p,value in [(paths[0],manifest),(paths[2],local),(paths[3],prod)]:
 original=p.read_bytes();newline='\r\n' if b'\r\n' in original else '\n';text=json.dumps(value,ensure_ascii=False,indent=2).replace('\n',newline)
 if original.endswith(b'\n'):text+=newline
 p.write_bytes(text.encode('utf8'))
print(json.dumps({'updated':mapping,'mapping_count':len(manifest['files'])}))
