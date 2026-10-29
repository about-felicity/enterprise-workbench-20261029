
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from pathlib import Path
import shutil
import subprocess

p=Path('/usr/local/bin/monitor-live')
original=p.read_text()
old="COALESCE(record->>'status','')"
new="COALESCE(NULLIF(record->>'status',''),CASE WHEN model_id='doubao' AND length(COALESCE(record->>'answerText',''))>0 AND record->>'complete'='true' AND jsonb_array_length(CASE WHEN jsonb_typeof(record->'items')='array' THEN record->'items' ELSE '[]'::jsonb END)>0 THEN 'captured' ELSE 'unknown' END)"
if old not in original:
    raise SystemExit('Expected expression missing; inspect rather than editing blindly')
backup=Path('/usr/local/bin/monitor-live.before-doubao-status-20261013')
if backup.exists():raise SystemExit('Backup already exists; inspect current version')
shutil.copy2(p,backup)
candidate=p.with_name('monitor-live.status-update')
candidate.write_text(original.replace(old,new))
subprocess.run(['bash','-n',str(candidate)],check=True)
candidate.chmod(p.stat().st_mode)
candidate.replace(p)
print('Updated display fallback only; no database changes')
