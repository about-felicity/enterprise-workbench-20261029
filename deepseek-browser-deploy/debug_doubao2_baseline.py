import sys,json,sqlite3,traceback
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_core import baseline
from unattended_worker import databases
paths=databases('doubao-hpe14-account2')
for p in paths:
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as d:
  cols={r[1] for r in d.execute('pragma table_info(im_message)')}
  print(json.dumps({'file':p.name[:30],'columns':len(cols),'compatible':{'local_message_id','conversation_id','user_type','content','local_index'}.issubset(cols)}))
try: baseline(paths,'推荐一款防脱精华液');print('baseline_ok')
except Exception:traceback.print_exc()
