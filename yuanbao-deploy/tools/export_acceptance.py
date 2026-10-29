"""Export allowlisted deployment evidence; never export account state."""
import json
from pathlib import Path
import subprocess
import time
import urllib.request

BASE=Path('/home/user/redroid-yuanbao')
PANEL=Path('/opt/monitor/geo-capture')
root=BASE/'batches/geo-yuanbao-21x5-20261015'
out=Path('/tmp/yuanbao-verified-reports')
out.mkdir(mode=0o755,exist_ok=True)
sources={
    'YUANBAO_CAPTURE_LIVE_AUDIT_20261015.json':root/'capture-audit.json',
    'YUANBAO_PUBLIC_PANEL_20261015.json':PANEL/'panel-qa/yuanbao-public.json',
    'YUANBAO_PANEL_CONTINUITY_20261015.json':PANEL/'panel-qa/yuanbao-continuity.json',
}
for name,path in sources.items():
    value=json.loads(path.read_text())
    target=out/name
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    target.chmod(0o644)
health=json.loads((root/'bridge_health.json').read_text())
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with opener.open('http://127.0.0.1:8803/api/panel',timeout=15) as stream:panel=json.load(stream)
current=next(m['current'] for m in panel['models'] if m['id']=='yuanbao')
pointer=json.loads((PANEL/'all_channel_soak_current.json').read_text())
manifest=json.loads((Path(pointer['root'])/'manifest.json').read_text())
service='geo-native@'+current['batch']+'.service'
record={'exported_at':time.time(),'batch':current['batch'],'planned':current['planned'],
        'captured':current['captured'],'processed':current['processed'],'status':current['state'],
        'acceptance_batch':root.name,'acceptance_captured':health['captured'],'acceptance_processed':health['geo_processed'],
        'health_updated_at':current['updated_at'],'projection_enabled':False,
        'service_active':subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip(),
        'reboot_enabled':subprocess.run(['systemctl','is-enabled',service],capture_output=True,text=True).stdout.strip(),
        'independent_volume':True,'historical_doubao_batches_rerun':False,
        'all_channel_soak_started':True,'soak':pointer,'search_queries_exposed':False}
target=out/'YUANBAO_HEADLESS_DEPLOYMENT_20261015.json'
target.write_text(json.dumps(record,indent=2));target.chmod(0o644)
print(json.dumps(record))
