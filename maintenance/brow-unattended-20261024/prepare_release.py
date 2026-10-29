"""Prepare a minimal release on top of live code, not unrelated local candidates."""
import json,shutil,subprocess,os
from pathlib import Path
BASE=Path(__file__).resolve().parent;stage=BASE/'validation';live=Path('/opt/monitor/geo-content');release=BASE/'release'
names=['engine/geo_source_cards/'+x+'.py' for x in ('api_worker','auto_repair','daily_editorial','deepseek_api')]
names += ['creation/'+x+'.py' for x in ('article_export','editorial_status','quality_repair','runtime','studio')]
names += [str(p.relative_to(stage)) for p in (stage/'engine/geo_source_cards/rewrite_v2').glob('*.py')]
for folder in ('engine/geo_source_cards','creation'):
    for source in (live/folder).rglob('*.py'):
        if '__pycache__' in source.parts:continue
        target=release/source.relative_to(live);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
for name in names:
    target=release/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(stage/name,target)
for source in (stage/'engine/tests').glob('*.py'):
    target=release/'engine/tests'/source.name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
for source in (stage/'creation').glob('test_*.py'):shutil.copy2(source,release/'creation'/source.name)
shutil.copy2(stage/'validate.py',release/'validate.py')
(BASE/'release-files.json').write_text(json.dumps(names,indent=2))
result=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B',str(release/'validate.py')])
raise SystemExit(result.returncode)
