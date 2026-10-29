"""Strict offline runner; sync only the disposable execution copy."""
import hashlib,json,os,platform,shutil,sys,unittest
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;mode=sys.argv[1];S=D/'isolated/current'
for p in (D/'candidate-source').rglob('*.py'):
 relative=p.relative_to(D/'candidate-source');dest=S/('' if relative.parts[0]=='creation' else 'engine')/relative
 dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
os.environ['GEO_OFFLINE_FIXTURES']=str(D/'fixtures');os.environ['GEO_OFFLINE_ALLOW_LOOPBACK']='1'
sys.path[:0]=[str(S/'engine'),str(S),str(D)]
loader=unittest.TestLoader()
if mode=='special':suite=loader.loadTestsFromName('tests.test_b2_repair_entry')
elif mode=='prior':suite=loader.loadTestsFromName('tests.test_b1_b2_offline')
elif mode=='edges':suite=loader.loadTestsFromName('test_acceptance_edges')
elif mode=='engine':suite=loader.loadTestsFromNames(['tests.'+name for name in json.loads((D/'engine-modules.json').read_text())])
elif mode=='creation':suite=loader.discover(str(S/'creation'),pattern='test*.py',top_level_dir=str(S))
else:raise ValueError(mode)
prefix=platform.system().lower()+'-'+mode;folder=D/'logs';folder.mkdir(exist_ok=True)
with (folder/(prefix+'.log')).open('w',encoding='utf8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
out={'suite':mode,'platform':platform.platform(),'python':sys.version,'tests':result.testsRun,'failures':[str(t) for t,e in result.failures],
 'errors':[str(t) for t,e in result.errors],'skips':[(str(t),reason) for t,reason in result.skipped],
 'blocked_network_attempts':len(offline_guard.blocked),'real_api_calls':0,'balance_calls':0,'external_business_service_calls':0}
(folder/(prefix+'.json')).write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out));sys.exit(not result.wasSuccessful())
