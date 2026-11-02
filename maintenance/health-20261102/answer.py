import json
from pathlib import Path
p=Path('/opt/monitor/geo-content/runtime/runs/creation-1793573228-f5e64267/api/runs/f35db76158e1fd6d726b8b32/call/answer.json')
print(p.read_text()[:16000])
