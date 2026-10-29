import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
from geo_source_cards.pipeline_control import pause
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');s=runtime.read(M/'task.json');task=runtime.read(studio.day_path(s['plan_id'],s['date']));jobs=[]
for jid in task['jobs'].values():
 root=runtime.job_root(jid);c=runtime.read(root/'control.json')
 if not c.get('paused'):pause(root,'maintenance_drain','本批测试章节顺序修复；允许已发送请求收尾，保留响应，不重发')
 a=runtime.read(root/'api/active.json');run=root/'api/runs'/a.get('run_id','no-run')
 calls=[runtime.read(run/p).get('state') for p in ('call/api_state.json','logic-call/api_state.json') if (run/p).exists()]
 jobs.append({'job':jid,'active':a.get('state'),'calls':calls,'safe':not any(v in {'REQUESTING','REQUEST_UNKNOWN'} for v in calls)})
print(json.dumps(jobs))
