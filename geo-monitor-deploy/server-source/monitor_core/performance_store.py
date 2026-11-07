"""Manual performance inputs, optimistic concurrency and immutable edit audit."""
from __future__ import annotations
import copy,hashlib,json,math,os,re,sqlite3,threading
from contextlib import contextmanager,closing
from datetime import date,datetime
from pathlib import Path
from zoneinfo import ZoneInfo

FIELDS={'traffic','expenses','traffic_target','budget_limit'}
_lock=threading.Lock()
_initialized=set()
class ConflictError(ValueError):pass

def database_path():
    return Path(os.environ.get('MONITOR_PERFORMANCE_DB',str(Path(__file__).resolve().parents[1]/'runtime/performance.sqlite')))

def template(month=None):
    name='performance_data_'+str(month).replace('-','')+'.json'
    path=Path(__file__).with_name(name) if month and re.fullmatch(r'\d{4}-\d{2}',month) else None
    return json.loads((path if path and path.is_file() else Path(__file__).with_name('performance_data_202610.json')).read_text('utf8'))

def today():return datetime.now(ZoneInfo('Asia/Shanghai')).date()

def valid_month(month):
    if not re.fullmatch(r'\d{4}-(?:0[1-9]|1[0-2])',str(month)) or not '2026-10'<=month<=today().strftime('%Y-%m'):
        raise ValueError('请选择2026年10月起、不晚于本月的月份')

@contextmanager
def connection():
    path=database_path();path.parent.mkdir(parents=True,exist_ok=True)
    with _lock:
        if str(path) not in _initialized or not path.exists():
            with closing(sqlite3.connect(path,timeout=30)) as db:
                db.execute('pragma journal_mode=WAL')
                db.execute('create table if not exists cells(month text,product text,day text,field text,value integer,revision integer not null,updated_by text,updated_at text,primary key(month,product,day,field))')
                db.execute('create table if not exists edits(id integer primary key,month text,product text,day text,field text,old_value integer,new_value integer,revision integer,actor text,at text,operation_id text)')
                db.execute('create table if not exists operations(id text primary key,payload_hash text,result text)')
                db.execute('create table if not exists metadata(key text primary key,value integer)')
                db.execute('insert or ignore into metadata values(?,?)',('revision',0))
                if not db.execute('select 1 from metadata where key=?',('seeded',)).fetchone():
                    seed=template();at=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
                    for p in seed['products']:
                        records=[('2026-10-01','traffic_target',int(p['daily_traffic_target'])),('2026-10-01','budget_limit',round(p['monthly_budget']*100))]
                        records += [(day,'traffic',int(value)) for day,value in p['traffic'].items() if value is not None]
                        records += [(day,'expenses',round(value*100)) for day,value in p['cumulative_expenses'].items()]
                        db.executemany('insert or ignore into cells values(?,?,?,?,?,?,?,?)', [('2026-10',p['product'],day,field,value,1,'historical_import',at) for day,field,value in records])
                    db.execute('insert into metadata values(?,?)',('seeded',1))
                db.commit()
            _initialized.add(str(path))
    db=sqlite3.connect(path,timeout=30);db.row_factory=sqlite3.Row
    try:yield db
    finally:db.close()

def revision():
    with connection() as db:return int(db.execute('select value from metadata where key=?',('revision',)).fetchone()[0])

def available_months():
    with connection() as db:months={r[0] for r in db.execute('select distinct month from cells')}
    months.add(today().strftime('%Y-%m'))
    return sorted(months,reverse=True)

def month_config(month):
    valid_month(month);config=copy.deepcopy(template(month));config['month']=month
    for p in config['products']:p['traffic']={};p['cumulative_expenses']={}
    by_name={p['product']:p for p in config['products']}
    with connection() as db:
        rows=list(db.execute('select * from cells where month=?',(month,)))
        current_revision=int(db.execute('select value from metadata where key=?',('revision',)).fetchone()[0])
    for row in rows:
        p=by_name.get(row['product'])
        if not p:continue
        value=row['value'];field=row['field']
        if field=='traffic':p['traffic'][row['day']]=value
        elif field=='expenses' and value is not None:p['cumulative_expenses'][row['day']]=value/100
        elif field=='traffic_target' and value is not None:p['daily_traffic_target']=value
        elif field=='budget_limit' and value is not None:p['monthly_budget']=value/100
    config['manual_data_revision']=current_revision
    config['targets_confirmed']=(bool(config.get('targets_confirmed')) or all(any(r['product']==p and r['field']==f and r['value'] is not None for r in rows) for p in by_name for f in ['traffic_target','budget_limit']))
    return config

