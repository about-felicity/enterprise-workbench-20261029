import json,shutil,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from geo_source_cards.runtime import process_lock
root=Path('/opt/monitor/geo-content/runtime/runs/creation-1792475798-7d2fc250')
with process_lock(root/'coordinator.lock'):
 original=root/'approved/2026-10-20/科普类/01'
 receipt=json.loads((original/'receipt.json').read_text());rev=json.loads((root/'revocations/processing-v1.json').read_text())
 assert receipt['word_sha256']==rev['word_sha256']
 destination=root/'quarantine/2026-10-20/科普类/processing-v1'
 assert not destination.exists();destination.parent.mkdir(parents=True,exist_ok=True)
 shutil.move(str(original),destination)
 (destination/'withdrawal.json').write_text(json.dumps(rev,ensure_ascii=False,indent=2))
print('Original wrong-genre test artifact retained in quarantine; revoked hash unchanged.')
