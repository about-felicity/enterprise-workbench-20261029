"""Package final Linux evidence without changing code, state or ledger."""
import hashlib,json,os,zipfile
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-structure-recovery-v3-final')
result=json.loads((D/'linux-results.json').read_text());assert result['production_and_ledger_unchanged'] and result['probe_exit']==0
assert sum(r['tests'] for r in result['results'])==453 and all(r['exit']==0 for r in result['results'])
manifest=json.loads((D/'manifest.json').read_text())
for name,h in manifest['execution_source_sha256'].items():assert hashlib.sha256((D/'isolated/current'/name).read_bytes()).hexdigest()==h
paths=[p for p in D.glob('*.json')]+[p for p in D.glob('*launcher.log')]+list((D/'logs').glob('*'))
paths += [p for p in (D/'probe-work').rglob('*') if p.is_file() and p.suffix=='.json']
archive=Path('/tmp/structure-recovery-v3-final-evidence.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in paths:z.write(p,p.relative_to(D))
os.chmod(archive,0o644)
print(json.dumps({'files':len(paths),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'tests':453,'ledger_rows':result['ledger_rows'],'protected_files':result['protected_file_count']}))
