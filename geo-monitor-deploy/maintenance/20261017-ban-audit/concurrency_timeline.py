import json,sqlite3,subprocess,time
from pathlib import Path
from datetime import datetime,timezone,timedelta
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-cleanup')
ZONE=timezone(timedelta(hours=8))
def stamp(t):return datetime.fromtimestamp(t,ZONE).isoformat()
units={'deepseek':'geo-native@geo-panel-deepseek-app-20261017-094524.service','deepseek2':'geo-native@geo-panel-deepseek2-20261017-134730-bf1a1e9e.service'}
paths={'deepseek':Path('/home/user/redroid-deepseek/batches/geo-panel-deepseek-app-20261017-094524/tasks.sqlite'),'deepseek2':Path('/home/user/redroid-deepseek-account2/batches/geo-panel-deepseek2-20261017-134730-bf1a1e9e/tasks.sqlite')}
events={}
for model,path in paths.items():
 with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
  db.execute('pragma query_only=on');events[model]=[r[0] for r in db.execute("select time from events where event='send_click_intent_committed' order by time")]
cutoff=min(events['deepseek2']);exits={}
for model,unit in units.items():
 raw=subprocess.check_output(['journalctl','-u',unit,'--since','2026-10-17 00:00:00 UTC','--no-pager','-o','json'],text=True,timeout=30)
 exits[model]=[stamp(int(v['__REALTIME_TIMESTAMP'])/1e6) for line in raw.splitlines() if (v:=json.loads(line)) and 'status=77/' in v.get('MESSAGE','')]
result={'at':stamp(time.time()),'first_primary_send':stamp(min(events['deepseek'])),'first_second_send':stamp(cutoff),'primary_send_intents_before_second':sum(t<cutoff for t in events['deepseek']),'primary_send_intents_after_second':sum(t>=cutoff for t in events['deepseek']),'exit77_times':exits,'causal_verdict':'Temporal association present; cannot establish causation without platform reason or a valid controlled comparison.','configuration_changed':False}
(ROOT/'concurrency.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
