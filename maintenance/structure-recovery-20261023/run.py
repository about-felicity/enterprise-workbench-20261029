"""Isolated zero-service regression runner; no model credentials or API calls."""
import json,os,platform,shutil,sys,unittest
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated/current';mode=sys.argv[1]
for p in (D/'candidate-source').rglob('*.py'):
 r=p.relative_to(D/'candidate-source');out=S/('' if r.parts[0]=='creation' else 'engine')/r
 out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,out)
os.environ['GEO_OFFLINE_FIXTURES']=str(D/'fixtures');os.environ['GEO_STRUCTURE_FIXTURES']=str(D);os.environ['GEO_OFFLINE_ALLOW_LOOPBACK']='1'
sys.path[:0]=[str(S/'engine'),str(S),str(D)]
loader=unittest.TestLoader()
if mode=='special':suite=loader.loadTestsFromName('tests.test_structure_recovery')
elif mode=='prior':suite=loader.loadTestsFromNames(['tests.test_b1_b2_offline','tests.test_b2_repair_entry','test_acceptance_edges'])
elif mode=='engine':suite=loader.loadTestsFromNames(['tests.'+n for n in json.loads((D/'engine-modules.json').read_text())])
elif mode=='creation':suite=loader.discover(str(S/'creation'),pattern='test*.py',top_level_dir=str(S))
else:raise ValueError(mode)
logs=D/'logs';logs.mkdir(exist_ok=True);prefix=platform.system().lower()+'-'+mode
with (logs/(prefix+'.log')).open('w',encoding='utf8') as out:result=unittest.TextTestRunner(stream=out,verbosity=2).run(suite)
summary={'suite':mode,'platform':platform.platform(),'python':sys.version,'tests':result.testsRun,'failures':[str(t) for t,e in result.failures],
 'errors':[str(t) for t,e in result.errors],'skips':[(str(t),why) for t,why in result.skipped],'blocked_network_attempts':len(offline_guard.blocked),'real_api_calls':0,'balance_queries':0,'external_service_calls':0}
(logs/(prefix+'.json')).write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(summary));sys.exit(not result.wasSuccessful())
