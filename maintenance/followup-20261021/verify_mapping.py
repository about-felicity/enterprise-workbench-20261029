"""Read-only SHA verification of every explicitly mapped production file."""
import hashlib
import json
import argparse
from pathlib import Path
default=Path(__file__).with_name('manifest.json')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--manifest',type=Path,default=default if default.exists() else Path('/tmp/geo-current-manifest.json'))
args=parser.parse_args()
manifest=json.loads(args.manifest.read_text())
result=[]
for item in manifest['files']:
    path=Path(item['server'])
    actual=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    result.append({'source':item['source'],'server':item['server'],'expected':item['sha256'],'actual':actual,'match':actual==item['sha256']})
report={'files':len(result),'matched':sum(r['match'] for r in result),'mismatches':[r for r in result if not r['match']]}
Path('/tmp/geo-source-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
raise SystemExit(bool(report['mismatches']))
