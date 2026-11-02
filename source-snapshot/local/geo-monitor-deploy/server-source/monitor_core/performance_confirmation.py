"""Server-owned monthly confirmation windows and immutable snapshot fingerprints."""
import calendar,hashlib,hmac,json,re,secrets,time
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

BEIJING=ZoneInfo('Asia/Shanghai')

def confirmation_window(month,now=None,deadline_hour=18):
    if not isinstance(month,str) or not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',month):
        raise ValueError('考核月份格式不正确')
    if deadline_hour not in (6,18):raise ValueError('确认截止时间不正确')
    now=now or datetime.now(BEIJING)
    if now.tzinfo is None:raise ValueError('必须提供带时区的时间')
    now=now.astimezone(BEIJING)
    year,number=map(int,month.split('-'))
    last=calendar.monthrange(year,number)[1]
    opens=datetime(year,number,last,tzinfo=BEIJING)
    deadline=opens.replace(hour=deadline_hour)
    state='open' if opens<=now<deadline else 'upcoming' if now<opens else 'closed'
    return {'month':month,'state':state,'opens_at':opens.isoformat(),
            'deadline':deadline.isoformat(),'server_time':now.isoformat(),
            'message':f'今日{deadline_hour:02d}:00前可以确认绩效' if state=='open' else
                      f'本月确认已截止（{last}日{deadline_hour:02d}:00）' if state=='closed' else
                      f'{number}月{last}日{deadline_hour:02d}:00前确认绩效'}

def snapshot_fingerprint(person,month):
    # Persist precisely the assessment the employee reviewed; do not accept a
    # browser-supplied score as the confirmed assessment.
    value={'month':month,'name':person['name'],'current':person['current']}
    raw=json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
    return raw,hashlib.sha256(raw.encode('utf8')).hexdigest()

PEOPLE=('佳佳','杨涛','小美','鑫悦','谭露')

@contextmanager
def database():
    from .performance_store import connection
    with connection() as db:
        db.executescript('''
        create table if not exists confirmation_passwords(name text primary key,salt text not null,digest text not null,failures integer not null default 0,locked_until real not null default 0,version integer not null default 1);
        create table if not exists confirmation_previews(token text primary key,name text,month text,session text,snapshot text,digest text,expires real,version integer);
        create table if not exists performance_confirmations(name text,month text,snapshot text,digest text,confirmed_at text,actor text,primary key(name,month));
        create table if not exists confirmation_audit(id integer primary key,name text,action text,actor text,at text,month text);
        ''')
        db.execute('begin immediate')
        try:yield db;db.commit()
        except Exception:db.rollback();raise

def password_hash(password,salt):
    return hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),600000).hex()

def valid_password(password):
    if not isinstance(password,str) or not 6<=len(password)<=128:
        raise ValueError('密码需为6至128个字符')

def verify_password(db,name,password):
    row=db.execute('select * from confirmation_passwords where name=?',(name,)).fetchone()
    if not row:raise ValueError('请先设置个人绩效确认密码')
    if row['locked_until']>time.time():raise ValueError('密码尝试过多，请15分钟后再试')
    if not hmac.compare_digest(row['digest'],password_hash(password,row['salt'])):
        count=row['failures']+1
        db.execute('update confirmation_passwords set failures=?,locked_until=? where name=?',(count,time.time()+900 if count>=5 else 0,name))
        db.commit() # Failed attempts must survive the rejected transaction.
        raise ValueError('个人绩效确认密码错误')
    db.execute('update confirmation_passwords set failures=0,locked_until=0 where name=?',(name,))
    return row

def audit(db,name,action,actor,month=''):
    db.execute('insert into confirmation_audit(name,action,actor,at,month) values(?,?,?,?,?)',
               (name,action,actor,datetime.now(BEIJING).isoformat(),month))

