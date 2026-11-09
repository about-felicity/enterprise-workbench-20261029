"""Daily task plans and safe continuation across immutable collector batches."""
from collections import Counter
from contextlib import closing
from datetime import datetime,timedelta
import hashlib
import json
import sqlite3
from pathlib import Path
import subprocess
import threading
import time
from zoneinfo import ZoneInfo

from monthly_monitoring import target as question_target
from capture_channels import log_channel
from control_panel import DEEPSEEK_CHANNELS,MODELS,BUSY,Conflict,atomic,read,validate

ZONE=ZoneInfo('Asia/Shanghai')
DOUBAO_CHANNELS={'doubao1','doubao2','doubao3','doubao4'}
WEB_PEERS={'baidu_ai':'wenxin_card','wenxin_card':'baidu_ai'}
DEVICES={'doubao-hpe14-13-test':'doubao1','doubao-hpe14-account2':'doubao2','doubao-hpe14-account3':'doubao3','doubao-hpe14-account4':'doubao4',
         'geo-headless-deepseek':'deepseek','deepseek-hpe14-android13':'deepseek','deepseek-hpe14-account2':'deepseek2','deepseek-browser-extension':'deepseek2','geo-headless-wenxin_card':'wenxin_card',
         'geo-headless-baidu_ai':'baidu_ai','yuanbao-hpe14-android13':'yuanbao'}
_cache={};_lock=threading.RLock()

def today():return datetime.now(ZONE).date().isoformat()

def question_digest(question):return hashlib.sha256(question.encode()).hexdigest()

def deferred_originals_allow_progress(root, *, drained=False):
    """Recognize bound exceptions that can yield to other work."""
    root=Path(root);marker=root/'deferred_originals.json'
    try:
        deferred=json.loads(marker.read_text()) if marker.is_file() else {}
        unknown_path=root/'uncertain_send_quarantine.json'
        unknown=json.loads(unknown_path.read_text()) if unknown_path.is_file() else {}
        with closing(sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
            rows=db.execute("select task_id,request_id,capture_retries,prepared_at,question from tasks where state='needs_attention'").fetchall()
            pending=db.execute("select count(*) from tasks where state in ('pending','prepared')").fetchone()[0]
        return bool(rows and (not pending if drained else pending) and all((request and deferred.get(tid)==request
            and (root/(tid+'-attempt-'+str(attempt)+'.binding.json')).is_file()
            ) or (not request and prepared and unknown.get(tid)=={'prepared_at':prepared,
                'question_sha256':question_digest(question)})
            for tid,request,attempt,prepared,question in rows))
    except (OSError,ValueError,sqlite3.Error):return False

def valid_day(day):
    if not isinstance(day,str) or len(day)!=10:raise ValueError('请选择有效日期')
    try:parsed=datetime.strptime(day,'%Y-%m-%d').date()
    except ValueError:raise ValueError('请选择有效日期')
    if parsed.isoformat()!=day:raise ValueError('请选择有效日期')
    return day


def daily_unavailable(db, model, day):
    """Read terminal non-samples from today's immutable collector journals."""
    if model not in DOUBAO_CHANNELS and model!='baidu_ai':return {}
    start=datetime.strptime(valid_day(day),'%Y-%m-%d').replace(tzinfo=ZONE)
    counts=Counter()
    native=model in DOUBAO_CHANNELS
    table='tasks' if native else 'captures'
    jobs=db.execute("select health,config from jobs where model=? and created>=? and created<?",
                    (model,start.timestamp(),(start+timedelta(days=1)).timestamp()))
    for job in jobs:
        if json.loads(job['config']).get('daily_date')!=day:continue
        path=Path(job['health']).parent/('tasks.sqlite' if native else 'collector/tasks.sqlite')
        if not path.is_file():continue
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=2)) as journal:
            if not journal.execute('select 1 from sqlite_master where name=?',(table,)).fetchone():continue
            sql=("select question,count(*) from tasks where state='completed_nontext' group by question"
                 if native else """select question,count(*) from captures where state='completed'
                 and json_extract(result,'$.availability')='supplement_unavailable'
                 and json_extract(result,'$.terminal_reason')='card_unavailable' group by question""")
            for question,n in journal.execute(sql):
                counts[question]+=n
    return counts

