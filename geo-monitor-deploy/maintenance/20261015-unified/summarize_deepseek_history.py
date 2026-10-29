import json
from pathlib import Path
data=json.loads(Path('/tmp/geo-deepseek-reconciliation-17920612/history.json').read_text())
def walk(value,depth=0):
    if isinstance(value,dict):
        return {key:walk(item,depth+1) for key,item in value.items() if not any(word in key.lower() for word in ['token','cookie','secret','phone','email','user','password'])}
    if isinstance(value,list):return [walk(item,depth+1) for item in value[:7]]
    return value
for entry in data['responses']:
    if entry.get('body'):print(json.dumps({'path':entry['path'],'body':walk(entry['body'])},ensure_ascii=False))
