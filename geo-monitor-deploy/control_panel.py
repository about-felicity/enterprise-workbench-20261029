"""Durable operations for GEO collectors. No arbitrary shell or queue resets."""
from contextlib import closing
from datetime import datetime, timezone, timedelta
import hashlib
import json
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid

MODELS = {
    'doubao1': {'name':'豆包 1','kind':'native','rounds':5,'interval':45,'minimum':30,'login':True},
    'doubao2': {'name':'豆包 2','kind':'native','rounds':5,'interval':45,'minimum':30,'login':True},
    'deepseek': {'name':'DeepSeek','kind':'native','backend':'android','rounds':3,'interval':600,'minimum':600,'maximum_interval':900,'interval_policy':'随机10–15分钟；关闭深度思考，仅开启智能搜索','login':True},
    'wenxin_card': {'name':'文心卡片','kind':'web','rounds':6,'interval':60,'minimum':60,'login':False},
    'baidu_ai': {'name':'百度卡片','kind':'web','rounds':5,'interval':60,'minimum':60,'login':False},
    'yuanbao': {'name':'元宝','kind':'native','rounds':5,'interval':45,'minimum':30,'login':True},
    'deepseek2': {'name':'DeepSeek 2','kind':'native','backend':'android','rounds':3,'interval':600,'minimum':600,'maximum_interval':900,'interval_policy':'随机10–15分钟；关闭深度思考，仅开启智能搜索','login':True},
}
for _meta in MODELS.values():
    _meta['maximum_rounds']=200 if _meta['kind']=='native' else 20
MODELS['deepseek']['maximum_rounds']=20
MODELS['deepseek2']['maximum_rounds']=20
DEEPSEEK_CHANNELS={'deepseek':('redroid-deepseek','deepseek-hpe14-android13'),
                   'deepseek2':('redroid-deepseek-account2','deepseek-hpe14-account2')}
BUSY = {'active','activating','reloading','deactivating'}

def job_kind(job):
    # Historical web journals must never be reinterpreted as Android queues.
    if job['service'].startswith('geo-native@'):return 'native'
    if job['service'].startswith('geo-web@'):return 'web'
    if job['model']=='deepseek':return 'web'
    return MODELS[job['model']]['kind']


class Conflict(ValueError):
    pass


def read(path, default=None):
    try:
        return json.loads(Path(path).read_text('utf-8-sig'))
    except FileNotFoundError:
        return {} if default is None else default


