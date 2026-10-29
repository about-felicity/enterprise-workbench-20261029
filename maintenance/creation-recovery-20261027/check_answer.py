import json
from pathlib import Path
p=Path('/opt/monitor/geo-content/runtime/runs/creation-1793057266-6659e9ab/api/runs/92c41f44907a51b08d505b06/call/answer.json')
r=json.loads(p.read_text());print({k:v for k,v in r.items() if k!='content'})
try:
 a=json.loads(r['content']);print('valid',list(a),len(a.get('draft_markdown','')))
except Exception as e:print(type(e).__name__,str(e))
print(repr(r['content'][-900:]))
