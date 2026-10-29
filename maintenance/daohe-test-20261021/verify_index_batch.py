"""Verify all manifest blobs in one Git batch without newline conversion."""
import json,subprocess,hashlib
from pathlib import Path
W=Path(__file__).resolve().parents[2];S=W/'source-snapshot';expected={}
for name in ('production-manifest.json','client-manifest.json'):
 for r in json.loads((S/name).read_text('utf-8'))['files']:expected['source-snapshot/'+r['snapshot']]=r['sha256']
for r in json.loads((S/'local-manifest.json').read_text('utf-8'))['files']:expected['source-snapshot/local/'+r['source']]=r['sha256']
names=list(expected);raw=subprocess.run(['git','cat-file','--batch'],input=''.join(':'+p+'\n' for p in names).encode(),cwd=W,capture_output=True,check=True).stdout
offset=0;errors=[]
for p in names:
 end=raw.index(b'\n',offset);header=raw[offset:end].split();assert header[1]==b'blob',p
 size=int(header[-1]);data=raw[end+1:end+1+size];offset=end+size+2
 if hashlib.sha256(data).hexdigest()!=expected[p]:errors.append(p)
result={'manifest_blobs':len(names),'git_index_hashes_verified':not errors,'errors':errors}
(Path(__file__).parent/'index-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(result));assert not errors
