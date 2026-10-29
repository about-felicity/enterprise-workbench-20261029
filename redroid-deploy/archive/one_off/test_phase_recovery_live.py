
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import pathlib,time,json
from unattended_core import Queue,lookup
from unattended_worker import Android,databases
root=pathlib.Path('/home/user/redroid-doubao');q=Queue(root/'hpe14-acceptance/tasks.sqlite');container='doubao-hpe14-13-test'
id='23588c18-debd-5040-a73a-446eadef9333';t=dict(q.db.execute('select * from tasks where task_id=?',(id,)).fetchone())
assert t['state']=='prepared'
a=Android('127.0.0.1:5557',str(root/'linux-tools/platform-tools/adb'))
assert a.device(resourceId='com.larus.nova:id/input_text').get_text()==t['wire_question']
assert lookup(databases(container),t)['status']=='absent'
with q.db:q.event(id,'operator_verified_unsent_draft','Controlled legacy-worker interruption; unchanged exact draft and no App request observed')
q.click_attempt(id)
a.tap(a.device(resourceId='com.larus.nova:id/action_send'))
print('Finished verified legacy draft once:',id,flush=True)
for _ in range(36):
 result=lookup(databases(container),t)
 if result['status']=='complete':q.complete(id,result);break
 time.sleep(5)
else:raise RuntimeError('Legacy draft answer did not complete; preserve state')
t=dict(q.db.execute("select * from tasks where state='pending' order by rowid limit 1").fetchone())
a.ready();q.prepare(t['task_id'],protocol='phase-v2')
a.device(resourceId='com.larus.nova:id/input_text').set_text(t['wire_question'])
assert a.device(resourceId='com.larus.nova:id/input_text').get_text()==t['wire_question']
assert q.may_finish_unsent(t['task_id'])
(root/'hpe14-acceptance/phase-v2-interruption.json').write_text(json.dumps({'legacy_draft_recovered':id,'v2_interrupted_before_click_task':t['task_id'],'injected_time':time.time()},indent=2))
print('Fault injected before first click; restart must safely continue:',t['task_id'],flush=True)
