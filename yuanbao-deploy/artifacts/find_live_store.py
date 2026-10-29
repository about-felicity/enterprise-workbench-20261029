import sys,subprocess,json,os,re,zipfile
from pathlib import Path
sys.path.insert(0,'/tmp')
import yuanbao_native_storage as ns
app=ns.app_directory()
pid=subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat'],text=True).strip()
raw=subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','ls','-l','/proc/'+pid+'/fd'],text=True)
paths=[]
for line in raw.splitlines():
    if ' -> ' in line:
        p=line.split(' -> ',1)[1]
        if any(k in p.lower() for k in ['.ybdb','database','sqlite','.db']):
            paths.append(re.sub(r'/[A-Za-z0-9_-]{12,}(?=[/.])','/[redacted]',p))
print(json.dumps({'open_database_paths':sorted(set(paths))}))
headers=[]
for p in app.rglob('*'):
    if p.is_file() and ('.ybdb' in str(p) or p.name.endswith('.db')):
        with p.open('rb') as f:b=f.read(16)
        headers.append({'name':re.sub(r'[A-Za-z0-9_-]{12,}','[redacted]',str(p.relative_to(app))),'bytes':p.stat().st_size,'sqlite_header':b==b'SQLite format 3\0'})
print(json.dumps({'store_files':headers}))
from inspect_qr_dex import classes
with zipfile.ZipFile('/home/user/redroid-yuanbao/artifacts/yuanbao-official-5040.apk') as z:
    found=set()
    for name in z.namelist():
        if name.endswith('.dex'):
            found.update(c for c in classes(z.read(name)) if c.startswith('Lcom/tencent/wcdb/') and any(k in c for k in ['Database;','Handle;','PreparedStatement;','Value;','StatementSelect;']))
print(json.dumps({'wcdb_classes':sorted(found)}))
