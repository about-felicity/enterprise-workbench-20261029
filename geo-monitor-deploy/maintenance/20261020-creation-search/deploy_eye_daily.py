"""One-time deployment at an idle creation boundary. Keeps GEO and paused tasks untouched."""
import json,shutil,subprocess,zipfile
from pathlib import Path
base=Path('/opt/monitor/geo-content');backup=Path('/opt/monitor/geo-capture/maintenance/20261020-eye-daily')
def idle():
 for p in (base/'studio/capture').glob('*/health.json'):
  assert not json.loads(p.read_text()).get('active_channels'),str(p)
 for p in (base/'runtime/runs').glob('*/job.json'):
  root=p.parent;control=json.loads((root/'control.json').read_text())
  if control.get('paused'):continue
  day=json.loads(p.read_text())['date'];assert json.loads((root/'days'/day/'day.json').read_text()).get('status')=='complete'
idle();backup.mkdir(parents=True,exist_ok=False,mode=0o700)
subprocess.run(['systemctl','stop','geo-content-worker.service','geo-creation-studio.service'],check=True)
try:
 idle()
 with zipfile.ZipFile('/tmp/eye-daily-patch.zip') as z:
  for name in z.namelist():
   if name.startswith('tests/'):continue
   assert name.startswith(('creation/','engine/geo_source_cards/')) and '..' not in Path(name).parts
   target=base/name;old=backup/name
   if target.exists():old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,old)
   data=z.read(name)
   if name.endswith('.py'):compile(data,str(target),'exec')
   temp=target.with_suffix('.eye-new');temp.write_bytes(data);temp.replace(target)
finally:subprocess.run(['systemctl','start','geo-content-worker.service','geo-creation-studio.service'],check=True)
subprocess.run(['systemctl','restart','geo-content-api.service'],check=True)
print(json.dumps({'deployed':True,'backup':str(backup),'main_geo_untouched':True,'user_pauses_preserved':True}))
