"""Rebuild pinned generated model mappings from the exact installed APK."""
import zipfile,json,re,sys,struct,hashlib
from pathlib import Path
from loguru import logger
logger.disable('androguard')
from androguard.core.dex import DEX
def classes(b):
    ns,so=struct.unpack_from('<II',b,56);nt,to=struct.unpack_from('<II',b,64);nc,co=struct.unpack_from('<II',b,96)
    def string(i):
        p=struct.unpack_from('<I',b,so+4*i)[0]
        while b[p]&128:p+=1
        p+=1
        return b[p:b.index(0,p)].decode('utf8',errors='replace')
    return {string(struct.unpack_from('<I',b,to+4*struct.unpack_from('<I',b,co+32*i)[0])[0]) for i in range(nc)}
apk=Path('/home/user/redroid-yuanbao/artifacts/yuanbao-official-5040.apk')
assert hashlib.sha256(apk.read_bytes()).hexdigest()=='b2d6f674358bbc27b10e800bafd49ba4fc596291142148d7d09494097348c7dd', 'APK changed; inspect mappings first'

prefix='Lcom/tencent/hunyuan/mpcommon/generated/biz/chat/'
schema={};unmapped=[]
alphabet='bcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
with zipfile.ZipFile('/home/user/redroid-yuanbao/artifacts/yuanbao-official-5040.apk') as z:
    for name in z.namelist():
        if not name.endswith('.dex'):continue
        raw=z.read(name)
        if not any(c.startswith(prefix) for c in classes(raw)):continue
        dex=DEX(raw)
        for c in dex.get_classes():
            if not c.get_name().startswith(prefix) or '$' in c.get_name():continue
            fields=[f.get_name() for f in c.get_fields() if f.get_descriptor()=='Ljava/lang/Object;' and 'static' not in f.get_access_flags_string()]
            if not fields or any(f not in alphabet for f in fields):continue
            fields.sort(key=alphabet.index)
            labels=[]
            for method in c.get_methods():
                if method.get_name()!='toString':continue
                for ins in method.get_instructions():
                    if ins.get_name() not in ('const-string','const-string/jumbo'):continue
                    output=ins.get_output();s=output.split(', ',1)[1]
                    try:s=json.loads(s)
                    except ValueError:continue
                    m=re.search(r'(?:\(|, )([A-Za-z][A-Za-z0-9_]*)=$',s)
                    if m:labels.append(m[1])
            if len(labels)==len(fields) and len(set(labels))==len(labels):
                schema[c.get_name()[1:-1].replace('/','.')]=dict(zip(fields,labels))
            else:unmapped.append({'class':c.get_name(),'fields':len(fields),'labels':len(labels)})
out=Path('/home/user/redroid-yuanbao/tools/chat_model_schema.json')
out.write_text(json.dumps(schema,indent=2));out.chmod(0o600)
print(json.dumps({'mapped':len(schema),'critical':{k:schema.get(prefix[1:].replace('/','.')+k) for k in ['Message','Content','ContentMetaInfo','MessageEntity','TextEntity','TextEntityItem','Conversation']},'unmapped':unmapped[:12]}))