def installed(db):
    db.execute('''create table if not exists daily_tasks(
      model text not null,day text not null,config text not null,revision integer not null,
      desired text not null,status text not null,batch text,updated real not null,error text,
      primary key(model,day))''')
    db.execute('''create table if not exists daily_launches(
      id text primary key,model text,day text,revision integer,base_batch text,
      execution text,created real)''')

def database_counts(day):
    valid_day(day)
    with _lock:
        cached=_cache.get(day)
        if cached and time.time()-cached[0]<3:return cached[1]
        sql="""select coalesce(json_agg(t),'[]') from (
          select e.source_device,coalesce(nullif(e.record->>'prompt',''),e.record->'capture_result'->>'question',e.record->>'question') question,coalesce(e.record->>'batch_id','') batch,count(*) n
          from monitor_ingest_events e join monitor_runs r on r.model_id=e.model_id and r.run_id=e.run_id
          where e.run_id<>'' and r.day='%s' and r.status='success' and coalesce(r.payload->>'body_capture_complete','true')='true'
          and e.source_device in (%s) group by 1,2,3)t"""%(day,','.join("'"+s+"'" for s in DEVICES))
        rows=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True,timeout=12))
        result={model:{} for model in MODELS}
        for row in rows:
            model=DEVICES[row['source_device']]
            if not belongs_to_daily_plan(model,row.get('batch',''),day):continue
            target=result[model]
            target[row['question']]=target.get(row['question'],0)+int(row['n'])
        _cache[day]=(time.time(),result)
        return result

def belongs_to_daily_plan(model,batch,day,base=Path('/opt/monitor/geo-capture')):
    """A late Doubao receipt cannot satisfy a different day's task target."""
    if model not in {'doubao1','doubao2','doubao3','doubao4'}:return True
    # Exact server-generated identities only; never interpret input as a path.
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,180}',batch):return False
    config=read(base/'panel/jobs'/(batch+'.json'))
    assigned=config.get('daily_date')
    if assigned:return assigned==day
    # Preserve older server jobs created before daily_date was added.
    match=re.fullmatch(r'geo-panel-doubao[1-4]-(\d{4})(\d{2})(\d{2})-.*',batch)
    return bool(match and '-'.join(match.groups())==day)