def editor_data(month,day):
    valid_month(month)
    try:parsed=date.fromisoformat(day)
    except (ValueError,TypeError):raise ValueError('请选择有效日期') from None
    if parsed.strftime('%Y-%m')!=month or parsed>today():raise ValueError('日期必须在所选月份内，且不能晚于今天')
    config=month_config(month);rows=[]
    with connection() as db:
        for p in config['products']:
            fields={}
            for field in FIELDS:
                cell_day=month+'-01' if field in {'traffic_target','budget_limit'} else day
                row=db.execute('select * from cells where month=? and product=? and day=? and field=?',(month,p['product'],cell_day,field)).fetchone()
                fallback=p['daily_traffic_target'] if field=='traffic_target' else p['monthly_budget'] if field=='budget_limit' else None
                value=(row['value']/100 if field in {'expenses','budget_limit'} else row['value']) if row and row['value'] is not None else fallback
                fields[field]={'value':value,'revision':row['revision'] if row else 0,'updated_by':row['updated_by'] if row else None,'updated_at':row['updated_at'] if row else None}
            rows.append({'product':p['product'],'owner':p['owner'],'priority':p['priority'],'fields':fields})
        history=[dict(r) for r in db.execute('select product,day,field,old_value,new_value,actor,at from edits where month=? order by id desc limit 30',(month,))]
    for item in history:
        if item['field'] in {'expenses','budget_limit'}:
            for key in ['old_value','new_value']:
                if item[key] is not None:item[key]/=100
    return {'month':month,'date':day,'rows':rows,'revision':config['manual_data_revision'],'targets_confirmed':config['targets_confirmed'],'history':history}

def save(payload,actor):
    if actor!='superadmin':raise PermissionError('仅superadmin可以录入绩效数据')
    if not isinstance(payload,dict):raise ValueError('需要JSON对象')
    month=payload.get('month');valid_month(month)
    operation=payload.get('operation_id','')
    if not re.fullmatch(r'[a-f0-9]{32}',str(operation)):raise ValueError('保存操作编号无效')
    changes=payload.get('changes')
    if not isinstance(changes,list) or not 1<=len(changes)<=60:raise ValueError('每次请保存1至60个数据单元格')
    products={p['product'] for p in template(month)['products']};validated=[];seen=set()
    for item in changes:
        if not isinstance(item,dict):raise ValueError('数据单元格格式无效')
        product=item.get('product');field=item.get('field');day=item.get('date');value=item.get('value');expected=item.get('expected_revision')
        if product not in products or field not in FIELDS:raise ValueError('产品或数据类型不在考核范围')
        try:parsed=date.fromisoformat(day)
        except (ValueError,TypeError):raise ValueError('日期无效') from None
        if parsed.strftime('%Y-%m')!=month or parsed>today():raise ValueError('只能填写本考核月份内、不晚于今天的数据')
        if field in {'traffic_target','budget_limit'} and day!=month+'-01':raise ValueError('月度目标须保存到当月1日')
        if type(expected) is not int or expected<0:raise ValueError('数据版本无效，请重新加载')
        if (product,day,field) in seen:raise ValueError('同一单元格不能重复保存')
        seen.add((product,day,field))
        if value is not None:
            if type(value) not in (int,float) or not math.isfinite(value) or not 0<=value<=1_000_000_000:raise ValueError('请输入非负的有效数字')
            scale=100 if field in {'expenses','budget_limit'} else 1
            if abs(value*scale-round(value*scale))>1e-5:raise ValueError('流量须为整数，金额最多两位小数')
            if field=='traffic_target' and value==0:raise ValueError('每日目标须大于0')
            value=round(value*scale)
        elif field in {'traffic_target','budget_limit'}:raise ValueError('月度目标不能为空')
        validated.append((product,day,field,value,expected))
    signature=hashlib.sha256(json.dumps({'month':month,'changes':changes},ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    at=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()
    with connection() as db:
        db.execute('begin immediate')
        try:
            old=db.execute('select * from operations where id=?',(operation,)).fetchone()
            if old:
                if old['payload_hash']!=signature:raise ConflictError('操作编号已用于不同数据，请重新加载')
                return json.loads(old['result'])
            updated=0
            for product,day,field,value,expected in validated:
                old=db.execute('select * from cells where month=? and product=? and day=? and field=?',(month,product,day,field)).fetchone()
                current=old['revision'] if old else 0
                if current!=expected:raise ConflictError('数据已被修改，请重新加载后核对再保存：'+product)
                if old and old['value']==value or not old and value is None:continue
                db.execute('insert or replace into cells values(?,?,?,?,?,?,?,?)',(month,product,day,field,value,current+1,actor,at))
                db.execute('insert into edits(month,product,day,field,old_value,new_value,revision,actor,at,operation_id) values(?,?,?,?,?,?,?,?,?,?)',(month,product,day,field,old['value'] if old else None,value,current+1,actor,at,operation))
                updated+=1
            if updated:db.execute('update metadata set value=value+1 where key=?',('revision',))
            result={'ok':True,'updated_cells':updated,'revision':int(db.execute('select value from metadata where key=?',('revision',)).fetchone()[0]),'saved_at':at,'saved_by':actor}
            db.execute('insert into operations values(?,?,?)',(operation,signature,json.dumps(result,ensure_ascii=False)))
            db.commit();return result
        except Exception:db.rollback();raise
