import hashlib
import json
from pathlib import Path

BASE=Path('/opt/monitor/geo-capture/maintenance/20261015-unified')
manifest=json.loads((BASE/'current-manifest.json').read_text())
units={'geo-creation-materials.service','geo-creation-studio.service','geo-daily-dispatch.service','geo-daily-dispatch.timer','geo-daily-control.service','geo-deepseek-auth-check.service','geo-deepseek-auth-check.timer'}
extras={'/etc/systemd/system/geo-capture-deepseek.service.d/40-deepseek-android.conf','/etc/systemd/system/geo-web@.service.d/20-unattended.conf','/etc/systemd/system/geo-native@.service.d/20-unattended.conf','/etc/systemd/system/geo-daily-dispatch.timer.d/30-schedule.conf'}
result=[]
for item in manifest['files']:
    p=Path(item['server'])
    assert p.is_absolute() and (str(p).startswith(('/opt/monitor/','/home/user/redroid-')) or str(p) in extras or (str(p.parent)=='/etc/systemd/system' and p.name in units))
    result.append({'source':item['source'],'server':str(p),'matches':p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==item['sha256']})
report={'files':len(result),'matched':sum(x['matches'] for x in result),'mismatches':[x for x in result if not x['matches']]}
(BASE/'current-source-mapping.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
assert not report['mismatches']
