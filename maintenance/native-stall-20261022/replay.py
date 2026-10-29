"""Reparse saved original Yuanbao response; no network or UI writes."""
import sys,json,hashlib,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');S=D/'stage'
sys.path[:0]=[str(S/'yuanbao'),str(S/'doubao')]
from native_core import parse_result
old=json.loads((D/'before.json').read_text());row=next(r for r in old['batches'] if r['model']=='yuanbao');task=row['task']
raw=json.loads((D/'yuanbao/before-native.json').read_text());binding=json.loads((D/'yuanbao/before-binding.json').read_text())
result=parse_result(task,binding,raw)
missing=[s for s in result['sources'] if s.get('title_missing')]
assert result['status']=='complete' and len(result['sources'])==48 and len(missing)==1
assert result['request_id']==task['request_id']
assert result['raw_source_entries']==[s['native_source'] for s in result['sources']]
out={'at':time.time(),'status':result['status'],'request_id':result['request_id'],'body_length':len(result['body_markdown']),
 'sources':len(result['sources']),'expected_sources':result['expected_source_count'],'explicit_missing_titles':len(missing),
 'body_sha256':hashlib.sha256(result['body_markdown'].encode()).hexdigest(),'new_questions_sent':0}
(D/'replay.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
