from pathlib import Path
base=Path('geo-monitor-deploy/creation')
p=base/'materials.py';s=p.read_text('utf8');s=s.replace("paths+=list((root/'days'/day).glob('*/results.jsonl'))","paths+=list((root/'days'/day).glob('*/results.jsonl'))\n paths+=list((root/'supplements'/day).glob('*/round-*/days/'+day+'/*/results.jsonl'))")
s=s.replace("resource=ROOT/'profiles/search'/model","resource=supplement_origin(ROOT)/'profiles/search'/model")
pos=s.index('def search_resources(model):');s=s[:pos]+'''def supplement_origin(root):
 value=os.environ.get('GEO_CREATION_SUPPLEMENT_ORIGIN')
 if not value:return Path(root)
 origin=Path(value).resolve();root=Path(root).resolve()
 if origin.parent!=CONTENT_BASE/'studio/capture' or not origin.name.startswith('plan-') or origin/'supplements' not in root.parents:raise ValueError('Invalid supplemental capture origin')
 return origin

'''+s[pos:]
s=s.replace("out=root/'private_source_analysis'","out=root/('private_source_analysis'+('-supplement-'+str(job['supplement_attempt']) if job.get('supplement_attempt') else ''))")
p.write_text(s,encoding='utf8')
p=base/'search_capture.py';s=p.read_text('utf8');needle='    # No unavailable placeholder';i=s.index(needle);s=s[:i]+'''    from .materials import supplement_origin,ROOT
    origin=supplement_origin(ROOT)
    if origin!=ROOT:
        from geo_source_cards import search_profiles
        original=search_profiles.profile_for_search
        day=args.runtime_dir.parents[1].name
        profile=original(origin/'days'/day/args.model/'collector',args.model)
        search_profiles.profile_for_search=lambda runtime,model: profile if model==args.model else original(runtime,model)
'''+s[i:];p.write_text(s,encoding='utf8')
p=base/'studio.py';s=p.read_text('utf8');s=s.replace("'capture_retrying'}:return ['day_pause']","'capture_retrying','supplementing'}:return ['day_pause']")
needle="  result.append({'daily_task_id':";i=s.index(needle);s=s[:i]+'''  if t.get('daily_task_id') and not t.get('paused'):
   from . import supplement
   extra=supplement.state(t)
   if supplement.eligible(t,supplement.policy()) and extra.get('status') in {'capturing','waiting','checking_materials','waiting_verification'}:
    state='waiting_login' if extra['status']=='waiting_verification' else 'supplementing'
    reason=extra.get('message','正在自动补采')
'''+s[i:]
s=s.replace("   except Exception as error:health.update(status='needs_attention'", "    from . import supplement\n    supplement.tick()\n   except Exception as error:health.update(status='needs_attention'")
p.write_text(s,encoding='utf8')
p=base/'panel.html';s=p.read_text('utf8').replace("const studioStates={","const studioStates={supplementing:'正在补充素材',");p.write_text(s,encoding='utf8')
p=base/'supplement.py';s=p.read_text('utf8');s=s.replace("and not task.get('deleted')", "and not task.get('deleted') and not task.get('error')")
s=s.replace("  if not rows:return False", "  if not rows:return False")
s=s.replace("   if list((root/'queue').glob('*/ticket.json')) or runtime.articles(root):return False", "   day_state=runtime.read(root/'days'/task['date']/'day.json')\n   if day_state.get('status') not in {'blocked_insufficient_sources','blocked_no_media_articles'} or list((root/'queue').glob('*/ticket.json')) or runtime.articles(root):return False")
s=s.replace("  with process_lock(path.with_suffix('.lock'),blocking=True):\n   latest=runtime.read(path)","  if not materials.records(task['date'],question,task['plan']['channels'],studio.capture_root(pid)):return False\n  with process_lock(path.with_suffix('.lock'),blocking=True):\n   latest=runtime.read(path)")
s=s.replace("  current=studio.plan(p['plan_id'],include_deleted=True)","  try:current=studio.plan(p['plan_id'],include_deleted=True)\n  except (ValueError,FileNotFoundError):continue")
s=s.replace("   if s and s.get('status') not in {'complete','waiting_verification'}:save", "   if s and s.get('status') not in {'complete','waiting_verification'} and all(task.get('jobs',{}).get(q) and runtime.articles(runtime.job_root(task['jobs'][q])) for q in p['questions']):save")
# Unfinished material checks remain visible until new job processing begins.
s=s.replace("   continue\n  if s.get('status')=='waiting_verification'", "   if s.get('status')=='checking_materials' and any(runtime.read(runtime.job_root(j)/'job.json').get('preparation')=='ready' for j in task.get('jobs',{}).values()):save(task,{**s,'status':'writing','message':''})\n   continue\n  if s.get('status')=='waiting_verification'")
# No parallel slot leak if stopped service; service itself retries on failure.
s += '''\n'''
p.write_text(s,encoding='utf8')
