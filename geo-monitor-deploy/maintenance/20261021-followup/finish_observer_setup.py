"""Finalize baseline metadata from the pre-repair evidence, preserving its contents."""
import json
from pathlib import Path
import shutil
import sys
sys.path[:0] = ['/opt/monitor/geo-content', '/opt/monitor/geo-content/engine']
from creation import observation as o
from datetime import datetime
baseline_path = o.OUTPUT / 'baseline.json'
backup = o.OUTPUT / 'baseline-before-metadata.json'
if not backup.exists():shutil.copy2(baseline_path, backup)
baseline = o.read(baseline_path)
initial = json.loads(Path('/tmp/geo-followup-baseline-unknown.json').read_text())
current = o.collect(datetime.now(o.ZONE))
assert datetime.now(o.ZONE).date().isoformat() == '2026-10-21', 'Installation finalization is only valid before the observed overnight workload'
baseline.setdefault('unknown_request_ids', initial)
baseline['source_fingerprint'] = current['source_fingerprint']
baseline['setup_finalized_at'] = current['at']
baseline_path.write_text(json.dumps(baseline, ensure_ascii=False, indent=2))
o.main()
