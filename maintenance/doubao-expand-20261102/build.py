from pathlib import Path
import json,hashlib,zipfile
root=Path.cwd();w=root/'maintenance/doubao-expand-20261102'; manifest={}
def edit(name,fn):
 p=root/name; old=p.read_bytes();s=old.decode('utf-8-sig')
 dest=('/opt/monitor/geo-capture/' if name.startswith('geo-monitor') else '/home/user/redroid-doubao/'+('' if p.name=='runtime_preflight.py' else 'geo-batch-code/'))+p.name
 snap=root/'source-snapshot/server'/dest.lstrip('/')
 def sha(v):return hashlib.sha256(v.replace(b'\r\n',b'\n')).hexdigest()
 base=snap.read_bytes() if snap.exists() else old; new=fn(base.decode('utf-8-sig')); assert sha(old) in (sha(base),sha(new.encode())),name
 p.write_bytes(new.replace('\r\n','\n').encode())
 manifest[name]={'target':dest,'base':sha(base),'sha':sha(p.read_bytes())}
def ids(s):return s.replace("'doubao1','doubao2'","'doubao1','doubao2','doubao3','doubao4'")
def dev(s):return s.replace("'doubao2':('doubao-hpe14-account2','127.0.0.1:5558')","'doubao2':('doubao-hpe14-account2','127.0.0.1:5558'), 'doubao3':('doubao-hpe14-account3','127.0.0.1:5563'), 'doubao4':('doubao-hpe14-account4','127.0.0.1:5564')")
g='geo-monitor-deploy/';r='redroid-deploy/'
edit(g+'control_panel.py',lambda s:s.replace('for _meta in MODELS.values():',"for _lane in (3,4):\n    MODELS[f'doubao{_lane}']={**MODELS['doubao2'],'name':f'豆包 {_lane}'}\nfor _meta in MODELS.values():"))
edit(g+'native_entry.py',ids);edit(g+'daily_tasks.py',lambda s:ids(s).replace("'doubao-hpe14-account2':'doubao2',","'doubao-hpe14-account2':'doubao2','doubao-hpe14-account3':'doubao3','doubao-hpe14-account4':'doubao4',").replace('doubao[12]','doubao[1-4]'))
edit(g+'fleet_status.py',lambda s:s.replace('doubao1|doubao2|','doubao[1-4]|'))
edit(g+'login_probe.py',lambda s:dev(ids(s)));edit(r+'question_only_worker.py',lambda s:dev(ids(s)))
edit(r+'runtime_preflight.py',lambda s:s.replace("'doubao-hpe14-account2')","'doubao-hpe14-account2','doubao-hpe14-account3','doubao-hpe14-account4')"))
edit(r+'native_memory_guard.py',ids)
welcome=(w/'welcome.py').read_text('utf-8-sig').split("a=a[:pos]+'''")[1].split("'''+a[pos:]")[0]
welcome=welcome.replace('if len(lists)==1 and len(lists[0])==2:\n        greeting,suggestions=lists[0]', '''rows=list(lists[0]) if len(lists)==1 else []
    if len(rows)==3 and not any(n.get('text') or n.get('content-desc') or n.get('resource-id','').endswith('/content_view') for n in rows[0].iter()):rows=rows[1:]
    if len(rows)==2:
        greeting,suggestions=rows''')
def adapter(s):
 pos=s.index('    if not any(',s.index('def assert_question_only_composer'));return s[:pos]+welcome+s[pos:]
edit(r+'question_only_adapters.py',adapter)
with zipfile.ZipFile(w/'lanes.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in manifest:z.write(root/name,name)
 z.writestr('manifest.json',json.dumps(manifest))

