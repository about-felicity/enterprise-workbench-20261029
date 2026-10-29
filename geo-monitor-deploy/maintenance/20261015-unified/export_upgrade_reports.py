"""Allowlisted sanitized evidence only, suitable for local review."""
import json
from pathlib import Path
import shutil
import time
base=Path('/opt/monitor/geo-capture');source=base/'maintenance/20261015-unified'
dest=Path('/tmp/geo-unified-export-20261015');dest.mkdir(mode=0o755,exist_ok=True)
names=['analysis-audit.json','creation-acceptance-report.json','creation-preview-qa.json','creation-public-qa.json','server-cleanup.json','creation-source-readiness.json']
for name in names:
    if (source/name).is_file():shutil.copy2(source/name,dest/name);(dest/name).chmod(0o644)
for pointer_name,label in [('soak12h_current.json','capture-12h'),('creation_soak_current.json','creation-6h')]:
    pointer=json.loads((base/pointer_name).read_text());root=Path(pointer['root']);status=json.loads((root/'status.json').read_text())
    (dest/(label+'-start-status.json')).write_text(json.dumps({'pointer':pointer,'snapshot':status},ensure_ascii=False,indent=2));(dest/(label+'-start-status.json')).chmod(0o644)
history=source/'doubao-history-summary.json'
if history.is_file():shutil.copy2(history,dest/history.name);(dest/history.name).chmod(0o644)
fidelity=source/'native-body-layer-audit.json'
if fidelity.is_file():
    # Report was produced by a read-only fixed-schema audit, no auth material.
    value=json.loads(fidelity.read_text());(dest/fidelity.name).write_text(json.dumps(value,ensure_ascii=False,indent=2));(dest/fidelity.name).chmod(0o644)
release=json.loads((base/'analysis_display_release.json').read_text())
safe={'at':release['at'],'source_sha256':release['source_sha256'],'api_restart_before':release['api_restart_before'],'api_restart_after':release['api_restart_after'],'retest':release['retest'],'scope':'Only analysis API restarted for authorized fix; capture jobs unchanged.'}
(dest/'analysis-display-release.json').write_text(json.dumps(safe,indent=2));(dest/'analysis-display-release.json').chmod(0o644)
for name in ['creation-public.png']:
    if (source/name).exists():shutil.copy2(source/name,dest/name);(dest/name).chmod(0o644)
print(json.dumps({'exported':[p.name for p in dest.iterdir()],'at':time.time()}))
