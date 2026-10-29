import ast,hashlib,json,shutil,sys,unittest,zipfile
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261024-doubao-stall');S=D/'candidate';LIVE=Path('/home/user/redroid-doubao/geo-batch-code')
if not S.exists():shutil.copytree(LIVE,S,ignore=shutil.ignore_patterns('__pycache__'))
with zipfile.ZipFile('/tmp/doubao24-changes.zip') as z:z.extractall(S)
(S/'tests/__init__.py').touch()
sys.path[:0]=[str(S),str(LIVE),'/home/user/redroid-yuanbao']
for name in ['question_only_adapters.py','draft_submission_recovery.py']:ast.parse((S/name).read_text())
suite=unittest.defaultTestLoader.discover(str(S/'tests'),pattern='test_*.py',top_level_dir=str(S))
result=unittest.TextTestRunner(verbosity=1).run(suite)
out={'tests':result.testsRun,'success':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors)}
(D/'tests.json').write_text(json.dumps(out));print(json.dumps(out))
if not result.wasSuccessful():raise SystemExit(1)
from draft_submission_recovery import exact_draft,absent_proof
before=json.loads((D/'before.json').read_text());after=json.loads((D/'after.json').read_text());xml=(D/'current.xml').read_text()
assert absent_proof(before,after) is not None
assert not exact_draft(xml,'推荐一款睫毛增长液') and exact_draft(xml,'推荐一款睫毛增长液\n')
names=['question_only_adapters.py','draft_submission_recovery.py']
manifest={n:{'before':hashlib.sha256((LIVE/n).read_bytes()).hexdigest(),'after':hashlib.sha256((S/n).read_bytes()).hexdigest()} for n in names}
(D/'manifest.json').write_text(json.dumps(manifest,indent=2));print('Real incident replay passed: exact draft plus one newline; all native request sets unchanged')
