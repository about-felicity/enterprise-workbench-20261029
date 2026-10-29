import json
from pathlib import Path
v=json.loads(Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015/native-getters-first.json').read_text())
print(json.dumps({'last':{k:v['last'].get(k) for k in ['id','serverId','serverIndex','pairId','serverPairId','speaker','state','contentCount','createTime','dataSource']},'message':{k:v['message'].get(k) for k in ['id','serverId','contentCount']}}))
