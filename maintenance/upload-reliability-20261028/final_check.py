import hashlib,json,subprocess,sys
from pathlib import Path
root=Path('/opt/monitor/geo-content/studio')
base=Path('/opt/monitor/geo-content/maintenance/upload-reliability-20261028')
release=json.loads((base/'release.json').read_text());assert all(hashlib.sha256(Path(r['server']).read_bytes()).hexdigest()==r['sha256'] for r in release['files'])
records=[r for p in (root/'library').glob('library-*.json') if not (r:=json.loads(p.read_text())).get('merged_into')];images=list((root/'images').glob('image-*/metadata.json'))
print(json.dumps({'verified_files':len(release['files']),'libraries':len(records),'temporary_libraries':[r['name'] for r in records if r['name'].startswith('临时上传验收-')],'products':len(list((root/'products').glob('product-*.json'))),'images':len(images)},ensure_ascii=False))
print(subprocess.run(['journalctl','-u','geo-content-api','-n','8','--no-pager'],capture_output=True,text=True).stdout)
