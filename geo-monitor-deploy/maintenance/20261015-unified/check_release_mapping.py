import hashlib
import json
from pathlib import Path
manifest=json.loads(Path('/tmp/geo-unified-manifest.json').read_text())
result=[]
for item in manifest['files']:
    path=Path(item['server'])
    assert path.is_absolute() and (str(path).startswith('/opt/monitor/') or str(path).startswith('/home/user/redroid-') or str(path) in {'/etc/systemd/system/geo-creation-materials.service','/etc/systemd/system/geo-creation-studio.service','/etc/systemd/system/geo-capture-deepseek.service.d/40-deepseek-android.conf'}
        or str(path) in {'/etc/systemd/system/geo-daily-dispatch.service','/etc/systemd/system/geo-daily-dispatch.timer','/etc/systemd/system/geo-daily-control.service',
                         '/etc/systemd/system/geo-web@.service.d/20-unattended.conf','/etc/systemd/system/geo-native@.service.d/20-unattended.conf','/etc/systemd/system/geo-daily-dispatch.timer.d/30-schedule.conf'})
    digest=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
    result.append({'source':item['source'],'server':str(path),'matches':digest==item['sha256']})
report={'files':len(result),'matched':sum(x['matches'] for x in result),'mismatches':[x for x in result if not x['matches']]}
target=Path('/opt/monitor/geo-capture/maintenance/20261015-unified/current-source-mapping.json')
target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
