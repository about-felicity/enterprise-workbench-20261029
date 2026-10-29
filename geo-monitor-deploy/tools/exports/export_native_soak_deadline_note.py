"""Append deadline intent evidence; no queue or service mutations."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from contextlib import closing
import json
from pathlib import Path
import sqlite3

out=Path('/home/user/redroid-doubao/doubao-soak2h-1792030883-export')
p=out/'summary.json'
s=json.loads(p.read_text())
deadline=1792038083.3113985
for model,value in s['models'].items():
    dbpath=Path('/home/user/redroid-doubao/batches')/value['batch']/'tasks.sqlite'
    with closing(sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)) as db:
        details=[]
        for task_id,clicked in db.execute("select task_id,time from events where event='send_click_intent_committed' and time>=?",(deadline,)):
            intent=db.execute("select max(time) from events where task_id=? and event='send_intent_committed' and time<=?",(task_id,clicked)).fetchone()[0]
            assert intent and intent < deadline
            details.append({'click_seconds_after_deadline':clicked-deadline,'send_intent_seconds_before_deadline':deadline-intent})
        value['deadline_click_evidence']=details
s['deadline_service_started_beijing']='2026-10-15T12:21:23+08:00'
s['deadline_service_exited_beijing']='2026-10-15T12:21:24+08:00'
s['unrelated_baidu_status_at_final_check']={
    'state':'needs_attention','captured':84,'processed':84,'unique_processed':28,'duplicates':56,'unavailable':6,
    'task_state':'failed_deferred','attempts':2,
    'confirmed_error':'百度 AI 卡片未完整呈现，已保存页面观测，不能用文心卡片代替',
    'action':'Evidence retained; did not reset exhausted retry or resend during native-only acceptance.'}
p.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'deadline_click_evidence':{m:v['deadline_click_evidence'] for m,v in s['models'].items()},'updated_summary':str(p)},ensure_ascii=False))
