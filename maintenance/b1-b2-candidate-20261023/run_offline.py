"""Local only. Never load a real API key or contact any external service."""
import json,os,shutil,sys,unittest
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated';C=D/'candidate-source'
for package,target in [('geo_source_cards',S/'engine/geo_source_cards'),('creation',S/'creation'),('tests',S/'engine/tests')]:
 for p in (C/package).glob('*.py'):shutil.copyfile(p,target/p.name)
os.environ['GEO_OFFLINE_FIXTURES']=str(D/'fixtures');sys.path[:0]=[str(S/'engine'),str(S)]
from geo_source_cards import structure_analyzer as a,article_compiler as c,review_quality as q
def read(p):return json.loads(Path(p).read_text('utf8'))
# First: replay the exact stored structures and the old B2 cache. No fake model
# is involved in this before/after check.
replay=[]
for label in ('review02','ranking01'):
 structure,k,p=[read(D/'fixtures'/(label+'-'+n+'.json')) for n in ('article_structure','knowledge','product')]
 out=a.bind(c.compile_article(k,p),structure);own=next(v for v in out['sections'] if v['subject']==p['name'])
 assert own['structure_binding']['role']=='subject'
 replay.append({'sample':label,'own_slot':own['id'],'source_section':own['structure_id'],'source_role':own['structure_task']['role'],
 'feasibility':out['feasibility']['status'],'roles':a.normalize_roles(structure),'paid_requests':0})
prior=read(D.parent/'candidate-validation-20261023/replay-results.json')
old_review=Path(prior['samples'][0]['work_dir']).parent/'arbitration/review'
new_review=S/'historical-cache-replay/review'
if not new_review.exists():shutil.copytree(old_review.parent,new_review.parent)
old_result=read(new_review/'answer.json')
class NoRequests:
 def __getattr__(self,name):raise AssertionError('No model request allowed during historical replay')
try:q.process(NoRequests(),new_review,old_result,{})
except ValueError as e:cache={'old_cache_rejected':True,'reason':str(e),'new_requests':0}
else:raise AssertionError('Old source-unbound cache reused')
(D/'real-material-replay.json').write_text(json.dumps({'type':'zero_call_replay','samples':replay,'old_cache':cache},ensure_ascii=False,indent=2),encoding='utf8')
mode=sys.argv[1] if len(sys.argv)>1 else 'new'
if mode=='new':suite=unittest.TestLoader().loadTestsFromName('tests.test_b1_b2_offline')
elif mode=='engine':
 import ast
 tree=ast.parse((D.parent/'candidate-validation-20261023/regressions.py').read_text('utf8'))
 modules=next(ast.literal_eval(n.value) for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='modules' for t in n.targets))
 suite=unittest.TestLoader().loadTestsFromNames(['tests.'+m for m in modules])
elif mode=='creation':suite=unittest.TestLoader().discover(str(S/'creation'),pattern='test*.py',top_level_dir=str(S))
else:raise ValueError('Unknown suite')
with (D/(mode+'-tests.log')).open('w',encoding='utf8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
value={'suite':mode,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
 'external_network_attempts':len(offline_guard.blocked),'real_api_calls':0,'synthetic_routing_not_real_model_acceptance':True}
(D/(mode+'-tests.json')).write_text(json.dumps(value,indent=2),encoding='utf8');print(json.dumps(value));sys.exit(not result.wasSuccessful())
