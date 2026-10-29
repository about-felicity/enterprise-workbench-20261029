from pathlib import Path
p=Path('geo-monitor-deploy/creation/supplement.py');s=p.read_text('utf8').replace("tasks=[runtime.read(p) for p in (studio.ROOT/'days').glob('*/*.json')]","tasks=[runtime.read(p) for p in (studio.ROOT/'days').glob('*/*.json')]\n tasks.sort(key=lambda t:(t['daily_task_id'] not in cfg.get('include_days',[]),t['date']))")
# Transient worker lock contention must not abort scheduler.
s=s.replace("    refreshed=refresh(task,s['question'],root,s['attempt'])", "    try:refreshed=refresh(task,s['question'],root,s['attempt'])\n    except RuntimeError:refreshed=False")
p.write_text(s,encoding='utf8')
p=Path('geo-monitor-deploy/creation/studio.py');s=p.read_text('utf8');needle=" return {'message':'当日任务已暂停";i=s.index(needle);s=s[:i]+''' from . import supplement
 extra=supplement.state(task)
 if extra and not pause and extra.get('status') in {'paused','waiting_verification'}:
  supplement.save(task,{**extra,'status':'waiting','next_at':0,'message':'正在重新检查补采通道'})
'''+s[i:];p.write_text(s,encoding='utf8')
