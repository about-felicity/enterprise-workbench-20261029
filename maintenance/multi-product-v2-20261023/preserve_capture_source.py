"""Refresh only the deployed collector CLI; keep undeployed V2 candidates out of production snapshots."""
import hashlib,json,shutil,zipfile
from pathlib import Path
W=Path(__file__).resolve().parents[2];D=Path(__file__).resolve().parent
release=W/'geo-monitor-deploy/releases/20261015/unified-current'
source='geo-source-card-collectors/geo_source_cards/cli.py'
target='/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/cli.py'
data=(W/source).read_bytes();sha=hashlib.sha256(data).hexdigest()
assert sha==hashlib.sha256((D/'verified-live-cli.py').read_bytes()).hexdigest()
paths=[release/'manifest.json',release/'source.zip',W/'source-snapshot/local-manifest.json',W/'source-snapshot/production-manifest.json']
back=D/'snapshot-before';back.mkdir(exist_ok=True)
for path in paths:
    dest=back/(path.parent.name+'-'+path.name)
    if not dest.exists():shutil.copy2(path,dest)
manifest=json.loads(paths[0].read_text('utf8'));local=json.loads(paths[2].read_text('utf8'));prod=json.loads(paths[3].read_text('utf8'))
for obj in (manifest,local):
    row=next(r for r in obj['files'] if r.get('source')==source and r['server']==target)
    row.update(sha256=sha,bytes=len(data))
row=next(r for r in prod['files'] if r['server']==target)
row.update(sha256=sha,bytes=len(data))
for dest in [W/'source-snapshot/local'/source,W/'source-snapshot'/row['snapshot']]:
    dest.write_bytes(data)
temp=release/'source.capture23.tmp'
with zipfile.ZipFile(paths[1]) as old,zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as out:
    for info in old.infolist():out.writestr(info,data if info.filename==source else old.read(info.filename))
temp.replace(paths[1]);manifest['zip_sha256']=hashlib.sha256(paths[1].read_bytes()).hexdigest();local['zip_sha256']=manifest['zip_sha256']
for path,value in [(paths[0],manifest),(paths[2],local),(paths[3],prod)]:
    old=path.read_bytes();newline='\r\n' if b'\r\n' in old else '\n'
    body=json.dumps(value,ensure_ascii=False,indent=2).replace('\n',newline)
    if old.endswith(b'\n'):body+=newline
    path.write_bytes(body.encode('utf8'))
(D/'snapshot-update.json').write_text(json.dumps({'source':source,'server':target,'sha256':sha,'production_code_verified':True},indent=2))
print('Updated only the deployed collector CLI: '+sha)
