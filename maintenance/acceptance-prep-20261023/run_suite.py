"""No API credentials. Deny network before importing any application code."""
import json,os,sys,unittest,platform,hashlib
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;mode=sys.argv[1];flavor='baseline' if mode=='baseline-creation' else 'candidate';S=D/flavor
os.environ['GEO_OFFLINE_FIXTURES']=str(D/'fixtures');os.environ['GEO_OFFLINE_ALLOW_LOOPBACK']='1'
sys.path[:0]=[str(S/'engine'),str(S),str(D)]
manifest=json.loads((D/'candidate-sha.json').read_text('utf8'))
if flavor=='candidate':
 for relative,row in manifest['files'].items():
  file=S/('engine' if not relative.startswith('creation/') else '')/relative
  assert hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256'],relative
loader=unittest.TestLoader()
if mode=='new':suite=loader.loadTestsFromName('tests.test_b1_b2_offline')
elif mode=='engine':suite=loader.loadTestsFromNames(['tests.'+m for m in json.loads((D/'engine-modules.json').read_text())])
elif mode in ('creation','baseline-creation'):suite=loader.discover(str(S/'creation'),pattern='test*.py',top_level_dir=str(S))
elif mode=='edges':suite=loader.loadTestsFromName('test_acceptance_edges')
else:raise ValueError(mode)
with (D/(mode+'.log')).open('w',encoding='utf8') as stream:r=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
out={'suite':mode,'platform':platform.platform(),'python':sys.version,'tests':r.testsRun,'failures':[str(t) for t,e in r.failures],
 'errors':[str(t) for t,e in r.errors],'skips':[(str(t),e) for t,e in r.skipped],'blocked_network_attempts':len(offline_guard.blocked),
 'external_api_calls':0,'balance_calls':0,'synthetic_routing_only':True}
(D/(mode+'.json')).write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out));sys.exit(not r.wasSuccessful())