class DailyTasks:
    def __init__(self,control,counts=None):
        self.control=control
        self.last_logged={}
        self.counts=counts or getattr(control,'daily_counts',None) or (database_counts if control.base==Path('/opt/monitor/geo-capture') else lambda day:{})

    def web_peer_busy(self,db,model):
        peer=WEB_PEERS.get(model)
        return bool(peer and self.control.system.state(self.control.current(db,peer)['service']) in BUSY)

    def row(self,db,model,day):
        found=db.execute('select * from daily_tasks where model=? and day=?',(model,day)).fetchone()
        return dict(found) if found else None

    def config(self,db,model,day):
        row=self.row(db,model,day)
        if row:return json.loads(row['config'])
        if day>=today():return json.loads(db.execute('select value from settings where model=?',(model,)).fetchone()[0])
        end=datetime.strptime(day,'%Y-%m-%d').replace(tzinfo=ZONE)+timedelta(days=1)
        job=db.execute('select config from jobs where model=? and created<? order by created desc limit 1',(model,end.timestamp())).fetchone()
        if job:
            config=json.loads(job[0]);return {k:config[k] for k in ('questions','rounds','interval')}
        return {'questions':[],'rounds':0,'interval':MODELS[model]['minimum']}

    def snapshot(self,db,model,day,counts,error=None):
        config=self.config(db,model,day);row=self.row(db,model,day)
        unavailable=daily_unavailable(db,model,day)
        questions=[{'question':q,'kind':'secondary' if q in config.get('secondary_questions',[]) else 'primary','target':question_target(config,q),'completed':counts.get(q,0),
                    'unavailable':min(unavailable.get(q,0),max(0,question_target(config,q)-counts.get(q,0))),
                    'remaining':max(0,question_target(config,q)-counts.get(q,0)-unavailable.get(q,0))} for q in config['questions']]
        remaining=sum(q['remaining'] for q in questions)
        missed=sum(q['unavailable'] for q in questions)
        job=self.control.current(db,model);current=self.control.snapshot(job)
        status=row['status'] if row else 'scheduled' if day>today() else 'not_started'
        if not error and questions and not remaining:status='complete_with_unavailable' if missed else 'complete'
        elif row and row['desired']=='paused':status='pausing' if day==today() and current['service_state'] in BUSY else 'paused'
        elif day==today() and current['service_state'] in BUSY:
            status='applying' if row and row['status']=='applying' else current['state']
        elif day<today():status='incomplete' if remaining else 'complete'
        if not questions:status='not_scheduled'
        return {'date':day,'config':config,'status':status,'desired':row['desired'] if row else None,
                'target':sum(q['target'] for q in questions),'completed':sum(q['completed'] for q in questions),
                'credited':sum(min(q['completed'],q['target']) for q in questions),'remaining':remaining,'unavailable':missed,
                'questions':questions,'error':error or (row['error'] if row else None),
                'progress_available':not bool(error),
                'updated_at':row['updated'] if row else None,'editable':day>=today(),
                'managed':bool(row),'batch':row['batch'] if row else None}

    def view(self,db,day):
        valid_day(day)
        try:counts=self.counts(day);error=None
        except Exception:counts={};error='当天入库进度暂不可用，后台保留原计划，请稍后重试'
        return {model:self.snapshot(db,model,day,counts.get(model,{}),error) for model in MODELS if model not in DEEPSEEK_CHANNELS}

    def request(self,db,model,day,config,revision,desired,*,apply=False):
        if valid_day(day)<today():raise ValueError('历史计划只供查看，请选择今天或未来日期')
        old=self.row(db,model,day)
        if apply and old and old['desired']=='paused':desired='paused'
        current=self.control.current(db,model)
        status='applying' if apply and desired=='running' else 'paused' if desired=='paused' else 'queued'
        if day>today() and desired=='running':status='scheduled'
        db.execute('insert into daily_tasks values(?,?,?,?,?,?,?,?,?) on conflict(model,day) do update set config=excluded.config,revision=excluded.revision,desired=excluded.desired,status=excluded.status,updated=excluded.updated,error=null',
                   (model,day,json.dumps(config,ensure_ascii=False),revision,desired,status,None,time.time(),None))
        snap=self.control.snapshot(current)
        if day==today() and (snap['service_state'] in BUSY or snap['state'] not in {'complete','complete_with_unavailable'}) and (apply or desired=='paused'):
            # Existing workers drain at the safe question/receipt boundary.
            marker=self.control.marker(current)
            if not marker.exists():atomic(marker,{'requested_at':time.time(),'source':'daily_tasks','action':'apply' if apply else 'pause','day':day})
        return {'ok':True,'message':('已保存所选日期的计划；将在当天按设置执行' if desired=='running' else '已暂停所选日期的任务') if day>today() else
                '已保存并立即应用；当前题完成回传后按新配置继续' if desired=='running' and apply else
                '配置已保存生效，今天保持手动暂停' if apply else '已请求暂停今天的任务' if desired=='paused' else '已请求继续今天的剩余任务',
                'revision':revision,'daily':True}

    def ensure_scheduled(self,db,model,day,desired='running'):
        if model in DEEPSEEK_CHANNELS:return
        settings=db.execute('select value,revision from settings where model=?',(model,)).fetchone()
        db.execute('insert or ignore into daily_tasks values(?,?,?,?,?,?,?,?,?)',
                   (model,day,settings[0],settings[1],desired,'queued' if desired=='running' else 'not_started',None,time.time(),None))

    def reconcile(self):
        """One operator process runs this; HTTP handlers only persist intents."""
        day=today()
        if (read(self.control.base/'daily_plan.json').get('secondary_monitoring_enabled')
                and time.monotonic()-getattr(self,'last_monthly_sync',-60)>=60):
            self.last_monthly_sync=time.monotonic()
            from monthly_monitoring import database_questions,sync
            try:health=sync(self.control,day,database_questions(day))
            except Exception as exc:
                # A source outage must not erase last-known plans or stop collectors.
                health={'status':'retrying','checked_at':time.time(),'error_code':type(exc).__name__}
            atomic(self.control.base/'secondary_monitoring_health.json',health)
        counts=self.counts(day)
        order=['doubao1','doubao2','doubao3','doubao4','baidu_ai','wenxin_card','yuanbao']
        for model in order:
            try:self._one(model,day,counts)
            except Exception as exc:
                # Keep controlled messages only; no raw command output/secrets.
                message=str(exc) if isinstance(exc,(Conflict,ValueError)) else '后台正在重试：'+type(exc).__name__
                with self.control.connect() as db:
                    db.execute('update daily_tasks set error=?,updated=? where model=? and day=?',(message,time.time(),model,day))
            else:
                with self.control.connect() as db:
                    db.execute("update daily_tasks set error=null,updated=? where model=? and day=? and error like '后台正在重试：%'",(time.time(),model,day))
        with self.control.connect() as db:
            rows=[dict(r) for r in db.execute('select model,status,batch,error,updated from daily_tasks where day=?',(day,)) if r['model'] not in DEEPSEEK_CHANNELS]
        plan=read(self.control.base/'daily_plan.json')
        by_model={r['model']:r for r in rows}
        for model in MODELS:
            if model in DEEPSEEK_CHANNELS:continue
            row=by_model.get(model,{})
            desktop=model in plan.get('desktop_collectors',[])
            state=row.get('status') or ('external' if desktop else 'not_scheduled')
            received=sum(counts.get(model,{}).values())
            signature=(day,state,row.get('batch'),row.get('error'),received)
            if self.last_logged.get(model)!=signature:
                from browser_backend import enabled as browser_enabled
                backend='desktop_extension' if desktop else 'browser_extension' if browser_enabled(model,self.control.base) else None
                log_channel(model,'daily_status',row.get('batch'),backend=backend,day=day,
                            status=state,received=received,error=row.get('error'))
                self.last_logged[model]=signature
        if rows:atomic(self.control.base/'daily'/day/'status.json',{'at':time.time(),'day':day,'models':rows})

    def login_ready(self,db,model,job,revision):
        if model not in DEEPSEEK_CHANNELS:return True
        from control_panel import read_login
        login=read_login(db,model)
        if login.get('status')=='ready' and time.time()-login.get('checked_at',0)<=240 and login.get('revision')==revision and login.get('batch')==job['batch']:return True
        row=self.row(db,model,today())
        if row and row['status']=='checking_login' and time.time()-row['updated']<60:return False
        db.commit();self.control._login(model,job,False,revision)
        login=read_login(db,model)
        db.execute('update daily_tasks set status=?,updated=? where model=? and day=?',
                   ('waiting_login' if login.get('status')=='login_required' else 'queued' if login.get('status')=='ready' else 'checking_login',time.time(),model,today()))
        return False

    def _one(self,model,day,counts):
        c=self.control
        with c.lock,c.connect() as db:
            row=self.row(db,model,day)
            if not row:return
            if row['desired']=='observing':return
            if model in DEEPSEEK_CHANNELS and row['desired']!='paused':
                monitored=read(c.base/'auth-monitor'/(model+'.json'))
                if monitored.get('status') in {'login_required','risk_blocked','verification_required'}:
                    job=c.current(db,model);snap=c.snapshot(job)
                    if snap['service_state'] in BUSY and not c.marker(job).exists():
                        atomic(c.marker(job),{'requested_at':time.time(),'source':'auth_monitor','action':'account_block'})
                    # A manual login flow releases this gate only after strict ready.
                    db.execute('update daily_tasks set status=? where model=? and day=?',('waiting_login' if monitored['status']=='login_required' else 'waiting_verification',model,day))
                    return
            if row['status']=='scheduled':
                from daily_dispatch import due
                if not due(read(c.base/'daily_plan.json'),datetime.now(ZONE)):return
            active_revision=db.execute('select revision from settings where model=?',(model,)).fetchone()[0]
            if row['desired']=='paused':
                job=c.current(db,model);snap=c.snapshot(job)
                if snap['service_state'] in BUSY and not c.marker(job).exists():
                    atomic(c.marker(job),{'requested_at':time.time(),'source':'daily_tasks','action':'pause','day':day})
                db.execute('update daily_tasks set status=? where model=? and day=?',('pausing' if snap['service_state'] in BUSY else 'paused',model,day));return
            if str(row['batch'] or '').startswith('launch:'):
                key=row['batch'][7:]
                launch=db.execute('select * from daily_launches where id=?',(key,)).fetchone()
                command=db.execute('select result from commands where id=?',(key,)).fetchone()
                if command:
                    result=json.loads(command[0]);batch=result.get('batch')
                    if not batch:raise Conflict('正在核对已提交的启动操作')
                    db.execute('update daily_tasks set batch=?,status=? where model=? and day=?',(batch,'applying' if launch and launch['revision']!=row['revision'] else 'running',model,day))
                    db.commit();row=self.row(db,model,day)
                elif launch:
                    if launch['revision']!=row['revision']:
                        db.execute('update daily_tasks set batch=null,status=? where model=? and day=?',('applying',model,day));db.commit();row=self.row(db,model,day)
                    else:self.launch(db,model,day,row,json.loads(launch['execution']),key,launch['base_batch']);return
                else:raise Conflict('启动记录不完整，保留任务等待核对')
            job=c.current(db,model);snap=c.snapshot(job);cfg=json.loads(row['config'])
            if snap['service_state'] in BUSY:
                if (model in DOUBAO_CHANNELS
                        and datetime.fromtimestamp(job['created'],ZONE).date().isoformat()<day
                        and not snap['pending_delivery'] and not snap['delivery_errors']
                        and deferred_originals_allow_progress(c.batch_root(job),drained=True)):
                    # Stop only a drained previous-day worker. Rollover will
                    # archive its unresolved originals before launching today.
                    subprocess.run(['systemctl','stop','--no-block',job['service']],
                                   check=True,capture_output=True,timeout=10)
                    return
                if row['status']=='applying' and json.loads(job['config']).get('daily_revision')!=row['revision'] and not c.marker(job).exists():
                    atomic(c.marker(job),{'requested_at':time.time(),'source':'daily_tasks','action':'apply','day':day})
                elif (row['batch']==job['batch'] and json.loads(job['config']).get('daily_revision')==row['revision']
                      and read(job['health']).get('status') in {'running','running_recovery'}
                      and snap['state'] in {'running','running_recovery'}
                      and not snap['pending_delivery'] and not snap['delivery_errors']):
                    db.execute('update daily_tasks set status=?,error=null where model=? and day=?',
                        ('recovering' if read(job['health']).get('status')=='running_recovery' else 'running',model,day))
                return
            # A later term edit can reopen Baidu while Wenxin is already in
            # flight. Both the start and recovery paths must yield to the peer.
            if self.web_peer_busy(db,model):
                db.execute('update daily_tasks set status=? where model=? and day=?',
                           ('waiting_for_wenxin' if model=='baidu_ai' else 'waiting_for_baidu',model,day))
                return
            raw_state=read(job['health']).get('status')
            if snap['state']=='waiting_verification' or raw_state=='waiting_verification':
                db.execute('update daily_tasks set status=? where model=? and day=?',(snap['state'],model,day));return
            if snap['state']=='waiting_login' or raw_state=='waiting_login' or row['status']=='waiting_login':
                from control_panel import read_login
                login=read_login(db,model)
                if (login.get('status') not in {'ready','locally_logged_in'} or login.get('batch')!=job['batch']
                        or login.get('revision')!=active_revision or time.time()-login.get('checked_at',0)>240):
                    if (model in DEEPSEEK_CHANNELS and job['service'].startswith('geo-native@')
                            and time.time()-login.get('checked_at',0)>30):
                        # Scrcpy login is detected without requiring a panel click.
                        db.commit();c._login(model,job,False,active_revision)
                    db.execute('update daily_tasks set status=? where model=? and day=?',('waiting_login',model,day));return
            c._ensure_delivery(job)
            unavailable=daily_unavailable(db,model,day)
            same_day_archive=None
            if model in DOUBAO_CHANNELS and hasattr(c,'deferred_segments'):
                archived=c.deferred_segments(model,day)
                blocked={digest for questions in archived.values() for digest in questions}
                if snap['needs_review'] and job['batch'] not in archived:
                    candidates=c.deferable_segment(job,day,snap)
                    if candidates and any(counts.get(model,{}).get(q,0)+unavailable.get(q,0)<question_target(cfg,q)
                                          and question_digest(q) not in blocked and question_digest(q) not in candidates
                                          for q in cfg['questions']):
                        same_day_archive=candidates
                        blocked.update(candidates)
            else:
                archived={};blocked=set()
            skip_readback=bool(same_day_archive or job['batch'] in archived)
            if snap['needs_review'] and not skip_readback:
                old_day=datetime.fromtimestamp(job['created'],ZONE).date().isoformat()
                if old_day>=day:
                    if (deferred_originals_allow_progress(c.batch_root(job),drained=True)
                            and read(job['health']).get('next_readback_at',0)>time.time()):
                        db.execute('update daily_tasks set status=? where model=? and day=?',
                                   ('needs_attention',model,day))
                        return
                    # Continue this original request through the existing strict
                    # readback path. New work remains blocked until it is known.
                    c._ensure_known(job,allow_readback=True)
                    if deferred_originals_allow_progress(c.batch_root(job)):
                        marker=read(c.marker(job))
                        if marker.get('source')=='daily_tasks' and marker.get('allow_original_readback') is True:
                            c.marker(job).unlink(missing_ok=True)
                    else:
                        atomic(c.marker(job),{'requested_at':time.time(),'source':'daily_tasks','action':'apply',
                                              'allow_original_readback':True,'day':day})
                    c.system.start(job['service'])
                    db.execute('update daily_tasks set status=? where model=? and day=?',('recovering',model,day));return
            same_revision=json.loads(job['config']).get('daily_revision')==row['revision']
            if not skip_readback and row['batch']==job['batch'] and same_revision and snap['state'] not in {'complete','complete_with_unavailable'}:
                c._ensure_known(job,allow_readback=True)
                if not self.login_ready(db,model,job,active_revision):return
                c.marker(job).unlink(missing_ok=True);c.system.start(job['service']);return
            # A just-processed receipt must be reflected before deciding the
            # next remaining group; never plan from a cached pre-completion count.
            with _lock:_cache.pop(day,None)
            counts=self.counts(day)
            remaining={q:max(0,question_target(cfg,q)-counts.get(model,{}).get(q,0)-unavailable.get(q,0)) for q in cfg['questions']}
            remaining={q:n for q,n in remaining.items() if n}
            if not remaining:
                status='complete_with_unavailable' if any(unavailable.get(q,0) and counts.get(model,{}).get(q,0)<question_target(cfg,q) for q in cfg['questions']) else 'complete'
                db.execute('update daily_tasks set status=?,error=null where model=? and day=?',(status,model,day));return
            remaining={q:n for q,n in remaining.items() if question_digest(q) not in blocked}
            if not remaining:
                db.execute('update daily_tasks set status=?,error=? where model=? and day=?',
                           ('needs_attention','剩余题目有原请求待核对，已保留记录',model,day));return
            if model=='wenxin_card':
                bcfg=self.config(db,'baidu_ai',day)
                baidu_job=c.snapshot(c.current(db,'baidu_ai'))
                baidu_missed=daily_unavailable(db,'baidu_ai',day)
                if (baidu_job['service_state'] in BUSY or baidu_job['pending_delivery'] or baidu_job['delivery_errors']
                        or any(counts.get('baidu_ai',{}).get(q,0)+baidu_missed.get(q,0)<question_target(bcfg,q) for q in bcfg['questions'])):
                    db.execute('update daily_tasks set status=? where model=? and day=?',('waiting_for_baidu',model,day));return
            rounds=max(remaining.values())
            execution={'questions':[q for q,n in remaining.items() if n==rounds], 'rounds':rounds,'interval':cfg['interval']}
            if not self.login_ready(db,model,job,active_revision):return
            if same_day_archive:
                c.archive_deferred_segment(job,day,same_day_archive)
            # Each segment is immutable and only covers the remaining rounds
            # for one group. Completed observations are never copied or resent.
            signature=json.dumps([day,model,row['revision'],job['batch'],execution],sort_keys=True,ensure_ascii=False)
            key=hashlib.sha256(('daily-segment:'+signature).encode()).hexdigest()[:32]
            db.execute('insert or ignore into daily_launches values(?,?,?,?,?,?,?)',
                       (key,model,day,row['revision'],job['batch'],json.dumps(execution,ensure_ascii=False),time.time()))
            changed=db.execute("update daily_tasks set batch=? where model=? and day=? and revision=? and desired='running'",('launch:'+key,model,day,row['revision'])).rowcount
            if not changed:return
            db.commit()
            self.launch(db,model,day,row,execution,key,job['batch'])

    def launch(self,db,model,day,row,execution,key,base_batch):
        c=self.control
        if self.web_peer_busy(db,model):raise Conflict('共享网页通道正在采集，等待当前批次结束')
        c.execution_config=execution
        c.execution_metadata={'daily_revision':row['revision'],'daily_date':day,
                              'daily_target_rounds':json.loads(row['config'])['rounds']}
        if hasattr(c,'rollover_batch'):c.rollover_batch=base_batch
        active_revision=db.execute('select revision from settings where model=?',(model,)).fetchone()[0]
        try:result=c.action(model,'new',{'revision':active_revision},key)
        finally:
            c.execution_config=None;c.execution_metadata=None
            if hasattr(c,'rollover_batch'):c.rollover_batch=None
        if not result.get('batch'):raise Conflict('未确认新任务身份，后台将继续核对')
        db.execute("update daily_tasks set batch=?,status=case when revision=? then 'running' else 'applying' end,error=null,updated=? where model=? and day=?",
                   (result['batch'],row['revision'],time.time(),model,day))

def run():
    from daily_dispatch import DailyController
    from geo_source_cards.runtime import process_lock
    control=DailyController();tasks=DailyTasks(control)
    with process_lock(control.base/'daily_control.lock'):
        while True:
            try:
                tasks.reconcile();health={'status':'running','time':time.time()}
            except Exception as exc:health={'status':'retrying','time':time.time(),'error_code':type(exc).__name__}
            atomic(control.base/'daily_control_health.json',health)
            time.sleep(3)

if __name__=='__main__':run()
