"""One-time dedicated, capture-only creation plan. Does not start paid writing."""
import json,os,pwd,shutil,subprocess,sys,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
base=Path('/opt/monitor/geo-content');backup=Path('/opt/monitor/geo-capture/maintenance/20261020-creation-search')
sys.path.insert(0,str(base));sys.path.insert(0,str(base/'engine'))
from creation import studio,runtime
legacy=next(v for v in studio.plans() if v.get('legacy_capture'))
assert not any(v.get('name')=='文心＋百度专用素材采集' for v in studio.plans()),'Already deployed'
assert all(not p.get('enabled') for p in studio.plans()),'Recheck active studio children before restarting'
assert not (base/'creation_search_pool.json').exists(),'Never overwrite operator pool settings'
backup.mkdir(parents=True,mode=0o700,exist_ok=False)
target=base/'creation/materials.py';shutil.copy2(target,backup/'materials.before.py')
source=Path('/tmp/creation-search-materials.py');compile(source.read_text(),str(target),'exec')
temp=target.with_suffix('.search-new');shutil.copy2(source,temp);temp.replace(target)
shutil.copy2('/tmp/creation-search-pool.json',base/'creation_search_pool.json')
owner=pwd.getpwnam('user');pool=base/'search-pool';pool.mkdir(mode=0o700,exist_ok=False);os.chown(pool,owner.pw_uid,owner.pw_gid)
today=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
result=studio.save_plan({'product_id':legacy['product_id'],'name':'文心＋百度专用素材采集','questions':legacy['questions'],'channels':['baidu_ai','wenxin_card'],'rounds':1,'capture_time':'01:00','writing_time':'04:00','start_date':today,'frequency':'daily','task_type':'capture_only','enabled':True,'max_per_category':1})
root=studio.capture_root(result['plan_id']);cfg=runtime.read(root/'settings.json');cfg['search_pool']='creation_only';runtime.atomic_json(root/'settings.json',cfg)
report={'at':time.time(),'plan_id':result['plan_id'],'questions':len(legacy['questions']),'rounds':1,'channels':cfg['channels'],'time':'01:00','task_type':'capture_only','scope':'creation_only','start_date':today,'root':str(root),'main_geo_untouched':True}
(backup/'deployment.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
subprocess.run(['systemctl','restart','geo-creation-studio.service'],check=True)
print(json.dumps(report,ensure_ascii=False))
