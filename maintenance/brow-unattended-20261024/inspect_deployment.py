import difflib,hashlib,json
from pathlib import Path
BASE=Path(__file__).resolve().parent
stage=BASE/'validation';live=Path('/opt/monitor/geo-content')
rows=[];diffs=[]
for folder in ('engine/geo_source_cards','creation'):
    for candidate in sorted((stage/folder).rglob('*.py')):
        if '__pycache__' in candidate.parts or candidate.name.startswith('test_'):continue
        relative=candidate.relative_to(stage);target=live/relative
        if target.exists() and candidate.read_bytes()==target.read_bytes():continue
        old=target.read_text() if target.exists() else ''
        new=candidate.read_text()
        diff=list(difflib.unified_diff(old.splitlines(),new.splitlines(),fromfile='live/'+str(relative),tofile='candidate/'+str(relative),n=3))
        rows.append({'path':str(relative),'new':not target.exists(),'diff_lines':len(diff),
            'live_sha256':hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None,
            'candidate_sha256':hashlib.sha256(candidate.read_bytes()).hexdigest()})
        diffs.extend(diff)
(BASE/'deployment-diff.json').write_text(json.dumps(rows,indent=2))
(BASE/'deployment.diff').write_text('\n'.join(diffs))
print(json.dumps(rows,indent=2))
