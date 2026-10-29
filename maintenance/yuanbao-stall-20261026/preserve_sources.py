"""Refresh only files whose deployed hashes were verified in this release."""
import hashlib,json,shutil,zipfile
from pathlib import Path
W=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
release=W/'geo-monitor-deploy/releases/20261015/unified-current'
deployed=json.loads((D/'verification/deployed.json').read_text('utf8'))
mapping={}
for row in deployed['files']:
 target=row['server']
 if '/redroid-yuanbao/' in target:source='yuanbao-deploy/'+target.split('/redroid-yuanbao/')[1]
 elif '/geo-batch-code/' in target:source='redroid-deploy/'+target.split('/geo-batch-code/')[1]
 else:raise ValueError(target)
 assert hashlib.sha256((W/source).read_bytes()).hexdigest()==row['sha256'],source
 mapping[source]=target
paths=[release/'manifest.json',release/'source.zip',W/'source-snapshot/local-manifest.json',W/'source-snapshot/production-manifest.json']
back=D/'snapshot-before';back.mkdir(exist_ok=True)
for path in paths:
 dest=back/(path.parent.name+'-'+path.name)
 if not dest.exists():shutil.copy2(path,dest)
manifest=json.loads(paths[0].read_text('utf8'));local=json.loads(paths[2].read_text('utf8'));prod=json.loads(paths[3].read_text('utf8'))
for source,target in mapping.items():
 raw=(W/source).read_bytes();digest=hashlib.sha256(raw).hexdigest()
 row={'source':source,'server':target,'sha256':digest,'bytes':len(raw)}
 for obj in [manifest,local]:
  found=[r for r in obj['files'] if r.get('source')==source and r['server']==target]
  if found:found[0].update(row)
  else:obj['files'].append(row.copy())
 snapshot='server/'+target.lstrip('/')
 row={'snapshot':snapshot,'server':target,'sha256':digest,'bytes':len(raw)}
 found=[r for r in prod['files'] if r['server']==target]
 if found:found[0].update(row)
 else:prod['files'].append(row)
 for target_path in [W/'source-snapshot/local'/source,W/'source-snapshot'/snapshot]:
  target_path.parent.mkdir(parents=True,exist_ok=True);target_path.write_bytes(raw)
tmp=release/'source.delete-fix.tmp'
with zipfile.ZipFile(paths[1]) as old,zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as out:
 for info in old.infolist():
  if info.filename not in mapping:out.writestr(info,old.read(info.filename))
 for source in mapping:out.writestr(source,(W/source).read_bytes())
tmp.replace(paths[1]);manifest['zip_sha256']=hashlib.sha256(paths[1].read_bytes()).hexdigest();local['zip_sha256']=manifest['zip_sha256']
for path,value in [(paths[0],manifest),(paths[2],local),(paths[3],prod)]:
 original=path.read_bytes();newline='\r\n' if b'\r\n' in original else '\n'
 text=json.dumps(value,ensure_ascii=False,indent=2).replace('\n',newline)
 if original.endswith(b'\n'):text+=newline
 path.write_bytes(text.encode('utf8'))
print(json.dumps({'updated':mapping,'mapping_count':len(manifest['files'])}))