def atomic(path, value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temporary.open('w',encoding='utf8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2)
        stream.flush()
        __import__('os').fsync(stream.fileno())
    temporary.replace(path)


def validate(model, value):
    if model not in MODELS: raise ValueError('未知采集通道')
    questions=value.get('questions')
    if not isinstance(questions,list) or not 1<=len(questions)<=500: raise ValueError('每个任务需要 1–500 个问题')
    if not all(isinstance(q,str) and 0<len(q.strip())<=2000 and '\n' not in q and '\r' not in q and '\x00' not in q for q in questions):
        raise ValueError('每行一个问题，单题最多 2000 字')
    questions=[q.strip() for q in questions]
    if len(set(questions))!=len(questions): raise ValueError('问题存在重复，请去重后保存')
    rounds,interval=value.get('rounds'),value.get('interval')
    maximum=MODELS[model]['maximum_rounds']
    if type(rounds) is not int or not 1<=rounds<=maximum: raise ValueError('轮数须为 1–'+str(maximum)+' 的整数')
    maximum_interval=MODELS[model].get('maximum_interval',3600)
    if type(interval) is not int or not MODELS[model]['minimum']<=interval<=maximum_interval:
        raise ValueError('发送间隔须在 '+str(MODELS[model]['minimum'])+'–'+str(maximum_interval)+' 秒之间')
    return {'questions':questions,'rounds':rounds,'interval':interval}


class System:
    def configure_daily_schedule(self,start,enabled):
        import schedule_control
        schedule_control.validate({'time':start,'enabled':enabled,'revision':0})
        directory=Path('/etc/systemd/system/geo-daily-dispatch.timer.d');directory.mkdir(exist_ok=True)
        target=directory/'30-schedule.conf'
        text='[Timer]\nOnCalendar=\nOnCalendar=*-*-* '+start+':00 Asia/Shanghai\n'
        temp=target.with_suffix('.tmp');temp.write_text(text);temp.chmod(0o644);temp.replace(target)
        subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=15)
        subprocess.run(['systemctl','enable' if enabled else 'disable','--now','geo-daily-dispatch.timer'],check=True,capture_output=True,timeout=15)
        if enabled:subprocess.run(['systemctl','restart','geo-daily-dispatch.timer'],check=True,capture_output=True,timeout=15)

    def state(self, service):
        return subprocess.run(['systemctl','is-active',service],capture_output=True,text=True,timeout=10).stdout.strip()

    def start(self, service):
        subprocess.run(['systemctl','start','--no-block',service],check=True,capture_output=True,timeout=10)

    def enable_current(self,service,old):
        directory=Path('/etc/systemd/system/geo-monitor.target.wants')
        directory.mkdir(exist_ok=True)
        if old and old!=service and old.startswith(('geo-web@','geo-native@')):
            (directory/old).unlink(missing_ok=True)
        target='/etc/systemd/system/'+('geo-native@.service' if service.startswith('geo-native@') else 'geo-web@.service')
        if not (directory/service).is_symlink():
            (directory/service).symlink_to(target)
        subprocess.run(['systemctl','daemon-reload'],check=True,capture_output=True,timeout=15)


class Controller:
    def __init__(self,base=Path('/opt/monitor/geo-capture'),system=None,native_base=Path('/home/user/redroid-doubao')):
        self.base,self.native_base,self.system=Path(base),Path(native_base),system or System()
        self.yuanbao_base=self.native_base.parent/'redroid-yuanbao'
        self.root=self.base/'panel'
        self.root.mkdir(parents=True,exist_ok=True)
        (self.root/'jobs').mkdir(exist_ok=True)
        self.lock=threading.RLock()
        self.checks={}
        self.db=self.root/'control.sqlite'
        with self.connect() as db:
            db.executescript('''
            pragma journal_mode=WAL;
            create table if not exists settings(model text primary key,value text not null,revision integer not null,current_batch text);
            create table if not exists jobs(batch text primary key,model text not null,service text not null,health text not null,config text not null,created real not null,stop_requested integer not null default 0);
            create table if not exists commands(id text primary key,model text not null,action text not null,input_hash text not null,result text not null,created real not null);
            create table if not exists events(id integer primary key,model text,event text,batch text,created real,message text);
            create table if not exists logins(model text primary key,result text not null);
            ''')
            from daily_tasks import installed
            installed(db)
        self._import_current()

    def connect(self):
        db=sqlite3.connect(self.db,timeout=15)
        db.row_factory=sqlite3.Row
        db.execute('pragma synchronous=FULL')
        return closing_transaction(db)

    def _import_current(self):
        fleet=read(self.base/'fleet.json')
        fallback=read(self.base/'config/wenxin_card.json').get('questions',[])
        with self.connect() as db:
            for model,lane in zip(MODELS,fleet['collectors']):
                if db.execute('select 1 from settings where model=?',(model,)).fetchone(): continue
                health=read(lane['health'])
                config=read(self.base/'config'/ (model+'.json')) if MODELS[model]['kind']=='web' else {}
                value=validate(model,{'questions':config.get('questions',fallback),'rounds':config.get('rounds',MODELS[model]['rounds']),
                                      'interval':config.get('interval',MODELS[model]['interval'])})
                batch=health.get('batch') or Path(lane['health']).parent.name
                config={**config,**value,'model':model,'batch':batch}
                root=Path(lane['health']).parent
                tasks=root/'tasks.sqlite' if MODELS[model]['kind']=='native' else root/'collector/tasks.sqlite'
                created=Path(lane['health']).stat().st_mtime
                if tasks.exists():
                    with closing(sqlite3.connect(tasks.as_uri()+'?mode=ro',uri=True)) as source:
                        query="select min(time) from events where event='enqueued'" if MODELS[model]['kind']=='native' else 'select min(started) from captures'
                        observed=source.execute(query).fetchone()[0]
                        created=observed or created
                db.execute('insert into jobs values(?,?,?,?,?,?,0)',(batch,model,lane['service'],lane['health'],json.dumps(config,ensure_ascii=False),created))
                db.execute('insert into settings values(?,?,1,?)',(model,json.dumps(value,ensure_ascii=False),batch))

    def current(self,db,model):
        return dict(db.execute('select j.* from jobs j join settings s on s.current_batch=j.batch where s.model=?',(model,)).fetchone())

    def batch_root(self,job): return Path(job['health']).parent

    def marker(self,job):
        return self.batch_root(job)/('maintenance_pause.json' if job_kind(job)=='native' else 'pause.json')

    def snapshot(self,job):
        health=read(job['health'])
        if job['model']=='baidu_ai':
            from baidu_body_delivery import merge_health
            health=merge_health(health,self.batch_root(job))
        service=self.system.state(job['service'])
        state=health.get('status','not_started')
        marker=self.marker(job).exists()
        if marker and state not in {'waiting_login','waiting_verification'}:
            state=('stopping' if job['stop_requested'] else 'pausing') if service in BUSY else ('stopped' if job['stop_requested'] else 'paused')
        elif service in BUSY and state in {'paused','stopped','not_started'}:
            state='starting'
        elif state.startswith('running') and (service not in BUSY or (health.get('heartbeat_expires_at') or 0)<time.time()):
            state='stale' if service in BUSY else 'stopped'
        if job['model']=='deepseek' and state=='needs_attention':
            if read(self.batch_root(job)/'collector/deepseek_session.json').get('status')=='login_required': state='waiting_login'
        config=json.loads(job['config'])
        review=sum(health.get('tasks',{}).get(k,0) for k in ('prepared','capturing','needs_attention','failed_deferred')) if service not in BUSY else 0
        errors=health.get('errors',health.get('delivery_errors',[]))
        diagnostics=[]
        for error in errors:
            # Only controlled codes, never raw HTTP error strings or credentials.
            code=error.get('code')
            if code and re.fullmatch(r'[a-z_]{1,80}',code):
                value={k:error[k] for k in ('code','retryable','http_status','next_at','first_pending_at') if k in error}
                if value not in diagnostics:diagnostics.append(value)
        progress=health.get('progress',{})
        progress={k:progress[k] for k in ('phase','ordinal','changed_at','deadline_at','next_at','attempt','pending_delivery','reason') if k in progress}
        pending=max(0,health.get('captured',0)-health.get('geo_processed',health.get('processed',0)))
        return {'model':job['model'],'name':MODELS[job['model']]['name'],'batch':job['batch'],'service_state':service,'state':state,
                'planned':len(config['questions'])*config['rounds'],'captured':health.get('captured',0),
                'processed':health.get('geo_processed',health.get('processed',0)),
                'unique_processed':health.get('geo_processed',health.get('unique_processed',0)),
                'duplicates':health.get('duplicates',0),'unavailable':health.get('unavailable',0),
                'nontext_observations':health.get('nontext_observations',0),'nontext_processed':health.get('nontext_processed',0),
                'nontext_pending':health.get('nontext_pending',0),
                'body_only_observations':health.get('body_only_observations',0),
                'body_only_processed':health.get('body_only_processed',0),
                'delivery_errors':len(errors),'diagnostics':diagnostics[:5],'progress':progress,
                'pending_delivery':pending,'heartbeat_age':max(0,time.time()-health['time']) if health.get('time') else None,
                'tasks':health.get('tasks',{}),'needs_review':review,'updated_at':health.get('time'),'created_at':job['created'],
                'memory':{k:v for k,v in health.get('memory',{}).items() if k in ('app_alive','pid','java_alloc_kib','java_limit_kib','native_alloc_kib','app_pss_kib','container_working_bytes','container_limit_bytes','sampled_at','pending','probe_error','last_exit','maintenance_at')},
                'config':config,'stop_requested':bool(job['stop_requested'])}

    def all(self,day=None):
        from daily_tasks import DailyTasks,today,valid_day
        day=valid_day(day or today())
        with self.lock,self.connect() as db:
            daily=DailyTasks(self).view(db,day)
            result=[]
            for model,meta in MODELS.items():
                settings=dict(db.execute('select * from settings where model=?',(model,)).fetchone())
                job=self.current(db,model)
                login=read_login(db,model)
                blocked=read(job['health'])
                if blocked.get('status')=='waiting_login' and blocked.get('time',0)>login.get('checked_at',0):
                    login={'status':'login_required','checked_at':blocked['time'],'batch':job['batch'],
                           'revision':settings['revision'],'message':meta['name']+' 登录已失效，请手动登录后重新校验'}
                    db.execute('insert or replace into logins values(?,?)',(model,json.dumps(login,ensure_ascii=False)))
                manual={}
                if model in DEEPSEEK_CHANNELS:
                    from manual_login import state as manual_state
                    manual=manual_state(self.base,model)
                    if (manual.get('status')=='ready' and manual.get('batch')==job['batch']
                            and manual.get('revision')==settings['revision']
                            and manual.get('updated_at',0)>login.get('checked_at',0)):
                        login={'status':'ready','checked_at':manual['updated_at'],'batch':job['batch'],
                               'revision':settings['revision'],'message':'手动登录及采集会话复核通过'}
                        db.execute('insert or replace into logins values(?,?)',(model,json.dumps(login,ensure_ascii=False)))
                    elif manual.get('status')=='failed' and login.get('status')=='manual_login':
                        login={'status':'login_required','checked_at':time.time(),'message':manual.get('message','请重新登录')}
                        db.execute('insert or replace into logins values(?,?)',(model,json.dumps(login,ensure_ascii=False)))
                if login.get('status')=='checking' and time.time()-login.get('checked_at',0)>180:
                    login={'status':'unknown','message':'上次校验未完成，请重新校验','checked_at':login.get('checked_at')}
                history=[]
                for old in db.execute('select * from jobs where model=? order by created desc limit 15',(model,)):
                    h=read(old['health']); c=json.loads(old['config'])
                    if model=='baidu_ai':
                        from baidu_body_delivery import merge_health
                        h=merge_health(h,Path(old['health']).parent)
                    history.append({'batch':old['batch'],'created_at':old['created'],'current':old['batch']==job['batch'],
                                    'config':{k:c[k] for k in ('questions','rounds','interval')},'state':h.get('status','not_started'),
                                    'planned':len(c['questions'])*c['rounds'],'captured':h.get('captured',0),
                                    'processed':h.get('geo_processed',h.get('processed',0))})
                events=[dict(row) for row in db.execute('select event,batch,created,message from events where model=? order by id desc limit 20',(model,))]
                readiness=self._readiness(job,settings,login,manual)
                current=self.snapshot(job)
                if model in DEEPSEEK_CHANNELS and current['state']=='waiting_login':
                    if login.get('status')=='checking' or manual.get('status')=='verifying':
                        current['state']='checking_login'
                    elif any(c['name']=='login' and c['ok'] for c in readiness['checks']):
                        current['state']='starting' if current['service_state'] in BUSY else 'ready_to_resume'
                    if current['state']!='waiting_login':
                        current['progress']={**current['progress'],'phase':current['state']}
                if (day==today() and daily[model]['remaining'] and daily[model].get('desired')!='paused'
                        and current['state'] in {'waiting_login','checking_login','ready_to_resume','starting'}):
                    daily[model]['status']=current['state']
                from browser_backend import enabled as browser_enabled
                if browser_enabled(model,self.base):meta={**meta,'backend':'browser_extension'}
                if model in read(self.base/'daily_plan.json').get('desktop_collectors',[]):
                    meta={**meta,'name':'DeepSeek 本机插件','backend':'desktop_extension','login':False}
                    current={**current,'state':'external','service_state':'inactive','captured':daily[model]['completed'],'processed':daily[model]['completed'],'heartbeat_age':None,'progress':{'phase':'external'},'needs_review':0}
                    daily[model]['status']='complete' if daily[model].get('remaining')==0 else 'external'
                    login={'status':'external','message':'请在本机Chrome中运行插件；服务器仅接收结果，不自动提问'}
                    manual={};readiness={'checks':[],'can_start':False,'can_resume':False}
                result.append({'id':model,**meta,'settings':json.loads(settings['value']),'revision':settings['revision'],
                               'manual_login':manual,'readiness':readiness,
                               'login_monitor':read(self.base/'auth-monitor'/(model+'.json')) if model in DEEPSEEK_CHANNELS else {},
                               'current':current,'login_status':login,'history':history,'events':events,'daily':daily[model]})
            from schedule_control import view as schedule_view
            return {'models':result,'generated_at':time.time(),'date':day,'today':today(),
                    'schedule':schedule_view(self.base)}

    def action(self,model,action,value,key):
        if model in read(self.base/'daily_plan.json').get('desktop_collectors',[]) and action!='settings':
            raise ValueError('已切换本机浏览器插件，请在本机插件中开始、暂停、继续或登录')
        if model not in MODELS or action not in {'settings','new','pause','resume','stop','login','login_sync','login_open'}:
            raise ValueError('未知操作')
        if not re.fullmatch(r'[a-f0-9]{32}',str(key)): raise ValueError('缺少有效操作编号')
        digest=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        with self.lock,self.connect() as db:
            old=db.execute('select * from commands where id=?',(key,)).fetchone()
            if old:
                if (old['model'],old['action'],old['input_hash'])!=(model,action,digest):raise Conflict('操作编号已用于其他请求')
                return json.loads(old['result'])
            job=self.current(db,model)
            if value.get('scope')=='daily' and action in {'pause','resume'}:
                from daily_tasks import DailyTasks,today
                tasks=DailyTasks(self);day=value.get('day',today())
                settings=db.execute('select value,revision from settings where model=?',(model,)).fetchone()
                config=tasks.config(db,model,day)
                result=tasks.request(db,model,day,config,settings['revision'],'paused' if action=='pause' else 'running')
                self._record(db,key,model,action,digest,result,job['batch'])
                return result
            if action=='settings':
                clean=validate(model,value)
                revision=db.execute('select revision from settings where model=?',(model,)).fetchone()[0]
                if value.get('revision')!=revision: raise Conflict('设置已被修改，请刷新后重试')
                db.execute('update settings set value=?,revision=revision+1 where model=?',(json.dumps(clean,ensure_ascii=False),model))
                if value.get('apply_now') is True:
                    from daily_tasks import DailyTasks,today
                    result=DailyTasks(self).request(db,model,value.get('day',today()),clean,revision+1,'running',apply=True)
                else:result={'ok':True,'message':'已保存下次任务设置；当前任务参数保持锁定','revision':revision+1}
            elif action=='new':
                metadata=getattr(self,'execution_metadata',None)
                if metadata:
                    if not db.in_transaction:db.execute('begin immediate')
                    expected=db.execute('select revision,desired from daily_tasks where model=? and day=?',(model,metadata['daily_date'])).fetchone()
                    if not expected or expected['revision']!=metadata['daily_revision'] or expected['desired']!='running':
                        raise Conflict('当天计划已更新或暂停，后台将按最新配置核对')
                return self._new(db,model,job,value,key)
            elif action in {'pause','stop'}:
                state=self.snapshot(job)
                if state['state'] in {'complete','complete_with_unavailable'}: raise Conflict('当前任务已完成，无需'+('暂停' if action=='pause' else '停止'))
                if job['stop_requested'] and action=='pause':raise Conflict('当前任务已停止，请创建新任务')
                atomic(self.marker(job),{'requested_at':time.time(),'source':'control_panel','action':action})
                if action=='stop':db.execute('update jobs set stop_requested=1 where batch=?',(job['batch'],))
                result={'ok':True,'message':'已请求'+('停止此任务' if action=='stop' else '暂停')+'，当前题完成并确认回传后生效；历史记录保留'}
            elif action=='resume':
                state=self.snapshot(job)
                if job['stop_requested']:raise Conflict('停止的任务不自动恢复，请创建新任务')
                if state['service_state'] in BUSY:raise Conflict('服务仍在运行或排空，请等待')
                if state['state'] in {'complete','complete_with_unavailable'}:raise Conflict('当前任务已完成，请创建新任务')
                self._ensure_known(job,allow_readback=True)
                if job_kind(job)=='native' and json.loads(job['config']).get('prompt_mode')!='question_only':
                    raise Conflict('旧批次包含附加任务提示，历史已保留；请开始仅发送问题原文的新任务')
                self._ensure_delivery(job)
                self._ensure_login(db,model)
                if not self.marker(job).exists() and state['state'] not in {'waiting_login','needs_attention','stopped','not_started'}:
                    raise Conflict('当前状态不能继续')
                self.marker(job).unlink(missing_ok=True)
                result=self._start_committed(db,model,job,key,action,value,digest)
                return result
            elif action=='login_open':
                if model not in DEEPSEEK_CHANNELS:raise ValueError('仅 DeepSeek 支持远程登录')
                if self.system.state(job['service']) in BUSY:raise Conflict('请先暂停采集并等待当前题结束')
                if model in self.checks:raise Conflict('正在校验，请等待校验结束')
                if read_login(db,model).get('status') not in {'login_required','risk_blocked','verification_required','manual_login'}:raise Conflict('账号未确认掉登录，不能打开登录投屏；请等待巡检结果')
                from browser_backend import enabled as browser_enabled
                if browser_enabled(model,self.base):
                    result={'ok':True,'message':'请打开浏览器登录画面','login_url':'http://127.0.0.1:18820/'}
                    self._record(db,key,model,action,digest,result,job['batch'])
                    return result
                from manual_login import start
                revision=db.execute('select revision from settings where model=?',(model,)).fetchone()[0]
                flow=start(self.base,self.batch_root(job)/'collector',job['batch'],revision,model=model)
                db.execute('insert or replace into logins values(?,?)',(model,json.dumps({'status':'manual_login','checked_at':time.time(),'message':'请在登录页面手动完成登录；完成后自动校验'})))
                result={'ok':True,'message':'scrcpy登录投屏已打开，请手动完成登录','login_url':'login/'+model+'/ui','flow':flow['id']}
            else:
                if not MODELS[model]['login']:raise ValueError('此通道无需登录校验')
                if action=='login_sync' and model!='deepseek':raise ValueError('仅 DeepSeek 支持同步内容工作台登录')
                if self.system.state(job['service']) in BUSY:raise Conflict('采集中不操作登录页面，请先暂停并等待当前题结束')
                if model in DEEPSEEK_CHANNELS:
                    from manual_login import state as manual_state
                    if manual_state(self.base,model).get('status') in {'opening','waiting_login','verifying','risk_blocked','verification_required'}:
                        raise Conflict('手动登录正在进行，请先完成登录')
                if model in self.checks:raise Conflict('登录校验正在进行')
                result={'ok':True,'message':'正在校验登录，不会发送问题'}
                db.execute('insert or replace into logins values(?,?)',(model,json.dumps({'status':'checking','checked_at':time.time(),'message':'正在校验'})))
                self.checks[model]=True
                revision=db.execute('select revision from settings where model=?',(model,)).fetchone()[0]
                thread=threading.Thread(target=self._login,args=(model,job,action=='login_sync',revision),daemon=True)
                thread.start()
            self._record(db,key,model,action,digest,result,job['batch'])
            return result

    def _record(self,db,key,model,action,digest,result,batch):
        db.execute('insert into commands values(?,?,?,?,?,?)',(key,model,action,digest,json.dumps(result,ensure_ascii=False),time.time()))
        db.execute('insert into events(model,event,batch,created,message) values(?,?,?,?,?)',(model,action,batch,time.time(),result.get('message','')))

    def _ensure_known(self,job,*,allow_readback=False):
        root=self.batch_root(job)
        path=root/'tasks.sqlite' if job_kind(job)=='native' else root/'collector/tasks.sqlite'
        if not path.exists():return
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row
            table='tasks' if job_kind(job)=='native' else 'captures'
            unknown=db.execute(f"select * from {table} where state in ('prepared','capturing','needs_attention','failed_deferred')").fetchall()
            count=len(unknown)
            if count and allow_readback:
                if job['model'] in {'baidu_ai','wenxin_card'}:return
                if job_kind(job)=='native' and json.loads(job['config']).get('prompt_mode')=='question_only':return
                if job['model']=='deepseek':
                    exists=db.execute("select 1 from sqlite_master where name='capture_submissions'").fetchone()
                    if exists and all((lambda intent:bool(intent and (not intent[0] or intent[1])))(
                        db.execute('select attempted,conversation_url from capture_submissions where task_id=?',(row['task_id'],)).fetchone()) for row in unknown):return
        if count:raise Conflict('存在结果未知或失败题目，需要核对原始记录；不会自动重发')

    def _ensure_login(self,db,model):
        if model in self.checks:raise Conflict('登录校验正在进行，请等待')
        if model in DEEPSEEK_CHANNELS:
            login=read_login(db,model)
            if login.get('status')!='ready' or time.time()-login.get('checked_at',0)>300:
                raise Conflict('请先校验 DeepSeek 登录，校验通过后再开始或继续')
            row=db.execute('select revision,current_batch from settings where model=?',(model,)).fetchone()
            if login.get('batch')!=row['current_batch'] or login.get('revision')!=row['revision']:
                raise Conflict('任务或设置已变化，请重新校验后开始或继续')

    def _ensure_delivery(self,job):
        snap=self.snapshot(job)
        if snap['pending_delivery'] or snap['nontext_pending'] or snap['delivery_errors']:
            raise Conflict('请等待所有结果回传并核对回执后再开始或继续')

    def _readiness(self,job,settings,login,manual):
        """Return the same known-result and login gates used by start/resume."""
        model=job['model']; snap=self.snapshot(job); checks=[]
        def add(name,ok,message):checks.append({'name':name,'ok':bool(ok),'message':message})
        try:validate(model,json.loads(settings['value']));valid=True
        except ValueError:valid=False
        add('settings',valid,'已保存的问题、轮数与间隔有效' if valid else '请修正并保存任务设置')
        if model in DEEPSEEK_CHANNELS:
            fresh=(login.get('status')=='ready' and time.time()-login.get('checked_at',0)<=300
                   and login.get('batch')==job['batch'] and login.get('revision')==settings['revision'])
            message=('DeepSeek 登录及采集会话有效' if fresh else
                     '任务运行中；启动前校验时效不影响本次采集' if snap['service_state'] in BUSY and snap['state'] not in {'waiting_login','waiting_verification'} else
                     '开始或继续前请重新校验；校验过期不代表登录失效' if login.get('status')=='ready' else
                     '登录尚未通过，请完成登录并重新校验')
            add('login',fresh,message)
        try:self._ensure_known(job);known=True
        except Conflict:known=False
        try:self._ensure_known(job,allow_readback=True);readback=True
        except Conflict:readback=False
        add('results',known or readback,'历史题目状态明确' if known else '已定位原任务，可安全补读' if readback else '旧任务有结果未知或失败题目，需先处理')
        add('delivery',snap['pending_delivery']==0 and snap['nontext_pending']==0 and not snap['delivery_errors'],
            '回传与回执已核对' if not snap['pending_delivery'] and not snap['delivery_errors'] else '仍有结果等待回传或回执处理')
        idle=snap['service_state'] not in BUSY
        add('idle',idle,'采集进程已空闲' if idle else '任务运行或收尾中，无需重复开始或继续')
        ready=all(check['ok'] for check in checks) and login.get('status')!='checking' and manual.get('status') not in {'opening','waiting_login','verifying'}
        return {'checks':checks,'can_start':ready and known,'can_resume':ready and readback and not job['stop_requested'] and snap['state'] not in {'complete','complete_with_unavailable'},
                'expires_at':login.get('checked_at',0)+300 if model in DEEPSEEK_CHANNELS else None}

    def _new(self,db,model,old,value,key):
        state=self.snapshot(old)
        if state['service_state'] in BUSY:raise Conflict('当前任务仍在运行，请先暂停或停止并等待当前题结束')
        self._ensure_known(old)
        self._ensure_delivery(old)
        self._ensure_login(db,model)
        settings=dict(db.execute('select * from settings where model=?',(model,)).fetchone())
        if value.get('revision')!=settings['revision']:raise Conflict('设置版本已变化，请刷新后开始')
        config=validate(model,getattr(self,'execution_config',None) or json.loads(settings['value']))
        # Legacy units are also listed in the original target. A superseded
        # unfinished batch must retain a pause marker even after a reboot.
        if state['state'] not in {'complete','complete_with_unavailable'}:
            if not self.marker(old).exists():
                atomic(self.marker(old),{'requested_at':time.time(),'source':'control_panel','action':'superseded_by_new_task'})
            db.execute('update jobs set stop_requested=1 where batch=?',(old['batch'],))
        stamp=datetime.now(timezone(timedelta(hours=8))).strftime('%Y%m%d-%H%M%S')
        batch='geo-panel-'+model.replace('_','-')+'-'+stamp+'-'+key[:8]
        config={**config,'model':model,'batch':batch,'device':'geo-headless-'+model,'created_at':time.time()}
        config.update(getattr(self,'execution_metadata',None) or {})
        native=MODELS[model]['kind']=='native'
        if native:config['prompt_mode']='question_only'
        if model in DEEPSEEK_CHANNELS and native:config.update(backend='android',device=DEEPSEEK_CHANNELS[model][1])
        from browser_backend import enabled as browser_enabled
        if browser_enabled(model,self.base):config.update(backend='browser_extension',device='deepseek-browser-extension')
        root=(self.native_base.parent/DEEPSEEK_CHANNELS[model][0] if model in DEEPSEEK_CHANNELS and native else self.yuanbao_base if model=='yuanbao' else self.native_base if native else self.base)/'batches'/batch
        root.mkdir(parents=True,exist_ok=False)
        if not native:
            (root/'collector').mkdir()
            shutil.chown(root,user='user',group='user') if self.system.__class__ is System else None
            shutil.chown(root/'collector',user='user',group='user') if self.system.__class__ is System else None
        if model=='deepseek' and native:
            rate=read(self.batch_root(old)/'collector/deepseek_last_prompt.json')
            shared=self.base/'deepseek_last_send.json'
            previous=read(shared)
            latest=max(rate.get('last_prompt_epoch',0),previous.get('last_prompt_epoch',0),previous.get('time',0))
            if latest>max(previous.get('last_prompt_epoch',0),previous.get('time',0)):
                atomic(shared,{'last_prompt_epoch':latest,'time':latest,'source':'android_transport_migration'})
        if model=='deepseek' and not native:
            rate=self.batch_root(old)/'collector/deepseek_last_prompt.json'
            if rate.exists():
                atomic(root/'collector/deepseek_last_prompt.json',read(rate))
            source=self.batch_root(old)/'collector/web_profiles/deepseek'
            if source.exists():
                target=root/'collector/web_profiles/deepseek'
                from geo_source_cards.runtime import process_lock
                with process_lock(self.batch_root(old)/'collector/collector.lock'):
                    shutil.copytree(source,target,ignore=shutil.ignore_patterns('Singleton*','Cache','Code Cache','GPUCache','Crashpad'))
                if self.system.__class__ is System:
                    subprocess.run(['chown','-R','user:user',str(root)],check=True)
        path=self.root/'jobs'/(batch+'.json')
        atomic(path,config)
        path.chmod(0o644)
        service=('geo-native@' if native else 'geo-web@')+batch+'.service'
        job={'batch':batch,'model':model,'service':service,'health':str(root/'bridge_health.json'),'config':json.dumps(config,ensure_ascii=False),'created':time.time(),'stop_requested':0}
        db.execute('insert into jobs values(?,?,?,?,?,?,0)',tuple(job[k] for k in ('batch','model','service','health','config','created')))
        db.execute('update settings set current_batch=? where model=?',(batch,model))
        return self._start_committed(db,model,job,key,'new',value,hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest(),in_new=True,old_service=old['service'])

    def _start_committed(self,db,model,job,key,action,value,digest,in_new=False,old_service=None):
        result={'ok':True,'message':'新任务已创建，正在启动' if in_new else '正在继续原任务，已完成题目不会重发','batch':job['batch']}
        self._record(db,key,model,action,digest,result,job['batch'])
        db.commit()  # Intent and immutable batch survive a lost HTTP reply.
        try:
            self._fleet(model,job)
            if job['service'].startswith(('geo-web@','geo-native@')):
                self.system.enable_current(job['service'],old_service)
            self.system.start(job['service'])
        except Exception:
            result={'ok':False,'message':'启动请求未确认，请查看服务状态；不会重复创建任务','batch':job['batch']}
            db.execute('update commands set result=? where id=?',(json.dumps(result,ensure_ascii=False),key))
        return result

    def _fleet(self,model,job):
        fleet=read(self.base/'fleet.json')
        lane=fleet['collectors'][list(MODELS).index(model)]
        lane.update(service=job['service'],health=job['health'],planned=len(json.loads(job['config'])['questions'])*json.loads(job['config'])['rounds'])
        atomic(self.base/'fleet.json',fleet)

    def _login(self,model,job,sync,revision):
        try:
            from browser_backend import enabled as browser_enabled,probe as browser_probe
            if browser_enabled(model,self.base):
                value={**browser_probe(),'checked_at':time.time(),'batch':job['batch'],'revision':revision}
                from deepseek_auth_monitor import record
                record(model,value,self.base)
                with self.lock,self.connect() as db:
                    db.execute('insert or replace into logins values(?,?)',(model,json.dumps(value,ensure_ascii=False)))
                    self.checks.pop(model,None)
                return
            if model in DEEPSEEK_CHANNELS and MODELS[model]['kind']=='native':
                result=subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-B','/home/user/'+DEEPSEEK_CHANNELS[model][0]+'/code/device.py'],capture_output=True,text=True,timeout=45,check=True)
                value=json.loads(result.stdout.strip().splitlines()[-1])
                value.update(checked_at=time.time(),batch=job['batch'],revision=revision)
                from deepseek_auth_monitor import record
                record(model,value,self.base)
                if value.get('status')=='ready':
                    atomic(self.base/(model+'_app_session.json'),{'backend':'android','status':'ready',
                           'checked_at':value['checked_at'],'last_checkpoint':value['checked_at']})
                with self.lock,self.connect() as db:
                    db.execute('insert or replace into logins values(?,?)',(model,json.dumps(value,ensure_ascii=False)))
                    self.checks.pop(model,None)
                return
            command=[str(self.base/'venv/bin/python'),str(self.base/'login_probe.py'),'--model',model,'--runtime',str(self.batch_root(job)/'collector')]
            if sync:command.append('--sync-source')
            prefix=['systemd-run','--unit=geo-login-'+model.replace('_','-')+'-'+uuid.uuid4().hex[:10],
                    '--wait','--pipe','--collect','--property=MemoryMax=1800M',
                    '--property=TasksMax=512','--property=RuntimeMaxSec=140']
            if model=='deepseek':prefix.append('--uid=user')
            command=prefix+command
            result=subprocess.run(command,capture_output=True,text=True,timeout=150)
            value=json.loads(result.stdout.strip().splitlines()[-1])
            value['checked_at']=time.time()
            value['batch']=job['batch']
            value['revision']=revision
        except Exception:
            value={'status':'unknown','checked_at':time.time(),'message':'校验未完成，请稍后重试；没有发送问题'}
        with self.lock,self.connect() as db:
            db.execute('insert or replace into logins values(?,?)',(model,json.dumps(value,ensure_ascii=False)))
            db.execute('insert into events(model,event,batch,created,message) values(?,?,?,?,?)',(model,'login_result',job['batch'],time.time(),value.get('message','')))
            self.checks.pop(model,None)


class closing_transaction:
    def __init__(self,db):self.db=db
    def __enter__(self):return self.db
    def __exit__(self,kind,value,tb):
        try:self.db.rollback() if kind else self.db.commit()
        finally:self.db.close()


def read_login(db,model):
    row=db.execute('select result from logins where model=?',(model,)).fetchone()
    return json.loads(row[0]) if row else {'status':'unchecked','message':'尚未校验'}
