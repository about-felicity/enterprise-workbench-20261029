import hashlib,json,shutil,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
# Reproduce the real import order before loading the patched matcher.
import monitor_core.cdp_chat
print('Initially loaded package:',sys.modules['monitor_core'].__file__)
import creation.owned_sources as owned
exec(compile(Path('/tmp/fixed-owned_sources.py').read_text(),owned.__file__,'exec'),owned.__dict__)
assert owned.ownership({'title':'科熙本控油蓬松洗发水评测'})['owned']
assert not owned.ownership({'title':'如何选择洗发水','article':{'text':'根据头皮出油情况选择清洁产品。'}})['owned']
print('Import-order regression and ownership checks passed')
backup=Path('/opt/monitor/geo-content/maintenance/20261027-creation-import');backup.mkdir(parents=True,exist_ok=True)
for name in ['owned_sources.py','worker.py']:
    dst=Path('/opt/monitor/geo-content/creation')/name
    saved=backup/name
    if not saved.exists():shutil.copy2(dst,saved)
    incoming=Path('/tmp')/('fixed-'+name)
    compile(incoming.read_text(),str(dst),'exec')
    shutil.copyfile(incoming,dst)
    print(name,hashlib.sha256(dst.read_bytes()).hexdigest())
from creation.runtime import read,resume
from creation.recovery import safe_original
resumed=[]
for root in Path('/opt/monitor/geo-content/runtime/runs').iterdir():
    error=read(root/'geo_worker.json');control=read(root/'control.json')
    if error.get('error_type')!='ModuleNotFoundError' or error.get('message')!="No module named 'monitor_core.analytics'":continue
    if not control.get('paused') or control.get('reason')!='execution_error' or not safe_original(root):continue
    archive=backup/root.name;archive.mkdir(exist_ok=True)
    for name in ['geo_worker.json','control.json','job.json']:
        shutil.copy2(root/name,archive/name)
    resume(root,check_balance=False)
    resumed.append(root.name)
(backup/'resumed.json').write_text(json.dumps(resumed,indent=2))
print('Resumed:',json.dumps(resumed))
