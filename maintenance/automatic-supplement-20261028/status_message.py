from pathlib import Path
p=Path('geo-monitor-deploy/creation/studio.py');s=p.read_text('utf8');needle="    reason=extra.get('message','正在自动补采')";s=s.replace(needle,needle+'''
    if extra.get('status')=='capturing' and extra.get('root'):
     for lane in materials.progress(t['date'],Path(extra['root'])):
      recovery=lane.get('recovery',{})
      if recovery.get('cooldown_until',0)>time.time():
       until=datetime.fromtimestamp(recovery['cooldown_until'],ZONE).strftime('%H:%M:%S')
       reason='第'+str(extra.get('attempt',1))+'轮补采：'+('平台验证' if recovery.get('kind')=='verification' else '读取未完成')+'，'+until+'后自动检查'
''');p.write_text(s,encoding='utf8')
