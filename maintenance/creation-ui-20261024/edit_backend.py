from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]/'geo-monitor-deploy/creation'
def edit(name,changes):
 p=ROOT/name;s=p.read_text('utf8')
 for old,new in changes:
  assert old in s,(name,old[:80]);s=s.replace(old,new)
 p.write_bytes(s.replace('\n','\r\n').encode('utf8'))
edit('studio.py',[
 ("def plans():return [runtime.read(p) for p in sorted((ROOT/'plans').glob('plan-*.json'))]", "def plans():return [v for p in sorted((ROOT/'plans').glob('plan-*.json')) if not (v:=runtime.read(p)).get('deleted_at')]"),
 ('def plan(value):','def plan(value,include_deleted=False):'),
 (" return runtime.read(p)\ndef capture_root", " result=runtime.read(p)\n if result.get('deleted_at') and not include_deleted:raise ValueError('任务已删除，不能再修改或执行')\n return result\ndef capture_root"),
 ("def capture_root(value):\n p=plan(value)","def capture_root(value):\n p=plan(value,include_deleted=True)"),
 ('def day_control(payload,pause):', '''TERMINAL_JOBS={'complete','complete_with_failures','complete_with_shortfall','blocked_insufficient_sources','blocked_no_media_articles'}
TERMINAL_DAYS={'complete','capture_only_complete','complete_with_failures','insufficient_materials'}

def day_actions(state):
 if state in {'paused','needs_attention','waiting_login'}:return ['day_resume']
 if state in {'collecting','creating','waiting_for_geo','waiting_writing'}:return ['day_pause']
 return []

def delete_plan(payload):
 """Tombstone first; drain sent work and preserve source, output and cost history."""
 p=plan(payload.get('plan_id'),include_deleted=True);value=p['plan_id'];root=capture_root(value)
 atomic_json(ROOT/'plans'/(value+'.json'),{**p,'enabled':False,'deleted_at':p.get('deleted_at') or time.time(),'updated_at':time.time()})
 with process_lock(root/'settings.lock',blocking=True):
  cfg=runtime.read(root/'settings.json');cfg.update(enabled=False,paused=True);cfg.pop('requested_day',None)
  atomic_json(root/'settings.json',cfg)
 for path in (ROOT/'days').glob('*/'+value+'.json'):
  with process_lock(path.with_suffix('.lock'),blocking=True):
   task=runtime.read(path);task.update(paused=True,deleted=True);atomic_json(path,task)
 for path in (runtime.BASE/'runs').glob('*/job.json'):
  if runtime.read(path).get('studio_plan_id')==value:
   runtime.pipeline_control.pause(path.parent,'plan_deleted','任务已删除，已发送请求安全收尾；已有成稿和费用记录保留')
 return {'plan_id':value,'deleted':True,'message':'任务已删除，后续执行已停止。正在处理的请求会安全收尾，已有成稿仍可在“成稿下载”查看。'}

def day_control(payload,pause):'''),
 (" p=plan(payload.get('plan_id'));day=payload.get('date');task=ensure_day(p,day)",""" p=plan(payload.get('plan_id'));day=payload.get('date');day_path(p['plan_id'],day)
 rows=runtime.status()['studio']['daily_tasks']
 row=next((t for t in rows if t['plan_id']==p['plan_id'] and t['date']==day),None)
 if not row or ('day_pause' if pause else 'day_resume') not in day_actions(row['status']):
  raise ValueError('任务状态已变化或本次执行已结束，请刷新查看；已结束的任务不能暂停或继续')
 task=ensure_day(p,day)"""),
 ("elif runtime.read(runtime.job_root(jid)/'days'/day/'day.json').get('status')!='complete':runtime.resume", "elif runtime.read(runtime.job_root(jid)/'days'/day/'day.json').get('status') not in TERMINAL_JOBS:runtime.resume"),
 (" tasks=[runtime.read(p) for p in paths]", " active_ids={p['plan_id'] for p in ps}\n tasks=[t for p in paths if (t:=runtime.read(p))['plan']['plan_id'] in active_ids]"),
 ("  if t.get('paused'):state='paused'", """  ended=bool(js) and len(js)==(1 if p.get('article_target') else len(p['questions'])) and all(j.get('day',{}).get('status') in TERMINAL_JOBS for j in js)
  if ended:
   state='complete' if complete==len(js) else 'complete_with_failures' if any(j.get('day',{}).get('status')=='complete_with_failures' for j in js) else 'insufficient_materials'
  elif t.get('paused'):state='paused'"""),
 ("  elif any(j.get('day',{}).get('status')=='complete_with_failures' for j in js):state='complete_with_failures'\n",''),
 ("  elif any(j.get('day',{}).get('status') in ('blocked_insufficient_sources','complete_with_shortfall','blocked_no_media_articles') for j in js):state='insufficient_materials'\n",''),
 (' for item in result:\n',' for item in result:\n  item[\'allowed_actions\']=day_actions(item[\'status\'])\n'),
 ('def advance(p,day,now):','def advance(p,day,now):\n if plan(p[\'plan_id\'],include_deleted=True).get(\'deleted_at\'):return')
])
edit('runtime.py',[
 ('def resume(root):','def resume(root):\n    assert_job_controllable(root)'),
 ("    if studio_plan:\n        from . import studio", "    if studio_plan:\n        from . import studio\n        studio.plan(studio_plan) # Reject stale scheduler snapshots after deletion."),
 ("{'kb_import','kb_save','plan_save','day_pause','day_resume'}", "{'kb_import','kb_save','plan_save','plan_delete','day_pause','day_resume'}"),
 ("'plan_save':studio.save_plan,", "'plan_save':studio.save_plan,'plan_delete':studio.delete_plan,"),
 ("            elif name in {'pause','resume'}:\n                root=job_root(payload.get('job_id',''))", "            elif name in {'pause','resume'}:\n                root=job_root(payload.get('job_id',''))\n                assert_job_controllable(root)"),
 ('def product_label(root,day):', '''def assert_job_controllable(root):
    from . import studio
    job=read(root/'job.json')
    if job.get('studio_plan_id'):studio.plan(job['studio_plan_id'])
    if read(root/'days'/job.get('date','')/'day.json').get('status') in studio.TERMINAL_JOBS:
        raise ValueError('本次执行已结束，不能暂停或继续；请查看已有成稿')

def product_label(root,day):''')
])
