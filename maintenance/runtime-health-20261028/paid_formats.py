import json
from pathlib import Path
targets=[('creation-1793138057-6e622eb2','cd29d2f7bc299fabaf58c393'),('creation-1793142584-b167f637','947f38d5db6a07c71df5b2b3'),('creation-1793067139-f0f51240','c8d78ef69d4560ca45d77f9e')]
for job,run in targets:
 root=Path('/opt/monitor/geo-content/runtime/runs')/job/'api/runs'/run
 print('RUN',job,run)
 for p in root.rglob('response.json'):
  v=json.loads(p.read_text());print('RESPONSE',str(p.relative_to(root)),list(v) if isinstance(v,dict) else type(v).__name__)
  choices=v.get('choices',[]) if isinstance(v,dict) else []
  if choices:
   msg=choices[0].get('message',{});txt=msg.get('content','');print('FINISH',choices[0].get('finish_reason'),'LEN',len(txt),'EDGES',repr(txt[:180]),repr(txt[-180:]))
   try:
    body=json.loads(txt)
    print('JSON_TYPE',type(body).__name__)
    if isinstance(body,dict):
     print('FIELDS',list(body));print('FORBIDDEN',repr(body.get('forbidden_pattern')))
   except ValueError:print('INVALID_JSON')
  elif isinstance(v,dict):print('SHAPE',{k:(list(x) if isinstance(x,dict) else (str(x)[:180])) for k,x in v.items() if k not in {'usage'}})
