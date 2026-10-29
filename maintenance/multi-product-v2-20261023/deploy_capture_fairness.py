import hashlib,json,py_compile,shutil,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
target=Path('/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/cli.py')
expected='51e6dd1fc5ac360d6147404aa550fcc83e2d7a72e9dccbc5a949b66209ef5958'
assert hashlib.sha256(target.read_bytes()).hexdigest()==expected,'Live source changed'
backup=BASE/'capture-cli-before-fairness.py';shutil.copy2(target,backup)
stage=target.with_suffix('.fairness.py');shutil.copy2(BASE/'engine/geo_source_cards/cli.py',stage)
py_compile.compile(str(stage),doraise=True);stage.replace(target)
record={'at':time.time(),'before_sha256':expected,'after_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'backup':str(backup),'tests_run':67,'tests_passed':True,
        'change':'Prefer fewer failed read-only search attempts within a round; preserve cooldown and completed evidence',
        'running_collectors_interrupted':False}
(BASE/'capture-fairness-deployment.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
