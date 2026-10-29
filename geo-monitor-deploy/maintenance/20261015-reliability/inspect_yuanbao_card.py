import json
from pathlib import Path
from urllib.parse import urlsplit
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261015-181821-d56b0d20')
raw=json.loads((root/'6281d5ee-597e-5d6d-b39b-a6112e17dfb4.native.json').read_text())
out=[]
def walk(value,path):
    if isinstance(value,dict):
        out.append({'path':path,'keys':list(value)})
        for k,v in value.items():walk(v,path+'.'+k)
    elif isinstance(value,list):
        out.append({'path':path,'items':len(value)})
        for i,v in enumerate(value):walk(v,path+'['+str(i)+']')
    elif isinstance(value,str):
        if value.strip().startswith(('{','[')):
            try:walk(json.loads(value),path+'(JSON)');return
            except ValueError:pass
        key=path.rsplit('.',1)[-1]
        safe={'path':path,'length':len(value)}
        if key.lower() in {'title','description','desc','summary','abstract','text','content','name','type','_type','label','source','key','mark','alt'}:safe['value']=value[:1200]
        if value.startswith(('http://','https://')):
            u=urlsplit(value);safe['url_without_query']=u.scheme+'://'+u.netloc+u.path
        out.append(safe)
    else:out.append({'path':path,'value':value})
for k in ['i','u','p','o','C']:walk(raw['render_snapshot'][k],k)
print(json.dumps(out,ensure_ascii=False))