def status(month,actor):
    window=confirmation_window(month)
    with database() as db:
        people=[]
        for name in PEOPLE:
            configured=bool(db.execute('select 1 from confirmation_passwords where name=?',(name,)).fetchone())
            row=db.execute('select confirmed_at,snapshot,digest from performance_confirmations where name=? and month=?',(name,month)).fetchone()
            people.append({'name':name,'password_set':configured,'confirmed_at':row['confirmed_at'] if row else None,
                           'snapshot':json.loads(row['snapshot']) if row else None})
    return {'window':window,'people':people,'can_confirm':actor=='geo_admin','can_reset':actor=='superadmin'}

def act(payload,actor,session,assessment):
    name=payload.get('name');action=payload.get('action');month=payload.get('month')
    if name not in PEOPLE:raise ValueError('请选择考核员工')
    if action=='reset':
        if actor!='superadmin':raise PermissionError('仅superadmin可以重置确认密码')
        with database() as db:
            db.execute('delete from confirmation_passwords where name=?',(name,))
            db.execute('delete from confirmation_previews where name=?',(name,))
            audit(db,name,'reset_password',actor)
        return {'ok':True}
    if actor!='geo_admin':raise PermissionError('请使用geo_admin登录后操作个人确认')
    if action in ('setup','change'):
        password=payload.get('password');valid_password(password)
        with database() as db:
            old=db.execute('select * from confirmation_passwords where name=?',(name,)).fetchone()
            if action=='setup' and old:raise ValueError('该员工已设置密码，请输入原密码或联系superadmin重置')
            if action=='change':
                valid_password(payload.get('old_password'));old=verify_password(db,name,payload['old_password'])
            salt=secrets.token_hex(16)
            db.execute('insert or replace into confirmation_passwords(name,salt,digest,version) values(?,?,?,?)',
                       (name,salt,password_hash(password,salt),(old['version']+1) if old else 1))
            db.execute('delete from confirmation_previews where name=?',(name,));audit(db,name,action,actor)
        return {'ok':True}
    if action not in ('preview','confirm'):raise ValueError('未知确认操作')
    if confirmation_window(month)['state']!='open':raise ValueError('仅月底当天18:00前可以确认当月绩效')
    if action=='preview':
        data=assessment(month)
        person=next((p for p in data['people'] if p['name']==name),None)
        if not person or person['current']['score'] is None:raise ValueError('绩效分数尚未生成，请先补齐数据')
        raw,digest=snapshot_fingerprint(person,month);token=secrets.token_urlsafe(32)
        with database() as db:
            row=db.execute('select version from confirmation_passwords where name=?',(name,)).fetchone()
            if not row:raise ValueError('请先设置个人确认密码')
            db.execute('delete from confirmation_previews where expires<?',(time.time(),))
            db.execute('insert into confirmation_previews values(?,?,?,?,?,?,?,?)',(token,name,month,session,raw,digest,time.time()+300,row['version']))
        return {'ok':True,'token':token,'snapshot':json.loads(raw)}
    valid_password(payload.get('password'))
    with database() as db:
        credential=verify_password(db,name,payload['password'])
        old=db.execute('select confirmed_at from performance_confirmations where name=? and month=?',(name,month)).fetchone()
        if old:return {'ok':True,'confirmed_at':old['confirmed_at'],'already_confirmed':True}
        preview=db.execute('select * from confirmation_previews where token=?',(payload.get('token',''),)).fetchone()
        if not preview or preview['expires']<time.time() or preview['name']!=name or preview['month']!=month or preview['session']!=session or preview['version']!=credential['version']:
            raise ValueError('确认预览已过期，请重新核对绩效')
        if confirmation_window(month)['state']!='open':raise ValueError('本月确认时间已截止')
        at=datetime.now(BEIJING).isoformat()
        db.execute('insert into performance_confirmations values(?,?,?,?,?,?)',(name,month,preview['snapshot'],preview['digest'],at,actor))
        audit(db,name,'confirm',actor,month)
        db.execute('delete from confirmation_previews where name=? and month=?',(name,month))
    return {'ok':True,'confirmed_at':at}
