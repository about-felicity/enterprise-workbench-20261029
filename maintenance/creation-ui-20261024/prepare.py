import hashlib,json,shutil,sys,zipfile
from pathlib import Path
D=Path('/tmp/geo-creation-ui-20261024');L=Path('/opt/monitor/geo-content');C=D/'candidate'
D.mkdir(exist_ok=True)
if C.exists():raise RuntimeError('Candidate exists')
shutil.copytree(L/'creation',C/'creation',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(L/'engine',C/'engine',ignore=shutil.ignore_patterns('__pycache__'))
with zipfile.ZipFile(D/'changes.zip') as z:z.extractall(C)
files=['panel.html','studio.py','runtime.py']
(D/'baseline.json').write_text(json.dumps({n:hashlib.sha256((L/'creation'/n).read_bytes()).hexdigest() for n in files}))
sys.path[:0]=[str(C),str(C/'engine')]
import unittest
suite=unittest.defaultTestLoader.loadTestsFromNames(['creation.test_task_controls','creation.test_studio','creation.test_workflow','creation.test_download_service','creation.test_materials','creation.test_unattended_recovery','creation.test_worker_recovery'])
result=unittest.TextTestRunner(verbosity=1).run(suite)
(D/'tests.json').write_text(json.dumps({'tests':result.testsRun,'success':result.wasSuccessful(),'failures':len(result.failures),'errors':len(result.errors)}))
raise SystemExit(not result.wasSuccessful())
