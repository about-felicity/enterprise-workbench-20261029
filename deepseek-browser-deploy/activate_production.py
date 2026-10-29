"""One-time migration of only the available DeepSeek lane, preserving daily settings."""
import json,shutil,sqlite3,subprocess,sys,time,uuid
from pathlib import Path
ROOT=Path('/opt/monitor/geo-deepseek-browser-test');BASE=Path('/opt/monitor/geo-capture');stage=ROOT/'production-stage'
backup=ROOT/('production-backup-'+str(int(time.time())));backup.mkdir()
with sqlite3.connect(BASE/'panel/control.sqlite') as db,sqlite3.connect(backup/'control.sqlite') as dst:
    db.backup(dst)
    unchanged=db.execute("select model,value,revision,current_batch from settings where model<>'deepseek2' order by model").fetchall()
subprocess.run(['systemctl','stop','geo-daily-control.service','geo-deepseek-auth-check.timer'],check=True,timeout=25)
try:
    subprocess.run(['systemctl','stop','geo-deepseek-browser-test.service'],check=True,timeout=30)
    pairs=[(stage/'control'/name,BASE/name) for name in ('control_panel.py','native_entry.py','daily_tasks.py','deepseek_auth_monitor.py','manual_login.py','panel.html','fleet_status.py')]
    pairs += [(stage/'browser_backend.py',BASE/'browser_backend.py'),(stage/'browser_task_bridge.py',BASE/'browser_task_bridge.py'),
              (stage/'browser_test.py',ROOT/'browser_test.py'),(stage/'login.html',ROOT/'login.html'),
              (stage/'project/extension/content.js',ROOT/'project/extension/content.js')]
    for source,target in pairs:
        if target.exists():shutil.copy2(target,backup/(str(target).strip('/').replace('/','__')))
        shutil.copy2(source,target)
    (ROOT/'production.json').write_text(json.dumps({'enabled':True,'model':'deepseek2','source_device':'deepseek-browser-extension','activated_at':time.time()}))
    stamp=time.time()
    subprocess.run(['systemctl','enable','--now','geo-deepseek-browser-test-receiver.service','geo-deepseek-browser-test.service'],check=True,timeout=30)
    deadline=time.time()+80
    while time.time()<deadline:
        try:state=json.loads((ROOT/'state.json').read_text())
        except (FileNotFoundError,ValueError):state={}
        if state.get('updated_at',0)>stamp and state.get('auth')=='ready':break
        time.sleep(1)
    else:raise RuntimeError('Browser login not ready; no task was sent')
    sys.path.insert(0,str(BASE))
    from browser_backend import command
    x=command('inspect');modes=x['modes']
    assert any('深度思考' in m['text'] and m['pressed']=='false' for m in modes)
    assert any('智能搜索' in m['text'] and m['pressed']=='true' for m in modes)
    from control_panel import Controller
    from daily_tasks import today
    c=Controller()
    with c.connect() as db:
        settings=db.execute("select * from settings where model='deepseek2'").fetchone()
        config=json.loads(settings['value']);revision=settings['revision']
    assert len(config['questions'])==21 and config['rounds']==3 and config['interval']==1200
    result=c.action('deepseek2','settings',{**config,'revision':revision,'day':today(),'apply_now':True},uuid.uuid4().hex)
    with c.connect() as db:job=c.current(db,'deepseek2')
    c._login('deepseek2',job,False,result['revision'])
    with c.connect() as db:
        assert unchanged==[tuple(r) for r in db.execute("select model,value,revision,current_batch from settings where model<>'deepseek2' order by model")]
    (ROOT/'activation.json').write_text(json.dumps({'at':time.time(),'backup':str(backup),'day':today(),'settings':config,'revision':result['revision'],'other_settings_unchanged':True,'modes_verified':True},ensure_ascii=False,indent=2))
    subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True,timeout=25)
finally:
    subprocess.run(['systemctl','start','geo-daily-control.service','geo-deepseek-auth-check.timer'],check=True,timeout=25)
print(json.dumps({'activated':True,'backup':str(backup),'questions':21,'rounds':3,'interval':'1200–1800','daily_start':'09:00'},ensure_ascii=False))
