import json,sys,unittest
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated';sys.path[:0]=[str(S/'engine'),str(S)]
suite=unittest.TestLoader().discover(str(S/'creation'),pattern='test*.py',top_level_dir=str(S))
with (D/'creation-regressions.log').open('w',encoding='utf8') as stream:
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
out={'type':'offline_mock_regressions','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'blocked_network_attempts':len(offline_guard.blocked),'new_api_calls':0}
(D/'creation-regressions.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out));sys.exit(not result.wasSuccessful())
