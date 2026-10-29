import json,sys,unittest
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated/baseline';sys.path[:0]=[str(S/'engine'),str(S)]
suite=unittest.TestLoader().discover(str(S/'creation'),pattern='test*.py',top_level_dir=str(S))
with (D/'creation-baseline-tests.log').open('w',encoding='utf8') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
out={'tests':r.testsRun,'failures':[str(t) for t,e in r.failures],'errors':[str(t) for t,e in r.errors],
     'external_network_attempts':len(offline_guard.blocked),'api_calls':0}
(D/'creation-baseline-tests.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out))
